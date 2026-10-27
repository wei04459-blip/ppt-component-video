"""Local-only creator workbench. No agent, credentials, or cloud processing."""
from __future__ import annotations
import base64, copy, hashlib, json, os, re, shutil, signal, subprocess, sys, threading, time, uuid, zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'engine'
if not ENGINE.exists(): ENGINE = ROOT.parent / 'xhs-ppt-engine'
sys.path.insert(0, str(ENGINE))
from PIL import Image, ImageEnhance
import pymupdf
from xhs_engine.templates import load_templates, run_templates
DATA = Path(os.environ.get('TOOLBOX_DATA', str(Path.home() / 'Documents' / '鱼丸创作工具箱'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
import image_editor
import component_video
from video_delivery import build_video_bundle
import image_service
from image_dedup import core as image_core
JOBS = {}; LOCK = threading.RLock(); POOL = ThreadPoolExecutor(max_workers=1)
COMPONENT_REVIEWS = {}
REGISTRY, TEMPLATE_ROOT = load_templates()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); tmp.replace(path)


def project(pid):
    if not re.fullmatch(r'[a-f0-9]{32}', pid): raise ValueError('项目编号无效')
    p = DATA / pid
    if not (p / 'project.json').exists(): raise ValueError('项目不存在')
    return p


def read_project(pid): return json.loads((project(pid) / 'project.json').read_text())


def file_url(path): return '/files/' + path.relative_to(DATA).as_posix()


def command(job, args, cwd=None, timeout=600):
    if job['cancel']: raise ValueError('任务已取消')
    with open(job['log'], 'ab') as log:
        proc = subprocess.Popen([str(x) for x in args], cwd=cwd, stdout=log, stderr=log, start_new_session=os.name!='nt')
        job['process'] = proc
        start=time.monotonic()
        while proc.poll() is None:
            if job['cancel'] or time.monotonic()-start>timeout:
                if os.name!='nt': os.killpg(proc.pid, signal.SIGTERM)
                else: subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                raise ValueError('任务已取消' if job['cancel'] else '处理超时，请减少页数后重试')
            time.sleep(.15)
        job.pop('process', None)
        if proc.returncode: raise ValueError('处理失败：'+Path(job['log']).read_text(errors='replace')[-1200:])


def ffmpeg():
    p=shutil.which('ffmpeg')
    if not p:
        try:
            import imageio_ffmpeg
            p=imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError: raise ValueError('未找到视频编码组件，请重新运行启动入口')
    return p


def office():
    choices=[shutil.which('soffice'),str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'LibreOffice/program/soffice.exe'), '/Applications/LibreOffice.app/Contents/MacOS/soffice', r'C:\Program Files\LibreOffice\program\soffice.exe']
    return next((x for x in choices if x and Path(x).exists()), None)


def import_files(job, payload, p):
    files=payload.get('files', [])
    if not files: raise ValueError('请选择 PPT、PDF 或图片')
    dest=p/'imports'/job['id'];dest.mkdir(parents=True)
    pages=dest/'pages';pages.mkdir(); count=0;objects={};input_records=[]
    for f in files:
        if job['cancel']: raise ValueError('任务已取消')
        name=Path(f['name']).name
        suffix=Path(name).suffix.lower()
        if suffix not in ['.pptx','.ppt','.pdf','.png','.jpg','.jpeg','.webp']: raise ValueError('不支持的文件类型：'+name)
        src=dest/(uuid.uuid4().hex+suffix);src.write_bytes(base64.b64decode(f['data'],validate=True))
        input_sha=hashlib.sha256(src.read_bytes()).hexdigest();first_page=count+1
        if suffix=='.pptx':
            try: objects.update({str(count+i+1):v for i,v in enumerate(component_video.object_pages(src))})
            except Exception: pass
        if suffix in ['.pptx','.ppt']:
            exe=office()
            if not exe: raise ValueError('PPT 转图需要 LibreOffice；也可以先导入 PDF 或图片')
            job['message']='正在将 PPT 转为页面'
            command(job,[exe,'-env:UserInstallation='+ (dest/'office-profile').as_uri(),'--headless','--convert-to','pdf','--outdir',dest,src],timeout=180)
            src=src.with_suffix('.pdf')
            if not src.exists(): raise ValueError('未生成 PDF，请检查课件是否加密或损坏')
        if src.suffix=='.pdf':
            with pymupdf.open(src) as doc:
                if doc.needs_pass: raise ValueError('请先解锁 PDF 后导入')
                if doc.page_count+count>200: raise ValueError('首版每个项目最多导入 200 页')
                for page in doc:
                    if job['cancel']: raise ValueError('任务已取消')
                    count+=1;page.get_pixmap(dpi=120).save(str(pages/f'page_{count:03d}.png'))
                    job['message']=f'正在读取第 {count} 页'
        else:
            count+=1
            with Image.open(src) as im: im.convert('RGB').save(pages/f'page_{count:03d}.png')
        input_records.append(dict(name=name,sha256=input_sha,firstPage=first_page,lastPage=count))
    write_json(dest/'objects.json',objects)
    state=read_project(p.name);state['pages']=[file_url(x) for x in sorted(pages.glob('*.png'))];state['pages_dir']=str(pages);state['sources']=[f['name'] for f in files];state['imported_inputs']=input_records
    state['updated']=time.time();write_json(p/'project.json',state)
    return {'pages':count}


def export_note(job, payload, p):
    state=read_project(p.name); cfg=payload['note']; tid=str(cfg['template_id'])
    if tid not in REGISTRY or REGISTRY[tid].get('approval_status')=='pending_user_review': raise ValueError('请选择可用模板')
    title=cfg.get('title','').strip()
    if not title or len(title)>20: raise ValueError('笔记标题需为 1–20 个字符')
    if not state.get('pages_dir'): raise ValueError('请先导入课件')
    if '\n' in cfg.get('display_title',''): raise ValueError('图内标题请保持单行')
    out=p/'exports'/job['id'];out.mkdir(parents=True)
    note={**cfg,'body':'','template_id':tid}
    plan=out/'方案.json';write_json(plan,{'notes':[note]})
    job['message']='正在生成封面和内容图'
    command(job,[sys.executable,ROOT/'worker.py',out,plan,state['pages_dir']])
    result=json.loads((out/'worker-result.json').read_text())
    if payload.get('variation'):
        for path in (out/tid).glob('*.png'):
            with Image.open(path) as im: ImageEnhance.Contrast(im.convert('RGB')).enhance(1.015).save(path)
            docpath=path.parent/(path.stem+'.layers')/'document.json'
            if docpath.exists():
                doc=json.loads(docpath.read_text());doc['contrast']=1.015;write_json(docpath,doc)
    if payload.get('compress'):
        for path in (out/tid).glob('*.png'):
            with Image.open(path) as im: im.convert('RGB').save(path.with_suffix('.jpg'),quality=88,optimize=True)
    imgs=[file_url(x) for x in sorted((out/tid).glob('*.png'))]
    return {'images':imgs,'check':result['publication_check'],'directory':str(out),'copy':title+'\n\n'+' '.join('#'+x for x in cfg.get('topics',[]))}


def validate_video(v):
    if not re.fullmatch('#[0-9a-fA-F]{6}',v.get('color','')): raise ValueError('请选择有效颜色')
    for k in ['topLabel','bottomLabel']:
        if not 1<=len(v.get(k,''))<=12: raise ValueError('上下标签需要 1–12 字')
    if not 1<=len(v.get('pages',[]))<=6: raise ValueError('视频需要 1–6 个段落')
    for page in v['pages']:
        if not 1<=len(page.get('title',''))<=24: raise ValueError('视频页标题需要 1–24 字')
        if len(page.get('subtitle',''))>38: raise ValueError('视频页说明最多 38 字')
        if page.get('layout') not in ['grid','columns','reverse']: raise ValueError('请选择有效视频布局')
        if not 2<=len(page.get('items',[]))<=6: raise ValueError('每段请填写 2–6 个组件')
        for item in page['items']:
            if not 1<=len(item.get('heading',''))<=14 or len(item.get('body',''))>45: raise ValueError('组件标题需要 1–14 字，内容最多 45 字')
    return v


def export_video(job,payload,p):
    v=payload['video']
    if v.get('mode')=='components': return component_video.export(sys.modules[__name__],job,payload,p)
    if v.get('mode')=='v7':
        if not isinstance(v.get('texts',{}),dict) or any(not isinstance(x,str) or len(x)>500 for x in v.get('texts',{}).values()): raise ValueError('请缩短文本内容')
        metrics=v.get('metrics',[84,50,35.6])
        fields=json.loads((ROOT/'video'/'v7-fields.json').read_text())
        limits={k:max(30,len(value)) for group in fields.values() for k,value in group.items()}
        if any(k not in limits or len(value)>limits[k] for k,value in v.get('texts',{}).items()): raise ValueError('文字超出模板容量，请精简后重试')
        if not 1<=v.get('startMonth',3)<=12: raise ValueError('起始月份应在 1–12')
        ranges=v.get('scheduleRanges')
        if ranges is not None and (len(ranges)!=10 or any(len(r)!=2 or not 0<=r[0]<r[1]<=24 for r in ranges)): raise ValueError('进度条起止位置应为 0–24，终点大于起点')
        if not re.fullmatch('#[0-9a-fA-F]{6}',v.get('color','')): raise ValueError('请选择有效颜色')
        if any(not 1<=len(v.get(k,''))<=12 for k in ['topLabel','bottomLabel']): raise ValueError('上下标签需要 1–12 字')
        if len(metrics)!=3 or any(type(x) not in (int,float) or not 0<=x<=100 for x in metrics): raise ValueError('当前图表范围为 0–100，请填入有效数值')
        v['pages']=[{}, {}, {}]
    else: validate_video(v)
    out=p/'exports'/job['id'];out.mkdir(parents=True)
    work=out/'project';shutil.copytree(ROOT/'video',work,ignore=shutil.ignore_patterns('node_modules','output','assets'))
    modules=ROOT/'video'/'node_modules'
    if not modules.exists(): raise ValueError('视频依赖未安装，请运行安装依赖')
    if os.name=='nt':
        shutil.copytree(modules,work/'node_modules')
    else: (work/'node_modules').symlink_to(modules.resolve(),target_is_directory=True)
    assets=work/'assets';assets.mkdir();shutil.copy(ENGINE/'fonts'/'LXGWWenKai-Medium.ttf',assets/'label.ttf');shutil.copy(ENGINE/'fonts'/'NotoSansCJKsc-Regular.otf',assets/'regular.otf');shutil.copy(ENGINE/'fonts'/'NotoSansCJKsc-Bold.otf',assets/'bold.otf')
    if v.get('mode')=='v7':
        shutil.copytree(ROOT/'video'/'v7-assets',assets,dirs_exist_ok=True)
        fields=json.loads((ROOT/'video'/'v7-fields.json').read_text())
        texts={k:value for group in fields.values() for k,value in group.items()}
        texts.update(v.get('texts',{}));texts['自己瞎做的']=v.get('topLabel','自己瞎做的');texts['护士长想要的']=v.get('bottomLabel','护士长想要的')
        v['texts']=texts
        for name,img in v.pop('images',{}).items():
            if name not in [x.name for x in (ROOT/'video'/'v7-assets').glob('*.png')]: raise ValueError('图片位置无效')
            import io
            with Image.open(io.BytesIO(base64.b64decode(img,validate=True))) as im: im.convert('RGB').save(assets/name)
        (work/'src'/'project.ts').write_text("import {makeProject} from '@motion-canvas/core';\nimport cover from './v7/cover?scene';\nimport plan from './v7/plan?scene';\nimport effects from './v7/effects?scene';\nexport default makeProject({scenes:[cover,plan,effects]});")
    write_json(work/'input.json',v)
    node=shutil.which('node')
    if not node: raise ValueError('未找到视频运行环境 Node.js')
    job['message']='正在制作组件动画，通常需要 1–3 分钟'
    command(job,[node,'render.mjs'],cwd=work,timeout=900)
    frames=sorted((work/'output'/'movie').rglob('*.png'))
    expected=len(v['pages'])*105
    if len(frames)<expected: raise ValueError(f'动画帧不完整：{len(frames)}/{expected}')
    seq=out/'frames';seq.mkdir()
    for i,frame in enumerate(frames[:expected]): shutil.copyfile(frame,seq/f'{i:06d}.png')
    job['message']='正在合成 MP4'
    movie=out/'对比视频.mp4'
    audio_args=['-stream_loop','-1','-i',ROOT/'video'/'music.wav'] if v.get('music',True) else ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    command(job,[ffmpeg(),'-y','-framerate','30','-i',seq/'%06d.png',*audio_args,'-frames:v',str(expected),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',movie])
    command(job,[ffmpeg(),'-v','error','-i',movie,'-f','null','-'])
    previews=[]
    for i in range(len(v['pages'])):
        for offset in [0,44,95]:
            target=out/f'预览_{i+1}_{offset}.png';shutil.copyfile(seq/f'{i*105+offset:06d}.png',target);previews.append(file_url(target))
    shutil.rmtree(seq);shutil.rmtree(work/'output')
    return {'video':file_url(movie),'images':previews,'frames':expected,'duration':len(v['pages'])*3.5,'directory':str(out)}


def clean_note_metadata(out):
    """Mandatory for new note exports and edited versions, before ZIP creation."""
    count=0
    for path in sorted(out.rglob('*')):
        if path.suffix.lower() not in ('.png','.jpg','.jpeg') or not path.is_file():continue
        image_core.strip_metadata(path)
        count+=1
    return count


def component_review_key(p,video):
    # Bind actual visual inputs and order, excluding confirmation/editor-only state.
    pages=[];sources=[]
    for page in video.get('pages',[]):
        value={k:copy.deepcopy(page[k]) for k in ('source','number','components','scene','design') if k in page}
        pages.append(value)
        path=(DATA/page['source'][len('/files/'):]).resolve()
        if not path.is_relative_to(p.resolve()):raise ValueError('源图片路径无效')
        sources.append(hashlib.sha256(path.read_bytes()).hexdigest())
    import semantic_scene
    record=dict(motion=video.get('motion'),pages=pages,sources=sources,renderer=semantic_scene.renderer_fingerprint(ROOT))
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def preview_components(payload):
    p=project(payload['project']);video=payload['video']
    component_video.validate(sys.modules[__name__],p,video,False)
    key=component_review_key(p,video)
    result=component_video.preview(sys.modules[__name__],payload)
    if component_review_key(p,video)!=key:raise ValueError('预览期间源文件或工具已变，请重新预览')
    with LOCK:COMPONENT_REVIEWS[p.name]=key
    result['previewToken']=key
    return result


def require_component_review(p,payload):
    video=payload.get('video',{})
    if video.get('mode')!='components':return
    component_video.validate(sys.modules[__name__],p,video)
    if COMPONENT_REVIEWS.get(p.name)!=component_review_key(p,video):
        raise ValueError('当前方案未有效预览或预览已失效，请重新预览并核对后再制作')


def submit(kind,payload):
    payload=copy.deepcopy(payload);p=project(payload['project'])
    with LOCK:
        if any(j.get('project')==p.name and j.get('status') in ('queued','running') for j in JOBS.values()):
            raise ValueError('该项目已有任务在制作或等待处理，请等待结束或取消完成后再试')
        if kind=='video':require_component_review(p,payload)
        jid=uuid.uuid4().hex
        job={'id':jid,'project':p.name,'kind':kind,'status':'queued','message':'等待处理','cancel':False,'log':str(p/(jid+'.log'))}
        JOBS[jid]=job
    def run():
        try:
            if job['cancel']: raise ValueError('任务已取消')
            job['status']='running'
            result={'import':import_files,'note':export_note,'video':export_video,'edit':lambda j,d,p:image_editor.save_image(sys.modules[__name__],j,d,p)}[kind](job,payload,p)
            if job['cancel']: raise ValueError('任务已取消')
            if kind!='import':
                out=Path(result['directory']);bundle=out/'素材包.zip'
                if kind in ('note','edit'):
                    job['message']='正在清除图片元信息'
                    result['metadata_cleaned']=clean_note_metadata(out)
                if kind=='video':
                    build_video_bundle(job,out,bundle);result['delivery_scope']='user-files-v1'
                else:
                    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
                        for f in out.rglob('*'):
                            if job['cancel']:raise ValueError('任务已取消')
                            if f.is_file() and f!=bundle and 'node_modules' not in f.parts and 'project' not in f.relative_to(out).parts:z.write(f,f.relative_to(out))
                if job['cancel']:raise ValueError('任务已取消')
                result['download']=file_url(bundle)
                state=read_project(p.name);state.setdefault('exports',[]).append(result);write_json(p/'project.json',state)
            job.update(status='done',message='本地导出完成' if kind!='import' else '素材导入完成',result=result)
        except Exception as e: job.update(status='cancelled' if job['cancel'] else 'error',message=str(e))
        finally: write_json(p/(jid+'-task.json'),{k:v for k,v in job.items() if k!='process'})
    POOL.submit(run);return {'job':jid}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self, data, code=200):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        try:
            if self.headers.get('Host','').split(':')[0] not in ['127.0.0.1','localhost']: return self.respond({'error':'仅允许本机访问'},403)
            path=unquote(urlparse(self.path).path)
            if path=='/api/health': return self.respond({'app':'creator-toolbox','version':'0.1.0'})
            if path=='/api/v7':
                return self.respond({'fields':json.loads((ROOT/'video'/'v7-fields.json').read_text()),'images':[x.name for x in (ROOT/'video'/'v7-assets').glob('*.png')]})
            if path=='/api/state':
                projects=[]
                for p in DATA.glob('*/project.json'):
                    try: projects.append(json.loads(p.read_text()))
                    except (ValueError,OSError): pass
                templates=[{'id':k,'name':v['name'],'capacity':v.get('page_capacity',1),'contentCapacity':v.get('content_default_capacity',1),'fixed':v.get('cover_fixed_pages',{}),'award':v.get('award_label',''),'usage':v.get('usage','')} for k,v in REGISTRY.items() if v['status']=='ready' and v.get('approval_status')!='pending_user_review']
                return self.respond({'projects':sorted(projects,key=lambda x:x.get('updated',0),reverse=True),'templates':templates,'dependencies':{'ppt':bool(office()),'video':bool(shutil.which('node') and shutil.which('ffmpeg') and (ROOT/'video'/'node_modules').exists())}})
            if path.startswith('/api/job/'):
                job=JOBS.get(path.rsplit('/',1)[1]);return self.respond({k:v for k,v in job.items() if k!='process'} if job else {'status':'error','message':'任务不存在'})
            base=DATA if path.startswith('/files/') else ROOT/'web'
            relative=path[len('/files/'):] if path.startswith('/files/') else (path.lstrip('/') or 'index.html')
            f=(base/relative).resolve()
            if not f.is_relative_to(base.resolve()) or not f.is_file(): return self.respond({'error':'文件不存在'},404)
            import mimetypes
            size=f.stat().st_size
            start,end=0,size-1
            range_header=self.headers.get('Range','')
            if range_header:
                match=re.fullmatch(r'bytes=(\d+)-(\d*)',range_header)
                if not match: return self.respond({'error':'无效读取范围'},416)
                start=int(match[1]);end=min(int(match[2]) if match[2] else size-1,size-1)
                if start>end: return self.respond({'error':'读取范围超出文件'},416)
            self.send_response(206 if range_header else 200)
            self.send_header('Content-Type',mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(end-start+1))
            self.send_header('Accept-Ranges','bytes')
            if range_header: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            with f.open('rb') as stream:
                stream.seek(start);remaining=end-start+1
                while remaining>0:
                    chunk=stream.read(min(1024*1024,remaining))
                    if not chunk: break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as e: self.respond({'error':str(e)},400)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if self.headers.get('Host','').split(':')[0] not in ['127.0.0.1','localhost']:
                return self.respond({'error':'仅允许本机访问'},403)
            if origin and origin!=f'http://{self.headers.get("Host")}': return self.respond({'error':'仅允许本机界面操作'},403)
            if 'application/json' not in self.headers.get('Content-Type',''): return self.respond({'error':'请求格式不正确'},415)
            size=int(self.headers.get('Content-Length',0))
            if size>150*1024*1024: raise ValueError('单次导入请小于 100 MB')
            data=json.loads(self.rfile.read(size));path=urlparse(self.path).path
            if path.startswith('/api/images/'):
                return self.respond(image_service.handle(sys.modules[__name__],path.rsplit('/',1)[1],data))
            if path=='/api/project':
                pid=data.get('id') or uuid.uuid4().hex
                if data.get('id'): p=project(pid);state=read_project(pid)
                else: p=DATA/pid;p.mkdir();state={'id':pid,'pages':[],'exports':[]}
                for key in ['name','note','video']:
                    if key in data: state[key]=data[key]
                state['updated']=time.time();write_json(p/'project.json',state);return self.respond(state)
            if path=='/api/components/import-plan':
                import ai_video_plan
                return self.respond(ai_video_plan.import_plan(sys.modules[__name__],data))
            if path=='/api/components/analyse': return self.respond(component_video.analyse(sys.modules[__name__],data))
            if path=='/api/components/preview': return self.respond(preview_components(data))
            if path=='/api/editor/open': return self.respond(image_editor.open_image(sys.modules[__name__],data))
            if path=='/api/editor/preview': return self.respond(image_editor.preview(sys.modules[__name__],data))
            if path in ['/api/import','/api/note','/api/video','/api/edit']: return self.respond(submit(path.rsplit('/',1)[1],data))
            if path=='/api/cancel':
                if data['job'] in JOBS: JOBS[data['job']]['cancel']=True
                return self.respond({'ok':True})
            return self.respond({'error':'接口不存在'},404)
        except Exception as e: self.respond({'error':str(e)},400)


def main():
    import argparse,webbrowser
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    write_json(DATA/'running.json',{'url':url})
    print(url,flush=True)
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        for job in JOBS.values(): job['cancel']=True
        server.server_close()

if __name__=='__main__': main()
