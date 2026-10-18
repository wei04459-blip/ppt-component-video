"""HTTP adapter: all writes stay inside imported copies and isolated exports."""
import base64, copy, io, json, os, secrets, threading, time, uuid, zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from image_dedup import core
POOL=ThreadPoolExecutor(max_workers=1);PREVIEW_LOCK=threading.Lock();LATEST={};CACHE={};JOBS={};LOCK=threading.RLock()
def root(app):
 p=app.DATA/'image-tools';p.mkdir(exist_ok=True);return p
def session(app,sid):
 if not isinstance(sid,str) or len(sid)!=32 or any(c not in '0123456789abcdef' for c in sid): raise core.Error('INVALID_CONFIG','无效图片会话')
 p=root(app)/sid
 if not (p/'session.json').is_file(): raise core.Error('INVALID_CONFIG','图片会话不存在')
 return p
def state(p): return json.loads((p/'session.json').read_text())
def url(app,p): return app.file_url(p)
def presets_path(app): return root(app)/'presets.json'
def validate_presets(doc):
 if not isinstance(doc,dict) or set(doc)!={'preset_schema_version','presets','selected_id'} or doc['preset_schema_version']!=1 or not isinstance(doc['presets'],list): raise core.Error('INVALID_CONFIG','预设文件无效')
 ids=set();names=set()
 for entry in doc['presets']:
  if set(entry)!={'id','name','config'} or not isinstance(entry['id'],str) or not isinstance(entry['name'],str) or not entry['name'].strip() or entry['id'] in ids or entry['name'] in names: raise core.Error('INVALID_CONFIG','预设重复或字段无效')
  entry['config']=core.validate(entry['config']);ids.add(entry['id']);names.add(entry['name'])
 if doc['selected_id'] is not None and doc['selected_id'] not in ids: raise core.Error('INVALID_CONFIG','选中预设不存在')
 return doc
def get_presets(app):
 p=presets_path(app);warning=None
 if p.exists():
  try: return validate_presets(json.loads(p.read_text())),warning
  except Exception:
   backup=p.with_name(f'presets.bad-{time.time_ns()}.json');os.link(p,backup);backup.chmod(0o444);p.unlink();warning='损坏预设已保留为只读备份，已使用空预设。'
 return dict(preset_schema_version=1,presets=[],selected_id=None),warning

def transport(value):
 value=copy.deepcopy(value)
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k=='seed': x[k]=str(v)
    else: walk(v)
  elif isinstance(x,list):
   for v in x: walk(v)
 walk(value);return value
def handle(app,action,data):
 if action=='defaults':
  presets,warning=get_presets(app);return dict(config=transport(core.DEFAULT),presets=transport(presets),warning=warning,environment=core.environment())
 if action=='presets':
  doc=validate_presets(copy.deepcopy(data['document']));app.write_json(presets_path(app),doc);return dict(ok=True,document=transport(doc))
 if action=='status':
  job=JOBS.get(data['job'])
  if not job: raise core.Error('INVALID_CONFIG','任务不存在')
  with LOCK: return {k:v for k,v in job.items() if k!='cancel_event'}
 if action=='cancel':
  JOBS[data['job']]['cancel_event'].set();return dict(ok=True,message='正在取消，等待当前步骤结束')
 if action in ['import','preview','export'] and any(j.get('session')==data.get('session') and j['status']=='running' for j in JOBS.values()): raise core.Error('INVALID_CONFIG','当前会话正在导出，请等待或取消')
 if action=='import':
  sid=data.get('session') or uuid.uuid4().hex;p=session(app,sid) if data.get('session') else root(app)/sid
  if not p.exists(): p.mkdir();app.write_json(p/'session.json',dict(files=[]))
  s=state(p);seen={(f['name'],f['sha256']) for f in s['files']};added=[];errors=[];skipped=0
  for f in data.get('files',[]):
   name=Path(f['name'].replace('\\','/')).name
   try:
    raw=base64.b64decode(f['data'],validate=True);fingerprint=core.sha(raw)
    if (name,fingerprint) in seen: skipped+=1;continue
    iid=uuid.uuid4().hex;dest=p/'imports'/iid/name;dest.parent.mkdir(parents=True);dest.write_bytes(raw)
    im,fp,fmt,warnings=core.load(dest);original=dest.parent/'preview-assets'/'original.png';original.parent.mkdir();im.save(original)
    entry=dict(id=iid,name=name,sha256=fingerprint,path=str(dest),original=url(app,original),width=im.width,height=im.height,warnings=warnings);s['files'].append(entry);added.append(entry);seen.add((name,fingerprint))
   except Exception as exc: errors.append(dict(name=name,error_code=getattr(exc,'code','DECODE_FAILED'),message=str(exc)))
  app.write_json(p/'session.json',s);return dict(session=sid,files=s['files'],added=len(added),skipped=skipped,errors=errors)
 p=session(app,data['session']);s=state(p);c=core.validate(data.get('config',{}))
 if action=='preview':
  f=next(x for x in s['files'] if x['id']==data['image']);src=Path(f['path']);key=(data['session'],f['id']);generation=data.get('generation',0)
  with LOCK: LATEST[key]=max(generation,LATEST.get(key,-1))
  with PREVIEW_LOCK:
   if LATEST[key]!=generation: return dict(stale=True,generation=generation)
   im,fp,fmt,warnings=core.load(src);cachekey=(fp['sha256'],json.dumps(c,sort_keys=True))
   if cachekey in CACHE: result,encoded=CACHE[cachekey]
   else:
    result=core.transform(im,fp['sha256'],c);encoded=core.encode(result,fmt,c);CACHE.clear();CACHE[cachekey]=(result,encoded)
  if LATEST.get((data['session'],f['id']))!=generation: return dict(stale=True,generation=generation)
  # Each response has its own URL; frontend generation guard prevents stale display.
  preview=p/'previews'/(uuid.uuid4().hex+'.png');preview.parent.mkdir(exist_ok=True);result.save(preview)
  if c['io']['write_source_processed'] and c['io']['preview_disk_side_effects']:
   # Serial generation watermark protects the fixed intermediate from stale requests.
   with LOCK:
    versions=s.setdefault('preview_versions',{});key=f['id'];current=state(p);versions=current.setdefault('preview_versions',{});generation=data.get('generation',0)
    if generation>=versions.get(key,-1) and LATEST.get((data['session'],f['id']))==generation and not any(j.get('session')==data['session'] and j['status']=='running' for j in JOBS.values()):
     try:
      core.atomic(src.parent/'processed'/('processed_'+src.name),encoded,'overwrite',None,{src.resolve()});versions[key]=generation;app.write_json(p/'session.json',current)
     except OSError as exc: warnings.append('PREVIEW_INTERMEDIATE_WRITE_FAILED: '+str(exc))
  return dict(preview=url(app,preview),generation=data.get('generation'),width=result.width,height=result.height,warnings=warnings,pixel_sha256=core.sha(result.tobytes()),metadata_verified=c['effects']['metadata']['enabled'])
 if action=='export':
  if not s['files']: raise core.Error('INVALID_CONFIG','请先导入图片')
  jid=uuid.uuid4().hex;out=p/'exports'/jid;cancel=threading.Event();job=dict(id=jid,session=data['session'],status='running',events=[],cancel_event=cancel,total=len(s['files']));JOBS[jid]=job;frozen=copy.deepcopy(c)
  with LOCK:
   for file in s['files']: LATEST[(data['session'],file['id'])]=2**63
  def run():
   def emit(e):
    with LOCK: job['events'].append(e)
   try:
    with PREVIEW_LOCK:
     result=core.batch([x['path'] for x in s['files']],out,frozen,emit,cancel,jid)
    with LOCK:
     for file in s['files']: LATEST.pop((data['session'],file['id']),None)
    bundle=out/'图片处理结果.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
     for item in result['items']:
      if item['status']=='success': z.write(item['output'],Path(item['output']).name)
     z.write(result['manifest'],Path(result['manifest']).name)
    with LOCK: job.update(status=result['status'],result=result,download=url(app,bundle),directory=str(out),manifest=url(app,Path(result['manifest'])))
   except Exception as exc:
    with LOCK: job.update(status='error',error_code=getattr(exc,'code','INTERNAL_ERROR'),message=str(exc))
  POOL.submit(run);return dict(job=jid)
 raise core.Error('INVALID_CONFIG','未知图片操作')
