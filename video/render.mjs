import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import net from 'node:net';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:['ignore','pipe','pipe']});
let browser;let errors=[];
server.stderr.on('data',d=>process.stderr.write(d));
try{
 for(let i=0;i<150;i++){if(server.exitCode!==null)throw Error('视频服务未能启动');try{const r=await fetch(`http://127.0.0.1:${port}/render.html`);if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,200));}
 let executablePath;
 if(!fs.existsSync(chromium.executablePath())){
 const cache=process.env.PLAYWRIGHT_BROWSERS_PATH || (process.platform==='darwin'?path.join(os.homedir(),'Library/Caches/ms-playwright'):process.platform==='win32'?path.join(process.env.LOCALAPPDATA||'','ms-playwright'):path.join(os.homedir(),'.cache/ms-playwright'));
 if(fs.existsSync(cache)){for(const folder of fs.readdirSync(cache).filter(x=>/^chromium-/.test(x)).sort().reverse()){
 const suffixes=['chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing','chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing','chrome-win/chrome.exe','chrome-linux/chrome'];
 for(const suffix of suffixes){const candidate=path.join(cache,folder,suffix);if(fs.existsSync(candidate)){executablePath=candidate;break;}}
 if(executablePath)break;
 }}
 }
 browser=await chromium.launch({headless:true,executablePath,channel:executablePath?undefined:'chromium'});const page=await browser.newPage();
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(`http://127.0.0.1:${port}/render.html`);
 await page.waitForFunction(()=>typeof window.renderProject==='function',null,{timeout:60000});
 const result=await page.evaluate(()=>window.renderProject());
 if(result!==0||errors.length)throw Error(`渲染失败 ${result}: ${errors.join(';')}`);
 console.log('RENDER_COMPLETE');
}finally{if(browser)await browser.close();server.kill();}
