"""Copy the reusable engine without changing the source project."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
source=root.parent/'xhs-ppt-engine'
dest=root/'engine'
dest.mkdir(exist_ok=True)
for folder in ['xhs_engine','templates','fonts']:
    shutil.copytree(source/folder,dest/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
# Use bundled fonts on both platforms; original approved templates remain untouched.
p=dest/'xhs_engine'/'award_grid.py'
s=p.read_text();start=s.index('def _font(');end=s.index('\n\ndef _header',start)
s=s[:start]+'''def _font(spec, size):
    from .fonts import load_font
    return load_font("文楷" if spec.get("font_index", 0) else "黑体", size)
'''+s[end:];p.write_text(s)
p=dest/'xhs_engine'/'blue_band.py';s=p.read_text().replace("ImageFont.truetype(spec['font_path'],fs)",'fonts.load_font("得意黑",fs)').replace("ImageFont.truetype(tags['font_path'],round(tags['font_size']*scale))",'fonts.load_font("黑体",round(tags["font_size"]*scale))')
s='from . import fonts\n'+s;p.write_text(s)
print(dest)
