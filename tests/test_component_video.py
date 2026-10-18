import copy,json,tempfile,unittest,uuid
from pathlib import Path
from PIL import Image,ImageChops
from pptx import Presentation
from pptx.util import Inches
import test_core
app=test_core.app
import component_video as cv

class ComponentTests(unittest.TestCase):
    def test_motion_has_exact_endpoints_and_no_double_exposure(self):
        source=Image.new('RGB',(320,180),'white')
        bitmap=Image.new('RGB',(80,120),'red')
        source.paste(bitmap,(224,36))
        tile=Image.new('RGB',(240,30),'blue')
        before=Image.new('RGB',source.size,'white');before.paste(tile,(16,18))
        item={'text':'文字','before':[.05,.1,.75,1/6],'target':[.7,.2,.25,2/3]}
        items=[(item,bitmap,tile)]
        for mode in ('smooth','stagger','lift'):
            self.assertEqual(cv.motion_stage(source,before,items,0,mode).tobytes(),before.tobytes())
            self.assertEqual(cv.motion_stage(source,before,items,3.0,mode).tobytes(),source.tobytes())
            frames=[cv.motion_stage(source,before,items,t/24,mode) for t in range(14,63)]
            self.assertGreater(len({f.tobytes() for f in frames}),20)
            # Red final / blue plain must never be alpha-blended into purple text.
            for frame in frames:
                self.assertFalse(any(r>5 and b>5 and g<5 for r,g,b in frame.get_flattened_data()))
        # After the style change, the portrait face retains its 2:3 ratio while moving.
        frame=cv.motion_stage(source,before,items,1.3,'smooth')
        coords=[(x,y) for y in range(180) for x in range(320) if frame.getpixel((x,y))==(255,0,0)]
        width=max(x for x,y in coords)-min(x for x,y in coords)+1
        height=max(y for x,y in coords)-min(y for x,y in coords)+1
        self.assertAlmostEqual(width/height,2/3,delta=.025)

    def test_native_objects_and_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'native.pptx';prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
            shape=slide.shapes.add_textbox(Inches(1),Inches(1),Inches(4),Inches(1));shape.text='真实标题'
            group=slide.shapes.add_group_shape();a=group.shapes.add_textbox(Inches(2),Inches(3),Inches(2),Inches(1));a.text='组合文字';prs.save(p)
            result=cv.object_pages(p)
            self.assertEqual(len(result[0]),2);self.assertEqual(result[0][0]['text'],'真实标题');self.assertEqual(result[0][1]['text'],'组合文字')
            for item in result[0]:cv.rectangle(item['target'])
    def test_validation_preview_and_stale_source(self):
        pid=uuid.uuid4().hex;p=app.DATA/pid;p.mkdir();src=p/'page.png';Image.new('RGB',(1600,900),'#204580').save(src);url=app.file_url(src)
        app.write_json(p/'project.json',{'id':pid,'pages':[url]})
        v={'mode':'components','motion':'stagger','pages':[{'source':url,'confirmed':True,'components':[{'text':'同一份内容','target':[.1,.1,.4,.3],'before':[.05,.1,.8,.6]}]}]}
        self.assertEqual(len(cv.validate(app,p,v)),1)
        result=cv.preview(app,{'project':pid,'video':v});self.assertTrue(result['pages'][0]['before'].startswith('data:image/png;'))
        source,before,items=cv.prepare(app,p,v['pages'][0]);self.assertEqual(source.size,(960,540));self.assertIsNotNone(ImageChops.difference(source,before).getbbox())
        bad=copy.deepcopy(v);bad['pages'][0]['confirmed']=False
        with self.assertRaises(ValueError):cv.validate(app,p,bad)
        cv.validate(app,p,bad,False)
        bad=copy.deepcopy(v);bad['pages'][0]['source']='/files/../../etc/passwd'
        with self.assertRaises(ValueError):cv.validate(app,p,bad)
        for r in [[-1,0,.1,.1],[0,0,float('nan'),.1],[.9,.1,.5,.1]]:
            with self.assertRaises(ValueError):cv.rectangle(r)

if __name__=='__main__':unittest.main()
