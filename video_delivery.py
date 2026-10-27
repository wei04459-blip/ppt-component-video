"""Shared user-facing video delivery manifest and cancellable atomic bundle."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def write_manifest(path,value):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


VIDEO_INTERMEDIATE_DIRS={'frames','motion-canvas','project','node_modules','output','__pycache__'}


def video_delivery_files(out):
    """User-facing video files only; retain intermediate frames locally for debugging."""
    out=Path(out)
    return sorted((f for f in out.rglob('*') if f.is_file()
        and not any(part in VIDEO_INTERMEDIATE_DIRS or part.startswith('.') for part in f.relative_to(out).parts[:-1])
        and f.suffix.lower() not in {'.zip','.partial','.tmp','.log','.pyc'}),key=lambda f:f.relative_to(out).as_posix())


def build_video_bundle(job,out,bundle):
    out=Path(out);bundle=Path(bundle);partial=bundle.with_name(bundle.name+'.partial')
    def check():
        if job.get('cancel'):raise ValueError('任务已取消')
    check()
    # Keep the editable legacy template input, without shipping its temporary project.
    if (out/'project'/'input.json').is_file():shutil.copy2(out/'project'/'input.json',out/'视频内容.json')
    files=[f for f in video_delivery_files(out) if f.relative_to(out).as_posix()!='sha256.json']
    manifest={}
    for f in files:
        check();h=hashlib.sha256()
        with f.open('rb') as source:
            for chunk in iter(lambda:source.read(1024*1024),b''):check();h.update(chunk)
        manifest[f.relative_to(out).as_posix()]=h.hexdigest()
    write_manifest(out/'sha256.json',manifest);files.append(out/'sha256.json')
    job['message']='正在整理视频交付文件'
    try:
        with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED) as archive:
            for f in files:
                check()
                with f.open('rb') as source,archive.open(f.relative_to(out).as_posix(),'w') as target:
                    for chunk in iter(lambda:source.read(1024*1024),b''):check();target.write(chunk)
        check();partial.replace(bundle)
    finally:
        partial.unlink(missing_ok=True)
    return manifest
