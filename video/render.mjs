import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import net from 'node:net';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
const input=JSON.parse(fs.readFileSync('input.json','utf8'));const runToken=randomUUID();input.runToken=runToken;fs.writeFileSync('input.json',JSON.stringify(input));
const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:['ignore','pipe','pipe']});
let browser;let errors=[];let closing=false;
const cleanup=async()=>{if(closing)return;closing=true;if(browser)await browser.close().catch(()=>{});if(server.exitCode===null){server.kill('SIGTERM');await Promise.race([new Promise(r=>server.once('exit',r)),new Promise(r=>setTimeout(r,1800))]);if(server.exitCode===null)server.kill('SIGKILL');}};
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>{cleanup().finally(()=>process.exit(signal==='SIGTERM'?143:130));});
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
 page.on('console',m=>{const s=m.text();if(m.type()==='error'||/Failed to load|Cannot load|Error loading|not loaded/i.test(s))errors.push(s+' at '+JSON.stringify(m.location()));if(s.startsWith('MC_SEMANTIC_PAGE'))console.log(s);});
 page.on('response',r=>{if(r.status()>=400)errors.push('HTTP '+r.status()+' '+r.url());});
 await page.goto(`http://127.0.0.1:${port}/render.html`);
 await page.waitForFunction(token=>typeof window.renderProject==='function'&&window.TOOLBOX_RENDER_TOKEN===token,runToken,{timeout:60000});

 const imagePaths=[...new Set((input.mode==='semantic'?input.pages:[]).flatMap(p=>p.groups.flatMap(g=>g.nodes.filter(n=>n.kind==='image').map(n=>'/'+n.src))))];
 await page.evaluate(async paths=>{await Promise.all(paths.map(src=>new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>i.naturalWidth>0?resolve(true):reject(Error('Empty image '+src));i.onerror=()=>reject(Error('Missing image '+src));i.src=src;})));},imagePaths);
 const result=await page.evaluate(()=>window.renderProject());
 if(result!==0||errors.length)throw Error(`渲染失败 ${result}: ${errors.join(';')}`);
 console.log('RENDER_COMPLETE');
}finally{await cleanup();}
