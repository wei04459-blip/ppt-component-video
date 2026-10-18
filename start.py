"""Start an independent local service and wait until the interface is ready."""
import argparse,json,os,plistlib,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('TOOLBOX_DATA',str(Path.home()/'Documents'/'鱼丸创作工具箱')))
DATA.mkdir(parents=True,exist_ok=True)
URL='http://127.0.0.1:8766'
LABEL='local.yuwan.creator-toolbox'
def ready():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL+'/api/health',timeout=2) as response:
            return json.load(response).get('app')=='creator-toolbox'
    except (OSError,ValueError):return False
def start():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if not ready():
        command=[sys.executable,str(ROOT/'app.py'),'--port','8766','--no-browser']
        if sys.platform=='darwin':
            domain=f'gui/{os.getuid()}'
            fallback=DATA/'launchd-fallback.json'
            def note(message):
                with (DATA/'startup.log').open('a') as log:log.write(time.ctime()+' '+message+'\n')
            if not fallback.exists():
                service=DATA/'service.plist'
                spec={'Label':LABEL,'ProgramArguments':command,'WorkingDirectory':str(ROOT),
                      'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':10,
                      'EnvironmentVariables':{'PATH':os.environ.get('PATH','/usr/bin:/bin'),'TOOLBOX_DATA':str(DATA)},
                      'StandardOutPath':str(DATA/'service.stdout.log'),'StandardErrorPath':str(DATA/'service.stderr.log')}
                service.write_bytes(plistlib.dumps(spec))
                existing=subprocess.run(['launchctl','print',domain+'/'+LABEL],capture_output=True)
                operation=['launchctl','kickstart',domain+'/'+LABEL] if existing.returncode==0 else ['launchctl','bootstrap',domain,str(service)]
                result=subprocess.run(operation,capture_output=True,text=True)
                for _ in range(5):
                    if ready():break
                    time.sleep(1)
                if not ready():
                    diagnostic=subprocess.run(['launchctl','print',domain+'/'+LABEL],capture_output=True,text=True)
                    fallback.write_text(json.dumps({'created':time.time(),'reason':'LaunchAgent did not become ready','result':result.stderr,'diagnostic':diagnostic.stdout},ensure_ascii=False,indent=2))
                    note('LaunchAgent unavailable; recorded diagnostics, switching to detached supervisor')
            if fallback.exists() and not ready():
                # Disable only our own failing LaunchAgent before starting the fallback.
                subprocess.run(['launchctl','bootout',domain+'/'+LABEL],capture_output=True)
                with (DATA/'startup.log').open('ab') as log:
                    subprocess.Popen([sys.executable,str(ROOT/'service_supervisor.py')],cwd=ROOT,
                                     stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
                note('Detached supervisor requested')
        else:
            with (DATA/'service.stdout.log').open('ab') as log:
                options={'creationflags':subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
                subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,**options)
        for _ in range(90):
            if ready():break
            time.sleep(1)
        else:raise RuntimeError('工具箱未能启动，请查看 '+str(DATA/'service.stderr.log'))
    print(URL,flush=True)
    if not args.no_browser:webbrowser.open(URL)
if __name__=='__main__':start()
