from pathlib import Path
import zipfile,hashlib,json,argparse
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=root.parent/'outputs/鱼丸创作工具箱_MVP_2026-10-17')
args=parser.parse_args()
out=args.output.resolve()
out.mkdir(parents=True,exist_ok=True)
archive=out/'鱼丸创作工具箱_Mac_Windows试用包.zip'
skip={'.git','.pytest_cache','.env','node_modules','.venv','__pycache__','.DS_Store','.browser-ready','prepare_engine.py','prepare_v7.py','make_previews.py'}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if not p.is_file() or any(part in skip for part in p.relative_to(root).parts):continue
        z.write(p,Path('鱼丸创作工具箱')/p.relative_to(root))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert any(x.endswith('启动Windows.cmd') for x in names)
    assert any(x.endswith('web/app.js') for x in names)
    assert any(x.endswith('AGENT_START.md') for x in names)
    assert any(x.endswith('agent_video.py') for x in names)
    assert not any('node_modules/' in x or '.venv/' in x for x in names)
(out/'校验.json').write_text(json.dumps({'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(names),'bytes':archive.stat().st_size,'mac_runtime':'verified','windows_runtime':'not_verified'},ensure_ascii=False,indent=2))
print(archive)
