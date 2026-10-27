"""Shared AI-plan contract, source binding and explicit ordinary-node checks."""
import copy,hashlib,re,tempfile
from pathlib import Path

def validate_page(page):
 review=page.get('aiReview',{})
 if not isinstance(review,dict) or any(review.get(k) is not True for k in ['sourceRead','ordinaryIndependent','contentChecked']) or not isinstance(review.get('notes'),str) or len(review['notes'].strip())<8:
  raise ValueError(f'第{page.get("number","?")}页须由AI读图并填写aiReview：sourceRead、ordinaryIndependent、contentChecked及具体notes；此记录不代替实际预览确认')
 scene=page.get('scene')
 if not isinstance(scene,dict) or not isinstance(scene.get('groups'),list):raise ValueError('AI方案须提供原生scene；辅助提取对象不是完成方案')
 expected_assets=set()
 def collect(value,component,path=''):
  if value.get('kind')=='image':expected_assets.add((component,path+'asset'))
  if value.get('kind')=='group':
   for i,part in enumerate(value.get('parts',[])):collect(part,component,path+f'parts/{i}/')
 for component in page.get('components',[]):collect(component.get('plain',{}),str(component.get('id')))
 seen_assets=set()
 for group in scene['groups']:
  for node in group.get('nodes',[]):
   if node.get('kind') not in ['text','image']:continue
   before=node.get('before')
   if not isinstance(before,dict) or not all(k in before for k in ['x','y']):raise ValueError('每条文字/照片须有独立node.before页坐标，不能以成品卡片拆散作普通版')
   if node['kind']=='image':
    if not all(k in before for k in ['w','h']):raise ValueError('普通版照片须填写before.w/h槽，工具会保持比例')
    ref=node.get('sourceRef',{});key=(ref.get('component'),ref.get('path'))
    if key not in expected_assets or key in seen_assets:raise ValueError('独立照片须用sourceRef逐一绑定plain图片asset，不能重复或遗漏')
    seen_assets.add(key)
    if not ('sourceCrop' in node or 'imageData' in node):raise ValueError('可移交AI方案的照片请用sourceCrop或imageData，不能引用其他工作目录的文件')
 if seen_assets!=expected_assets:raise ValueError('普通版与成品的独立照片映射不完整，请保留每张照片')
 return page

def import_plan(app,payload):
 import semantic_scene,component_video
 p=app.project(payload['project']);state=app.read_project(p.name);plan=payload.get('plan')
 if not isinstance(plan,dict) or plan.get('schemaVersion')!=1 or not re.fullmatch(r'[0-9a-f]{64}',str(plan.get('input_sha256',''))):raise ValueError('请选择Agent方案：schemaVersion=1、input_sha256和pages均须保留')
 sources=state.get('pages',[])
 if not sources:raise ValueError('请先导入与AI方案相同的源课件')
 records=state.get('imported_inputs',[]);matched=next((r for r in records if r['sha256']==plan['input_sha256']),None)
 if records and not matched:raise ValueError('AI方案与当前源文件指纹不匹配；请导入同一原始课件，不能只改文件名或指纹')
 if not records:
  folder=Path(state['pages_dir']).parent
  candidates=[z for z in folder.iterdir() if z.is_file() and z.suffix.lower() in ['.ppt','.pptx','.pdf','.png','.jpg','.jpeg','.webp']]
  if not any(hashlib.sha256(z.read_bytes()).hexdigest()==plan['input_sha256'] for z in candidates):raise ValueError('AI方案与当前源文件指纹不匹配，请先导入同一原件')
  matched=dict(firstPage=1,lastPage=len(sources))
 pages=copy.deepcopy(plan.get('pages'));seen=set()
 if not isinstance(pages,list) or not 1<=len(pages)<=6:raise ValueError('AI方案请选择1–6页')
 for page in pages:
  number=page.get('number')
  if type(number) is not int or number in seen or not 1<=number<=matched['lastPage']-matched['firstPage']+1:raise ValueError('AI方案页号无效或重复')
  seen.add(number);validate_page(page);global_number=matched['firstPage']+number-1;page.update(source=sources[global_number-1],number=global_number,confirmed=False,include=True)
  if page.get('automation'):page['automation']=dict(page['automation'],status='ai-reviewed')
 video=dict(mode='components',motion='stagger',music=bool(plan.get('music',True)),pages=pages,editorPages=copy.deepcopy(pages),workflow='ai-native-v1')
 component_video.validate(app,p,video,False)
 with tempfile.TemporaryDirectory() as folder:
  assets=Path(folder)/'assets';assets.mkdir()
  for page in pages:semantic_scene.compile_page(component_video.source_image(app,p,page['source']),page,assets)
 return dict(video=video,notice='AI方案已绑定当前源课件，原有确认已清空。请查看实际首尾与运动预览后再逐页确认。')
