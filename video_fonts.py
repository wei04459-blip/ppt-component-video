"""Bundled video fonts; no imports from the note-making engine."""
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont
FONT_DIR=Path(__file__).resolve().parent/'engine'/'fonts'
@lru_cache(maxsize=128)
def load_font(name,size):
    filename='NotoSansCJKsc-Bold.otf' if name in ('黑体粗','思源黑体粗') else 'NotoSansCJKsc-Regular.otf'
    path=FONT_DIR/filename
    if not path.is_file():raise FileNotFoundError('缺少随包字体：'+str(path))
    return ImageFont.truetype(str(path),size)
