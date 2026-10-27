"""Native scene invariants and an actual Motion Canvas export, never the retired wipe."""
import copy,json,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageChops
import semantic_scene as s
import video_runtime as runtime

class SemanticTests(unittest.TestCase):
 def test_compiler_preserves_every_character_cell_and_photo(self):
  page={'number':1,'components':[{'id':'title','before':[.05,.05,.8,.16],'target':[.05,.05,.8,.16],'plain':{'kind':'text','text':'完整原文 84.0／50.0／35.6','role':'title'}},{'id':'table','before':[.05,.3,.65,.5],'target':[.3,.4,.65,.5],'plain':{'kind':'table','title':'成员信息','rows':[['姓名','人数'],['XXX','8人']]}}]}
  with tempfile.TemporaryDirectory() as folder:
   scene=s.compile_page(Image.new('RGB',(1600,900),'red'),page,Path(folder));self.assertTrue(s.audit_content(page,scene)['identity'])
   self.assertFalse(any(n['kind']=='image' for g in scene['groups'] for n in g['nodes']))
   wrong=copy.deepcopy(scene);wrong['groups'][1]['nodes'][-1]['text']='9人'
   with self.assertRaisesRegex(ValueError,'来源不一致'):s.audit_content(page,wrong)
   swapped=copy.deepcopy(scene);cells=[n for g in swapped['groups'] for n in g['nodes'] if n.get('sourceRef',{}).get('path') in ['rows/1/0','rows/1/1']];cells[0]['text'],cells[1]['text']=cells[1]['text'],cells[0]['text']
   with self.assertRaisesRegex(ValueError,'来源不一致'):s.audit_content(page,swapped)
 def test_contentless_or_unreadable_input_is_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   page={'components':[{'id':'a','before':[0,0,.5,.1],'target':[0,0,.1,.9],'plain':{'kind':'text','text':'教育 Education 工作 Employment 评价 Evaluation'}},{'id':'b','before':[.5,.5,.5,.3],'target':[.5,.5,.5,.3],'plain':{'kind':'text','text':'完整正文'}}]}
   with self.assertRaisesRegex(ValueError,'文字过小'):s.compile_page(Image.new('RGB',(960,540)),page,Path(folder))

 def test_many_groups_never_extend_scene_duration(self):
  scene=dict(groups=[dict(index=i) for i in range(40)]);t=s.timeline(scene)
  self.assertLessEqual(t['totalStagger'],.420001);self.assertGreaterEqual(t['finalHold'],1.8);self.assertLessEqual(t['animationEnd'],2.150001)

 def test_invalid_json_and_static_group_contract(self):
  scene={'width':960,'height':540,'groups':[dict(id=str(i),size=[200,80],before=[10+i*250,100,1],after=[10+i*250,100,1],index=i,nodes=[dict(kind='text',id=str(i),text='content',x=4,y=4,fontSize=20)]) for i in range(2)]}
  s.validate(scene)
  cases=[]
  bad=copy.deepcopy(scene);bad['width']=float('nan');cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['size']=[-1,80];cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['before']=[0,1];cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['after'][0]=float('nan');cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['nodes'][0]['fontSize']=float('nan');cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['index']=40;cases.append(bad)
  bad=copy.deepcopy(scene);bad['groups'][0]['index']=-1;bad['groups'][0]['after'][0]+=50;cases.append(bad)
  for bad in cases:
   with self.assertRaises(ValueError):s.validate(bad)

class ActualMotionCanvasTests(unittest.TestCase):
 def test_two_pages_fixed_top_complete_sequence_and_loaded_photo(self):
  with tempfile.TemporaryDirectory() as folder:
   out=Path(folder);work,assets=s.workspace(runtime,out);Image.new('RGB',(180,120),'red').save(assets/'photo.png')
   scene={'width':960,'height':540,'groups':[{'id':'photo','size':[180,120],'before':[10,100,1],'after':[600,100,1],'index':0,'nodes':[{'kind':'image','src':'assets/photo.png','x':0,'y':0,'w':180,'h':120}]},{'id':'text','size':[250,70],'before':[350,100,1],'after':[20,350,1],'index':1,'nodes':[{'kind':'text','text':'同一内容 8人 32岁','x':0,'y':0,'fontSize':24,'fill':'#222222','afterFill':'#005ea6'}]}]}
   job={'id':'native-test','cancel':False,'log':str(out/'render.log')}
   second_scene=copy.deepcopy(scene);second_scene['height']=720
   frames,audit=s.render_frames(runtime,job,work,[scene,second_scene]);self.assertEqual(len(frames),240);self.assertFalse(audit['missingFramePadding'])
   first=Image.open(frames[0]).convert('RGB');last=Image.open(frames[119]).convert('RGB');second=Image.open(frames[120]).convert('RGB')
   self.assertEqual(first.size,(1080,1440));self.assertIsNone(ImageChops.difference(first.crop((62,160,1018,699)),last.crop((62,160,1018,699))).getbbox())
   self.assertIsNotNone(ImageChops.difference(first.crop((54,834,1026,1381)),last.crop((54,834,1026,1381))).getbbox())
   # Red photo pixels move with the native group and remain visibly loaded.
   self.assertEqual(first.getpixel((90,960)),(255,0,0));self.assertEqual(last.getpixel((700,960)),(255,0,0));self.assertEqual(second.getpixel((210,950)),(255,0,0));self.assertEqual(s.actual_crop(frames[120],second_scene).size,(960,720))
   for f in frames:
    with Image.open(f) as im:self.assertEqual(im.size,(1080,1440))
   missing=copy.deepcopy(scene);missing['groups'][0]['nodes'][0]['src']='assets/missing.png'
   with self.assertRaisesRegex(ValueError,'Missing image|HTTP 404|Missing|渲染失败|处理失败'):s.render_frames(runtime,job,work,[missing])

if __name__=='__main__':unittest.main()
