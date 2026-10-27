"""Use this task's bundled-font configuration; never install/change system fonts."""
import argparse,json,os,shutil,subprocess,uuid
from pathlib import Path

def main():
 parser=argparse.ArgumentParser(description='用本任务fontconfig将普通PPT转为PDF/PNG，供实际字形与换行检查')
 parser.add_argument('--work',required=True);parser.add_argument('--ppt',required=True);args=parser.parse_args()
 work=Path(args.work).expanduser().resolve();ppt=Path(args.ppt).expanduser().resolve();config=work/'fontconfig.xml'
 if not config.is_file() or not ppt.is_file():raise ValueError('请提供prepare生成的WORK和存在的普通PPT；原件不会被覆盖')
 choices=[shutil.which('soffice'),'/Applications/LibreOffice.app/Contents/MacOS/soffice',str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'LibreOffice/program/soffice.exe')]
 office=next((x for x in choices if x and Path(x).is_file()),None)
 if not office:raise ValueError('未找到LibreOffice，请先安装或按AGENT_START准备环境')
 out=work/('ppt-font-check-'+uuid.uuid4().hex[:8]);out.mkdir();env=os.environ.copy();env['FONTCONFIG_FILE']=str(config)
 command=[office,'-env:UserInstallation='+(out/'office-profile').as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(ppt)]
 result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=180);(out/'convert.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 pdf=out/(ppt.stem+'.pdf')
 if result.returncode or not pdf.exists():raise ValueError('转换失败，请查看 '+str(out/'convert.log'))
 import pymupdf
 with pymupdf.open(pdf) as document:
  for i,page in enumerate(document):page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(out/f'page-{i+1:02d}.png')
 (out/'check.json').write_text(json.dumps(dict(ppt=str(ppt),fontconfig=str(config),office=office,pdf=str(pdf),boundary='请逐页查看PNG的实际字形、换行、照片比例；PDF提取文字成功不等于字体可见；未验证其他编辑器/平台'),ensure_ascii=False,indent=2),encoding='utf-8')
 print(out)
if __name__=='__main__':main()
