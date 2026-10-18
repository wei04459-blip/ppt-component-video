"""Detached, local-only fallback when macOS LaunchAgent cannot spawn this checkout."""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('TOOLBOX_DATA',str(Path.home()/'Documents'/'鱼丸创作工具箱'))).resolve()
DATA.mkdir(parents=True,exist_ok=True)
def main():
    import fcntl
    with (DATA/'supervisor.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        (DATA/'supervisor.json').write_text(json.dumps({'pid':os.getpid(),'root':str(ROOT),'started':time.time()}))
        delay=1
        while True:
            started=time.monotonic()
            with (DATA/'service.stdout.log').open('ab') as stdout,(DATA/'service.stderr.log').open('ab') as stderr:
                process=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--port','8766','--no-browser'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                code=process.wait()
            with (DATA/'startup.log').open('a') as log:log.write(f'{time.ctime()} fallback child exited {code}; retry in {delay}s\n')
            if time.monotonic()-started>30:delay=1
            time.sleep(delay);delay=min(delay*2,30)
if __name__=='__main__':main()
