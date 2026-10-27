const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('web/app.js','utf8');const fn=source.slice(source.indexOf('function videoData()'),source.indexOf('\nfunction renderSidebar'));
const els={videoMode:{value:'components'},music:{checked:true},topLabel:{value:'普通版'},bottomLabel:{value:'成品版'},color:{value:'#123b78'},metric0:{valueAsNumber:84},metric1:{valueAsNumber:50},metric2:{valueAsNumber:35.6},startMonth:{valueAsNumber:3}};
const ctx={$:id=>els[id],componentVideoData:()=>({mode:'components',pages:[{number:1}]}),v7Images:{},document:{querySelectorAll:()=>[]}};vm.createContext(ctx);vm.runInContext(fn,ctx);
assert.equal(ctx.videoData().mode,'components');assert.equal(ctx.videoData().pages.length,1);
els.videoMode.value='v7';assert.equal(ctx.videoData().mode,'v7');assert.deepEqual(Array.from(ctx.videoData().metrics),[84,50,35.6]);
els.videoMode.value='cards';assert.equal(ctx.videoData().mode,undefined);assert.deepEqual(Array.from(ctx.videoData().pages),[]);assert.equal(ctx.videoData().color,'#123b78');
console.log('Video mode routing passed: components / v7 / cards');
