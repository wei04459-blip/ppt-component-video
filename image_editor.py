"""Image edit API. All sources must belong to a recorded export in this project."""
import base64, copy, io, json, math, shutil
from pathlib import Path
from PIL import Image, ImageEnhance
from xhs_engine import nursing_dual, award_grid  # register renderer implementations
from xhs_engine.editable import render_layer


def locate(app, payload):
    p=app.project(payload['project'])
    state=app.read_project(p.name)
    source=next((r for r in state.get('exports',[]) if not r.get('video') and payload['image'] in r.get('images',[])),None)
    if source is None:raise ValueError('这张图片不属于当前作品')
    out=Path(source['directory']).resolve()
    if not out.is_relative_to((p/'exports').resolve()):raise ValueError('导出路径无效')
    image=(app.DATA/payload['image'][len('/files/'):]).resolve()
    if not image.is_relative_to(out):raise ValueError('图片路径无效')
    folder=image.parent/(image.stem+'.layers')
    if not (folder/'document.json').exists():raise ValueError('这份旧预览尚未保存文字层，请先点击“生成笔记预览”，之后即可直接编辑')
    doc=json.loads((folder/'document.json').read_text())
    return p,source,out,image,folder,doc


def public(app,folder,doc):
    return {'size':doc['size'],'background':app.file_url(folder/doc['background']),
            'layers':[{k:v for k,v in item.items() if k not in ['args','renderer']}|{'image':app.file_url(folder/item['image'])} for item in doc['layers']]}


def open_image(app,payload):
    *_,folder,doc=locate(app,payload)
    return public(app,folder,doc)


def validate(item, change, size):
    texts=change.get('texts')
    if not isinstance(texts,list) or len(texts)!=item['textCount'] or any(not isinstance(t,str) or len(t)>100 or '\n' in t for t in texts):raise ValueError('每段文字请保持单行，最多 100 字')
    values=[change.get(k) for k in ['x','y','fontSize']]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('位置或字号无效')
    x,y,font_size=values
    if not 8<=font_size<=300:raise ValueError('字号范围为 8–300')
    bitmap=render_layer(item,size,texts,font_size)
    if x<0 or y<0 or x+bitmap.width>size[0]+1 or y+bitmap.height>size[1]+1:raise ValueError('文字超出画布，请移回图内或减小字号')
    return bitmap


def preview(app,payload):
    *_,doc=locate(app,payload)
    item=next((i for i in doc['layers'] if i['id']==payload['layer'].get('id') and i['textCount']),None)
    if item is None:raise ValueError('请选择可编辑文字')
    bitmap=validate(item,payload['layer'],doc['size'])
    buf=io.BytesIO();bitmap.save(buf,format='PNG')
    return {'image':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode(),'width':bitmap.width,'height':bitmap.height}


def save_image(app,job,payload,p):
    _,source,old,image,folder,doc=locate(app,payload)
    changes=payload.get('layers',[])
    editable=[i for i in doc['layers'] if i['textCount']]
    if not isinstance(changes,list) or len(changes)!=len(editable) or {i.get('id') for i in changes}!={i['id'] for i in editable}:raise ValueError('文字层不完整，请重新打开图片')
    rendered={}
    for item in editable:
        change=next(c for c in changes if c['id']==item['id'])
        rendered[item['id']]=validate(item,change,doc['size'])
    out=p/'exports'/job['id']
    shutil.copytree(old,out,ignore=shutil.ignore_patterns('*.zip'))
    target=out/image.relative_to(old);dest=out/folder.relative_to(old)
    canvas=Image.open(dest/doc['background']).convert('RGBA')
    for item in doc['layers']:
        if item['textCount']:
            change=next(c for c in changes if c['id']==item['id'])
            bitmap=rendered[item['id']]
            item.update(texts=change['texts'],x=round(change['x']),y=round(change['y']),fontSize=change['fontSize'],width=bitmap.width,height=bitmap.height)
            # Keep original arguments and font size as the stable rendering recipe.
            bitmap.save(dest/item['image'])
        else:bitmap=Image.open(dest/item['image']).convert('RGBA')
        canvas.alpha_composite(bitmap,(item['x'],item['y']))
    canvas=canvas.convert('RGB')
    if doc.get('contrast'):canvas=ImageEnhance.Contrast(canvas).enhance(doc['contrast'])
    canvas.save(target)
    if target.with_suffix('.jpg').exists():canvas.save(target.with_suffix('.jpg'),quality=88,optimize=True)
    app.write_json(dest/'document.json',doc)
    app.write_json(out/'图内编辑记录.json',{'source':str(image),'image':str(target),'layers':changes})
    result=copy.deepcopy(source)
    result.pop('download',None)
    result.update(directory=str(out),images=[app.file_url(out/Path(app.DATA/u[len('/files/'):]).relative_to(old)) for u in source['images']],check={'status':'已手动调整图内文字，请核对内容与排版；原检查结果不再作为当前版本结论'})
    app.write_json(out/'检查结果.json',result['check'])
    return result
