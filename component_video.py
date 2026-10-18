"""Deterministic, local component selection and before/after motion export."""
import io, json, math, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from pptx import Presentation
from pptx.util import Inches, Pt
import video_fonts as fonts


def object_pages(path):
    prs=Presentation(path);result=[]
    def text(shape):
        if getattr(shape,'has_text_frame',False):return shape.text
        if hasattr(shape,'shapes'):return '\n'.join(filter(None,(text(s) for s in shape.shapes)))
        if getattr(shape,'has_table',False):return '\n'.join(' | '.join(c.text for c in row.cells) for row in shape.table.rows)
        return ''
    for slide in prs.slides:
        items=[]
        for shape in slide.shapes:
            x=max(0,shape.left/prs.slide_width);y=max(0,shape.top/prs.slide_height)
            w=min(1-x,shape.width/prs.slide_width);h=min(1-y,shape.height/prs.slide_height)
            if min(w,h)<.008 or w*h>.92:continue
            items.append({'id':str(shape.shape_id),'name':shape.name[:60],'text':text(shape)[:2000], 'target':[x,y,w,h]})
        result.append(items[:40])
    return result


def analyse(app,payload):
    p=app.project(payload['project']);state=app.read_project(p.name)
    urls=state.get('pages',[])
    if not urls:raise ValueError('请先导入课件')
    folder=Path(state['pages_dir']).parent
    manifest=folder/'objects.json'
    objects=json.loads(manifest.read_text()) if manifest.exists() else {}
    # Earlier imports stored one source file and its rendered pages.
    pptx=list(folder.glob('*.pptx'))
    if not objects and len(pptx)==1:
        try:objects={str(i+1):v for i,v in enumerate(object_pages(pptx[0]))}
        except Exception:objects={}
    return {'pages':[{'source':u,'number':i+1,'objects':objects.get(str(i+1),[])} for i,u in enumerate(urls)],'notice':'每页最多读取 40 个对象，长文字最多 2000 字，请核对是否遗漏。读取的是对象边界；组件画面取自原页截图，重叠对象可能连带背景，请检查并合并。整页图片需要手动画框。'}


def rectangle(value):
    if not isinstance(value,list) or len(value)!=4 or any(type(n) not in (int,float) or not math.isfinite(n) for n in value):raise ValueError('组件位置无效')
    x,y,w,h=value
    if min(x,y)<0 or min(w,h)<.005 or x+w>1.001 or y+h>1.001:raise ValueError('请将组件完整放在页面内')
    return value


def validate(app,p,v,require_confirm=True):
    pages=v.get('pages',[]);state=app.read_project(p.name)
    if not isinstance(pages,list) or not 1<=len(pages)<=6:raise ValueError('请选择 1–6 页制作视频')
    if v.get('motion') not in ['smooth','stagger','lift']:raise ValueError('请选择动效')
    for page in pages:
        if page.get('source') not in state.get('pages',[]):raise ValueError('源课件已更换，请重新读取组件')
        items=page.get('components',[])
        if not 1<=len(items)<=40:raise ValueError('每页请保留 1–40 个组件，截图页需要先画框')
        if require_confirm and not page.get('confirmed'):raise ValueError('请逐页确认组件和两版布局')
        for item in items:
            rectangle(item.get('target'));rectangle(item.get('before'))
            if not isinstance(item.get('text',''),str) or len(item.get('text',''))>2000:raise ValueError('组件文字最多 2000 字')
    return pages


def source_image(app,p,url):
    path=(app.DATA/url[len('/files/'):]).resolve()
    if not path.is_relative_to(p.resolve()):raise ValueError('源图片路径无效')
    return Image.open(path).convert('RGB')


def crop(source,rect):
    x,y,w,h=rect
    return source.crop((round(x*source.width),round(y*source.height),round((x+w)*source.width),round((y+h)*source.height)))


def simple_tile(item,bitmap,size):
    w,h=size;tile=Image.new('RGB',size,'white');d=ImageDraw.Draw(tile)
    if item.get('text','').strip():
        text=item['text'].strip()
        for n in range(min(28,max(10,h//3)),7,-1):
            font=fonts.load_font('黑体',n);lines=[];line=''
            for char in text:
                if char=='\n' or d.textlength(line+char,font=font)>w-16:
                    lines.append(line);line='' if char=='\n' else char
                else:line+=char
            lines.append(line)
            if len(lines)*(n+4)<=h-12:break
        if len(lines)*(n+4)>h-12:raise ValueError('普通版文字放不下，请扩大组件或精简文字')
        for i,line in enumerate(lines):d.text((8,6+i*(n+4)),line,font=font,fill='#222222')
    else:
        im=ImageOps.contain(bitmap,(max(1,w-12),max(1,h-12)),Image.Resampling.LANCZOS)
        tile.paste(im,((w-im.width)//2,(h-im.height)//2))
    d.rectangle((0,0,w-1,h-1),outline='#b8b8b8',width=1)
    return tile


def prepare(app,p,page):
    source=source_image(app,p,page['source']);ratio=source.width/source.height
    size=(960,round(960/ratio)) if ratio>=960/540 else (round(540*ratio),540)
    size=tuple(max(1,n) for n in size)
    source=source.resize(size,Image.Resampling.LANCZOS)
    prepared=[];before=Image.new('RGB',size,'white')
    for ci,item in enumerate(page['components']):
        bitmap=crop(source,item['target']);x,y,w,h=item['before']
        try: tile=simple_tile(item,bitmap,(max(1,round(w*size[0])),max(1,round(h*size[1]))))
        except ValueError as exc: raise ValueError(f'第 {page.get("number","?")} 页，组件 {ci+1}：{exc}') from exc
        before.paste(tile,(round(x*size[0]),round(y*size[1])))
        prepared.append((item,bitmap,tile))
    return source,before,prepared


def motion_stage(source, before, items, t, motion):
    """Move aspect-preserved cards; replace styles without double-exposing text."""
    if t <= .55:return before.copy()
    if t >= 3.0:return source.copy()
    stage=Image.new('RGB',source.size,'white')
    for ci,(item,bitmap,tile) in enumerate(items):
        delay=(ci/max(1,len(items)-1)*.45) if motion=='stagger' else 0
        q=max(0,min(1,(t-.55-delay)/1.55))
        ease=q*q*q*(q*(q*6-15)+10)
        a,b=item['before'],item['target']
        r=[a[k]+(b[k]-a[k])*ease for k in range(4)]
        if motion=='lift':r[1]-=math.sin(math.pi*q)*.035
        x,y,w,h=r
        left,top=round(x*source.width),round(y*source.height)
        right,bottom=round((x+w)*source.width),round((y+h)*source.height)
        size=(max(1,right-left),max(1,bottom-top))
        # Fade out the old face before revealing the new one. Never blend two text images.
        turn=max(0,min(1,(q-.12)/.26)) if item.get('text','').strip() else 1
        face=tile if turn<.5 else bitmap
        fitted=ImageOps.contain(face,size,Image.Resampling.LANCZOS)
        # Paste only the actual face, not an opaque letterbox covering adjacent cards.
        opacity=abs(math.cos(math.pi*turn))
        if opacity>.025:
            mask=Image.new('L',fitted.size,round(255*opacity))
            stage.paste(fitted,(left+(size[0]-fitted.width)//2,top+(size[1]-fitted.height)//2),mask)
    # Settled components already match the original. Restore only remaining background.
    reveal=max(0,min(1,(t-2.65)/.35))
    return Image.blend(stage,source,reveal) if reveal else stage


def motion_preview(source,before,items,motion):
    times=[0,.9,1.3,1.8,2.4,3.2]
    thumb=(320,max(1,round(320*source.height/source.width)))
    sheet=Image.new('RGB',(thumb[0]*3,(thumb[1]+26)*2),'#eeeeed')
    draw=ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        frame=motion_stage(source,before,items,t,motion)
        frame=frame.resize(thumb,Image.Resampling.LANCZOS)
        x,y=(i%3)*thumb[0],(i//3)*(thumb[1]+26)
        sheet.paste(frame,(x,y+26));draw.text((x+8,y+5),f'{t:.1f}s',fill='#222222')
    return sheet


def preview(app,payload):
    p=app.project(payload['project']);v=payload['video'];pages=validate(app,p,v,False)
    import base64
    results=[]
    for page in pages:
        source,before,items=prepare(app,p,page);buf=io.BytesIO();before.save(buf,format='PNG')
        motion=io.BytesIO();motion_preview(source,before,items,v['motion']).save(motion,format='PNG')
        results.append({'before':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode(),'after':page['source'], 'motion':'data:image/png;base64,'+base64.b64encode(motion.getvalue()).decode()})
    return {'pages':results}


def export(app,job,payload,p):
    v=payload['video'];pages=validate(app,p,v)
    out=p/'exports'/job['id'];out.mkdir(parents=True);frames=out/'frames';frames.mkdir()
    prs=Presentation();prs.slide_width=Inches(12);prs.slide_height=Inches(6.75)
    previews=[];index=0;fps=24;length=96
    label_font=fonts.load_font('黑体粗',48);small_font=fonts.load_font('黑体',21)
    for pi,page in enumerate(pages):
        source,before,items=prepare(app,p,page)
        before.save(out/f'{pi+1:02d}-普通版.png');source.save(out/f'{pi+1:02d}-成品版.png')
        motion_preview(source,before,items,v['motion']).save(out/f'{pi+1:02d}-运动预览.png')
        offset=((960-source.width)//2,(540-source.height)//2)
        slide=prs.slides.add_slide(prs.slide_layouts[6])
        for ci,(item,bitmap,tile) in enumerate(items):
            x,y,w,h=item['before'];left=Inches((offset[0]+x*source.width)/80);top=Inches((offset[1]+y*source.height)/80);width=Inches(w*source.width/80);height=Inches(h*source.height/80)
            if item.get('text','').strip():
                shape=slide.shapes.add_textbox(left,top,width,height);shape.text_frame.word_wrap=True;shape.text=item['text']
                from pptx.enum.text import MSO_AUTO_SIZE
                shape.text_frame.auto_size=MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
                for paragraph in shape.text_frame.paragraphs:paragraph.font.size=Pt(14);paragraph.font.name='Arial'
            else:
                stream=io.BytesIO();tile.save(stream,format='PNG');stream.seek(0);slide.shapes.add_picture(stream,left,top,width,height)
        for f in range(length):
            if job['cancel']:raise ValueError('任务已取消')
            t=f/fps;canvas=Image.new('RGB',(1080,1440),'#eeeeed');draw=ImageDraw.Draw(canvas)
            draw.text((60,36),'普通排版',font=label_font,fill='#222222');draw.text((60,731),'成品重组',font=label_font,fill='#a51c24')
            canvas.paste(before,(60+offset[0],130+offset[1]))
            stage=motion_stage(source,before,items,t,v['motion'])
            canvas.paste(stage,(60+offset[0],830+offset[1]));draw.text((60,1396),'同一份内容 · 普通版为重新排版演示',font=small_font,fill='#666666')
            canvas.save(frames/f'{index:06d}.png');index+=1
            if f in [0,42,90]:
                path=out/f'预览_{pi+1}_{f}.png';canvas.save(path);previews.append(app.file_url(path))
            job['message']=f'正在制作第 {pi+1}/{len(pages)} 页：{f+1}/{length} 帧'
    deck=out/'普通排版版.pptx';prs.save(deck);app.write_json(out/'组件方案.json',v)
    movie=out/'组件重组视频.mp4';audio=['-stream_loop','-1','-i',app.ROOT/'video'/'music.wav'] if v.get('music',True) else ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    app.command(job,[app.ffmpeg(),'-y','-framerate',str(fps),'-i',frames/'%06d.png',*audio,'-frames:v',str(index),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',movie])
    app.command(job,[app.ffmpeg(),'-v','error','-i',movie,'-f','null','-']);shutil.rmtree(frames)
    return {'video':app.file_url(movie),'simplePpt':app.file_url(deck),'images':previews,'frames':index,'duration':len(pages)*4,'directory':str(out)}
