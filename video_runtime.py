"""Standalone local PPT video runtime, independent of note/image-tool dependencies."""
import base64,json,os,re,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
from PIL import Image
import pymupdf
import component_video
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('TOOLBOX_DATA',str(Path.home()/'Documents'/'鱼丸创作工具箱'))).resolve()

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
    pages=dest/'pages';pages.mkdir(); count=0;objects={}
    for f in files:
        if job['cancel']: raise ValueError('任务已取消')
        name=Path(f['name']).name
        suffix=Path(name).suffix.lower()
        if suffix not in ['.pptx','.ppt','.pdf','.png','.jpg','.jpeg','.webp']: raise ValueError('不支持的文件类型：'+name)
        src=dest/(uuid.uuid4().hex+suffix);src.write_bytes(base64.b64decode(f['data'],validate=True))
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
    write_json(dest/'objects.json',objects)
    state=read_project(p.name);state['pages']=[file_url(x) for x in sorted(pages.glob('*.png'))];state['pages_dir']=str(pages);state['sources']=[f['name'] for f in files]
    state['updated']=time.time();write_json(p/'project.json',state)
    return {'pages':count}


def export_video(job,payload,p):
    return component_video.export(sys.modules[__name__],job,payload,p)
