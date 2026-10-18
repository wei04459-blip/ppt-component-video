import argparse, json, signal, sys, threading
from pathlib import Path
from .core import *
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--version',action='version',version='image-dedup 1.0');sub=parser.add_subparsers(dest='command',required=True)
 for cmd,flag in [('run','job'),('validate','config'),('inspect','input')]:
  p=sub.add_parser(cmd);p.add_argument('--'+flag,required=True)
  if cmd=='inspect': p.add_argument('--json',action='store_true')
 args=parser.parse_args();cancel=threading.Event();signal.signal(signal.SIGINT,lambda *_:cancel.set())
 def emit(e): print(json.dumps(e,ensure_ascii=False),flush=True)
 try:
  if args.command=='inspect': emit(inspect(args.input));return 0
  if args.command=='validate': emit(validate(json.loads(Path(args.config).read_text())));return 0
  path=Path(args.job).resolve();job=json.loads(path.read_text())
  if set(job)-{'job_schema_version','inputs','output_dir','config'} or type(job.get('job_schema_version'))!=int or job.get('job_schema_version')!=1 or not isinstance(job.get('inputs'),list) or not job['inputs']: raise Error('INVALID_CONFIG','无效任务')
  if any(not isinstance(x,str) or not x for x in job['inputs']) or not isinstance(job.get('output_dir'),str) or not job['output_dir'].strip(): raise Error('INVALID_CONFIG','输入输出路径无效')
  config=validate(job.get('config',{}));config['io']['open_output_when_done']=False
  # Inputs are copied into an isolated workspace before any compatibility side effect.
  import shutil,tempfile
  workspace_manager=tempfile.TemporaryDirectory(prefix='image-dedup-import-');workspace=Path(workspace_manager.name);inputs=[];seen=set();original_sources={}
  for i,raw in enumerate(job['inputs']):
   src=(path.parent/raw).resolve()
   if src in seen: continue
   seen.add(src)
   if not src.is_file(): raise Error('FILE_NOT_FOUND',str(src))
   dest=workspace/str(i)/src.name;dest.parent.mkdir();shutil.copy2(src,dest);inputs.append(dest);original_sources[str(dest.resolve())]=str(src)
  # Protect original input aliases too: output may never overwrite a source.
  output=(path.parent/job['output_dir']).resolve()
  for src in seen:
   if (output/('processed_'+src.name)).resolve() in seen: raise Error('WOULD_OVERWRITE_INPUT')
  result=batch(inputs,output,config,emit,cancel,protected_inputs=seen,original_sources=original_sources);workspace_manager.cleanup();return 130 if result['cancelled'] else 1 if result['failed'] else 0
 except Exception as e: emit(dict(type='error',error_code=getattr(e,'code','INVALID_CONFIG'),message=str(e)));return 2
if __name__=='__main__': sys.exit(main())
