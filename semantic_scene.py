"""Data-only semantic scene compiler; Motion Canvas owns animation and timing."""
import json,math,hashlib,shutil,os,subprocess,base64,io,re
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
import plain_components as plain
import video_fonts as fonts
BLUE='#005ea6';INK='#103758'

def rgb(s):return tuple(int(s[i:i+2],16) for i in (1,3,5))
def color(v):return '#'+''.join(f'{x:02x}' for x in v) if isinstance(v,(tuple,list)) else v

def node(kind,**kw):return dict(kind=kind,**kw)
def text_nodes(text,x,y,w,h,role='body',title=False):
 # Compute wrapping once, in content coordinates. It never changes in animation.
 f,lines,lead=plain.text_layout(text,(max(1,round(w)),max(1,round(h))),role)
 return [node('text',text=line,x=x+4,y=y+4+j*lead,fontSize=f.size,fill='#222222',afterFill=BLUE if title else INK,fontWeight=700 if title else 400) for j,line in enumerate(lines) if line.strip()]
def compile_text_card(value,size,component,path):
 w,h=size;title=value.get('title','');body=value['text'];title_path=path+'title';body_path=path+'text'
 if not title and '\n' in body:
  first,rest=body.split('\n',1)
  if 0<len(first)<=40:title=first;body=rest;title_path=body_path
 nodes=[node('rect',x=0,y=0,w=w-1,h=h-1,fill='#ffffff',afterFill='#f0f7fc',stroke='#ffffff',afterStroke='#c3d9ea',lineWidth=1,radius=0,afterRadius=10)]
 off=0
 if title:
  off=min(50,max(32,h*.18));nodes.append(node('rect',x=0,y=0,w=w-1,h=off,fill='#ffffff',afterFill=BLUE,radius=0,afterRadius=9))
  f,lines,lead=plain.text_layout(title,(max(1,round(w-28)),max(1,round(off-4))),'body')
  for j,line in enumerate(lines):
   if line.strip():nodes.append(node('text',x=14,y=max(3,(off-len(lines)*lead)/2)+j*lead,text=line,fontSize=min(f.size,22),fontWeight=700,fill='#222222',afterFill='#ffffff',sourceRef=dict(component=component,path=title_path)))
 else:nodes.append(node('rect',x=18,y=17,w=min(58,w*.35),h=4,fill='#ffffff',afterFill=BLUE,radius=0,afterRadius=2));off=32
 f,lines,lead=plain.text_layout(body,(max(1,round(w-32)),max(1,round(h-off-24))),'body');yy=off+max(12,(h-off-len(lines)*lead)/2)
 for j,line in enumerate(lines):
  if line.strip():nodes.append(node('text',x=20,y=yy+j*lead,text=line,fontSize=f.size,fontWeight=400,fill='#222222',afterFill=INK,sourceRef=dict(component=component,path=body_path)))
 return nodes

def compile_value(value,bitmap,size,assets,prefix,component,path=""):
 w,h=size;nodes=[];kind=value['kind'];off=0
 if kind=='text' and not path and value.get('role')!='title':return compile_text_card(value,size,component,path)
 if kind=='group':nodes.append(node('rect',x=0,y=0,w=w,h=h,fill='#ffffff',afterFill='#f6fbff',stroke='#ffffff',afterStroke='#c4ddeb',lineWidth=1,radius=0,afterRadius=8))
 if value.get('title'):
  off=30;nodes.append(node('rect',x=0,y=0,w=w,h=28,fill='#ffffff',afterFill=BLUE,radius=5,afterRadius=5))
  added=text_nodes(value['title'],7,0,w-14,28,title=True)
  for n in added:n['sourceRef']=dict(component=component,path=path+'title')
  nodes+=added
  for n in nodes:
   if n['kind']=='text':n['afterFill']='#ffffff'
 if kind=='group':
  for j,part in enumerate(value['parts']):
   x,y,pw,ph=part['box'];sub=compile_value(part,bitmap,(round(pw*w),round(ph*(h-off))),assets,prefix+f'-{j}',component,path+f'parts/{j}/')
   for n in sub:n['x']+=x*w;n['y']+=off+y*(h-off)
   if part['kind']=='text' and j==0 and y==0 and ph<=.2:
    nodes.append(node('rect',x=x*w,y=off+y*(h-off),w=pw*w,h=ph*(h-off),fill='#ffffff',afterFill=BLUE,radius=0,afterRadius=6))
    for n in sub:
     if n['kind']=='text':n['afterFill']='#ffffff'
   nodes+=sub
 elif kind=='image':
  im=plain.asset(bitmap,value);name=prefix+'.png';im.save(assets/name);factor=min((w-8)/im.width,(h-off-8)/im.height);iw,ih=im.width*factor,im.height*factor
  nodes.append(node('image',src='assets/'+name,x=(w-iw)/2,y=off+(h-off-ih)/2,w=iw,h=ih))
 elif kind=='text':
  added=text_nodes(value['text'],0,off,w,h-off,value.get('role','body'),value.get('role')=='title')
  for n in added:n['sourceRef']=dict(component=component,path=path+'text')
  nodes+=added
 elif kind=='table':
  f,lines,lead,xs,heights=plain.table_layout(value,(round(w*2),round((h-off)*2)));xs=[a/2 for a in xs];heights=[a/2 for a in heights];lead/=2;y=off
  for ri,(row,rh) in enumerate(zip(lines,heights)):
   for j,cell in enumerate(row):
    head=ri==0;nodes.append(node('rect',x=xs[j],y=y,w=xs[j+1]-xs[j],h=rh,fill='#ffffff',afterFill=BLUE if head else ('#edf7ff' if ri%2 else '#ffffff'),stroke='#555555',afterStroke='#b1cde0',lineWidth=1))
    for k,line in enumerate(cell):
     if not line:continue
     nodes.append(node('text',text=line,x=xs[j]+3,y=y+2+k*lead,fontSize=f.size/2,fill='#222222',afterFill='#ffffff' if head else INK,fontWeight=700 if head else 400,sourceRef=dict(component=component,path=path+f'rows/{ri}/{j}')))
   y+=rh
 return nodes

def node_state(group,node,which):
    """One authoritative absolute-page pose for preview, MC data and ordinary PPT."""
    gx,gy,scale=group[which]
    state=dict(x=gx+node['x']*scale,y=gy+node['y']*scale,
        opacity=node.get('afterOpacity',node.get('opacity',1)) if which=='after' else node.get('opacity',1),
        fill=node.get('afterFill',node.get('fill','#222222')) if which=='after' else node.get('fill','#222222'),
        stroke=node.get('afterStroke',node.get('stroke')) if which=='after' else node.get('stroke'),
        radius=node.get('afterRadius',node.get('radius',0)) if which=='after' else node.get('radius',0),
        lineWidth=node.get('lineWidth',0)*scale,fontWeight=node.get('fontWeight',400))
    if node['kind']=='text':state['fontSize']=node['fontSize']*scale
    if node['kind'] in ['rect','image']:state.update(w=node['w']*scale,h=node['h']*scale)
    if node['kind']=='line':state['points']=[[x*scale,y*scale] for x,y in node['points']]
    if which=='before':
        override=node.get('before',{})
        if not isinstance(override,dict):raise ValueError('node.before必须为页坐标对象')
        allowed={'x','y','w','h','fontSize','fontWeight','fill','stroke','opacity','radius','lineWidth'}
        if set(override)-allowed:raise ValueError('node.before只支持位置、尺寸、字号和样式；不能替换文字内容')
        for k,v in override.items():
            if k not in ['fill','stroke'] and (type(v) not in (int,float) or not math.isfinite(v)):raise ValueError('node.before数值无效')
        state.update(override)
    if node['kind']=='text':
        f=fonts.load_font('黑体粗' if state['fontWeight']>=700 else '黑体',max(1,round(state['fontSize']*4)))
        state['w']=f.getlength(node['text'])/4;state['h']=state['fontSize']*1.2
    elif node['kind']=='line':
        state['w']=max(x for x,y in state['points']);state['h']=max(y for x,y in state['points'])
    return state


def prepare_node_states(scene,assets):
    for group in scene['groups']:
        independent=any('before' in n for n in group['nodes'])
        group['nodeBefore']=independent
        if not independent:continue
        for node in group['nodes']:
            override=node.get('before',{})
            node_state(group,node,'before') # Validate override types before asset sizing.
            if node['kind'] in ['rect','image'] and any(k in override and override[k]<=0 for k in ['w','h']):raise ValueError('node.before图片或矩形尺寸必须为正数')
            if node['kind']=='image' and 'w' in override and 'h' in override:
                path=(Path(assets).parent/node['src']).resolve()
                if not path.is_relative_to(Path(assets).resolve()):raise ValueError('普通版照片必须来自隔离素材')
                with Image.open(path) as im:
                    factor=min(override['w']/im.width,override['h']/im.height)
                    w,h=im.width*factor,im.height*factor
                    override['x']=override.get('x',node_state(group,node,'before')['x'])+(override['w']-w)/2
                    override['y']=override.get('y',node_state(group,node,'before')['y'])+(override['h']-h)/2
                    override['w']=w;override['h']=h
            states={which:node_state(group,node,which) for which in ['before','after']}
            for which,pose in states.items():
                for field in ['x','y','w','h','opacity','radius','lineWidth','fontWeight']+(['fontSize'] if node['kind']=='text' else []):
                    if type(pose.get(field)) not in (int,float) or not math.isfinite(pose[field]):raise ValueError('node.before位置或样式数值无效')
                if not 0<=pose['opacity']<=1 or min(pose['w'],pose['h'])<0:raise ValueError('node.before透明度或尺寸无效')
                if pose['opacity']>0 and (pose['x']<-.1 or pose['y']<-.1 or pose['x']+pose['w']>scene['width']+.75 or pose['y']+pose['h']>scene['height']+.75):raise ValueError(f'节点 {node.get("id","?")} 的{which}绘制范围超出页面')
                if node['kind']=='text' and pose['fontSize']*min(972/scene['width'],547/scene['height'])<8:raise ValueError('node.before文字过小，请扩大普通版排版范围')
            if node['kind'] in ['text','image'] and 'before' in node and (states['before']['opacity']<=0 or states['after']['opacity']<=0):raise ValueError('普通版与成品必须保留同一文字和照片，不能隐藏内容')
            node['states']=states
    return scene


def compile_page(source,page,assets):
 if page.get('scene'):
  scene=json.loads(json.dumps(page['scene']))
  if not isinstance(scene,dict) or not isinstance(scene.get('groups'),list):raise ValueError('语义场景groups必须为组件组列表')
  for g in scene['groups']:
   if not isinstance(g,dict) or not isinstance(g.get('nodes'),list) or any(not isinstance(n,dict) or 'kind' not in n for n in g['nodes']):raise ValueError('语义场景组件与节点结构无效')
  for gi,g in enumerate(scene['groups']):
   for ni,n in enumerate(g['nodes']):
    if n['kind']=='image' and 'sourceCrop' in n:
     rect=n.pop('sourceCrop')
     plain.rect(rect);x,y,w,h=rect
     if w*h>.8:raise ValueError('独立照片不能使用整页截图；请仅框取照片或标志')
     image=source.crop((round(x*source.width),round(y*source.height),round((x+w)*source.width),round((y+h)*source.height)));buffer=io.BytesIO();image.save(buffer,format='PNG');n['imageData']=base64.b64encode(buffer.getvalue()).decode()
    if n['kind']=='image' and 'imageData' in n:
     raw=base64.b64decode(n.pop('imageData'),validate=True)
     if len(raw)>30_000_000:raise ValueError('场景图片过大')
     name=f'p{page.get("number",1)}-g{gi}-n{ni}.png'
     with Image.open(io.BytesIO(raw)) as im:
      im=im.convert('RGB');fit=n.get('fit','contain')
      if fit=='cover':
       position=n.get('cropPosition',[.5,.5])
       if len(position)!=2 or any(not 0<=v<=1 for v in position):raise ValueError('照片裁切中心应在0–1')
       im=ImageOps.fit(im,(max(1,round(n['w']*2)),max(1,round(n['h']*2))),centering=tuple(position))
      elif fit=='contain':
       factor=min(n['w']/im.width,n['h']/im.height);iw=im.width*factor;ih=im.height*factor;n['x']+=(n['w']-iw)/2;n['y']+=(n['h']-ih)/2;n['w']=iw;n['h']=ih
      else:raise ValueError('照片适配只能为contain或cover，不能拉伸')
      im.save(assets/name)
     n['src']='assets/'+name
  validate(scene);audit_content(page,scene);prepare_node_states(scene,assets);return scene
 scale=min(960/source.width,540/source.height);source=source.resize((round(source.width*scale),round(source.height*scale)),Image.Resampling.LANCZOS);groups=[]
 for j,item in enumerate(page['components']):
  tx,ty,tw,th=item['target'];bx,by,bw,bh=item['before'];w=max(1,round(tw*source.width));h=max(1,round(th*source.height));bitmap=source.crop((round(tx*source.width),round(ty*source.height),round((tx+tw)*source.width),round((ty+th)*source.height)))
  nodes=compile_value(plain.spec(item),bitmap,(w,h),assets,f'p{page.get("number",1)}-g{j}',str(item.get('id',j)))
  factor=min(bw*source.width/w,bh*source.height/h)
  groups.append(dict(id=str(item.get('id',j)),size=[w,h],before=[bx*source.width+(bw*source.width-w*factor)/2,by*source.height+(bh*source.height-h*factor)/2,factor],after=[tx*source.width,ty*source.height,1],nodes=nodes,index=j))
 design=page.get('design',{})
 if not isinstance(design,dict) or set(design)-{'accent','ink','surface','line'} or any(not isinstance(v,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in design.values()):raise ValueError('页面design只支持accent/ink/surface/line的六位HEX颜色')
 palette={BLUE:design.get('accent',BLUE),INK:design.get('ink',INK),'#f0f7fc':design.get('surface','#f0f7fc'),'#c3d9ea':design.get('line','#c3d9ea')}
 for g in groups:
  for n in g['nodes']:
   for key in ['afterFill','afterStroke']:
    if n.get(key) in palette:n[key]=palette[n[key]]
 scene=dict(width=source.width,height=source.height,groups=groups);
 for gi,g in enumerate(groups):
  for ni,n in enumerate(g['nodes']):n['id']=f'g{gi}-n{ni}'
 validate(scene);audit_content(page,scene);prepare_node_states(scene,assets);return scene

def audit_content(page,scene):
 expected={}
 def add(value,component,path=''):
  if value.get('title'):expected[(component,path+'title')]=value['title']
  if value['kind']=='text':expected[(component,path+'text')]=value['text']
  elif value['kind']=='table':
   for ri,row in enumerate(value['rows']):
    for ci,text in enumerate(row):
     if text.strip():expected[(component,path+f'rows/{ri}/{ci}')]=text
  elif value['kind']=='group':
   for pi,part in enumerate(value['parts']):add(part,component,path+f'parts/{pi}/')
 for i,item in enumerate(page['components']):add(plain.spec(item),str(item.get('id',i)))
 bindings={};seen_ids=set()
 for group in scene['groups']:
  for n in group['nodes']:
   if n['kind']!='text':continue
   if not n.get('id') or n['id'] in seen_ids:raise ValueError('原生文字节点须有独立稳定id')
   seen_ids.add(n['id']);ref=n.get('sourceRef')
   if not isinstance(ref,dict) or not isinstance(ref.get('component'),str):raise ValueError('显式scene文字须提供sourceRef，逐段/单元格核对来源')
   paths=ref.get('path');paths=[paths] if isinstance(paths,str) else paths
   if not isinstance(paths,list) or not paths or any(not isinstance(p,str) for p in paths):raise ValueError('sourceRef.path必须为原文路径或有序路径列表')
   key=(ref['component'],tuple(paths));bindings.setdefault(key,[]).append(n['text'])
 covered=set();proof=[];norm=lambda x:''.join(x.split())
 for (component,paths),parts in bindings.items():
  keys=[(component,p) for p in paths]
  if any(k not in expected or k in covered for k in keys):raise ValueError('原生文字来源重复或不存在：'+component+' / '+str(paths))
  source=''.join(expected[k] for k in keys);actual=''.join(parts)
  if norm(source)!=norm(actual):raise ValueError('原生文字与来源不一致：'+component+' / '+str(paths)+'，请保留原句及单元格对应')
  covered.update(keys);proof.append(dict(component=component,paths=list(paths),source=source,rendered=actual,match=True))
 missing=set(expected)-covered
 if missing:raise ValueError('原生场景缺少文字来源：'+str(sorted(missing)[:5]))
 return dict(identity=True,bindings=proof)


def validate(scene):
 if not isinstance(scene,dict):raise ValueError('语义场景必须为对象')
 if set(scene)-{'width','height','groups','description'}:raise ValueError('语义场景包含未知字段')
 for k in ['width','height']:
  if type(scene.get(k)) not in (float,int) or not math.isfinite(scene[k]) or not 100<=scene[k]<=5000:raise ValueError('语义画布尺寸无效')
 groups=scene.get('groups',[])
 if not isinstance(groups,list) or not 2<=len(groups)<=40:raise ValueError('语义场景需要2–40个真实组件组')
 ids=[]
 for g in groups:
  if not isinstance(g,dict):raise ValueError('组件组必须为对象')
  for field,length in [('size',2),('before',3),('after',3)]:
   values=g.get(field)
   if not isinstance(values,list) or len(values)!=length or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('组件组'+field+'长度或数值无效')
  if min(g['size'])<=0:raise ValueError('组件组size必须为正尺寸')
  if not isinstance(g.get('id'),str) or g['id'] in ids:raise ValueError('组件组ID必须独立且稳定')
  ids.append(g['id']);w,h=g['size']
  if not any('before' in n for n in g.get('nodes',[])) and g.get('index',0)==-1 and any(abs(a-b)>1e-6 for a,b in zip(g['before'],g['after'])):raise ValueError('index=-1为固定组，before与after必须相同；需要移动请使用0–39的index')
  if type(g.get('index',0)) is not int or not -1<=g.get('index',0)<=39:raise ValueError('组件index必须为-1或0–39整数')
  for key in ['before','after']:
   x,y,s=g[key]
   if min(x,y)<-.01 or s<=0 or x+w*s>scene['width']+.1 or y+h*s>scene['height']+.1:raise ValueError(f'组件组 {g["id"]} 的{key}位置越界')
  if not isinstance(g.get('nodes'),list) or not 1<=len(g['nodes'])<=3000:raise ValueError('组件组需要1–3000个原生节点')
  for n in g['nodes']:
   if not isinstance(n,dict) or 'kind' not in n:raise ValueError('原生节点无效')
   if n['kind'] in ['text','image','rect','line'] and any(k not in n for k in ['x','y']):raise ValueError('原生节点缺位置')
   if n['kind'] in ['image','rect'] and any(type(n.get(k)) not in (int,float) or not math.isfinite(n[k]) or n[k]<=0 for k in ['w','h']):raise ValueError('原生节点尺寸无效')
   if n['kind']=='text' and (type(n.get('fontSize')) not in (int,float) or not math.isfinite(n['fontSize']) or n['fontSize']<=0):raise ValueError('字号无效')
   if n['kind'] not in ['text','rect','image','line']:raise ValueError('不支持的原生节点类型')
   if any(type(v) not in (int,float) or not math.isfinite(v) for k,v in n.items() if k in ['x','y','w','h','fontSize','lineWidth']):raise ValueError('原生节点数值无效')
   if n['kind']=='text':
    for key in ['before','after']:
     if key=='before' and 'before' in n:continue
     if n['fontSize']*g[key][2]*min(972/scene['width'],547/scene['height'])<8:raise ValueError(f'组件组 {g["id"]} 的{key}文字过小，请扩大普通版区域或提供明确scene布局')
    if not isinstance(n.get('text'),str) or not n['text']:raise ValueError('原生文字不能为空')
    f=fonts.load_font('黑体粗' if n.get('fontWeight',400)>=700 else '黑体',round(n['fontSize']*4));nw=f.getlength(n['text'])/4;nh=n['fontSize']*1.2
   elif n['kind']=='line':
    pts=n.get('points')
    if not isinstance(pts,list) or not 2<=len(pts)<=200 or any(not isinstance(pt,list) or len(pt)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in pt) for pt in pts):raise ValueError('线条节点坐标无效')
    if min(pt[0] for pt in pts)+n['x']<0 or min(pt[1] for pt in pts)+n['y']<0:raise ValueError('线条节点越界')
    nw=max(pt[0] for pt in pts);nh=max(pt[1] for pt in pts)
   else:nw=n.get('w',0);nh=n.get('h',0)
   if n['x']<-.1 or n['y']<-.1 or n['x']+nw>w+.75 or n['y']+nh>h+.75:raise ValueError(f'组件组 {g["id"]} 内节点 {n.get("id","?")} 超出绘制范围，请扩大容器或调整原生布局')
   if n['kind']=='image' and (not str(n['src']).startswith('assets/') or '..' in Path(n['src']).parts):raise ValueError('照片必须来自隔离素材目录')
 return scene

def static_image(scene,assets,after=False):
 im=Image.new('RGB',(round(scene['width']*2),round(scene['height']*2)),'white')
 for group in scene['groups']:
  for n in group['nodes']:
   pose=node_state(group,n,'after' if after else 'before')
   if pose['opacity']<=0:continue
   layer=Image.new('RGBA',im.size,(0,0,0,0));d=ImageDraw.Draw(layer);x,y=pose['x']*2,pose['y']*2
   if n['kind']=='rect':d.rounded_rectangle((x,y,x+pose['w']*2,y+pose['h']*2),radius=pose['radius']*2,fill=pose['fill'],outline=pose['stroke'],width=max(1,round(pose['lineWidth']*2)))
   elif n['kind']=='text':d.text((x,y),n['text'],font=fonts.load_font('黑体粗' if pose['fontWeight']>=700 else '黑体',round(pose['fontSize']*2)),fill=pose['fill'])
   elif n['kind']=='image':
    a=Image.open(Path(assets).parent/n['src']).convert('RGBA').resize((max(1,round(pose['w']*2)),max(1,round(pose['h']*2))),Image.Resampling.LANCZOS);layer.paste(a,(round(x),round(y)))
   elif n['kind']=='line':
    points=[(x+px*2,y+py*2) for px,py in pose['points']]
    if n.get('closed'):d.polygon(points,fill=pose['fill'])
    else:d.line(points,fill=pose['stroke'],width=max(1,round(pose['lineWidth']*2)))
   if pose['opacity']<1:layer.putalpha(layer.getchannel('A').point(lambda a:round(a*pose['opacity'])))
   im.paste(layer,(0,0),layer)
 return im.resize((round(scene['width']),round(scene['height'])),Image.Resampling.LANCZOS)


def workspace(app,out):
 work=out/'motion-canvas';shutil.copytree(app.ROOT/'video',work,ignore=shutil.ignore_patterns('node_modules','output','assets','input.json'))
 modules=app.ROOT/'video'/'node_modules'
 if not modules.exists():raise ValueError('Motion Canvas依赖未安装，不能回退截图动画')
 if os.name=='nt':shutil.copytree(modules,work/'node_modules')
 else:(work/'node_modules').symlink_to(modules.resolve(),target_is_directory=True)
 assets=work/'assets';assets.mkdir()
 for src,dst in [('LXGWWenKai-Medium.ttf','label.ttf'),('NotoSansCJKsc-Regular.otf','regular.otf'),('NotoSansCJKsc-Bold.otf','bold.otf')]:
  path=getattr(app,'ENGINE',app.ROOT/'engine')/'fonts'/src
  if not path.is_file():raise ValueError('视频字体缺失：'+src)
  shutil.copy(path,assets/dst)
 (work/'src'/'project.ts').write_text("import {makeProject} from '@motion-canvas/core';\nimport semantic from './semantic?scene';\nexport default makeProject({scenes:[semantic]});\n")
 return work,assets

def render_frames(app,job,work,scenes):
 value=dict(mode='semantic',motion='v7-regroup',pages=scenes,color=BLUE,topLabel='自己瞎做的',bottomLabel='护士长想要的',secondsPerPage=4,fps=30,expectedFrames=len(scenes)*120)
 (work/'input.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
 exe=shutil.which('node')
 if not exe:raise ValueError('未找到Node.js，不能回退截图动画')
 app.command(job,[exe,'render.mjs'],cwd=work,timeout=1800)
 frames=sorted((work/'output'/'movie').rglob('*.png'));expected=value['expectedFrames']
 # Motion Canvas may export one boundary frame. Never fill missing frames.
 if len(frames) not in [expected,expected+1]:raise ValueError(f'Motion Canvas帧数异常：{len(frames)}，需要{expected}（最多一个边界帧）')
 from PIL import Image
 for frame in frames:
  with Image.open(frame) as im:
   if im.size!=(1080,1440):raise ValueError('动画帧尺寸错误')
 return frames[:expected],dict(engine='motion-canvas-native',fps=30,frames=expected,exportedFrames=len(frames),pages=len(scenes),duration=len(scenes)*4,missingFramePadding=False)


def render(app,job,work,scenes,music,out):
 frames,audit=render_frames(app,job,work,scenes);expected=audit['frames']
 seq=out/'frames';seq.mkdir()
 for i,f in enumerate(frames[:expected]):shutil.copyfile(f,seq/f'{i:06d}.png')
 for pi,scene in enumerate(scenes):
  actual_crop(frames[pi*120],scene).save(out/f'{pi+1:02d}-普通版.png')
  actual_crop(frames[pi*120+119],scene).save(out/f'{pi+1:02d}-语义成品版.png')
 movie=out/'组件重组视频.mp4';audio=['-stream_loop','-1','-i',app.ROOT/'video'/'music.wav'] if music else ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
 app.command(job,[app.ffmpeg(),'-y','-framerate','30','-i',seq/'%06d.png',*audio,'-frames:v',str(expected),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',movie])
 app.command(job,[app.ffmpeg(),'-v','error','-i',movie,'-f','null','-'])
 previews=[]
 for pi in range(len(scenes)):
  for offset in [0,20,26,33,40,47,54,65,85,119]:
   dest=out/f'预览_{pi+1}_{offset:03d}.png';shutil.copyfile(seq/f'{pi*120+offset:06d}.png',dest);previews.append(app.file_url(dest))
 audit['timelines']=[timeline(scene) for scene in scenes]
 (out/'render-audit.json').write_text(json.dumps(audit,indent=2))
 return dict(video=app.file_url(movie),images=previews,frames=expected,fps=30,duration=len(scenes)*4,directory=str(out),engine='motion-canvas-native')


def renderer_fingerprint(root):
    files=['ai_video_plan.py','auto_components.py','local_ocr.py','local_ocr.swift','component_video.py','plain_components.py','video_fonts.py','semantic_scene.py','video/src/semantic.tsx','video/src/v7/shared.ts','video/render.html','video/render.mjs','video/vite.config.ts','video/package.json','video/package-lock.json']
    files+=['engine/fonts/'+n for n in ['LXGWWenKai-Medium.ttf','NotoSansCJKsc-Regular.otf','NotoSansCJKsc-Bold.otf']]
    files+=['video/node_modules/'+n+'/package.json' for n in ['@motion-canvas/core','@motion-canvas/2d','@motion-canvas/vite-plugin','vite','playwright']]
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files if (root/name).is_file()}
    from importlib.metadata import version,PackageNotFoundError
    for name in ['numpy','opencv-python','opencv-python-headless','rapidocr','onnxruntime']:
        try:hashes['python-package:'+name]=version(name)
        except PackageNotFoundError:hashes['python-package:'+name]='unavailable'
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()


def actual_preview(app,p,page):
    import uuid
    staging=p/'semantic-previews'/uuid.uuid4().hex;staging.mkdir(parents=True)
    work,assets=workspace(app,staging)
    import component_video
    source=component_video.source_image(app,p,page['source']);scene=compile_page(source,page,assets)
    asset_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in assets.iterdir() if f.is_file()}
    renderer_version=renderer_fingerprint(app.ROOT)
    signature=hashlib.sha256(json.dumps(dict(scene=scene,assets=asset_hashes,renderer=renderer_version),sort_keys=True).encode()).hexdigest()
    cache=p/'semantic-previews'/signature
    if (cache/'preview.json').is_file():
        shutil.rmtree(staging);record=json.loads((cache/'preview.json').read_text());return {k:cache/v for k,v in record.items()}
    job=dict(id=uuid.uuid4().hex,cancel=False,log=str(staging/'render.log'))
    frames,audit=render_frames(app,job,work,[scene])
    if renderer_fingerprint(app.ROOT)!=renderer_version:raise ValueError('预览期间工具已更新，请重启后重新预览')
    def extract(path):return actual_crop(path,scene)
    extract(frames[0]).save(staging/'before.png');extract(frames[-1]).save(staging/'after.png')
    thumb=(320,round(320*scene['height']/scene['width']));board=Image.new('RGB',(960,(thumb[1]+28)*2),'#eeeeed');d=ImageDraw.Draw(board)
    for i,index in enumerate([0,25,34,43,54,119]):
        x=i%3*320;y=i//3*(thumb[1]+28);board.paste(extract(frames[index]).resize(thumb),(x,y+28));d.text((x+6,y+7),f'MC frame {index} / {index/30:.2f}s',fill='#222222')
    board.save(staging/'motion.png');(staging/'render-audit.json').write_text(json.dumps(audit,indent=2))
    (staging/'preview.json').write_text(json.dumps(dict(before='before.png',after='after.png',motion='motion.png')))
    if cache.exists():shutil.rmtree(cache)
    staging.rename(cache)
    return dict(before=cache/'before.png',after=cache/'after.png',motion=cache/'motion.png')


def timeline(scene):
    highest=max([g.get('index',0) for g in scene['groups']]+[0]);step=min(.07,.42/max(1,highest));end=.65+max(0,highest)*step+1.08
    return dict(staggerStep=step,totalStagger=max(0,highest)*step,animationEnd=end,finalHold=4-end,secondsPerPage=4)


def actual_crop(path,scene):
    image=Image.open(path).convert('RGB');factor=min(972/scene['width'],547/scene['height']);w=scene['width']*factor;h=scene['height']*factor;x=(1080-w)/2;y=1107.5-h/2
    return image.crop((round(x),round(y),round(x+w),round(y+h))).resize((round(scene['width']),round(scene['height'])),Image.Resampling.LANCZOS)
