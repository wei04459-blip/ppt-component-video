"""Reusable layout registry, independent of the original manifest pipeline."""
import json
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from .ppt2img import ppt_to_images
from .similarity import find_too_similar
from . import fonts
from .editable import layer, render_document

LIBRARY = Path(__file__).resolve().parents[1] / "templates/library.yaml"
FONT = str(fonts.resolve_font("黑体粗"))


def load_templates(path=None):
    path = Path(path or LIBRARY).resolve()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    registry = dict(sorted(data["templates"].items(),
                           key=lambda item: -item[1].get("priority", 0)))
    return registry, path.parent


@layer("text")
def _text(canvas, text, spec):
    if not text:
        return
    x, y, width, height = spec["box"]
    draw = ImageDraw.Draw(canvas)
    stroke = spec.get("stroke_width", 0)
    colors = [spec.get("color", "#222222")] * len(text)
    for item in spec.get("highlights", []):
        start = 0
        while True:
            start = text.find(item["text"], start)
            if start < 0:
                break
            colors[start:start+len(item["text"])] = [item["color"]] * len(item["text"])
            start += len(item["text"])
    for size in range(spec.get("font_size", 52), 17, -1):
        font = fonts.load_font(spec.get("font_name", "黑体粗"), size)
        lines, line = [], []
        for index, char in enumerate(text):
            if char == "\n":
                lines.append(line); line = []; continue
            trial = ''.join(text[i] for i in line) + char
            bounds = draw.textbbox((0,0),trial,font=font,stroke_width=stroke)
            if line and bounds[2]-bounds[0] > width:
                lines.append(line); line = []
            line.append(index)
        lines.append(line)
        bounds = [draw.textbbox((0,0),''.join(text[i] for i in line),font=font,stroke_width=stroke) for line in lines]
        heights = [b[3]-b[1] for b in bounds]
        gap = spec.get("line_gap", 12)
        total = sum(heights) + gap*(len(lines)-1)
        if total > height or len(lines) > spec.get("max_lines", 10):
            continue
        top = y + ((height-total)/2 if spec.get("vertical_align") == "center" else 0)
        for line, bbox, h in zip(lines,bounds,heights):
            offset = (width-(bbox[2]-bbox[0]))/2 if spec.get("align") == "center" else 0
            baseline = top-bbox[1]
            prefix = ''
            for index in line:
                char_x = x+offset-bbox[0]+draw.textlength(prefix,font=font)
                fonts.draw_text(draw,(char_x,baseline),text[index],font=font,
                    fill=colors[index],stroke_width=stroke,
                    stroke_fill=spec.get("stroke_fill", "#222222"))
                prefix += text[index]
            top += h+gap
        return
    raise ValueError("模板标题区域放不下文字，请缩短展示标题")


@layer("scene")
def _scene_text(canvas, text, spec):
    mode=canvas.mode
    canvas=canvas.convert("RGBA")
    w,h=spec["size"]
    overlay=Image.new("RGBA",(w,h))
    if spec.get("background"):
        ImageDraw.Draw(overlay).rounded_rectangle((0,0,w-1,h-1),radius=spec.get("radius",12),fill=spec["background"])
    pad=spec.get("padding",16)
    _text(overlay,text,dict(spec,box=[pad,pad,w-pad*2,h-pad*2],vertical_align="center"))
    overlay=overlay.rotate(spec.get("angle",0),resample=Image.Resampling.BICUBIC,expand=True)
    x,y=spec["position"]
    if spec.get("shadow",True):
        shadow=Image.new("RGBA",overlay.size)
        shadow.putalpha(overlay.getchannel("A").point(lambda a:round(a*.28)))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)),(x+3,y+6))
    canvas.alpha_composite(overlay,(x,y))
    return canvas.convert(mode)


def _scene_overlays(canvas,template,title):
    for spec in template.get("scene_overlays",[]):
        text=title if spec.get("role")=="title" else spec.get("text","")
        if text:canvas=_scene_text(canvas,text,spec)
    return canvas


def render_template(template, root, pages, out_path, title="", source_pages=None):
    return render_document(_render_template,template,root,pages,out_path,title,source_pages)


def _render_template(template, root, pages, out_path, title="", source_pages=None):
    """Keep all slide content; never regenerate text or crop source slides."""
    if template["status"] != "ready":
        raise ValueError(template.get("reason", "模板尚未就绪"))
    if not pages:
        raise ValueError("至少需要一张真实渲染的PPT页")
    if template.get("cover_fixed_pages"):
        if source_pages is None:
            if template["kind"] == "award_grid":
                raise ValueError("获奖拼图封面须传入完整有序的source_pages，以保证第一大槽为PPT第1页")
            raise ValueError("此封面模板须传入完整有序的source_pages，以保证右侧为PPT第1、2、3页")
        pages = list(pages)
        for slot, number in template["cover_fixed_pages"].items():
            if len(source_pages) < number or len(pages) <= slot:
                if template["kind"] == "award_grid":
                    raise ValueError("获奖拼图需要完整原始PPT与对应数量的封面槽位")
                raise ValueError("模板07需要至少3页原始PPT及8个封面槽位")
            pages[slot] = source_pages[number-1]
    size = tuple(template.get("output_size", [1080, 1440]))
    if template["kind"] == "blue_band":
        from .blue_band import render_blue_band
        canvas = render_blue_band(template, pages, title)
    elif template["kind"] == "award_grid":
        from .award_grid import render_award_grid
        canvas = render_award_grid(template, root, pages, title)
    elif template["kind"] == "nursing_dual":
        from .nursing_dual import render_nursing_dual
        canvas = render_nursing_dual(template, pages, title)
    elif template["kind"] == "scene":
        original = Image.open(root / template["background"]).convert("RGB")
        q = np.array(template["corners"], dtype=np.float32)
        if q.shape != (4, 2) or not np.isfinite(q).all():
            raise ValueError("屏幕坐标必须是四组有效像素坐标")
        if (q < 0).any() or (q[:, 0] >= original.width).any() or (q[:, 1] >= original.height).any():
            raise ValueError("屏幕四角超出背景边界")
        # Map the complete source directly to the screen, without a letterbox.
        panel = Image.open(pages[0]).convert("RGB")
        width, height = panel.size
        src = np.float32([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]])
        warped = cv2.warpPerspective(np.array(panel), cv2.getPerspectiveTransform(src, q), original.size, borderMode=cv2.BORDER_REPLICATE)
        mask = np.zeros((original.height, original.width), dtype=np.uint8)
        cv2.fillConvexPoly(mask, q.astype(np.int32), 255)
        result = Image.composite(Image.fromarray(warped), original, Image.fromarray(mask))
        if template.get("foreground_polygons"):
            foreground = Image.new("L", original.size)
            painter = ImageDraw.Draw(foreground)
            for polygon in template["foreground_polygons"]:
                painter.polygon([tuple(point) for point in polygon], fill=255)
            result = Image.composite(original, result, foreground)
        # Keep the complete photograph and reserve typography space where configured.
        canvas = Image.new("RGB", size, template.get("canvas_color", "#F3F2EF"))
        if template.get("scene_backdrop") == "blurred_photo":
            backdrop = ImageOps.fit(original,size,Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(34))
            canvas = Image.blend(backdrop,Image.new("RGB",size,"#101A27"),0.63)
        vx,vy,vw,vh = template.get("scene_viewport",[0,0,size[0],size[1]])
        result = ImageOps.fit(result,(vw,vh),Image.Resampling.LANCZOS)
        canvas.paste(result,(vx+(vw-result.width)//2,vy+(vh-result.height)//2))
        if template.get("scene_overlays"):
            canvas = _scene_overlays(canvas,template,title)
        elif result.height < size[1] - 140:
            _text(canvas,title,{"box":[36,35,size[0]-72,110],"font_size":48})
    else:
        canvas = Image.new("RGB", size, template.get("background_color", "white"))
        for decoration in template.get("decorations", []):
            x, y, w, h = decoration["box"]
            ImageDraw.Draw(canvas).rounded_rectangle((x,y,x+w,y+h),
                radius=decoration.get("radius",0),fill=decoration["fill"])
        for i, (x, y, width, height) in enumerate(template["slots"]):
            if i >= len(pages):
                break
            if width <= 0 or height <= 0 or x < 0 or y < 0 or x+width > size[0] or y+height > size[1]:
                raise ValueError("拼图槽位超出画布边界")
            slide = ImageOps.contain(Image.open(pages[i]).convert("RGB"), (width, height), Image.Resampling.LANCZOS)
            x += (width-slide.width)//2
            y += (height-slide.height)//2
            width, height = slide.size
            if template.get("shadow"):
                shadow = Image.new("RGBA", size)
                dx, dy = template.get("shadow_offset", [3, 5])
                ImageDraw.Draw(shadow).rounded_rectangle((x+dx, y+dy, x+width+dx, y+height+dy),
                       radius=template.get("radius", 0), fill=(0, 0, 0, 35))
                canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(template.get("shadow_blur", 4)))).convert("RGB")
            card = slide
            mask = Image.new("L", card.size)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, width-1, height-1), radius=template.get("radius", 0), fill=255)
            canvas.paste(card, (x, y), mask)
        _text(canvas, title, template["header"])
        if template.get("strapline"):
            _text(canvas, template["strapline"].get("text", ""), template["strapline"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return str(out_path)


def _content_capacity(cfg):
    return cfg.get("content_default_capacity", 1 if cfg["kind"] == "scene" else 2)


def _content_groups(note, cfg, page_count):
    # Explicit nested groups specify each exported image's PPT slots.
    raw = note.get("content_groups", note.get("content_pages", []))
    capacity = _content_capacity(cfg)
    groups = []
    for entry in raw:
        if isinstance(entry, list):
            groups.append(entry)
        elif type(entry) is int:
            # Legacy flat lists remain one entry per image; extend from its page.
            groups.append([(entry-1+j) % page_count+1 for j in range(capacity)]
                          if 1 <= entry <= page_count else [entry])
        else:
            raise ValueError("内容页必须是整数页号或每张图的页号数组")
    allowed = cfg.get("content_allowed_capacities", [capacity])
    if len(groups) < 3:
        raise ValueError("至少需要3张内容图，每张图分别填写一组页号")
    for group in groups:
        if len(group) not in allowed:
            raise ValueError(f"当前模板内容图须为{allowed}拼，不能转为单拼")
    return groups


def _content_template(cfg, capacity):
    if cfg["kind"] == "scene":
        return cfg
    slots = cfg.get("content_layouts", {}).get(str(capacity))
    if slots is None:
        slots = cfg["slots"] if len(cfg["slots"]) == capacity else None
    if slots is None:
        raise ValueError(f"模板未定义{capacity}拼内容布局")
    inner = dict(cfg, slots=slots, cover_fixed_pages={})
    if cfg["kind"] == "nursing_dual":
        inner = _nursing_options(inner, cfg.get("content_options", {}))
    elif cfg["kind"] == "award_grid":
        inner = dict(inner, render_role="content")
        inner = _award_options(inner, cfg.get("content_options", {}))
    return inner


def _cover_pages(cfg, selected, page_count):
    selected = list(selected)
    for slot, number in cfg.get("cover_fixed_pages", {}).items():
        if page_count < number:
            raise ValueError("模板07需要至少3页原始PPT，不能用重复页代替右侧第1、2、3页")
        if len(selected) <= slot:
            raise ValueError("模板07首图需要8个页号")
        selected[slot] = number
    return selected


def _default_note(template_id, cfg, index, page_count, title):
    capacity = cfg.get("page_capacity", 1)
    inner_capacity = _content_capacity(cfg)
    choose = lambda start, n: [(start + j) % page_count + 1 for j in range(n)]
    return {"id": template_id, "template_id": template_id, "title": title,
            "cover_pages": _cover_pages(cfg, choose(index, capacity), page_count),
            "content_groups": [choose(index+capacity+j*inner_capacity, inner_capacity) for j in range(4)],
            "body": "", "topics": [], "selection_mode": "按页序自动排图，未做内容语义选页"}


def run_templates(ppt_path, out_root, template_ids=None, plan_path=None,
                  title="护理PPT内容展示", library_path=None, pages_dir=None):
    registry, root = load_templates(library_path)
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8")) if plan_path else None
    ids = ([str(n["template_id"]).zfill(2) for n in plan["notes"]] if plan else
           [str(i).zfill(2) for i in template_ids] if template_ids else
           [i for i, cfg in registry.items() if cfg["status"] == "ready"
            and cfg.get("approval_status") != "pending_user_review"])
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("请选择不同的有效模板编号")
    # Reject invalid/pending templates before spending time rendering the deck.
    for id in ids:
        if id not in registry or registry[id]["status"] != "ready":
            raise ValueError(f"模板{id}不可调用：{registry.get(id, {}).get('reason', '编号不存在')}")
    out = Path(out_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(pages_dir).glob("page_*.png")) if pages_dir else ppt_to_images(ppt_path, str(out / "_pages"))
    if not pages:
        raise ValueError("没有找到PPT渲染页")
    notes = plan["notes"] if plan else [_default_note(id, registry[id], i, len(pages), title) for i, id in enumerate(ids)]
    normalized = []
    for i, note in enumerate(notes):
        id = ids[i]
        cfg = registry[id]
        cover_pages = note.get("cover_pages", [note.get("cover_page", 1)])
        content_groups = _content_groups(note, cfg, len(pages))
        if len(cover_pages) != cfg.get("page_capacity", 1):
            raise ValueError(f"模板{id}首图需要{cfg.get('page_capacity', 1)}个页号，可重复")
        cover_pages = _cover_pages(cfg, cover_pages, len(pages))
        for number in cover_pages + [n for group in content_groups for n in group]:
            if type(number) is not int or number < 1 or number > len(pages):
                raise ValueError(f"页号{number}超出1–{len(pages)}")
        headline = note.get("title", title)
        title_limit = plan.get("title_limit", 20) if plan else 20
        if title_limit is not None and len(headline) > title_limit:
            raise ValueError(f"笔记标题不能超过{title_limit}字符")
        normalized.append(dict(note, id=id, template_id=id, title=headline,
                               cover_pages=cover_pages, content_groups=content_groups))
    covers = []
    for note in normalized:
        id = note["template_id"]
        cfg = dict(registry[id])
        if cfg["kind"] == "blue_band":
            cfg = _blue_options(cfg, note.get("template_options", {}))
        elif cfg["kind"] == "nursing_dual":
            cfg = _nursing_options(cfg, note.get("template_options", {}))
        elif cfg["kind"] == "award_grid":
            cfg = _award_options(cfg, note.get("template_options", {}))
            cfg["award_label"] = note.get("award_label", cfg.get("award_label", "获奖PPT"))
            if cfg.get("info_line"):
                cfg["info_line"] = dict(cfg["info_line"], text=cfg["info_line"]["template"].format(
                    page_count=len(pages),duration=note.get("report_duration","按需调整")))
        if "\n" in note.get("display_title", ""):
            if cfg.get("header"):
                cfg["header"] = dict(cfg["header"], max_lines=2)
            if cfg.get("scene_overlays"):
                cfg["scene_overlays"] = [dict(item,max_lines=2) if item.get("role") == "title" else item for item in cfg["scene_overlays"]]
        if cfg.get("strapline"):
            cfg["strapline"] = dict(cfg["strapline"], text=note.get("subtitle", "真实课件展示 · 框架参考"))
        if cfg.get("scene_overlays"):
            cfg["scene_overlays"] = [dict(item,text=note.get("subtitle", "真实课件 · 框架展示"))
                if item.get("role") == "subtitle" else item for item in cfg["scene_overlays"]]
        if cfg.get("scene_overlays"):
            cfg["scene_overlays"] = [dict(item, **note.get("scene_title_style", {}))
                if item.get("role") == "title" else dict(item, **note.get("scene_subtitle_style", {}))
                if item.get("role") == "subtitle" else item for item in cfg["scene_overlays"]]
        dest = out / id
        dest.mkdir(exist_ok=True)
        cover = dest / "01-封面.png"
        render_template(cfg, root, [pages[n-1] for n in note["cover_pages"]], cover, note.get("display_title", note["title"]), source_pages=pages)
        covers.append(str(cover))
        for j, group in enumerate(note["content_groups"], 2):
            inner = _content_template(cfg, len(group))
            inner_title = note.get("content_display_title", note.get("display_title", note["title"]))
            if cfg["kind"] == "nursing_dual":
                variants = note.get("content_variants", cfg.get("content_variants", []))
                if variants:
                    name = variants[(j-2) % len(variants)]
                    if name not in cfg.get("layout_variants", {}):
                        raise ValueError(f"模板14内容布局不存在：{name}")
                    inner = _nursing_options(inner, cfg["layout_variants"][name])
                inner = _nursing_options(inner, note.get("content_options", {}))
                titles = note.get("content_display_titles", [])
                subtitles = note.get("content_subtitles", [])
                if titles:
                    if len(titles) != len(note["content_groups"]):
                        raise ValueError("内容图标题数量须与内容图组数一致")
                    inner_title = titles[j-2]
                if subtitles:
                    if len(subtitles) != len(note["content_groups"]):
                        raise ValueError("内容图副标题数量须与内容图组数一致")
                    inner["strapline"] = dict(inner["strapline"], text=subtitles[j-2])
            if not inner_title and inner["kind"] == "collage":
                inner = dict(inner, decorations=[])
                if inner.get("strapline"):
                    inner["strapline"] = dict(inner["strapline"], box=[32, 54, 1016, 80], vertical_align="center")
                # Redistribute the released heading space while keeping each full slide.
                count = len(group)
                gap, top, bottom = 28, 178, 1396
                slot_height = (bottom-top-gap*(count-1)) // count
                inner["slots"] = [[32, top+k*(slot_height+gap), 1016, slot_height] for k in range(count)]
            render_template(inner, root, [pages[n-1] for n in group],
                            dest/f"{j:02d}-内容页.png", inner_title)
        copy = "\n\n".join([note["title"], note.get("body", ""), " ".join("#"+t for t in note.get("topics", []))])
        (dest/"文案.md").write_text(copy, encoding="utf-8")
    from .publication_check import check_notes
    publication_check = check_notes(out, normalized, registry, semantic_review_required=True)
    result = {"publication_check": publication_check, "out": str(out), "notes": len(normalized), "page_count": len(pages),
              "template_ids": ids, "too_similar": find_too_similar(covers, 10),
              "planning_status": "用户内容规划" if plan else "自动排图草稿；标题话题与语义选页待核对，正文默认空",
              "pending_templates": {i:c["reason"] for i,c in registry.items() if c["status"] != "ready"},
              "materials_status": ("程序化通用视觉模板；页图为用户本地真实课件；未发布"
                  if all(registry[id]['kind'] in {'nursing_dual','award_grid','blue_band'} for id in ids)
                  else "原帖参考与AI优化素材用于本地样稿，非已授权发布素材库")}
    (out/"执行清单.json").write_text(json.dumps({"ppt": ppt_path, "notes": normalized}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out/"检查结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    cards = []
    for note in normalized:
        import html
        id = note["template_id"]
        cards.append(f'<section><h2>{id} · {html.escape(registry[id]["name"])}</h2><div class="images">' +
                     ''.join(f'<a href="{id}/{im.name}"><img src="{id}/{im.name}" alt="模板{id}输出"></a>' for im in sorted((out/id).glob("0*-*.png"))) + '</div></section>')
    (out/"预览.html").write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>通用模板实际出图</title><style>body{margin:30px;background:#f3f2ef;color:#222;font:16px system-ui}section{margin:30px 0}.images{display:flex;gap:12px;flex-wrap:wrap}img{width:230px;border-radius:8px}a{color:#36513b}</style><h1>通用模板实际出图</h1><p>同一套真实渲染PPT调用不同模板，不使用生图重写屏幕内容。点击图片看大图。</p>'+''.join(cards), encoding="utf-8")
    return result


def _nursing_options(cfg, options):
    """Expose only the visual fields supported by the dedicated renderer."""
    allowed = {"slots", "header", "strapline", "arrow", "card_style", "soft_background", "output_size"}
    unknown = set(options)-allowed
    if unknown:
        raise ValueError(f"模板14不支持这些视觉参数：{sorted(unknown)}")
    result = dict(cfg)
    for key, value in options.items():
        result[key] = dict(cfg.get(key, {}), **value) if isinstance(value, dict) else value
    return result


def _award_options(cfg, options):
    allowed={"header","strapline","trophy","info_line","card_style","background_color","output_size","slots"}
    unknown=set(options)-allowed
    if unknown:raise ValueError(f"获奖拼图不支持这些参数：{sorted(unknown)}")
    result=dict(cfg)
    for key,value in options.items():
        result[key]=dict(cfg.get(key,{}),**value) if isinstance(value,dict) else value
    return result


def _blue_options(cfg, options):
    allowed={"header","title_band","tags","card_style","background_color","background_blocks","output_size","slots"}
    unknown=set(options)-allowed
    if unknown: raise ValueError(f"蓝标题带不支持这些参数：{sorted(unknown)}")
    result=dict(cfg)
    for key,value in options.items():
        result[key]=dict(cfg.get(key,{}),**value) if isinstance(value,dict) else value
    return result
