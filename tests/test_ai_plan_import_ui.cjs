const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('web/app.js','utf8'),fn=src.slice(src.indexOf('async function importCreatorPlan('),src.indexOf("\n$('planFile').onchange="));let requests=[],loaded=null,saves=0,rejectImport=false;
const scene={width:960,height:540,groups:[{id:'group',before:[0,0,1],after:[0,0,1],nodes:[{kind:'text',id:'n',text:'原文',before:{x:20,y:30,fontSize:24},sourceRef:{component:'c',path:'text'}}]}]};
const video={mode:'components',pages:[{number:8,source:'/files/current/page8.png',components:[{id:'c',plain:{kind:'text',text:'原文'}}],scene,aiReview:{sourceRead:true,ordinaryIndependent:true,contentChecked:true,notes:'已核对第8页密表与单位'},confirmed:false,include:true}]};
const ctx={activeJob:null,current:{id:'current',name:'当前作品',note:{title:'保持图文笔记'}},save:async()=>{saves++},api:async(path,payload)=>{requests.push({path,payload});if(path==='/api/components/import-plan'){if(rejectImport)throw Error('源课件指纹不一致，请先导入相同原件');return {video,notice:'源已核对'}}return {...ctx.current,...payload}},loadProject:p=>loaded=p,notice(){}};vm.createContext(ctx);vm.runInContext(fn,ctx);
(async()=>{
 const plan={schemaVersion:1,input_sha256:'original-hash',pages:[{number:8,scene,components:video.pages[0].components,aiReview:video.pages[0].aiReview}]};
 await ctx.importCreatorPlan(plan);assert.equal(saves,1);assert.equal(requests[0].path,'/api/components/import-plan');assert.equal(requests[0].payload.project,'current');assert.strictEqual(requests[0].payload.plan,plan);assert.equal(requests[1].payload.video.pages[0].source,'/files/current/page8.png');assert.strictEqual(loaded.video.pages[0].scene.groups[0].nodes[0].before,scene.groups[0].nodes[0].before);assert.equal(loaded.note.title,'保持图文笔记');
 requests=[];loaded=null;rejectImport=true;await assert.rejects(ctx.importCreatorPlan(plan),/指纹不一致/);assert.equal(requests.length,1);assert.equal(loaded,null);
 requests=[];rejectImport=false;await ctx.importCreatorPlan({schemaVersion:1,note:{title:'旧方案'},video:{mode:'v7'}});assert.equal(requests.length,1);assert.equal(requests[0].path,'/api/project');assert.equal(loaded.video.mode,'v7');
 ctx.activeJob='running';requests=[];await assert.rejects(ctx.importCreatorPlan(plan),/请等待/);assert.equal(requests.length,0);
 console.log('AI plan import UI checks passed: source validation endpoint, mapped source, scene/node.before/aiReview preserved, rejection stops save, legacy import retained, active task guard');
})().catch(e=>{console.error(e);process.exitCode=1});
