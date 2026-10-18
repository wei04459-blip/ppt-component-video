from pathlib import Path
import sys,tempfile,copy
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
from xhs_engine.templates import load_templates,render_template
from xhs_engine.fonts import load_font
out=ROOT/'web/template-previews';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    pages=[]
    for i in range(15):
        im=Image.new('RGB',(960,540),'white');d=ImageDraw.Draw(im)
        d.rectangle((0,0,960,94),fill='#204c7a')
        d.text((36,20),['项目背景','工作计划','实施过程','效果展示'][i%4],font=load_font('黑体粗',38),fill='white')
        d.text((36,115),'版式示例 · 导入后替换为你的真实课件',font=load_font('黑体',23),fill='#687e8b')
        for j in range(3):
            x=36+j*300;d.rounded_rectangle((x,180,x+280,470),radius=8,fill='#eef4f9')
            d.text((x+20,205),['内容一','内容二','内容三'][j],font=load_font('黑体粗',27),fill='#204c7a')
            for k in range(4):d.rounded_rectangle((x+20,270+k*35,x+240-(k%2)*35,281+k*35),radius=4,fill='#c8d9e6')
        p=Path(tmp)/f'{i}.png';im.save(p);pages.append(p)
    registry,assets=load_templates()
    for tid,cfg in registry.items():
        if cfg.get('approval_status')=='pending_user_review':continue
        cfg=copy.deepcopy(cfg)
        if cfg.get('strapline'):cfg['strapline']['text']='真实课件 · 内容展示'
        p=out/(tid+'.png');render_template(cfg,assets,pages[:cfg.get('page_capacity',1)],p,'汇报这样排',source_pages=pages)
        with Image.open(p) as image:
            image.thumbnail((270,360));image.save(p)
