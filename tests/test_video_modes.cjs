const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const code=fs.readFileSync(require('path').join(__dirname,'../web/app.js'),'utf8');
const body=code.slice(code.indexOf('function videoData()'),code.indexOf('function renderSidebar()'));
const fields={videoMode:{value:'v7'},music:{checked:true},topLabel:{value:'上'},bottomLabel:{value:'下'},color:{value:'#123b78'},metric0:{valueAsNumber:84},metric1:{valueAsNumber:50},metric2:{valueAsNumber:35.6},startMonth:{valueAsNumber:3}};
const context={$:id=>fields[id],document:{querySelectorAll:()=>[]},v7Images:{},componentVideoData:()=>({mode:'components',pages:[{number:1}]})};vm.createContext(context);vm.runInContext(body,context);
let data=context.videoData();assert.equal(data.mode,'v7');assert.equal(data.metrics[0],84);
fields.videoMode.value='cards';assert.equal(context.videoData().mode,'cards');
fields.videoMode.value='components';assert.equal(context.videoData().mode,'components');
console.log('PASS: three GUI video modes preserve the correct export route');
