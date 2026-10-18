"""Versioned, offline legacy image pipeline. Never writes a caller's source."""
import copy, hashlib, io, json, math, os, platform, struct, tempfile, threading, uuid, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, IptcImagePlugin, features, __version__ as pillow_version

VERSION = 1
DEFAULT = dict(schema_version=1, pipeline_version=1, profile='legacy_compatible', seed=0,
 effects=dict(enhance=dict(enabled=False,blur=5,sharpen=100,contrast_pct=5), color=dict(enabled=False,hue_deg=0,saturation_pct=0,value_pct=0),border=dict(enabled=False,width_px=5,style='solid'),noise=dict(enabled=False,strength=10),rotation=dict(enabled=False,angle_deg=15,direction='right'),flip=dict(enabled=False,direction='horizontal'),scale=dict(enabled=False,percent=105),metadata=dict(enabled=False)),
 encoding=dict(jpeg_quality=95,jpeg_subsampling=2,jpeg_optimize=False,jpeg_progressive=False,png_compress_level=6,webp_lossless=True,webp_quality=90),io=dict(write_source_processed=True,preview_disk_side_effects=True,collision_policy='overwrite',open_output_when_done=True))
RANGES={'blur':(0,100),'sharpen':(0,500),'contrast_pct':(-100,100),'hue_deg':(-180,180),'saturation_pct':(-100,100),'value_pct':(-100,100),'width_px':(0,200),'strength':(0,100),'angle_deg':(0,180),'percent':(100,200),'jpeg_quality':(1,95),'jpeg_subsampling':(0,2),'png_compress_level':(0,9),'webp_quality':(0,100)}
class Error(ValueError):
 def __init__(self,code,message=''): self.code=code;super().__init__(message or code)
def validate(raw):
 def merge(base,patch):
  if not isinstance(patch,dict): raise Error('INVALID_CONFIG','配置必须是对象')
  if set(patch)-set(base): raise Error('INVALID_CONFIG','未知字段: '+','.join(set(patch)-set(base)))
  result=copy.deepcopy(base)
  for k,v in patch.items():
   d=base[k]
   if isinstance(d,dict): result[k]=merge(d,v);continue
   if k=='profile' and v!='legacy_compatible': raise Error('UNSUPPORTED_PROFILE')
   if k=='seed':
    if isinstance(v,str) and v.isascii() and v.isdecimal(): v=int(v)
    if type(v)!=int or not 0<=v<2**64: raise Error('INVALID_CONFIG','seed需为uint64十进制整数')
   elif type(v)!=type(d): raise Error('INVALID_CONFIG',k+'类型错误')
   if k in RANGES and not RANGES[k][0]<=v<=RANGES[k][1]: raise Error('INVALID_CONFIG',k+'越界')
   if k in ['schema_version','pipeline_version'] and v!=1: raise Error('INVALID_CONFIG','不支持的版本')
   if k=='style' and v not in ['solid','gradient']: raise Error('INVALID_CONFIG','边框样式错误')
   if k=='direction' and v not in (['left','right'] if d=='right' else ['horizontal','vertical']): raise Error('INVALID_CONFIG','方向错误')
   if k=='collision_policy' and v not in ['overwrite','skip','rename']: raise Error('INVALID_CONFIG','碰撞策略错误')
   result[k]=v
  return result
 return merge(DEFAULT,raw)
def check(cancel):
 if cancel and cancel.is_set(): raise Error('CANCELLED')
def sha(data): return hashlib.sha256(data).hexdigest()
def rng(seed,fingerprint,effect):
 payload=('image-dedup/v1\0'+str(seed)+'\0'+fingerprint+'\0'+effect).encode()
 return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(payload).digest()[:16],'big')))
def q(x): return np.clip(np.floor(x+.5),0,255).astype(np.uint8)
def load(path):
 path=Path(path)
 if not path.is_file(): raise Error('FILE_NOT_FOUND')
 if path.stat().st_size>512*1024*1024: raise Error('IMAGE_TOO_LARGE')
 data=path.read_bytes(); suffix=path.suffix.lower()
 if suffix=='.webp': raise Error('FORMAT_NOT_IMPLEMENTED')
 expected={'.png':'PNG','.jpg':'JPEG','.jpeg':'JPEG'}.get(suffix)
 if not expected: raise Error('FORMAT_NOT_IMPLEMENTED')
 try:
  with Image.open(io.BytesIO(data)) as im:
   if im.format!=expected: raise Error('FORMAT_MISMATCH')
   if im.width*im.height>40_000_000 or max(im.size)>20000: raise Error('IMAGE_TOO_LARGE')
   if getattr(im,'n_frames',1)!=1: raise Error('ANIMATED_NOT_SUPPORTED')
   if im.mode not in ['RGB','RGBA','L','LA','P','CMYK']: raise Error('UNSUPPORTED_IMAGE_MODE')
   im.load(); warnings=[]
   if im.mode in ['RGBA','LA'] or 'transparency' in im.info: warnings.append('ALPHA_DROPPED')
   if im.getexif().get(274,1)!=1: warnings.append('ORIENTATION_IGNORED')
   if im.mode=='CMYK': warnings.append('CMYK_CONVERTED_WITHOUT_COLOR_MANAGEMENT')
   if im.mode=='P': im=im.convert('RGBA')
   rgb=Image.fromarray(np.array(im.convert('RGB')))
 except Error: raise
 except Image.DecompressionBombError: raise Error('IMAGE_TOO_LARGE')
 except Exception as e: raise Error('DECODE_FAILED',str(e))
 return rgb,dict(sha256=sha(data),size_bytes=len(data),mtime_ns=path.stat().st_mtime_ns),expected,warnings

def transform(image, fingerprint, config, cancel=None):
 c=validate(config);e=c['effects']; im=image.copy();check(cancel)
 n=e['noise']
 if n['enabled'] and n['strength']: im=Image.fromarray(q(np.asarray(im,dtype=np.float64)+rng(c['seed'],fingerprint,'noise').normal(0,8*n['strength']/100,np.asarray(im).shape)))
 check(cancel)
 f=e['flip']
 if f['enabled']: im=ImageOps.mirror(im) if f['direction']=='horizontal' else ImageOps.flip(im)
 check(cancel)
 r=e['rotation']
 if r['enabled'] and r['angle_deg']: im=im.rotate(r['angle_deg']*(1 if r['direction']=='left' else -1),resample=Image.Resampling.BICUBIC,expand=True,fillcolor=(255,255,255))
 check(cancel)
 s=e['scale']
 if s['enabled'] and s['percent']!=100:
  w,h=im.size; nw,nh=[max(v,math.floor(v*s['percent']/100+.5)) for v in (w,h)];im=im.resize((nw,nh),Image.Resampling.LANCZOS).crop(((nw-w)//2,(nh-h)//2,(nw-w)//2+w,(nh-h)//2+h))
 check(cancel)
 col=e['color']
 if col['enabled'] and any(col[k] for k in ['hue_deg','saturation_pct','value_pct']):
  a=np.asarray(im,dtype=np.float64)/255;r,g,b=np.moveaxis(a,-1,0);mx=a.max(-1);mn=a.min(-1);d=mx-mn; nz=d!=0;h=np.zeros(mx.shape);sat=np.divide(d,mx,out=np.zeros_like(d),where=mx!=0)
  masks=[nz&(mx==r),nz&(mx!=r)&(mx==g),nz&(mx!=r)&(mx!=g)]
  for mask,num,offset in zip(masks,[g-b,b-r,r-g],[0,2,4]): h[mask]=(num[mask]/d[mask]+offset)%6/6
  h=(h+col['hue_deg']/360)%1;sat=np.clip(sat*(1+col['saturation_pct']/100),0,1);v=np.clip(mx*(1+col['value_pct']/100),0,1);h6=h*6;i=np.floor(h6).astype(int)%6;f=h6-np.floor(h6);p=v*(1-sat);qq=v*(1-f*sat);t=v*(1-(1-f)*sat);out=np.empty_like(a)
  for j,channels in enumerate([(v,t,p),(qq,v,p),(p,v,t),(p,qq,v),(t,p,v),(v,p,qq)]): out[i==j]=np.stack(channels,-1)[i==j]
  im=Image.fromarray(q(out*255))
 check(cancel)
 b=e['border']
 if b['enabled'] and b['width_px']:
  bw=b['width_px'];w,h=im.size;w+=2*bw;h+=2*bw;gen=rng(c['seed'],fingerprint,'border');c0=gen.integers(0,256,3)
  if b['style']=='solid': a=np.broadcast_to(c0,(h,w,3)).astype(np.uint8).copy()
  else:
   c1=gen.integers(0,256,3);direction=gen.integers(0,3);x=np.broadcast_to(np.arange(w)[None,:]/max(w-1,1),(h,w));y=np.broadcast_to(np.arange(h)[:,None]/max(h-1,1),(h,w));t=[x,y,(x+y)/2][direction][...,None];a=q((1-t)*c0+t*c1)
  a[bw:h-bw,bw:w-bw]=np.asarray(im);im=Image.fromarray(a)
 check(cancel)
 en=e['enhance']
 if en['enabled']:
  if en['blur']: im=im.filter(ImageFilter.GaussianBlur(en['blur']/10))
  check(cancel)
  if en['sharpen']: im=im.filter(ImageFilter.UnsharpMask(radius=2,percent=en['sharpen'],threshold=3))
  check(cancel)
  if en['contrast_pct']: im=ImageEnhance.Contrast(im).enhance(1+en['contrast_pct']/100)
 check(cancel);return im

def structure(data,fmt):
 if fmt=='PNG':
  if not data.startswith(b'\x89PNG\r\n\x1a\n'): raise Error('DECODE_FAILED','无效PNG签名')
  names=[];pos=8
  while pos<len(data):
   if pos+12>len(data): raise Error('DECODE_FAILED','PNG区块被截断')
   size=int.from_bytes(data[pos:pos+4],'big')
   if pos+12+size>len(data): raise Error('DECODE_FAILED','PNG区块长度越界')
   kind=data[pos+4:pos+8];payload=data[pos+8:pos+8+size];crc=int.from_bytes(data[pos+8+size:pos+12+size],'big')
   if zlib.crc32(kind+payload)&0xffffffff!=crc: raise Error('DECODE_FAILED','PNG CRC不符')
   name=kind.decode('ascii');names.append(name);pos+=size+12
   if name=='IEND':
    if size or pos!=len(data): raise Error('DECODE_FAILED','无效PNG结束区块')
    return names
  raise Error('DECODE_FAILED','缺少PNG结束区块')
 if fmt!='JPEG' or not data.startswith(b'\xff\xd8'): raise Error('DECODE_FAILED','无效JPEG签名')
 names=[];pos=2
 while pos<len(data):
  if data[pos]!=255: raise Error('DECODE_FAILED','无效JPEG标记')
  while pos<len(data) and data[pos]==255: pos+=1
  if pos>=len(data): raise Error('DECODE_FAILED','JPEG标记截断')
  marker=data[pos];pos+=1;names.append(f'{marker:02X}')
  if marker==0xD9: return names
  if pos+2>len(data): raise Error('DECODE_FAILED','JPEG长度截断')
  size=int.from_bytes(data[pos:pos+2],'big')
  if size<2 or pos+size>len(data): raise Error('DECODE_FAILED','JPEG段长度越界')
  pos+=size
  if marker==0xDA:
   # Validate entropy-coded scan marker escapes, restart markers and EOI.
   while pos<len(data)-1:
    if data[pos]!=255: pos+=1;continue
    code=data[pos+1]
    if code==0 or 0xD0<=code<=0xD7: pos+=2;continue
    if code==255: pos+=1;continue
    if code==0xD9: names.append('D9');return names
    break
   if pos>=len(data)-1: raise Error('DECODE_FAILED','JPEG扫描数据截断')
 return names

def encode(im,fmt,c):
 check(None);buf=io.BytesIO();enc=c['encoding']
 try:
  clean=Image.fromarray(np.asarray(im))
  if fmt=='PNG': clean.save(buf,format=fmt,compress_level=enc['png_compress_level'])
  else: clean.save(buf,format=fmt,quality=enc['jpeg_quality'],subsampling=enc['jpeg_subsampling'],optimize=enc['jpeg_optimize'],progressive=enc['jpeg_progressive'])
 except Exception as e: raise Error('ENCODE_FAILED',str(e))
 data=buf.getvalue()
 if c['effects']['metadata']['enabled']:
  markers=structure(data,fmt)
  if (fmt=='PNG' and set(markers)-{'IHDR','IDAT','IEND'}) or (fmt=='JPEG' and set(markers)&{'E1','E2','ED','FE'}): raise Error('METADATA_VERIFY_FAILED')
 return data

def inspect(path):
 data=Path(path).read_bytes()
 with Image.open(io.BytesIO(data)) as im:
  im.load();ex=im.getexif();markers=structure(data,im.format);iptc=IptcImagePlugin.getiptcinfo(im) if im.format=='JPEG' else None
  return dict(format=im.format,width=im.width,height=im.height,mode=im.mode,alpha='A' in im.mode or 'transparency' in im.info,orientation=ex.get(274),exif_count=len(ex),gps_count=len(ex.get_ifd(34853)) if 34853 in ex else 0,icc=bool(im.info.get('icc_profile')),xmp=bool(im.info.get('xmp')) or 'XML:com.adobe.xmp' in im.info,iptc=bool(iptc),iptc_count=len(iptc or {}),app13_present='ED' in markers,comment='FE' in markers,png_text=any(x in markers for x in ['tEXt','zTXt','iTXt']),markers=markers,sha256=sha(data))

def atomic(path,data,policy,cancel,inputs,guard=None):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.resolve() in inputs: raise Error('WOULD_OVERWRITE_INPUT')
 fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as stream: stream.write(data);stream.flush();os.fsync(stream.fileno())
  check(cancel)
  if guard: guard()
  if path.resolve() in inputs: raise Error('WOULD_OVERWRITE_INPUT')
  if policy=='overwrite': os.replace(tmp,path)
  else: os.link(tmp,path);os.unlink(tmp)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

def environment(): return dict(python=platform.python_version(),pillow=pillow_version,numpy=np.__version__,libjpeg=features.version_codec('jpg'),libwebp=features.version_module('webp'),system=platform.platform(),pipeline_version=1)
def batch(inputs,output_dir,config,emit=lambda e:None,cancel=None,job_id=None,protected_inputs=None,original_sources=None):
 c=validate(config);cancel=cancel or threading.Event();jid=job_id or uuid.uuid4().hex;out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True);paths=list(dict.fromkeys(Path(x).resolve() for x in inputs));protected=set(paths)|{Path(x).resolve() for x in (protected_inputs or [])};reserved=set();items=[];seq=0
 fingerprints={};intermediate_owners={};intermediate_conflicts=set()
 for source in paths:
  intermediate_key=str((source.parent/'processed'/('processed_'+source.name)).resolve()).casefold()
  if intermediate_key in intermediate_owners: intermediate_conflicts.add(source)
  else: intermediate_owners[intermediate_key]=source
  try: fingerprints[source]=sha(source.read_bytes())
  except OSError: pass
 def verify(source):
  if source not in fingerprints:
   if not source.is_file(): raise Error('FILE_NOT_FOUND')
   raise Error('SOURCE_CHANGED')
  try: current=sha(source.read_bytes())
  except OSError: raise Error('SOURCE_CHANGED')
  if current!=fingerprints[source]: raise Error('SOURCE_CHANGED')
 def event(kind,**kw):
  nonlocal seq
  seq+=1;emit(dict(event_schema_version=1,seq=seq,type=kind,job_id=jid,**kw))
 event('job_started',total=len(paths),profile=c['profile']);attempted=0
 for index,src in enumerate(paths):
  target=out/('processed_'+src.name);item=dict(source=str(src),original_source=(original_sources or {}).get(str(src),str(src)),output=str(target),status='error',warnings=[],intermediate_committed=False,final_committed=False)
  try:
   check(cancel)
   if c['io']['write_source_processed'] and src in intermediate_conflicts: raise Error('DUPLICATE_OUTPUT_NAME','中间路径冲突')
   if target.resolve() in protected: raise Error('WOULD_OVERWRITE_INPUT')
   policy=c['io']['collision_policy']
   if policy=='skip' and (target.exists() or str(target).casefold() in reserved): item['status']='skipped';items.append(item);event('item_completed',index=index,**item);continue
   if policy=='overwrite' and str(target).casefold() in reserved: raise Error('DUPLICATE_OUTPUT_NAME')
   if policy=='rename':
    n=2
    while target.exists() or str(target).casefold() in reserved: target=out/(f'processed_{src.stem}_{n}'+src.suffix);n+=1
   reserved.add(str(target).casefold());item['output']=str(target);attempted+=1;event('item_started',index=index,source=str(src))
   verify(src);im,fp,fmt,warnings=load(src);item.update(source_fingerprint=fp,original_source_sha256=fp['sha256'],warnings=warnings);check(cancel);result=transform(im,fp['sha256'],c,cancel);encoded=encode(result,fmt,c);check(cancel)
   verify(src)
   intermediate=src.parent/'processed'/('processed_'+src.name)
   if c['io']['write_source_processed']:
    item['intermediate']=str(intermediate)
    if intermediate.resolve().parent==out: item['intermediate_aliases_final']=True
    else:
     verify(src);atomic(intermediate,encoded,'overwrite',cancel,protected,lambda:verify(src));item['intermediate_committed']=True;event('stage_completed',index=index,stage='intermediate',path=str(intermediate),metadata_verified=c['effects']['metadata']['enabled'])
   try:
    verify(src);atomic(target,encoded,policy,cancel,protected,lambda:verify(src))
   except FileExistsError:
    if policy=='skip': item['status']='skipped';items.append(item);event('item_completed',index=index,**item);continue
    if policy!='rename': raise
    n=2
    while True:
     target=out/(f'processed_{src.stem}_{n}'+src.suffix);n+=1
     try:
      verify(src);atomic(target,encoded,'rename',cancel,protected,lambda:verify(src));reserved.add(str(target).casefold());break
     except FileExistsError: continue
    item['output']=str(target)
   if item.get('intermediate_aliases_final'): item['intermediate_committed']=True
   item.update(status='success',final_committed=True,width=result.width,height=result.height,mode=result.mode,sha256=sha(encoded),seed=c['seed'],metadata_verified=c['effects']['metadata']['enabled']);event('stage_completed',index=index,stage='final',path=str(target),metadata_verified=c['effects']['metadata']['enabled'])
  except Exception as exc:
   code=getattr(exc,'code',None) or ({13:'OUTPUT_PERMISSION_DENIED',28:'DISK_FULL',16:'OUTPUT_BUSY'}.get(getattr(exc,'errno',None),'INTERNAL_ERROR'));item.update(status='cancelled' if code=='CANCELLED' else 'error',error_code=code,message=str(exc))
  items.append(item);event('item_completed',index=index,**item)
 counts={key:sum(x['status']==status for x in items) for key,status in [('succeeded','success'),('failed','error'),('skipped','skipped'),('cancelled','cancelled')]};status='cancelled' if counts['cancelled'] else 'error' if counts['failed'] else 'success'
 manifest=out/f'job-{jid}.json';result=dict(schema_version=1,job_id=jid,status=status,total=len(paths),attempted=attempted,**counts,resolved_config=c,environment=environment(),items=items,manifest=str(manifest));atomic(manifest,json.dumps(result,ensure_ascii=False,indent=2).encode(),'overwrite',None,protected);event('job_finished',**{k:result[k] for k in ['status','total','attempted','succeeded','failed','skipped','cancelled','manifest']});return result


def strip_metadata(path):
 """Remove metadata losslessly; keep encoded pixels and PNG alpha unchanged."""
 path=Path(path);data=path.read_bytes()
 fmt='PNG' if data.startswith(b'\x89PNG') else 'JPEG'
 structure(data,fmt)  # Use the same structural validation as metadata mode.
 if fmt=='PNG':
  chunks=[data[:8]];pos=8
  while pos<len(data):
   size=int.from_bytes(data[pos:pos+4],'big');end=pos+12+size
   if data[pos+4:pos+8] in (b'IHDR',b'PLTE',b'tRNS',b'IDAT',b'IEND'):chunks.append(data[pos:end])
   pos=end
  cleaned=b''.join(chunks)
 else:
  chunks=[data[:2]];pos=2
  while pos<len(data):
   start=pos
   while data[pos]==255:pos+=1
   marker=data[pos];pos+=1
   if marker in (0xDA,0xD9):
    chunks.append(data[start:]);break
   size=int.from_bytes(data[pos:pos+2],'big');end=pos+size
   if not (0xE1<=marker<=0xEF or marker==0xFE):chunks.append(data[start:end])
   pos=end
  cleaned=b''.join(chunks)
 markers=structure(cleaned,fmt)
 if (fmt=='PNG' and set(markers)-{'IHDR','PLTE','tRNS','IDAT','IEND'}) or (fmt=='JPEG' and set(markers)&{*(f'{x:02X}' for x in range(0xE1,0xF0)),'FE'}):
  raise Error('METADATA_VERIFY_FAILED')
 if cleaned!=data:atomic(path,cleaned,'overwrite',None,set())
 return True
