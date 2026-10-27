import copy,hashlib,tempfile,unittest,uuid
from pathlib import Path
from PIL import Image
import ai_video_plan as protocol
import video_runtime as app

class AIPlanTests(unittest.TestCase):
 def plan(self,sha):
  return dict(schemaVersion=1,input_sha256=sha,workflow='ai-native-v1',motion='stagger',pages=[dict(number=1,aiReview=dict(sourceRead=True,ordinaryIndependent=True,contentChecked=True,notes='已看原页，核对完整文字并独立安排普通版'),components=[dict(id='a',before=[.05,.1,.4,.3],target=[.05,.1,.4,.3],plain=dict(kind='text',text='完整内容A')),dict(id='b',before=[.5,.5,.4,.3],target=[.5,.5,.4,.3],plain=dict(kind='text',text='完整内容B'))],scene=dict(width=960,height=540,groups=[dict(id=c,size=[300,70],before=[x,y,1],after=[x,y,1],index=i,nodes=[dict(kind='text',id=c,text='完整内容'+c.upper(),x=0,y=0,fontSize=24,sourceRef=dict(component=c,path='text'),before=dict(x=40,y=80+i*50,fontSize=24,fontWeight=400))]) for i,(c,x,y) in enumerate([('a',40,100),('b',500,300)])]))])
 def test_import_binds_source_and_clears_confirmations_without_writing_project(self):
  previous=app.DATA
  with tempfile.TemporaryDirectory() as d:
   try:
    app.DATA=Path(d);pid=uuid.uuid4().hex;p=app.DATA/pid;p.mkdir();folder=p/'imports';folder.mkdir();source=folder/'input.png';Image.new('RGB',(960,540),'white').save(source);sha=hashlib.sha256(source.read_bytes()).hexdigest();state=dict(id=pid,pages=[app.file_url(source)],pages_dir=str(folder/'pages'),imported_inputs=[dict(sha256=sha,firstPage=1,lastPage=1)],video=dict(unchanged=True));app.write_json(p/'project.json',state);before=(p/'project.json').read_bytes();plan=self.plan(sha);plan['pages'][0]['source']='/files/foreign/file.png';result=protocol.import_plan(app,dict(project=pid,plan=plan));self.assertEqual(result['video']['pages'][0]['source'],state['pages'][0]);self.assertFalse(result['video']['pages'][0]['confirmed']);self.assertEqual((p/'project.json').read_bytes(),before)
    bad=copy.deepcopy(plan);bad['input_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'指纹'):protocol.import_plan(app,dict(project=pid,plan=bad))
    self.assertEqual((p/'project.json').read_bytes(),before)
   finally:app.DATA=previous
 def test_portable_photo_mapping_and_source_crop(self):
  import semantic_scene
  page=self.plan('0'*64)['pages'][0];page['components'].append(dict(id='photo',before=[.05,.7,.2,.2],target=[.6,.5,.2,.2],plain=dict(kind='image',assetRole='photo')))
  page['scene']['groups'].append(dict(id='photo',size=[180,120],before=[600,100,1],after=[600,100,1],index=2,nodes=[dict(kind='image',x=0,y=0,w=180,h=120,sourceCrop=[.1,.1,.2,.2],sourceRef=dict(component='photo',path='asset'),before=dict(x=40,y=400,w=180,h=100))]))
  protocol.validate_page(page)
  with tempfile.TemporaryDirectory() as d:
   assets=Path(d)/'assets';assets.mkdir();scene=semantic_scene.compile_page(Image.new('RGB',(960,540),'red'),page,assets);node=scene['groups'][-1]['nodes'][0];self.assertAlmostEqual(node['w']/node['h'],960/540);self.assertEqual(Image.open(assets/Path(node['src']).name).getpixel((0,0)),(255,0,0))
  bad=copy.deepcopy(page);bad['scene']['groups'][-1]['nodes'][0]['sourceRef']['component']='a'
  with self.assertRaisesRegex(ValueError,'照片'):protocol.validate_page(bad)
 def test_draft_or_missing_independent_before_is_rejected(self):
  p=self.plan('0'*64)['pages'][0];p['aiReview']['contentChecked']=False
  with self.assertRaisesRegex(ValueError,'aiReview'):protocol.validate_page(p)
  p=self.plan('0'*64)['pages'][0];p['scene']['groups'][0]['nodes'][0].pop('before')
  with self.assertRaisesRegex(ValueError,'node.before'):protocol.validate_page(p)
if __name__=='__main__':unittest.main()
