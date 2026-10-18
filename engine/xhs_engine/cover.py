"""6.4 封面引擎：三种首图形式。

- scene_single：场景 + 单页（复用透视合成）
- collage：拼图首图（复用拼图引擎）
- big_title：大字报（大标题 + 页图，支持描边/背景色块/换颜色/换字体）
"""

from typing import Optional

from PIL import Image, ImageDraw

from . import fonts
from .collage import make_collage
from .perspective import perspective_compose


def cover_scene_single(
    background_path: str,
    page_path: str,
    screen_corners,
    out_path: str,
    feather: int = 2,
) -> str:
    """场景单页封面：复用透视合成。"""
    return perspective_compose(background_path, page_path, screen_corners, out_path, feather)


def cover_collage(page_paths: list, out_path: str, header_text: Optional[str] = None, **kwargs) -> str:
    """拼图封面：复用拼图引擎。"""
    return make_collage(page_paths, out_path, header_text=header_text, **kwargs)


def cover_big_title(
    page_path: str,
    out_path: str,
    title: str,
    subtitle: Optional[str] = None,
    canvas_size=(1080, 1440),
    bg_color=(255, 255, 255),
    title_color=(30, 30, 30),
    # 字体 + 文字样式
    font_name: str = "黑体粗",
    title_stroke_width: int = 0,
    title_stroke_fill=(255, 255, 255),
    title_bg_color=None,          # 标题背景色块颜色，None = 不画底
    title_bg_padding: int = 10,   # 背景色块内边距
    title_bg_radius: int = 12,    # 背景色块圆角
    subtitle_font_name: str = "黑体",
    subtitle_color=(120, 120, 120),
) -> str:
    """大字报封面：大标题 + 页图。

    文字样式能力：font_name 换字体、title_color 换颜色、title_stroke_width/fill 描边、
    title_bg_color 背景色块（含圆角 + 内边距）。
    """
    W, H = canvas_size
    canvas = Image.new("RGB", canvas_size, bg_color)
    draw = ImageDraw.Draw(canvas)

    # 标题（自适应字号，含描边宽度参与换行判断）
    font = fonts.load_font(font_name, 120)
    lines, line = [], ""
    for ch in title:
        test = line + ch
        if line and draw.textbbox((0, 0), test, font=font, stroke_width=title_stroke_width)[2] > W - 120:
            lines.append(line)
            line = ch
        else:
            line = test
    if line:
        lines.append(line)

    y = 120
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font, stroke_width=title_stroke_width)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        cx = W // 2
        # 背景色块（圆角底框）
        if title_bg_color is not None:
            pad = title_bg_padding
            draw.rounded_rectangle(
                [cx - tw // 2 - pad, y - pad, cx + tw // 2 + pad, y + th + pad],
                radius=title_bg_radius,
                fill=title_bg_color,
            )
        # 文字（居中，换颜色 + 描边）
        draw.text(
            (cx - tw // 2 - bbox[0], y - bbox[1]),
            ln,
            font=font,
            fill=title_color,
            stroke_width=title_stroke_width,
            stroke_fill=title_stroke_fill,
        )
        y += th + 60  # 行距

    # 副标题
    if subtitle:
        y += 30
        sub_font = fonts.load_font(subtitle_font_name, 44)
        sb = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = sb[2] - sb[0]
        draw.text(((W - sw) // 2, y), subtitle, fill=subtitle_color, font=sub_font)
        y += sb[3] - sb[1] + 60

    # 页图（等比缩放，放在下方）
    img = Image.open(page_path).convert("RGB")
    target_w = W - 120
    ratio = target_w / img.width
    target_h = int(img.height * ratio)
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    canvas.paste(img, ((W - target_w) // 2, int(y)))

    canvas.save(out_path)
    return str(out_path)
