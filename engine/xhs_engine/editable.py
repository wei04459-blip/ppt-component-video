"""Editable typography exported alongside each image, with native renderer styling."""
import copy
import json
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from PIL import Image

ACTIVE = ContextVar('editable_canvas', default=None)
RENDERERS = {}


def layer(key, text_count=1):
    def decorate(fn):
        RENDERERS[key] = fn
        @wraps(fn)
        def wrapped(canvas, *args):
            session = ACTIVE.get()
            if session is None:
                return fn(canvas, *args)
            token = ACTIVE.set(None)
            try:
                overlay = Image.new('RGBA', canvas.size)
                result = fn(overlay, *args)
                if isinstance(result, Image.Image): overlay = result
            finally: ACTIVE.reset(token)
            bounds = overlay.getbbox()
            if bounds:
                item = {'renderer': key, 'args': copy.deepcopy(args), 'textCount': text_count,
                        'x': bounds[0], 'y': bounds[1], 'width': bounds[2]-bounds[0], 'height': bounds[3]-bounds[1]}
                spec = next((a for a in args if isinstance(a, dict)), {})
                item['fontSize'] = spec.get('font_size', 52)
                item['baseFontSize'] = item['fontSize']
                item['texts'] = list(args[:text_count])
                session.append((item, overlay.crop(bounds)))
            return canvas
        return wrapped
    return decorate


def render_document(fn, template, root, pages, out_path, title='', source_pages=None):
    layers = []
    token = ACTIVE.set(layers)
    try: fn(template, root, pages, out_path, title, source_pages)
    finally: ACTIVE.reset(token)
    path = Path(out_path)
    folder = path.parent / (path.stem + '.layers')
    folder.mkdir(exist_ok=True)
    background = Image.open(path).convert('RGBA')
    background.convert('RGB').save(folder/'background.png')
    items=[]
    for i,(item, bitmap) in enumerate(layers):
        item.update(id=str(i), image=f'layer-{i}.png')
        bitmap.save(folder/item['image'])
        background.alpha_composite(bitmap, (item['x'],item['y']))
        items.append(item)
    background.convert('RGB').save(path)
    doc={'version':1,'size':list(background.size),'background':'background.png','layers':items}
    (folder/'document.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2))
    return str(path)


def render_layer(item, size, texts, font_size):
    args=copy.deepcopy(item['args'])
    args[:item['textCount']]=texts
    canvas=Image.new('RGBA',tuple(size))
    result=RENDERERS[item['renderer']](canvas,*args)
    if isinstance(result,Image.Image):canvas=result
    bounds=canvas.getbbox()
    if not bounds: return Image.new('RGBA',(1,1))
    bitmap=canvas.crop(bounds)
    factor=font_size/item['baseFontSize']
    target=(max(1,round(bitmap.width*factor)), max(1,round(bitmap.height*factor)))
    if target[0]>size[0] or target[1]>size[1]:raise ValueError('文字超出画布，请减小字号或缩短内容')
    return bitmap.resize(target,Image.Resampling.LANCZOS)
