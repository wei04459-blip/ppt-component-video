import contextlib,io,json,os,shutil,tempfile,unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import agent_video as av
import video_runtime as app

class AgentVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.work=Path(self.tmp.name)/'work';self.work.mkdir()
        self.old_data=app.DATA;self.old_env=dict(os.environ)
        pid='d'*32;p=self.work/'data'/pid;p.mkdir(parents=True)
        image=p/'page.png';Image.new('RGB',(960,540),'#ddf2ee').save(image)
        app.write_json(p/'project.json',{'id':pid,'pages':[],'exports':[]})
        path=str(image.relative_to(self.work))
        av.write(self.work/'project.json',{'schemaVersion':1,'project':pid,'input_sha256':'fixture','input_name':'fixture.pptx','pages':[{'number':1,'image':path,'objects':[]}]})
        av.write(self.work/'source-hashes.json',{path:av.digest(image)})
        self.plan={'schemaVersion':1,'input_sha256':'fixture','motion':'stagger','music':False,'pages':[{'number':1,'components':[
            {'id':'a','text':'标题','target':[.1,.1,.8,.2],'before':[.1,.1,.8,.2]},
            {'id':'b','text':'完整内容','target':[.1,.4,.8,.4],'before':[.1,.5,.8,.3]}]}]}
        av.write(self.work/'plan.json',self.plan)
        self.args=Namespace(work=str(self.work),plan=None)
    def tearDown(self):
        app.DATA=self.old_data;os.environ.clear();os.environ.update(self.old_env);self.tmp.cleanup()
    def preview(self):
        with contextlib.redirect_stdout(io.StringIO()):av.preview(self.args)
        r=av.read(self.work/'preview-review.json')
        return Namespace(**vars(self.args),reviewed=r['plan_sha256'],review_note='已查看全部页面及运动预览')
    def test_plan_source_and_renderer_changes_require_new_preview(self):
        args=self.preview()
        with patch.object(app,'export_video') as export:
            self.plan['motion']='smooth';av.write(self.work/'plan.json',self.plan)
            with self.assertRaisesRegex(ValueError,'方案已变'):av.render(args)
            export.assert_not_called()
        args=self.preview();review=av.read(self.work/'preview-review.json');review['renderer_sha256']='old-version';av.write(self.work/'preview-review.json',review)
        with self.assertRaisesRegex(ValueError,'引擎已更新'):av.render(args)
        args=self.preview();image=next((self.work/'data').rglob('page.png'));Image.new('RGB',(960,540),'red').save(image)
        with self.assertRaisesRegex(ValueError,'导入页已变化'):av.render(args)
    def test_plain_renderer_is_part_of_review_fingerprint(self):
        original=Path.read_bytes
        before=av.renderer_digest(app)
        with patch.object(Path,'read_bytes',lambda path:original(path)+b'changed' if path.name=='plain_components.py' else original(path)):
            self.assertNotEqual(before,av.renderer_digest(app))

    def test_moved_work_folder_keeps_page_mapping_and_preview(self):
        self.preview();moved=Path(self.tmp.name)/'moved';shutil.move(self.work,moved);self.work=moved;self.args.work=str(moved)
        self.preview();state=app.read_project('d'*32)
        self.assertTrue(Path(state['pages_dir']).is_relative_to(moved.resolve()))
        files=av.read(moved/'preview-review.json')['files']
        self.assertEqual(len(files),3)
        self.assertTrue(any(x.endswith('-motion.png') for x in files))
    def test_single_whole_page_and_wrong_source_are_rejected(self):
        self.plan['pages'][0]['components']=self.plan['pages'][0]['components'][:1];av.write(self.work/'plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'两个真实组件'):av.load(self.args)
        self.plan['input_sha256']='different';av.write(self.work/'plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'指纹不匹配'):av.load(self.args)

if __name__=='__main__':unittest.main()
