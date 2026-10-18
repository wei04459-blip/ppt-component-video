from pathlib import Path
import re,json,shutil
root=Path(__file__).resolve().parent
source=root.parent/'outputs/PPT视频复现_2026-10-13/同内容美化对比_v7_motion_canvas_参考视觉'
out=root/'video/src/v7';out.mkdir(parents=True,exist_ok=True)
fields={}
for p in (source/'src/scenes').glob('*.ts*'):
    s=p.read_text().replace("'Arial Unicode MS'","'Toolbox'").replace("'Songti SC'","'Toolbox'").replace("'PingFang SC'","'Toolbox'").replace("'ReferenceXingkai'","'Toolbox'")
    entries={}
    def convert(m):
        raw=m.group(0)
        if not re.search('[\u4e00-\u9fff]',raw): return raw
        text=raw[1:-1].replace('\\n','\n')
        if text in ['改善前','改善后']: return raw
        entries[text]=text
        return 'T('+raw+')'
    s=re.sub(r"'(?:\\.|[^'\\])*'",convert,s)
    if p.name=='shared.ts':
        s=s.replace("export const blue='#123b78'","export const blue=data.color")
    if p.name=='effects.tsx':
        s=s.replace('[84,50,35.6][i]',"(data.metrics ?? [84,50,35.6])[i]")
    s="import data from '../../input.json';\nconst T=(s:string)=>(data.texts as any)?.[s] ?? s;\n"+s
    (out/p.name).write_text(s)
    fields[p.stem]=entries
(root/'video/v7-fields.json').write_text(json.dumps(fields,ensure_ascii=False,indent=2))
assets=root/'video/v7-assets';assets.mkdir(exist_ok=True)
for p in (source/'assets').glob('*.png'):shutil.copy(p,assets/p.name)
