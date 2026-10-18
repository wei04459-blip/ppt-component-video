from . import fonts
"""Blue title band with replaceable seven-panel cover and aligned double pages."""
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .award_grid import _panel


def render_blue_band(cfg, pages, title):
    size=tuple(cfg.get('output_size',[2160,2880]))
    if size[0]*4!=size[1]*3: raise ValueError('蓝标题带输出须为3:4')
    scale=size[0]/1080
    if len(pages)!=len(cfg['slots']): raise ValueError('蓝标题带源页数量须与槽位相同')
    canvas=Image.new('RGBA',size,cfg.get('background_color','#E8ECF2'))
    draw=ImageDraw.Draw(canvas)
    # Quiet angular blocks visible only in the gaps between the source slides.
    for block in cfg.get('background_blocks',[]):
        draw.polygon([(round(x*scale),round(y*scale)) for x,y in block['points']],fill=block['color'])
    band=cfg['title_band'];draw.rectangle((0,0,size[0],round(band['height']*scale)),fill=band['color'])
    spec=cfg['header'];x,y,w,h=[round(v*scale) for v in spec['box']]
    for fs in range(round(spec['font_size']*scale),round(20*scale),-1):
        font=fonts.load_font("得意黑",fs)
        bounds=draw.textbbox((0,0),title,font=font,stroke_width=round(spec.get('stroke_width',0)*scale))
        if bounds[2]-bounds[0]<=w and bounds[3]-bounds[1]<=h: break
    else: raise ValueError('标题过长')
    # Font is an actual oblique face; tighten the headline to match the reference.
    layer=Image.new('RGBA',(bounds[2]-bounds[0]+8,bounds[3]-bounds[1]+8))
    ImageDraw.Draw(layer).text((4-bounds[0],4-bounds[1]),title,font=font,fill=spec['color'],stroke_width=round(spec.get('stroke_width',0)*scale),stroke_fill=spec['color'])
    if spec.get('fill_width',True): layer=layer.resize((w,layer.height),Image.Resampling.LANCZOS)
    canvas.alpha_composite(layer,(x+(w-layer.width)//2,y+(h-layer.height)//2))
    tags=cfg['tags'];labels=tags['labels']
    if len(labels)!=len(tags['boxes']): raise ValueError('标签文字和框数量不同')
    for text,box in zip(labels,tags['boxes']):
        tx,ty,tw,th=[round(v*scale) for v in box]
        draw.rounded_rectangle((tx,ty,tx+tw,ty+th),radius=round(tags.get('radius',9)*scale),outline=tags['color'],width=max(1,round(tags.get('border_width',1.5)*scale)))
        font=fonts.load_font("黑体",round(tags["font_size"]*scale))
        bb=draw.textbbox((0,0),text,font=font)
        if bb[2]-bb[0]>tw-8*scale: raise ValueError('标签文字过长')
        draw.text((tx+(tw-bb[2]+bb[0])/2-bb[0],ty+(th-bb[3]+bb[1])/2-bb[1]),text,font=font,fill=tags['color'])
    for page,box in zip(pages,cfg['slots']): _panel(canvas,page,box,cfg['card_style'],scale)
    return canvas.convert('RGB')
