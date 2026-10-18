"""Award grids: template15 trophy nine-panel/triple; template16 award-label five-panel/double."""
from .editable import layer
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


def _font(spec, size):
    from .fonts import load_font
    return load_font("文楷" if spec.get("font_index", 0) else "黑体", size)


@layer("award_header",2)
def _header(canvas, title, award, spec, scale):
    if spec.get("finish")=="metallic":
        return _finished_header(canvas,title,award,spec,scale)
    x,y,width,height=[round(v*scale) for v in spec["box"]]
    draw=ImageDraw.Draw(canvas)
    gap=round(spec.get("segment_gap", 8)*scale)
    for size in range(round(spec.get("font_size",78)*scale),round(28*scale),-1):
        font=_font(spec,size)
        tw=draw.textlength(title,font=font)
        aw=draw.textlength(award,font=font) if award else 0
        bbox=draw.textbbox((0,0),title+award,font=font)
        if tw+aw+(gap if award else 0)<=width and bbox[3]-bbox[1]<=height:
            break
    else:
        raise ValueError("模板15图片标题过长，请缩短")
    baseline=y-bbox[1]
    draw.text((x,baseline),title,font=font,fill=spec.get("color","#17266E"))
    if award:
        draw.text((x+tw+gap,baseline),award,font=font,fill=spec.get("award_color","#DF873F"))


def _finished_header(canvas,title,award,spec,scale):
    """Restrained title finish, drawn from glyph masks at native output size."""
    import numpy as np
    x,y,w,h=[round(v*scale) for v in spec["box"]]
    draw=ImageDraw.Draw(canvas)
    tracking=spec.get("tracking",0.6)*scale
    gap=spec.get("segment_gap",10)*scale
    for size in range(round(spec.get("font_size",86)*scale),round(28*scale),-1):
        font=_font(spec,size)
        widths=[sum(draw.textlength(c,font=font) for c in text)+max(0,len(text)-1)*tracking for text in [title,award]]
        bbox=draw.textbbox((0,0),title+award,font=font)
        if sum(widths)+gap<=w and bbox[3]-bbox[1]<=h:break
    for text,left,colors in [(title,x,spec.get("navy_stops",[[0,"#29445F"],[1,"#122B47"]])),(award,x+widths[0]+gap,spec.get("gold_stops",[[0,"#967032"],[0.42,"#C7A15C"],[0.54,"#AD863D"],[1,"#866026"]]))]:
        mask=Image.new("L",canvas.size)
        md=ImageDraw.Draw(mask);cursor=left
        for char in text:
            md.text((cursor,y-bbox[1]),char,font=font,fill=255)
            cursor+=draw.textlength(char,font=font)+tracking
        bounds=mask.getbbox()
        if not bounds:continue
        from PIL import ImageColor
        rows=np.clip((np.arange(canvas.height)-bounds[1])/max(1,bounds[3]-bounds[1]),0,1)
        rgb=np.empty((canvas.height,canvas.width,3),dtype=np.uint8)
        for channel in range(3):
            rgb[:,:,channel]=np.interp(rows,[s[0] for s in colors],[ImageColor.getrgb(s[1])[channel] for s in colors])[:,None]
        layer=Image.fromarray(rgb).convert("RGBA");layer.putalpha(mask)
        canvas.alpha_composite(layer)


@layer("award_subtitle",1)
def _subtitle(canvas, text, spec, scale):
    if not text:return
    if spec.get("finish")=="tracked":
        draw=ImageDraw.Draw(canvas)
        x,y,w,h=[round(v*scale) for v in spec["box"]]
        tracking=spec.get("tracking",2.0)*scale
        line=spec.get("lead_line",36)*scale
        for size in range(round(spec.get("font_size",40)*scale),round(20*scale),-1):
            font=_font(spec,size);bbox=draw.textbbox((0,0),text,font=font)
            width=sum(draw.textlength(c,font=font) for c in text)+(len(text)-1)*tracking
            if width+line+18*scale<=w and bbox[3]-bbox[1]<=h:break
        mid=y+(bbox[3]-bbox[1])/2
        draw.line((x,mid,x+line,mid),fill=spec.get("line_color","#B68A43"),width=max(1,round(scale*1.5)))
        cursor=x+line+18*scale
        for char in text:
            draw.text((cursor,y-bbox[1]),char,font=font,fill=spec.get("color","#41546B"))
            cursor+=draw.textlength(char,font=font)+tracking
        return
    x,y,width,height=[round(v*scale) for v in spec["box"]]
    draw=ImageDraw.Draw(canvas)
    for size in range(round(spec.get("font_size",40)*scale),round(20*scale),-1):
        font=_font(spec,size)
        bbox=draw.textbbox((0,0),text,font=font)
        if bbox[2]-bbox[0]<=width and bbox[3]-bbox[1]<=height:break
    else:raise ValueError("模板15结构说明过长，请缩短")
    offset=(width-(bbox[2]-bbox[0]))/2 if spec.get("align")=="center" else 0
    draw.text((x-bbox[0]+offset,y-bbox[1]),text,font=font,fill=spec.get("color","#14246C"))


def _panel(canvas, page, box, spec, scale):
    x,y,w,h=[round(v*scale) for v in box]
    if min(w,h)<=0 or min(x,y)<0 or x+w>canvas.width or y+h>canvas.height:
        raise ValueError("模板15PPT槽位超出画布")
    with Image.open(page) as src:
        slide=ImageOps.contain(src.convert("RGB"),(w,h),Image.Resampling.LANCZOS)
    x+=(w-slide.width)//2
    y+=(h-slide.height)//2
    w,h=slide.size
    shadow=Image.new("RGBA",canvas.size)
    dx,dy=[round(v*scale) for v in spec.get("shadow_offset",[3,4])]
    ImageDraw.Draw(shadow).rectangle((x+dx,y+dy,x+w+dx-1,y+h+dy-1),fill=(0,0,0,90))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(spec.get("shadow_blur",2)*scale)))
    panel=slide
    canvas.alpha_composite(panel.convert("RGBA"),(x,y))


@layer("award_label_header",2)
def _label_header(canvas, title, award, spec, scale):
    """Yellow award label and separate black/navy Songti topic, template16."""
    draw=ImageDraw.Draw(canvas)
    bx,by,bw,bh=[round(v*scale) for v in spec["label_box"]]
    draw.rectangle((bx,by,bx+bw-1,by+bh-1),fill=spec.get("label_fill","#FFFF00"))
    pad=round(spec.get("label_padding",2)*scale)
    _subtitle(canvas,award,dict(spec,box=[v/scale for v in (bx+pad,by+pad,bw-pad*2,bh-pad*2)],
                               font_size=spec.get("label_font_size",58),color=spec.get("label_color","#E95C35")),scale)
    x,y,w,h=[round(v*scale) for v in spec["box"]]
    for size in range(round(spec.get("font_size",58)*scale),round(24*scale),-1):
        font=_font(spec,size);bbox=draw.textbbox((0,0),title,font=font)
        if bbox[2]-bbox[0]<=w and bbox[3]-bbox[1]<=h:break
    else:raise ValueError("获奖标签拼图主题过长，请缩短")
    colors=[spec.get("color","#090D10")]*len(title)
    for item in spec.get("highlights",[]):
        start=0
        while True:
            pos=title.find(item["text"],start)
            if pos<0:break
            colors[pos:pos+len(item["text"])]=[item["color"]]*len(item["text"])
            start=pos+len(item["text"])
    prefix=""
    for ch,color in zip(title,colors):
        draw.text((x-bbox[0]+draw.textlength(prefix,font=font),y-bbox[1]),ch,font=font,fill=color)
        prefix+=ch


def render_award_grid(template, root, pages, title):
    title=title or template.get("default_prefix", "")
    if template.get("fixed_award_label"):
        template=dict(template,award_label=template["fixed_award_label"])
    size=tuple(template.get("output_size",[2160,2880]))
    if size[0]*4!=size[1]*3:raise ValueError("获奖拼图输出须为3:4")
    scale=size[0]/1080
    role=template.get("render_role","cover")
    expected=template.get("content_default_capacity",3) if role=="content" else template.get("page_capacity",9)
    if len(pages)!=expected:raise ValueError(f"获奖拼图{role}需要{expected}张真实PPT页")
    slots=template["slots"]
    if len(slots)!=expected:raise ValueError("获奖拼图槽位数量不符合固定构图")
    canvas=Image.new("RGBA",size,template.get("background_color","#F2F2F2"))
    # Optional gentle paper glow for the template09 award revision.
    glow=template.get("paper_glow")
    if glow:
        import numpy as np
        yy,xx=np.mgrid[0:size[1],0:size[0]]
        base=np.array(canvas.getpixel((0,0))[:3],dtype=float)
        tint=np.array(glow.get("color",[255,255,255]),dtype=float)
        cx,cy=glow.get("center",[0.3,0.0])
        strength=np.exp(-(((xx/size[0]-cx)/0.8)**2+((yy/size[1]-cy)/0.7)**2))*glow.get("strength",0.75)
        rgb=np.clip(base+(tint-base)*strength[:,:,None],0,255).astype("uint8")
        canvas=Image.fromarray(rgb).convert("RGBA")
    for page,box in zip(pages,slots):
        _panel(canvas,page,box,template.get("card_style",{}),scale)
    if role=="cover" or template.get("header_on_content",False):
        if template["header"].get("mode")=="award_label":
            _label_header(canvas,title,template.get("award_label","获奖课件"),template["header"],scale)
            _subtitle(canvas,template.get("info_line",{}).get("text",""),template["info_line"],scale)
        else:
            _header(canvas,title,template.get("award_label","获奖PPT"),template["header"],scale)
            _subtitle(canvas,template.get("strapline",{}).get("text",""),template["strapline"],scale)
        _trophy(canvas, str(root), template["trophy"], scale)
    # Plain template15 content has no outside overlays; label template16 retains its reference header.
    return canvas.convert("RGB")


@layer("trophy",0)
def _trophy(canvas, root, spec, scale):
    from pathlib import Path
    root=Path(root)
    if spec.get("enabled",True):
        with Image.open(root/spec["asset"]) as original:
            trophy=original.convert("RGBA")
            # Ignore faint alpha specks when locating the usable trophy edge.
            threshold=spec.get("trim_alpha_threshold",8)
            bbox=trophy.getchannel("A").point(lambda a:255 if a>threshold else 0).getbbox()
            if not bbox:raise ValueError("模板15奖杯素材为空")
            trophy=trophy.crop(bbox)
        x,y,w,h=[round(v*scale) for v in spec["box"]]
        trophy=ImageOps.contain(trophy,(w,h),Image.Resampling.LANCZOS)
        canvas.alpha_composite(trophy,(x+(w-trophy.width)//2,y+(h-trophy.height)//2))
