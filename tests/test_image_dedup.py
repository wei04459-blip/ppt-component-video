import copy, io, json, subprocess, sys, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image, PngImagePlugin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from image_dedup import core as c

class Images(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.src=self.root/'中文 (图).png';self.a=np.arange(7*5*3,dtype=np.uint8).reshape(5,7,3);meta=PngImagePlugin.PngInfo();meta.add_text('author','private');Image.fromarray(self.a).save(self.src,pnginfo=meta);self.config=c.validate({})
 def tearDown(self): self.tmp.cleanup()
 def test_schema(self):
  for patch_config in [{'seed':True},{'seed':' 1'},{'seed':2**64},{'unknown':0},{'effects':{'noise':{'strength':101}}},{'encoding':{'jpeg_quality':1.2}},{'schema_version':True},{'profile':'corrected'}]:
   with self.assertRaises(c.Error): c.validate(patch_config)
  self.assertEqual(c.validate({'seed':str(2**64-1)})['seed'],2**64-1)
 def test_neutral_and_flip(self):
  im,fp,fmt,w=c.load(self.src);self.assertTrue(np.array_equal(c.transform(im,fp['sha256'],self.config),self.a))
  for direction,expected in [('horizontal',self.a[:,::-1]),('vertical',self.a[::-1])]:
   config=c.validate({'effects':{'flip':{'enabled':True,'direction':direction}}});self.assertTrue(np.array_equal(c.transform(im,fp['sha256'],config),expected))
 def test_hsv(self):
  a=np.array([[[255,0,0],[0,255,0],[0,0,255],[80,80,80]]],dtype=np.uint8);im=Image.fromarray(a);config=c.validate({'effects':{'color':{'enabled':True,'hue_deg':120}}});self.assertTrue(np.array_equal(np.array(c.transform(im,'a',config)),np.array([[[0,255,0],[0,0,255],[255,0,0],[80,80,80]]])))
 def test_noise_border_and_scale(self):
  im,fp,fmt,w=c.load(self.src);conf=c.validate({'seed':str(2**64-1),'effects':{'noise':{'enabled':True},'border':{'enabled':True,'style':'gradient','width_px':2}}});a=np.array(c.transform(im,fp['sha256'],conf));b=np.array(c.transform(im,fp['sha256'],conf));self.assertTrue(np.array_equal(a,b));conf['effects']['border']['enabled']=False;self.assertTrue(np.array_equal(a[2:-2,2:-2],c.transform(im,fp['sha256'],conf)));conf['effects']['scale']['enabled']=True;self.assertEqual(c.transform(im,fp['sha256'],conf).size,im.size)
 def test_metadata_and_alpha(self):
  rgba=np.dstack([self.a,np.zeros(self.a.shape[:2],dtype=np.uint8)]);Image.fromarray(rgba).save(self.src);im,fp,fmt,w=c.load(self.src);self.assertTrue(np.array_equal(im,self.a));off=c.encode(im,fmt,self.config);on=c.encode(im,fmt,c.validate({'effects':{'metadata':{'enabled':True}}}));self.assertEqual(off,on);self.assertEqual(set(c.structure(on,'PNG')),{'IHDR','IDAT','IEND'})
  p=self.root/'x.jpg';ex=Image.Exif();ex[274]=6;Image.fromarray(self.a).save(p,exif=ex);im,fp,fmt,w=c.load(p);out=self.root/'out.jpg';out.write_bytes(c.encode(im,fmt,c.validate({'effects':{'metadata':{'enabled':True}}})));self.assertIsNone(c.inspect(out)['orientation']);self.assertNotIn('E1',c.inspect(out)['markers']);self.assertEqual(im.size,(7,5))
 def test_structure_bounds(self):
  for data,fmt in [(b'\xff\xd8\xff\xe1\x00\x00','JPEG'),(b'\x89PNG\r\n\x1a\n\x7f\xff\xff\xffIHDR','PNG')]:
   with self.assertRaises(c.Error): c.structure(data,fmt)
 def test_batch_collision_atomic_cancel(self):
  original=self.src.read_bytes();out=self.root/'out';conf=c.validate({'io':{'write_source_processed':False}});r=c.batch([self.src],out,conf);self.assertEqual(r['succeeded'],1);self.assertEqual(self.src.read_bytes(),original)
  conf['io']['collision_policy']='rename';r=c.batch([self.src],out,conf);self.assertTrue(Path(r['items'][0]['output']).name.endswith('_2.png'))
  conf['io']['collision_policy']='skip';r=c.batch([self.src],out,conf);self.assertEqual(r['skipped'],1)
  cancel=threading.Event();cancel.set();self.assertEqual(c.batch([self.src],self.root/'cancel',conf,cancel=cancel)['cancelled'],1)
  existing=out/'existing.png';existing.write_bytes(b'keep')
  with patch('os.replace',side_effect=PermissionError(13,'denied')):
   with self.assertRaises(PermissionError): c.atomic(existing,b'new','overwrite',None,set())
  self.assertEqual(existing.read_bytes(),b'keep');self.assertFalse(list(out.glob('*.tmp')))
 def test_source_changes_while_queued(self):
  second=self.root/'second.png';second.write_bytes(self.src.read_bytes());conf=c.validate({'io':{'write_source_processed':False}})
  def emit(e):
   if e['type']=='item_completed' and e['index']==0: second.write_bytes(b'changed')
  r=c.batch([self.src,second],self.root/'out',conf,emit);self.assertEqual(r['items'][1]['error_code'],'SOURCE_CHANGED')
 def test_all_enabled_neutral(self):
  conf=c.validate({'effects':{'noise':{'enabled':True,'strength':0},'rotation':{'enabled':True,'angle_deg':0},'scale':{'enabled':True,'percent':100},'color':{'enabled':True},'border':{'enabled':True,'width_px':0},'enhance':{'enabled':True,'blur':0,'sharpen':0,'contrast_pct':0},'metadata':{'enabled':True}}});im,fp,fmt,w=c.load(self.src);self.assertTrue(np.array_equal(c.transform(im,fp['sha256'],conf),self.a))
 def test_rotation_direction_and_odd_scale(self):
  im,fp,fmt,w=c.load(self.src)
  for direction in ['left','right']:
   conf=c.validate({'effects':{'rotation':{'enabled':True,'angle_deg':90,'direction':direction}}});expected=np.rot90(self.a,1 if direction=='left' else -1);self.assertTrue(np.array_equal(c.transform(im,fp['sha256'],conf),expected))
  conf=c.validate({'effects':{'scale':{'enabled':True,'percent':120}}});expected=im.resize((8,6),Image.Resampling.LANCZOS).crop((0,0,7,5));self.assertTrue(np.array_equal(c.transform(im,fp['sha256'],conf),expected))
 def test_jpeg_off_on_and_orientation(self):
  outputs=[]
  for orientation in [1,6]:
   src=self.root/f'{orientation}.jpg';ex=Image.Exif();ex[274]=orientation;Image.fromarray(self.a).save(src,exif=ex);im,fp,fmt,w=c.load(src);off=c.encode(im,fmt,self.config);on=c.encode(im,fmt,c.validate({'effects':{'metadata':{'enabled':True}}}));self.assertEqual(off,on);outputs.append(off)
  self.assertEqual(*outputs)
 def test_input_protection_and_batch_duplicate(self):
  conf=c.validate({'io':{'write_source_processed':False}});other=self.root/'processed_中文 (图).png';other.write_bytes(self.src.read_bytes());r=c.batch([self.src,other],self.root,conf);self.assertEqual(r['items'][0]['error_code'],'WOULD_OVERWRITE_INPUT')
  sub=self.root/'sub';sub.mkdir();same=sub/self.src.name;same.write_bytes(self.src.read_bytes());r=c.batch([self.src,same],self.root/'out',conf);self.assertEqual(r['items'][1]['error_code'],'DUPLICATE_OUTPUT_NAME')
 def test_middle_cancel_and_retry(self):
  other=self.root/'other.png';other.write_bytes(self.src.read_bytes());cancel=threading.Event();out=self.root/'out';conf=c.validate({'io':{'write_source_processed':False}})
  def emit(e):
   if e['type']=='item_completed':cancel.set()
  r=c.batch([self.src,other],out,conf,emit,cancel);self.assertEqual((r['succeeded'],r['cancelled']),(1,1));self.assertTrue((out/('processed_'+self.src.name)).exists());self.assertFalse((out/'processed_other.png').exists());self.assertEqual(c.batch([other],out,conf)['succeeded'],1)
 def test_io_switches_and_alias(self):
  conf=c.validate({'io':{'write_source_processed':False}});self.assertEqual(c.batch([self.src],self.root/'out',conf)['succeeded'],1);self.assertFalse((self.root/'processed').exists());conf['io']['write_source_processed']=True;conf['io']['preview_disk_side_effects']=False;r=c.batch([self.src],self.root/'processed',conf);self.assertTrue(r['items'][0]['intermediate_aliases_final']);self.assertTrue(r['items'][0]['intermediate_committed'])
 def test_unsupported_and_bad_inputs(self):
  webp=self.root/'x.webp';webp.write_bytes(b'webp')
  with self.assertRaises(c.Error) as error:c.load(webp)
  self.assertEqual(error.exception.code,'FORMAT_NOT_IMPLEMENTED')
  mismatch=self.root/'x.jpg';mismatch.write_bytes(self.src.read_bytes())
  with self.assertRaises(c.Error) as error:c.load(mismatch)
  self.assertEqual(error.exception.code,'FORMAT_MISMATCH')
  animated=self.root/'animated.png';Image.new('RGB',(2,2),'red').save(animated,save_all=True,append_images=[Image.new('RGB',(2,2),'blue')],duration=20)
  with self.assertRaises(c.Error) as error:c.load(animated)
  self.assertEqual(error.exception.code,'ANIMATED_NOT_SUPPORTED')
 def test_missing_16bit_disk_full(self):
  conf=c.validate({'io':{'write_source_processed':False}});r=c.batch([self.root/'missing.png'],self.root/'out',conf);self.assertEqual(r['items'][0]['error_code'],'FILE_NOT_FOUND')
  p=self.root/'16bit.png';Image.fromarray(np.zeros((2,2),dtype=np.uint16)).save(p)
  with self.assertRaises(c.Error) as error:c.load(p)
  self.assertEqual(error.exception.code,'UNSUPPORTED_IMAGE_MODE')
  out=self.root/'keep.png';out.write_bytes(b'keep')
  with patch('os.fsync',side_effect=OSError(28,'full')):
   with self.assertRaises(OSError):c.atomic(out,b'new','overwrite',None,set())
  self.assertEqual(out.read_bytes(),b'keep');self.assertFalse(list(self.root.glob('.*.tmp')))
 def test_cli_error_exit_codes(self):
  base=Path(__file__).parents[1];job=self.root/'job.json'
  for config in [{'profile':'corrected'},{'seed':True}]:
   job.write_text(json.dumps(dict(job_schema_version=1,inputs=[self.src.name],output_dir='out',config=config)));p=subprocess.run([sys.executable,'-m','image_dedup','run','--job',str(job)],cwd=base,capture_output=True,text=True);self.assertEqual(p.returncode,2)
  bad=self.root/'bad.png';bad.write_bytes(b'bad');job.write_text(json.dumps(dict(job_schema_version=1,inputs=[self.src.name,bad.name],output_dir='partial',config={'io':{'write_source_processed':False}})));p=subprocess.run([sys.executable,'-m','image_dedup','run','--job',str(job)],cwd=base,capture_output=True,text=True);self.assertEqual(p.returncode,1,p.stdout);last=json.loads(p.stdout.splitlines()[-1]);self.assertEqual((last['succeeded'],last['failed']),(1,1))
 def test_presets_bad_backup_and_restore(self):
  import image_service
  from types import SimpleNamespace
  def write_json(path,data):
   path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data));temp.replace(path)
  app=SimpleNamespace(DATA=self.root,write_json=write_json,file_url=lambda p:str(p));p=image_service.presets_path(app);p.write_text('broken')
  doc,warning=image_service.get_presets(app);backups=list(p.parent.glob('presets.bad-*.json'));self.assertTrue(warning);self.assertEqual(backups[0].read_text(),'broken');self.assertFalse(backups[0].stat().st_mode&0o222)
  doc={'preset_schema_version':1,'presets':[{'id':'a','name':'test','config':c.validate({'seed':str(2**64-1)})}],'selected_id':'a'};image_service.handle(app,'presets',{'document':doc});original=p.read_bytes();bad=copy.deepcopy(doc);bad['presets'][0]['config']['seed']=True
  with self.assertRaises(c.Error):image_service.handle(app,'presets',{'document':bad})
  self.assertEqual(p.read_bytes(),original)
 def test_preview_io_four_combinations(self):
  import image_service,base64
  from types import SimpleNamespace
  def write_json(path,data):
   path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data));temp.replace(path)
  app=SimpleNamespace(DATA=self.root,write_json=write_json,file_url=lambda p:str(p))
  for write in [False,True]:
   for preview in [False,True]:
    x=image_service.handle(app,'import',{'files':[{'name':'test.png','data':base64.b64encode(self.src.read_bytes()).decode()}]});f=x['files'][0];conf=c.validate({'io':{'write_source_processed':write,'preview_disk_side_effects':preview}});image_service.handle(app,'preview',{'session':x['session'],'image':f['id'],'config':conf,'generation':1});middle=Path(f['path']).parent/'processed'/'processed_test.png';self.assertEqual(middle.exists(),write and preview)
    r=c.batch([f['path']],self.root/f'out-{write}-{preview}',conf);self.assertEqual(r['succeeded'],1);self.assertEqual(middle.exists(),write)
 def test_cli_cancel_130(self):
  import signal
  big=self.root/'big.png';Image.new('RGB',(1600,1600),'red').save(big);job=self.root/'job.json';job.write_text(json.dumps(dict(job_schema_version=1,inputs=[big.name],output_dir='cancel-cli',config={'effects':{'noise':{'enabled':True}},'io':{'write_source_processed':False}})))
  process=subprocess.Popen([sys.executable,'-m','image_dedup','run','--job',str(job)],cwd=Path(__file__).parents[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);first=process.stdout.readline();self.assertEqual(json.loads(first)['type'],'job_started');process.send_signal(signal.SIGINT);stdout,stderr=process.communicate(timeout=30);self.assertEqual(process.returncode,130,stdout+stderr);self.assertEqual(json.loads(stdout.splitlines()[-1])['type'],'job_finished')
 def test_cli(self):
  job=self.root/'job.json';job.write_text(json.dumps(dict(job_schema_version=1,inputs=[self.src.name],output_dir='out',config={'io':{'write_source_processed':False}})));p=subprocess.run([sys.executable,'-m','image_dedup','run','--job',str(job)],cwd=Path(__file__).parents[1],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);events=[json.loads(x) for x in p.stdout.splitlines()];self.assertEqual(events[-1]['type'],'job_finished');self.assertEqual([e['seq'] for e in events],list(range(1,len(events)+1)))
if __name__=='__main__': unittest.main()
