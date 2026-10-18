"""6.3 拼图引擎：多张 PPT 页拼成 3:4 拼图。"""

from typing import Optional

from PIL import Image, ImageDraw

from . import fonts


def _fit_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """等比缩放并居中裁剪到 (w, h)，避免拉伸变形。"""
    ratio = max(w / img.width, h / img.height)
    new_w = max(int(img.width * ratio), 1)
    new_h = max(int(img.height * ratio), 1)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def make_collage(
    image_paths: list,
    out_path: str,
    canvas_size=(1080, 1440),  # 3:4 竖版
    rows: int = 2,
    cols: int = 1,
    gap: int = 12,  # 槽位间距
    margin: int = 24,  # 四周留白
    bg_color=(255, 255, 255),
    header_text: Optional[str] = None,  # 表头文字
    header_height: int = 120,  # 表头高度
    header_color=(40, 40, 40),
    header_bg=None,  # 表头底色，None = 透明
    # 新增：字体 + 文字样式（描边/背景色块/换颜色）
    font_name: str = "黑体粗",
    header_stroke_width: int = 0,
    header_stroke_fill=(255, 255, 255),
    header_bg_radius: int = 0,
) -> str:
    """把多张图按 rows×cols 网格拼成拼图。"""
    canvas = Image.new("RGB", canvas_size, bg_color)
    W, H = canvas_size

    top = margin + (header_height if header_text else 0)
    content_h = H - top - margin
    cell_w = (W - 2 * margin - gap * (cols - 1)) // cols
    cell_h = (content_h - gap * (rows - 1)) // rows

    for idx, path in enumerate(image_paths):
        if idx >= rows * cols:
            break
        img = Image.open(path).convert("RGB")
        # Preserve every PPT pixel rather than cropping slide edges.
        img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
        r, c = divmod(idx, cols)
        x = margin + c * (cell_w + gap)
        y = top + r * (cell_h + gap)
        canvas.paste(img, (x + (cell_w - img.width) // 2, y + (cell_h - img.height) // 2))

    # 表头文字（字体 + 描边 + 底色 + 颜色）
    if header_text:
        draw = ImageDraw.Draw(canvas)
        # 自适应字号（含描边宽度）
        size = 52
        font = fonts.load_font(font_name, size)
        while (
            draw.textbbox((0, 0), header_text, font=font, stroke_width=header_stroke_width)[2]
            > W - 2 * margin
            and size > 20
        ):
            size -= 1
            font = fonts.load_font(font_name, size)
        # 表头整条底色（可选圆角）
        if header_bg:
            if header_bg_radius > 0:
                draw.rounded_rectangle(
                    [0, 0, W, margin + header_height], radius=header_bg_radius, fill=header_bg
                )
            else:
                draw.rectangle([0, 0, W, margin + header_height], fill=header_bg)
        # 文字居中（带描边）
        fonts.draw_text_centered(
            draw,
            (W // 2, margin + header_height // 2),
            header_text,
            font=font,
            fill=header_color,
            stroke_width=header_stroke_width,
            stroke_fill=header_stroke_fill,
        )

    canvas.save(out_path)
    return str(out_path)
