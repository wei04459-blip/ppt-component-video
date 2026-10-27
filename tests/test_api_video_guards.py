import copy,threading,uuid,unittest
from unittest.mock import patch
from PIL import Image
import test_core
app=test_core.app

class VideoGuardTests(unittest.TestCase):
 def setUp(self):
  self.pid=uuid.uuid4().hex;self.p=app.DATA/self.pid;self.p.mkdir();self.sources=[]
  for i in range(2):
   f=self.p/f'page-{i}.png';Image.new('RGB',(960,540),'white').save(f);self.sources.append(app.file_url(f))
  app.write_json(self.p/'project.json',dict(id=self.pid,pages=self.sources,exports=[]))
  self.video=dict(mode='components',motion='stagger',music=False,pages=[dict(source=self.sources[i],number=i+1,confirmed=False,components=[dict(id='title',text='title',before=[.05,.05,.8,.2],target=[.05,.05,.8,.2]),dict(id='body',text='stable content',before=[.05,.3,.8,.5],target=[.05,.3,.8,.5])]) for i in range(2)])
 def preview(self):
  with patch.object(app.component_video,'preview',return_value=dict(pages=[])):
   app.preview_components(dict(project=self.pid,video=self.video))
 def confirmed(self):
  v=copy.deepcopy(self.video)
  for p in v['pages']:p['confirmed']=True
  return v
 def tearDown(self):
  with app.LOCK:
   for key in list(app.JOBS):
    if app.JOBS[key].get('project')==self.pid:app.JOBS.pop(key)
   app.COMPONENT_REVIEWS.pop(self.pid,None)
 def test_two_simultaneous_submits_admit_exactly_one_job(self):
  gate=threading.Barrier(3);success=[];errors=[]
  def submit():
   gate.wait()
   try:success.append(app.submit('import',dict(project=self.pid,files=[])))
   except ValueError as e:errors.append(str(e))
  with patch.object(app.POOL,'submit') as pool:
   threads=[threading.Thread(target=submit) for _ in range(2)]
   for t in threads:t.start()
   gate.wait()
   for t in threads:t.join()
   self.assertEqual(len(success),1);self.assertEqual(len(errors),1);self.assertIn('\u5df2\u6709\u4efb\u52a1',errors[0]);self.assertEqual(pool.call_count,1)
   self.assertEqual(sum(j['project']==self.pid for j in app.JOBS.values()),1)
 def test_stale_confirmed_body_cannot_create_job(self):
  self.preview();v=self.confirmed();v['pages'][0]['components'][1]['text']='changed but still confirmed'
  with patch.object(app.POOL,'submit') as pool:
   with self.assertRaisesRegex(ValueError,'\u91cd\u65b0\u9884\u89c8'):app.submit('video',dict(project=self.pid,video=v))
   pool.assert_not_called();self.assertFalse(any(j['project']==self.pid for j in app.JOBS.values()))
 def test_selection_order_source_and_engine_invalidate_preview(self):
  self.preview();v=self.confirmed();app.require_component_review(self.p,dict(video=v))
  wrong=copy.deepcopy(v);wrong['pages'].reverse()
  with self.assertRaisesRegex(ValueError,'\u91cd\u65b0\u9884\u89c8'):app.require_component_review(self.p,dict(video=wrong))
  with patch('semantic_scene.renderer_fingerprint',return_value='different-engine'):
   with self.assertRaisesRegex(ValueError,'\u91cd\u65b0\u9884\u89c8'):app.require_component_review(self.p,dict(video=v))
  Image.new('RGB',(960,540),'red').save(self.p/'page-0.png')
  with self.assertRaisesRegex(ValueError,'\u91cd\u65b0\u9884\u89c8'):app.require_component_review(self.p,dict(video=v))
 def test_ui_confirmation_and_audio_do_not_invalidate_visual_review(self):
  self.preview();v=self.confirmed();v['music']=True;v['editorPages']=[dict(unused='editor-only')]
  app.require_component_review(self.p,dict(video=v))

if __name__=='__main__':unittest.main()
