"""Build a clean distributable; excludes local work, caches and retired experiments."""
from pathlib import Path
import zipfile,hashlib,json,argparse
ROOT=Path(__file__).resolve().parent
SKIP_PARTS={'node_modules','.venv','__pycache__','.git','.backups','.pytest_cache','.cache','.DS_Store','.browser-ready','output','exports','semantic-previews','frames'}
SKIP_TOP={'data','outputs','previews','tmp','temp'}
SKIP_FILES={'prepare_engine.py','prepare_v7.py','make_previews.py','native_motion.py','native_group_motion.py'}
SKIP_SUFFIXES={'.pyc','.pyo','.log','.tmp','.bak','.zip','.db','.sqlite','.sqlite3'}

def release_files(root=ROOT):
    for p in sorted(root.rglob('*')):
        relative=p.relative_to(root)
        if not p.is_file() or p.is_symlink():continue
        if any(part in SKIP_PARTS for part in relative.parts) or relative.parts[0] in SKIP_TOP:continue
        if p.name in SKIP_FILES or p.suffix.lower() in SKIP_SUFFIXES:continue
        if p.name.startswith('.env') or '.bak.' in p.name or p.name.endswith('~'):continue
        yield p

def build(output):
    out=output.resolve();out.mkdir(parents=True,exist_ok=True)
    archive=out/'\u9c7c\u4e38\u521b\u4f5c\u5de5\u5177\u7bb1_Mac_Windows\u8bd5\u7528\u5305.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in release_files():z.write(p,Path('\u9c7c\u4e38\u521b\u4f5c\u5de5\u5177\u7bb1')/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None;names=z.namelist()
        for suffix in ['\u542f\u52a8Windows.cmd','web/app.js','AGENT_START.md','agent_video.py','semantic_scene.py','video/src/semantic.tsx']:
            assert any(x.endswith(suffix) for x in names),suffix
        assert not any(any(part in SKIP_PARTS for part in Path(x).parts) for x in names)
    (out/'\u6821\u9a8c.json').write_text(json.dumps(dict(archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(names),bytes=archive.stat().st_size,mac_runtime='tested_on_current_mac_only',windows_runtime='not_verified',video_engine='motion-canvas-native',boundary='archive integrity does not establish visual acceptance'),ensure_ascii=False,indent=2))
    return archive

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT.parent/'outputs'/'creator-toolbox-release');parser.add_argument('--list',action='store_true');args=parser.parse_args()
    if args.list:
        for p in release_files():print(p.relative_to(ROOT))
    else:print(build(args.output))
if __name__=='__main__':main()
