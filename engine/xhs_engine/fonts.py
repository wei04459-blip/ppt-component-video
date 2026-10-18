"""字体库管理 + 文字样式渲染（描边 / 背景色 / 换颜色）。

字体库：项目自带 fonts/ 目录（免费商用字体，可移植），不用依赖系统字体。
文字渲染：一个 draw_text 函数搞定三种能力——
  1. 换颜色：fill 参数
  2. 描边：stroke_width + stroke_fill 参数
  3. 背景色块：bg_color（圆角底框 + 内边距）

用法：
    from xhs_engine import fonts
    f = fonts.load_font("得意黑", 72)
    fonts.draw_text(draw, (x, y), "护理PPT", font=f,
                    fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0),
                    bg_color=(255, 80, 80), bg_padding=10, bg_radius=12)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
_SYSTEM_FALLBACK = "/System/Library/Fonts/STHeiti Medium.ttc"

# 友好别名 -> 文件名。方便调用方用「得意黑」「文楷」这类名字。
FONT_ALIASES = {
    "思源黑体": "NotoSansCJKsc-Regular.otf",
    "黑体": "NotoSansCJKsc-Regular.otf",
    "思源黑体粗": "NotoSansCJKsc-Bold.otf",
    "黑体粗": "NotoSansCJKsc-Bold.otf",
    "霞鹜文楷": "LXGWWenKai-Regular.ttf",
    "文楷": "LXGWWenKai-Regular.ttf",
    "霞鹜文楷粗": "LXGWWenKai-Medium.ttf",
    "文楷粗": "LXGWWenKai-Medium.ttf",
    "得意黑": "SmileySans-Oblique.ttf",
    "标题体": "SmileySans-Oblique.ttf",
}


def list_fonts() -> list[str]:
    """列出字体库所有可用字体文件名（不含路径）。"""
    if not FONT_DIR.exists():
        return []
    return sorted(
        p.name for p in FONT_DIR.iterdir() if p.suffix.lower() in (".ttf", ".otf", ".ttc")
    )


def resolve_font(name: str) -> Path:
    """把字体别名 / 文件名 / 路径解析成字体文件路径。

    解析顺序：绝对路径 > 别名表 > fonts/ 目录文件名 > 系统兜底。
    """
    # 1. 直接路径
    p = Path(name)
    if p.exists():
        return p

    # 2. 别名表
    if name in FONT_ALIASES:
        fp = FONT_DIR / FONT_ALIASES[name]
        if fp.exists():
            return fp

    # 3. fonts/ 目录里按 stem 或全名找
    if FONT_DIR.exists():
        for cand in FONT_DIR.iterdir():
            if cand.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            if cand.stem == name or cand.name == name:
                return cand

    # 4. 系统兜底
    fallback = Path(_SYSTEM_FALLBACK)
    if fallback.exists():
        return fallback

    raise FileNotFoundError(f"字体找不到: {name}")


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """加载字体，返回 ImageFont 对象。name 可为别名 / 文件名 / 路径。"""
    return ImageFont.truetype(str(resolve_font(name)), size)


def _to_rgba(color, alpha=255):
    """把 '#rrggbb' / (r,g,b) / (r,g,b,a) 统一成 (r,g,b,a)。"""
    if isinstance(color, str):
        color = color.lstrip("#")
        if len(color) == 6:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return (r, g, b, alpha)
        if len(color) == 8:
            r, g, b, a = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), int(color[6:8], 16)
            return (r, g, b, a)
        raise ValueError(f"颜色格式不对: {color}")
    if isinstance(color, (tuple, list)):
        c = tuple(color)
        if len(c) == 3:
            return (c[0], c[1], c[2], alpha)
        if len(c) == 4:
            return c
    raise ValueError(f"颜色格式不对: {color}")


def text_bbox(
    draw: ImageDraw.ImageDraw,
    xy,
    text: str,
    font: ImageFont.FreeTypeFont,
    anchor: str = "la",
    align: str = "left",
    stroke_width: int = 0,
) -> tuple:
    """计算文字（含描边）的边界框 (x0, y0, x1, y1)。"""
    return draw.textbbox(
        xy, text, font=font, anchor=anchor, align=align, stroke_width=stroke_width
    )


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=(34, 34, 34),
    stroke_width: int = 0,
    stroke_fill=(255, 255, 255),
    bg_color=None,
    bg_padding: int = 6,
    bg_radius: int = 0,
    anchor: str = "la",
    align: str = "left",
):
    """画一段文字，支持描边 + 背景色块 + 换颜色。

    参数：
      fill         文字颜色（换颜色）
      stroke_width 描边宽度（px），0 = 不描边
      stroke_fill  描边颜色
      bg_color     背景色块颜色，None = 不画底
      bg_padding   背景色块内边距（px）
      bg_radius    背景色块圆角半径（px）
      anchor/align 锚点 / 对齐，同 Pillow
    """
    # 1. 背景色块（在文字底下垫一个圆角矩形）
    if bg_color is not None:
        bbox = draw.textbbox(
            xy, text, font=font, anchor=anchor, align=align, stroke_width=stroke_width
        )
        box = [
            bbox[0] - bg_padding,
            bbox[1] - bg_padding,
            bbox[2] + bg_padding,
            bbox[3] + bg_padding,
        ]
        if bg_radius > 0:
            draw.rounded_rectangle(box, radius=bg_radius, fill=bg_color)
        else:
            draw.rectangle(box, fill=bg_color)

    # 2. 文字（颜色 + 描边）
    draw.text(
        xy,
        text,
        font=font,
        fill=fill,
        anchor=anchor,
        align=align,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def draw_text_centered(
    draw: ImageDraw.ImageDraw,
    center_xy,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=(34, 34, 34),
    stroke_width: int = 0,
    stroke_fill=(255, 255, 255),
    bg_color=None,
    bg_padding: int = 6,
    bg_radius: int = 0,
):
    """以某点为中心画文字（背景色块 + 描边 + 颜色都支持）。"""
    # 用 center 锚点：Pillow 的 'mm' 是正中心
    draw_text(
        draw,
        center_xy,
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
        bg_color=bg_color,
        bg_padding=bg_padding,
        bg_radius=bg_radius,
        anchor="mm",
        align="center",
    )


def font_preview_text(name: str, size: int = 40) -> str:
    """返回一段预览用的中文文本。"""
    return f"护理PPT 汇报 查房 循证 {name} 0123"
