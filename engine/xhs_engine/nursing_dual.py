"""Template 14: native-resolution typography and faithful two-slide cards.

All geometry uses 1080×1440 design coordinates. Only PPT images are resized;
background, lettering, card edges and the arrow render at the export size.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from . import fonts
from .editable import layer


def _background(size, spec):
    # Smooth colour fields, not a cropped photograph or a social-platform UI.
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    xx /= width
    yy /= height
    base = np.array(spec.get("base", [39, 43, 30]), dtype=np.float32)
    rgb = np.empty((height, width, 3), dtype=np.float32)
    rgb[:] = base
    for glow in spec.get("glows", []):
        x, y = glow["center"]
        sx, sy = glow["spread"]
        weight = np.exp(-0.5 * (((xx-x)/sx)**2 + ((yy-y)/sy)**2))
        weight *= glow.get("strength", 1)
        rgb = rgb*(1-weight[..., None]) + np.array(glow["color"])*weight[..., None]
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255)), "RGB")


@layer("lettering")
def _lettering(canvas, text, spec, scale):
    """Single-line bold italic sign with a bounded, fully visible footprint."""
    if not text:
        return
    if "\n" in text:
        raise ValueError("模板14使用单行图片标题，请缩短或去掉换行")
    font = fonts.load_font(spec.get("font_name", "黑体粗"), round(spec.get("font_size", 128)*scale))
    stroke = round(spec.get("stroke_width", 3)*scale)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.textbbox((0, 0), text, font=font, stroke_width=stroke)
    pad = round(12*scale)
    raw = Image.new("RGBA", (bbox[2]-bbox[0]+pad*2, bbox[3]-bbox[1]+pad*2))
    ImageDraw.Draw(raw).text((pad-bbox[0], pad-bbox[1]), text, font=font,
                             fill=spec.get("color", "white"), stroke_width=stroke,
                             stroke_fill=spec.get("stroke_fill", "#1D2427"))
    shear = spec.get("shear", 0.13)
    extra = math.ceil(abs(shear)*raw.height)
    raw = raw.transform((raw.width+extra, raw.height), Image.Transform.AFFINE,
                        (1, shear, -extra if shear > 0 else 0, 0, 1, 0),
                        Image.Resampling.BICUBIC)
    ink = raw.getbbox()
    if ink:
        raw = raw.crop(ink)
    # A maximum width controls long replacement subjects; short phrases keep
    # their natural proportions unless fill_width is explicitly requested.
    x, y, max_width, max_height = [round(v*scale) for v in spec["box"]]
    factor = min(max_width/raw.width, max_height/raw.height)
    if not spec.get("fill_width", False):
        factor = min(1, factor)
    target = (round(raw.width*factor), round(raw.height*factor))
    if spec.get("fill_width", False):
        target = (max_width, min(max_height, target[1]))
    raw = raw.resize(target, Image.Resampling.LANCZOS)
    angle = spec.get("angle", 0)
    raw = raw.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    # Rotation can enlarge the footprint. Keep all strokes inside the canvas.
    if raw.width > canvas.width-2*scale:
        raw = ImageOps.contain(raw, (round(canvas.width-2*scale), raw.height), Image.Resampling.LANCZOS)
    if spec.get("align") == "right":
        x += max_width-raw.width
    elif spec.get("align") == "center":
        x += (max_width-raw.width)//2
    x = min(max(0, x), canvas.width-raw.width)
    y = min(max(0, y), canvas.height-raw.height)
    rgba = spec.get("shadow_color", "#233037B0")
    colored = Image.new("RGBA", raw.size, rgba)
    colored.putalpha(Image.eval(raw.getchannel("A"), lambda a: round(a*0.65)))
    dx, dy = spec.get("shadow_offset", [3, 5])
    canvas.alpha_composite(colored, (x+round(dx*scale), y+round(dy*scale)))
    canvas.alpha_composite(raw, (x, y))


def _card(canvas, page, box, spec, scale):
    x, y, width, height = [round(v*scale) for v in box]
    if min(width, height) <= 0 or x < 0 or y < 0 or x+width > canvas.width or y+height > canvas.height:
        raise ValueError("模板14卡片槽位超出画布边界")
    with Image.open(page) as original:
        slide = ImageOps.contain(original.convert("RGB"), (width,height), Image.Resampling.LANCZOS)
    x += (width-slide.width)//2
    y += (height-slide.height)//2
    width, height = slide.size
    radius = round(spec.get("radius", 18)*scale)
    shadow = Image.new("RGBA", canvas.size)
    ImageDraw.Draw(shadow).rounded_rectangle((x+12*scale,y+14*scale,x+width+12*scale,y+height+14*scale),
                                             radius=radius, fill=(0, 0, 0, 130))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7*scale)))
    panel = slide.convert("RGBA")
    mask = Image.new("L", panel.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1),radius=radius,fill=255)
    panel.putalpha(mask)
    canvas.alpha_composite(panel,(x,y))


@layer("arrow",0)
def _arrow(canvas, spec, scale):
    if not spec.get("enabled", True):
        return
    x,y,width,height = spec.get("box", [775,681,248,235])
    # A broad curved arrow, with a pale outer keyline and a white inner shine.
    # Use the float curves directly; integer rounding happens after scaling.
    def curve(points):
        a,b,c,d=points
        return [((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+3*(1-t)*t*t*c[0]+t**3*d[0],
                 (1-t)**3*a[1]+3*(1-t)**2*t*b[1]+3*(1-t)*t*t*c[1]+t**3*d[1])
                for t in np.linspace(0,1,80)]
    outline = curve([(0.76,0.02),(1.06,0.20),(0.90,0.45),(0.47,0.67)])
    outline += [(0.62,0.86),(0.04,0.90),(0.30,0.43),(0.42,0.58)]
    outline += curve([(0.42,0.58),(0.65,0.40),(0.69,0.24),(0.76,0.02)])
    points=[(round((x+px*width)*scale),round((y+py*height)*scale)) for px,py in outline]
    layer=Image.new("RGBA",canvas.size)
    draw=ImageDraw.Draw(layer)
    draw.polygon(points, fill=spec.get("color", "#FFD64E"))
    draw.line(points+[points[0]],fill="#FFF9D7",width=round(8*scale),joint="curve")
    shine=curve([(0.90,0.18),(0.91,0.34),(0.77,0.48),(0.66,0.54)])
    draw.line([(round((x+px*width)*scale),round((y+py*height)*scale)) for px,py in shine],fill="#FFFFFF",width=round(5*scale),joint="curve")
    draw.ellipse((round((x+width*.09)*scale),round((y+height*.96)*scale),round((x+width*.13)*scale),round((y+height*1.02)*scale)),fill="#FFE07B")
    # The default reproduces the reference overlap across both cards.
    # Slide protection remains an explicitly opt-in visual parameter.
    if spec.get("protect_slides", False):
        alpha=layer.getchannel("A")
        mask_draw=ImageDraw.Draw(alpha)
        for box in spec.get("protected_boxes", []):
            bx,by,bw,bh=[round(v*scale) for v in box]
            mask_draw.rectangle((bx,by,bx+bw,by+bh),fill=0)
        layer.putalpha(alpha)
    canvas.alpha_composite(layer)


def render_nursing_dual(template, pages, title):
    if len(pages) != 2:
        raise ValueError("模板14每张图需要恰好2张真实PPT页")
    size=tuple(template.get("output_size",[2160,2880]))
    if size[0]*4 != size[1]*3:
        raise ValueError("模板14输出必须保持3:4")
    scale=size[0]/1080
    canvas=_background(size,template["soft_background"]).convert("RGBA")
    slots=template["slots"]
    for page,box in zip(pages,slots):
        _card(canvas,page,box,template.get("card_style",{}),scale)
    _lettering(canvas,title,template["header"],scale)
    subtitle=template.get("strapline",{})
    _lettering(canvas,subtitle.get("text",""),subtitle,scale)
    arrow=dict(template.get("arrow",{}),protected_boxes=slots)
    _arrow(canvas,arrow,scale)
    return canvas.convert("RGB")
