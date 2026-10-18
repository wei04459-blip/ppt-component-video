import io, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from PIL import Image, PngImagePlugin

class NoteMetadataTests(unittest.TestCase):
    def test_note_and_edit_bundles_clean_without_pixel_changes(self):
        for kind in ('note','edit'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);pid='c'*32;p=root/pid;p.mkdir()
                app.write_json(p/'project.json',{'id':pid,'exports':[]})
                originals={}
                def export(job,payload,project):
                    out=project/'exports'/job['id'];layers=out/'01.layers';layers.mkdir(parents=True)
                    meta=PngImagePlugin.PngInfo();meta.add_text('Author','private')
                    Image.new('RGBA',(16,12),(12,34,56,100)).save(layers/'layer.png',pnginfo=meta)
                    exif=Image.Exif();exif[315]='private'
                    Image.new('RGB',(16,12),(90,20,130)).save(out/'01.jpg',exif=exif,icc_profile=b'private')
                    for f in out.rglob('*'):
                        if f.is_file():
                            with Image.open(f) as im: originals[str(f.relative_to(out))]=(im.mode,im.tobytes())
                    return {'directory':str(out),'images':[]}
                def immediate(fn):fn()
                with patch.object(app,'DATA',root),patch.object(app.POOL,'submit',side_effect=immediate),patch.object(app,'export_note',side_effect=export),patch.object(app.image_editor,'save_image',side_effect=lambda a,j,d,p:export(j,d,p)):
                    jid=app.submit(kind,{'project':pid})['job'];job=app.JOBS[jid]
                    self.assertEqual(job['status'],'done',job)
                    self.assertEqual(job['result']['metadata_cleaned'],2)
                    out=Path(job['result']['directory'])
                    with zipfile.ZipFile(out/'素材包.zip') as z:
                        for name,(mode,pixels) in originals.items():
                            data=z.read(name)
                            self.assertEqual(data,(out/name).read_bytes())
                            with Image.open(io.BytesIO(data)) as im:
                                self.assertEqual((im.mode,im.tobytes()),(mode,pixels))
                                self.assertFalse(im.getexif());self.assertNotIn('Author',im.info);self.assertNotIn('icc_profile',im.info)
                            before=(out/name).read_bytes();app.image_core.strip_metadata(out/name);self.assertEqual(before,(out/name).read_bytes())

if __name__=='__main__':unittest.main()
