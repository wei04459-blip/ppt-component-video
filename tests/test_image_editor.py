import copy, hashlib, json, tempfile, unittest, uuid
from pathlib import Path
import test_core
app=test_core.app
from PIL import Image, ImageChops
from xhs_engine.templates import render_template, _render_template
from xhs_engine.editable import render_layer
import image_editor

class EditorTests(unittest.TestCase):
    def test_layers_preserve_rendering_and_noop_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pages=[]
            for i in range(15):
                p=root/f'p{i}.png';Image.new('RGB',(960,540),(242-i*3,247,251)).save(p);pages.append(p)
            for tid,cfg in app.REGISTRY.items():
                if cfg.get('approval_status')=='pending_user_review':continue
                output=root/(tid+'.png');original=root/(tid+'-original.png')
                chosen=pages[:cfg.get('page_capacity',1)]
                render_template(cfg,app.TEMPLATE_ROOT,chosen,output,'课件展示',source_pages=pages)
                _render_template(cfg,app.TEMPLATE_ROOT,chosen,original,'课件展示',source_pages=pages)
                diff=ImageChops.difference(Image.open(output),Image.open(original))
                # Alpha rounding can differ by one at the edge of a shadow.
                self.assertLessEqual(max(v[1] for v in diff.getextrema()),2,tid)
                folder=root/(tid+'.layers');doc=json.loads((folder/'document.json').read_text())
                for layer in doc['layers']:
                    if not layer['textCount']:continue
                    bitmap=render_layer(layer,doc['size'],layer['texts'],layer['fontSize'])
                    self.assertEqual(bitmap.tobytes(),Image.open(folder/layer['image']).tobytes(),tid)
    def test_save_isolated_and_reopen_edit(self):
        pid=uuid.uuid4().hex;p=app.DATA/pid;p.mkdir();old=p/'exports'/uuid.uuid4().hex;old.mkdir(parents=True)
        page=p/'page.png';Image.new('RGB',(960,540),'white').save(page)
        target=old/'cover.png';render_template(app.REGISTRY['14'],app.TEMPLATE_ROOT,[page,page],target,'测试标题')
        other=old/'other.png';Image.new('RGB',(20,20),'red').save(other)
        result={'directory':str(old),'images':[app.file_url(target),app.file_url(other)],'copy':'标题'}
        app.write_json(p/'project.json',{'id':pid,'exports':[result]})
        payload={'project':pid,'image':app.file_url(target)}
        doc=image_editor.open_image(app,payload);layers=[l for l in doc['layers'] if l['textCount']]
        before=hashlib.sha256(target.read_bytes()).hexdigest()
        layers[0].update(texts=['已修改文字'],x=10,y=10,fontSize=60)
        edited=image_editor.save_image(app,{'id':uuid.uuid4().hex},dict(payload,layers=layers),p)
        new=Path(edited['directory'])
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),before)
        self.assertEqual(other.read_bytes(),(new/'other.png').read_bytes())
        self.assertNotEqual(target.read_bytes(),(new/'cover.png').read_bytes())
        app.write_json(p/'project.json',{'id':pid,'exports':[result,edited]})
        reopened=image_editor.open_image(app,dict(payload,image=edited['images'][0]))
        self.assertEqual(reopened['layers'][0]['texts'],['已修改文字'])
        with self.assertRaises(ValueError):image_editor.preview(app,dict(payload,layer=dict(layers[0],x=-1)))
        with self.assertRaises(ValueError):image_editor.open_image(app,dict(payload,image='/files/../../etc/passwd'))

if __name__=='__main__':unittest.main()
