import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from video_delivery import build_video_bundle,video_delivery_files

class DeliveryTests(unittest.TestCase):
 def test_user_manifest_and_zip_exclude_intermediates_without_deleting(self):
  with tempfile.TemporaryDirectory() as folder:
   out=Path(folder)
   keep=['视频.mp4','普通版.pptx','01-普通版.png','01-语义成品版.png','组件方案.json','agent-plan.json','agent-review.json','render-audit.json','审阅/说明.md']
   excluded=['frames/000001.png','motion-canvas/input.json','project/input.json','project/output/frame.png','node_modules/pkg/index.js','素材包.zip','old.log','.backups/plan.json']
   for name in keep+excluded:
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
   (out/'project/input.json').write_text('{"title":"editable"}')
   manifest=build_video_bundle({'cancel':False},out,out/'交付.zip')
   self.assertEqual(set(manifest),set(keep+['视频内容.json']))
   with zipfile.ZipFile(out/'交付.zip') as archive:
    self.assertIsNone(archive.testzip());self.assertEqual(set(archive.namelist()),set(manifest)|{'sha256.json'})
    for name,expected in manifest.items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),expected)
   self.assertTrue((out/'frames/000001.png').exists());self.assertTrue((out/'motion-canvas/input.json').exists())
 def test_cancel_during_zip_never_publishes_partial_bundle(self):
  with tempfile.TemporaryDirectory() as folder:
   out=Path(folder);(out/'视频.mp4').write_bytes(b'x'*2000000);job={'cancel':False};original=zipfile.ZipFile.open
   class CancelOnWrite:
    def __init__(self,stream):self.stream=stream
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def write(self,chunk):self.stream.write(chunk);job['cancel']=True
   def opened(archive,*args,**kw):
    stream=original(archive,*args,**kw)
    return CancelOnWrite(stream) if len(args)>1 and args[1]=='w' else stream
   with patch.object(zipfile.ZipFile,'open',opened),self.assertRaisesRegex(ValueError,'取消'):build_video_bundle(job,out,out/'交付.zip')
   self.assertFalse((out/'交付.zip').exists());self.assertFalse((out/'交付.zip.partial').exists());self.assertTrue((out/'视频.mp4').exists())


class AgentManifestCompatibilityTests(unittest.TestCase):
 def test_legacy_full_manifest_still_verifies(self):
  import agent_video as av
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as folder:
   work=Path(folder);out=work/'out';(out/'frames').mkdir(parents=True)
   (out/'视频.mp4').write_bytes(b'fixture');(out/'frames/legacy.png').write_bytes(b'legacy-debug')
   manifest={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['视频.mp4','frames/legacy.png']}
   (out/'sha256.json').write_text(json.dumps(manifest))
   with zipfile.ZipFile(out/'legacy.zip','w') as archive:
    for n in manifest:archive.write(out/n,n)
   (work/'latest-result.json').write_text(json.dumps({'directory':'out','video':'视频.mp4','bundle':'legacy.zip','frames':120,'duration':4}))
   with patch.object(av,'engine',return_value=SimpleNamespace(command=lambda *a,**k:None,ffmpeg=lambda:'ffmpeg')):av.verify(SimpleNamespace(work=str(work)))
 def test_new_scope_zip_exactly_matches_user_manifest(self):
  import agent_video as av
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as folder:
   work=Path(folder);out=work/'out';out.mkdir();(out/'视频.mp4').write_bytes(b'fixture')
   build_video_bundle({'cancel':False},out,out/'new.zip')
   (work/'latest-result.json').write_text(json.dumps({'directory':'out','video':'视频.mp4','bundle':'new.zip','frames':120,'duration':4,'delivery_scope':'user-files-v1'}))
   with patch.object(av,'engine',return_value=SimpleNamespace(command=lambda *a,**k:None,ffmpeg=lambda:'ffmpeg')):av.verify(SimpleNamespace(work=str(work)))

if __name__=='__main__':unittest.main()
