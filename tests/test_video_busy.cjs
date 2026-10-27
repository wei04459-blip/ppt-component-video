const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('web/app.js','utf8');
const editor={inert:false},elements=new Map();const $=id=>{if(!elements.has(id))elements.set(id,{disabled:false,hidden:true,textContent:'',value:'components',querySelector:()=>editor});return elements.get(id)};
const ctx={$,document:{querySelectorAll:()=>[]},setTimeout:fn=>{fn()},activeJob:null,current:{id:'test'},notice(){},save:async()=>{},refresh:async()=>{},autoPages(){},console};vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('function setVideoWorkLocked'),source.indexOf('\nasync function importFiles')),ctx);
(async()=>{
 ctx.busy(true);assert(editor.inert);assert.equal($('videoBusyNotice').hidden,false);ctx.busy(false);assert.equal(editor.inert,false);assert.equal($('videoBusyNotice').hidden,true);
 let creates=0,polls=0;ctx.api=async url=>{if(url==='/api/video'){creates++;return {job:'job1'}}if(url==='/api/job/job1'){polls++;if(polls===1)throw Error('临时断线');assert(editor.inert);return {status:'done',message:'完成'}}throw Error(url)};
 await ctx.run('video',{video:{mode:'components'}});assert.equal(creates,1);assert.equal(polls,2);assert.equal(ctx.activeJob,null);assert.equal(editor.inert,false);
 const handler=source.slice(source.indexOf("$('makeVideo').onclick="),source.indexOf('\n',source.indexOf("$('makeVideo').onclick=")));
 ctx.safe=fn=>fn;ctx.componentExportIssue=()=>'';ctx.videoData=()=>({mode:'components'});let finish;ctx.run=()=>new Promise(r=>finish=r);vm.runInContext(handler,ctx);
 const pending=$('makeVideo').onclick();assert(editor.inert);finish();await pending;assert.equal(editor.inert,false);
 ctx.run=async()=>{throw Error('提交失败')};await assert.rejects($('makeVideo').onclick(),/提交失败/);assert.equal(editor.inert,false);
 const cancelHandler=source.slice(source.indexOf("$('cancel').onclick="),source.indexOf('\n',source.indexOf("$('cancel').onclick=")));vm.runInContext(cancelHandler,ctx);ctx.activeJob='running';let message='';ctx.notice=text=>message=text;ctx.api=async()=>{throw Error('offline')};await $('cancel').onclick();assert(message.includes('任务可能仍在运行'));assert.equal(ctx.activeJob,'running');ctx.api=async()=>({ok:true});await $('cancel').onclick();assert($('progressMessage').textContent.includes('等待任务停止确认'));assert.equal(ctx.activeJob,'running');
 console.log('Video busy checks passed: editor lock, progress visibility, polling reconnect without duplicate submission, unlock on completion and submission failure');
})().catch(error=>{console.error(error);process.exitCode=1});
