"""Portable Agent entry point; same import/preview/render engine as the GUI."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def doctor():
    modules = ['PIL', 'pymupdf', 'pptx']
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    office = next((str(p) for p in [Path(shutil.which('soffice') or '__missing__'),
        Path('/Applications/LibreOffice.app/Contents/MacOS/soffice'),
        Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'LibreOffice/program/soffice.exe'] if p.is_file()), None)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg and importlib.util.find_spec('imageio_ffmpeg'):
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    encoder_ok = False
    if ffmpeg:
        probe = subprocess.run([ffmpeg, '-hide_banner', '-encoders'], capture_output=True, text=True)
        encoder_ok = probe.returncode == 0 and 'libx264' in probe.stdout and 'aac' in probe.stdout
    result = dict(python=sys.version.split()[0], missing_modules=missing, libreoffice=office,
                  ffmpeg=ffmpeg, encoders_ok=encoder_ok, engine=(ROOT/'engine').is_dir(),
                  ready=sys.version_info >= (3, 11) and not missing and bool(office) and encoder_ok and (ROOT/'engine').is_dir())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ready'] else 2


def engine(work):
    # Every CLI work folder is isolated from the user's running GUI service.
    os.environ['TOOLBOX_DATA'] = str(work/'data')
    # Headless LibreOffice may otherwise miss CJK fonts despite successful export.
    # Configure only this CLI process; never install or change system fonts.
    from xml.sax.saxutils import escape
    fontdirs = [ROOT/'engine/fonts', Path('/System/Library/Fonts'), Path('/Library/Fonts'),
                Path.home()/'Library/Fonts', Path('/usr/share/fonts'), Path('/usr/local/share/fonts'),
                Path.home()/'.fonts', Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts']
    config = work/'fontconfig.xml'
    config.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'+
        ''.join('<dir>'+escape(str(d))+'</dir>' for d in fontdirs if d.is_dir())+
        '<cachedir>'+escape(str(work/'font-cache'))+'</cachedir>'+
        '<alias><family>sans-serif</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>'+
        '</fontconfig>',encoding='utf-8')
    os.environ['FONTCONFIG_FILE'] = str(config)
    import video_runtime as app
    app.DATA = work/'data'
    app.DATA.mkdir(parents=True, exist_ok=True)
    return app


def job(work, tag):
    return dict(id=uuid.uuid4().hex, cancel=False, log=str(work/(tag+'.log')))


def prepare(args):
    source = Path(args.ppt).expanduser().resolve()
    if source.suffix.lower() not in ('.ppt', '.pptx', '.pdf') or not source.is_file():
        raise ValueError('请提供存在的 PPT/PPTX/PDF 文件')
    work = Path(args.work).expanduser().resolve()
    if work.exists():
        raise ValueError('工作目录已存在；请使用新目录，避免覆盖已有作品')
    work.mkdir(parents=True)
    app = engine(work)
    pid = uuid.uuid4().hex
    p = app.DATA/pid
    p.mkdir()
    app.write_json(p/'project.json', dict(id=pid, name=source.stem, exports=[]))
    app.import_files(job(work, 'import'), dict(files=[dict(name=source.name,
        data=base64.b64encode(source.read_bytes()).decode())]), p)
    state = app.read_project(pid)
    analysis = app.component_video.analyse(app, {'project': pid})
    # Relative paths and page numbers keep plans valid after moving the folder.
    catalog = []
    for page in analysis['pages']:
        local = app.DATA/page['source'][len('/files/'):]
        catalog.append(dict(number=page['number'], image=str(local.relative_to(work)), objects=page['objects']))
    manifest = dict(schemaVersion=1, project=pid, input_name=source.name, input_sha256=digest(source),
                    pages=catalog, notice=analysis['notice'])
    write(work/'project.json', manifest)
    write(work/'source-hashes.json', {x['image']: digest(work/x['image']) for x in catalog})
    from PIL import Image, ImageDraw
    for start in range(0, len(catalog), 12):
        batch = catalog[start:start+12]
        sheet = Image.new('RGB', (1200, 260*((len(batch)+2)//3)), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, page in enumerate(batch):
            with Image.open(work/page['image']) as im:
                im.thumbnail((380, 225))
                x, y = (i%3)*400, (i//3)*260
                sheet.paste(im, (x+(400-im.width)//2, y+25))
                draw.text((x+12, y+5), f"Page {page['number']}", fill='black')
        sheet.save(work/f'contact-{start//12+1:02d}.jpg', quality=90)
    selected = [int(x) for x in args.pages.split(',')] if args.pages else [x['number'] for x in catalog[:3]]
    if not 1 <= len(selected) <= 6 or len(set(selected)) != len(selected) or any(n<1 or n>len(catalog) for n in selected):
        raise ValueError('请选择 1–6 个不重复、存在的页号')
    plan = dict(schemaVersion=1, input_sha256=manifest['input_sha256'], motion='stagger', music=True, pages=[])
    for n in selected:
        objects = catalog[n-1]['objects']
        cols = 1 if len(objects)<=3 else 2 if len(objects)<=12 else 4
        rows = max(1, (len(objects)+cols-1)//cols)
        components = [dict(id=o['id'], name=o['name'], text=o['text'], target=o['target'],
            before=[.025+(i%cols)*.95/cols, .025+(i//cols)*.95/rows, .95/cols-.025, .95/rows-.025]) for i,o in enumerate(objects)]
        plan['pages'].append(dict(number=n, components=components))
    write(work/'plan.json', plan)
    print(json.dumps(dict(work=str(work), plan=str(work/'plan.json'), pages=len(catalog),
        next='查看 contact-*.jpg 和原页；编辑 plan.json。图片型页面需 Agent 视觉框选，空组件不能直接导出。'), ensure_ascii=False))


def load(args):
    work = Path(args.work).expanduser().resolve()
    manifest = read(work/'project.json')
    planpath = Path(args.plan).expanduser().resolve() if args.plan else work/'plan.json'
    plan = read(planpath)
    if plan.get('schemaVersion') != 1 or plan.get('input_sha256') != manifest['input_sha256']:
        raise ValueError('方案版本或源课件指纹不匹配；请重新 prepare')
    for path, expected in read(work/'source-hashes.json').items():
        if digest(work/path) != expected:
            raise ValueError('导入页已变化；请重新 prepare，不能沿用旧方案')
    app = engine(work)
    p = app.project(manifest['project'])
    # Repair absolute state paths only inside this work folder after relocation.
    state = app.read_project(p.name)
    state['pages'] = [app.file_url(work/x['image']) for x in manifest['pages']]
    state['pages_dir'] = str((work/manifest['pages'][0]['image']).parent)
    app.write_json(p/'project.json', state)
    video = dict(mode='components', motion=plan.get('motion'), music=plan.get('music', True), pages=[])
    numbers=[]
    for page in plan.get('pages', []):
        number=page.get('number')
        if type(number) is not int or not 1<=number<=len(manifest['pages']) or number in numbers:
            raise ValueError('方案页号无效或重复')
        numbers.append(number)
        components=page.get('components', [])
        if len(components)<2:
            raise ValueError(f'第 {number} 页至少需要两个真实组件；不可用整页替代组件动画')
        video['pages'].append(dict(number=number, source=state['pages'][number-1], components=components, confirmed=True))
    app.component_video.validate(app,p,video)
    return work, manifest, planpath, app, p, video


def preview(args):
    work, manifest, planpath, app, p, video = load(args)
    out=work/'previews'/uuid.uuid4().hex
    out.mkdir(parents=True)
    from PIL import Image, ImageDraw
    files=[]
    for page in video['pages']:
        source, before, items=app.component_video.prepare(app,p,page)
        board=Image.new('RGB',(source.width*2,source.height),'white')
        board.paste(before,(0,0));board.paste(source,(source.width,0))
        name=out/f"page-{page['number']:03d}-before-after.png"
        board.save(name);files.append(name)
        name=out/f"page-{page['number']:03d}-motion.png"
        app.component_video.motion_preview(source,before,items,video['motion']).save(name);files.append(name)
        boxes=source.copy();draw=ImageDraw.Draw(boxes)
        for i,(item,_,_) in enumerate(items):
            x,y,w,h=item['target'];rect=(x*source.width,y*source.height,(x+w)*source.width,(y+h)*source.height)
            draw.rectangle(rect,outline='#e60000',width=3);draw.text((rect[0]+3,rect[1]+3),str(i+1),fill='#e60000',stroke_width=1,stroke_fill='white')
        name=out/f"page-{page['number']:03d}-regions.png"
        boxes.save(name);files.append(name)
    review=dict(plan_sha256=digest(planpath),input_sha256=manifest['input_sha256'],
                renderer_sha256=digest(Path(app.component_video.__file__)),
                files={str(f.relative_to(work)):digest(f) for f in files})
    write(work/'preview-review.json',review)
    print(json.dumps(dict(previews=str(out),review_token=review['plan_sha256'],
        next='打开所有预览核对内容、裁剪、布局。修改方案后重新 preview；看过正确预览后 render --reviewed 此令牌 --review-note 核对说明。'),ensure_ascii=False))


def render(args):
    work, manifest, planpath, app, p, video = load(args)
    review=read(work/'preview-review.json')
    if args.reviewed!=digest(planpath) or review['plan_sha256']!=args.reviewed or review['input_sha256']!=manifest['input_sha256']:
        raise ValueError('方案已变或未预览；请重新 preview 并检查')
    if review.get('renderer_sha256')!=digest(Path(app.component_video.__file__)):
        raise ValueError('视频引擎已更新，请重新 preview 并检查后再导出')
    for path, expected in review['files'].items():
        if digest(work/path)!=expected:raise ValueError('预览已变化，请重新 preview')
    if len(args.review_note.strip())<8:raise ValueError('请记录实际核对了什么，不能只填通过')
    j=job(work,'render')
    result=app.export_video(j,dict(video=video),p)
    out=Path(result['directory'])
    shutil.copy2(planpath,out/'agent-plan.json')
    write(out/'agent-review.json',dict(note=args.review_note,preview=review,
          input_name=manifest['input_name'],input_sha256=manifest['input_sha256']))
    # export_video already decodes the complete MP4 and fails on decode errors.
    result.update(decode_verified=True, review_note=args.review_note)
    write(out/'result.json',result)
    write(out/'sha256.json',{str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()})
    bundle=out/'视频交付包.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for f in out.rglob('*'):
            if f.is_file() and f!=bundle:z.write(f,f.relative_to(out))
    state=app.read_project(p.name);state['video']=video;state.setdefault('exports',[]).append(result);app.write_json(p/'project.json',state)
    write(work/'latest-result.json',dict(directory=str(out.relative_to(work)),video='组件重组视频.mp4',bundle=bundle.name,
          frames=result['frames'],duration=result['duration'],decode_verified=True))
    print(json.dumps(dict(output=str(out),video=str(out/'组件重组视频.mp4'),bundle=str(bundle),
        frames=result['frames'],duration=result['duration'],next='观看导出视频与起点/中段/终点预览。技术解码通过不代表视觉验收通过。'),ensure_ascii=False))


def verify(args):
    work=Path(args.work).expanduser().resolve();record=read(work/'latest-result.json');out=work/record['directory']
    for path, expected in read(out/'sha256.json').items():
        if digest(out/path)!=expected:raise ValueError('交付文件校验失败：'+path)
    app=engine(work)
    app.command(job(work,'verify'),[app.ffmpeg(),'-v','error','-i',out/record['video'],'-f','null','-'])
    with zipfile.ZipFile(out/record['bundle']) as z:
        if z.testzip() is not None:raise ValueError('交付 ZIP 损坏')
        for name,expected in read(out/'sha256.json').items():
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:raise ValueError('ZIP 内文件与交付不匹配：'+name)
    print(json.dumps(dict(verified=True,output=str(out),frames=record['frames'],duration=record['duration'],
        boundary='已校验文件、素材包及全片解码；视觉质量需要 Agent 查看成片。'),ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description='陌生 Agent 从 PPT 到组件重组视频；先读 AGENT_START.md')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    prep=sub.add_parser('prepare');prep.add_argument('--ppt',required=True);prep.add_argument('--work',required=True);prep.add_argument('--pages')
    for name in ('preview','render'):
        cmd=sub.add_parser(name);cmd.add_argument('--work',required=True);cmd.add_argument('--plan')
        if name=='render':cmd.add_argument('--reviewed',required=True);cmd.add_argument('--review-note',required=True)
    check=sub.add_parser('verify');check.add_argument('--work',required=True)
    args=parser.parse_args()
    try:
        if args.command=='doctor':return doctor()
        globals()[args.command](args)
        return 0
    except Exception as exc:
        print(json.dumps(dict(error=str(exc),command=args.command),ensure_ascii=False),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
