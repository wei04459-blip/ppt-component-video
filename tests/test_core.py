import os,sys,tempfile,unittest
from pathlib import Path
os.environ['TOOLBOX_DATA']=tempfile.mkdtemp(prefix='toolbox-tests-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class CoreTests(unittest.TestCase):
    def test_project_paths_reject_traversal(self):
        for bad in ['../outside','/tmp/x','x'*32,'']:
            with self.assertRaises(ValueError):app.project(bad)
    def test_video_invalid_limits(self):
        v={'color':'#123b78','topLabel':'普通版','bottomLabel':'美化版','pages':[{'title':'标题','subtitle':'','layout':'grid','items':[{'heading':'甲','body':'内容'},{'heading':'乙','body':'内容'}]}]}
        self.assertEqual(app.validate_video(v),v)
        for key,value in [('color','url(http://bad)'),('pages',[]),('topLabel','长'*13)]:
            with self.assertRaises(ValueError):app.validate_video({**v,key:value})
        v['pages'][0]['items'][0]['body']='超'*46
        with self.assertRaises(ValueError):app.validate_video(v)
    def test_all_enabled_templates_render_with_bundled_fonts(self):
        from PIL import Image
        from xhs_engine.templates import render_template
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);pages=[]
            for i in range(15):
                p=folder/f'page_{i+1:03d}.png';Image.new('RGB',(960,540),(240-i*4,248,251)).save(p);pages.append(p)
            for tid,cfg in app.REGISTRY.items():
                if cfg.get('approval_status')=='pending_user_review':continue
                output=folder/(tid+'.png')
                render_template(cfg,app.TEMPLATE_ROOT,pages[:cfg.get('page_capacity',1)],output,'课件展示',source_pages=pages)
                with Image.open(output) as image:self.assertEqual(image.size,tuple(cfg['output_size']))
    def test_bad_import_cannot_replace_existing_pages(self):
        import base64
        pid='a'*32;p=app.DATA/pid;p.mkdir()
        original={'id':pid,'pages':['keep'],'pages_dir':'keep'}
        app.write_json(p/'project.json',original)
        with self.assertRaises(Exception):
            app.import_files({'id':'bad','cancel':False},{'files':[{'name':'broken.png','data':base64.b64encode(b'invalid').decode()}]},p)
        self.assertEqual(app.read_project(pid),original)

if __name__=='__main__':unittest.main()
