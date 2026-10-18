let componentPages=[],componentIndex=0,componentHistory=[],drawingRegion=false;
function componentVideoData(){return {mode:'components',editorPages:componentPages,pages:componentPages.filter(p=>p.include).map(p=>({source:p.source,number:p.number,components:p.components,confirmed:p.confirmed})),motion:$('componentMotion').value,music:$('music').checked,topLabel:$('topLabel').value,bottomLabel:$('bottomLabel').value,color:$('color').value};}
function loadComponentVideo(v){componentPages=v.mode==='components'?(v.editorPages||v.pages||[]).map(p=>({...p,include:p.include!==false})):[];componentIndex=0;componentHistory=[];$('componentMotion').value=v.motion||'stagger';renderComponentPages();}
function componentCurrent(){return componentPages[componentIndex];}
function componentRemember(){componentHistory.push(JSON.stringify(componentPages));if(componentHistory.length>25)componentHistory.shift();}
function componentChanged(){const p=componentCurrent();if(p)p.confirmed=false;dirty=true;$('componentStill').innerHTML='';renderComponentPages();}
function gridComponents(items){const cols=items.length<=3?1:items.length<=12?2:4,rows=Math.ceil(items.length/cols);items.forEach((item,i)=>{item.before=[.025+(i%cols)*.95/cols,.025+Math.floor(i/cols)*.95/rows,.95/cols-.025,.95/rows-.025];});}
$('readComponents').onclick=safe(async()=>{
 if(activeJob)throw Error('请等待当前任务完成');if(componentPages.some(p=>p.components.length)&&!confirm('重新读取会替换当前组件方案，继续吗？'))return;
 $('componentNotice').textContent='正在读取课件对象…';const r=await api('/api/components/analyse',{project:current.id});
 componentRemember();componentPages=r.pages.map((p,i)=>({...p,include:i===0,confirmed:false,components:p.objects.map(o=>({...o,before:[0,0,.2,.2]}))}));componentPages.forEach(p=>gridComponents(p.components));componentIndex=0;dirty=true;renderComponentPages();$('componentNotice').textContent=r.notice;
});
function renderComponentPages(){
 $('componentPages').innerHTML=componentPages.map((p,i)=>'<div><label class="check"><input type="checkbox" data-include="'+i+'" '+(p.include?'checked':'')+'>第 '+p.number+' 页</label><button data-component-page="'+i+'" class="'+(componentIndex===i?'primary':'')+'">编辑 '+p.components.length+' 个组件'+(p.confirmed?' ✓':'')+'</button></div>').join('');
 const p=componentCurrent();$('componentWork').hidden=!p;if(!p)return;
 $('componentsConfirmed').checked=!!p.confirmed;renderComponentBoards();
 $('componentList').innerHTML=p.components.map((c,i)=>'<div class="component-config"><label class="check"><input type="checkbox" data-merge="'+i+'">组件 '+(i+1)+' · '+esc(c.name||'手动框选')+'</label><textarea data-component-text="'+i+'" rows="2" maxlength="2000" placeholder="普通版文字（留空则使用原图块）">'+esc(c.text||'')+'</textarea><button data-remove-component="'+i+'">删除</button></div>').join('');
}
function renderComponentBoards(){
 const p=componentCurrent();if(!p)return;
 const target=$('targetBoard'),plain=$('plainBoard');
 target.innerHTML='<img class="component-source" src="'+esc(p.source)+'" alt="成品页">'+p.components.map((c,i)=>'<div class="component-region" style="'+rectStyle(c.target)+'"><span>'+(i+1)+'</span></div>').join('');
 const image=target.querySelector('img');image.onload=()=>{p.aspect=image.naturalWidth/image.naturalHeight;plain.style.aspectRatio=image.naturalWidth+'/'+image.naturalHeight;};
 plain.innerHTML=p.components.map((c,i)=>'<div class="plain-component" data-move-component="'+i+'" style="'+rectStyle(c.before)+'"><b>'+(i+1)+'</b>'+plainComponentContent(p,c)+'<span class="component-resize"></span></div>').join('');
 $('drawRegion').textContent=drawingRegion?'在成品页拖出一个矩形…':'＋ 在成品页画框';target.classList.toggle('drawing',drawingRegion);
}
function rectStyle(r){return 'left:'+r[0]*100+'%;top:'+r[1]*100+'%;width:'+r[2]*100+'%;height:'+r[3]*100+'%';}
$('componentPages').onclick=e=>{const b=e.target.closest('[data-component-page]');if(b){componentIndex=Number(b.dataset.componentPage);renderComponentPages();}};
$('componentPages').onchange=e=>{if(!e.target.matches('[data-include]'))return;const p=componentPages[Number(e.target.dataset.include)];if(e.target.checked&&componentPages.filter(p=>p.include).length>=6){e.target.checked=false;return notice('每条视频最多选择 6 页');}p.include=e.target.checked;dirty=true;};
$('componentList').onchange=e=>{if(e.target.matches('[data-component-text]')){componentRemember();componentCurrent().components[Number(e.target.dataset.componentText)].text=e.target.value;componentChanged();}};
$('componentList').onclick=e=>{const b=e.target.closest('[data-remove-component]');if(b){componentRemember();componentCurrent().components.splice(Number(b.dataset.removeComponent),1);componentChanged();}};
$('resetPlain').onclick=()=>{componentRemember();gridComponents(componentCurrent().components);componentChanged();};
$('componentUndo').onclick=()=>{if(!componentHistory.length)return;componentPages=JSON.parse(componentHistory.pop());componentIndex=Math.min(componentIndex,Math.max(0,componentPages.length-1));dirty=true;renderComponentPages();};
$('componentsConfirmed').onchange=()=>{componentCurrent().confirmed=$('componentsConfirmed').checked;dirty=true;renderComponentPages();};
$('drawRegion').onclick=()=>{drawingRegion=!drawingRegion;renderComponentBoards();};
$('mergeRegions').onclick=()=>{const indexes=[...document.querySelectorAll('[data-merge]:checked')].map(e=>Number(e.dataset.merge));if(indexes.length<2)return notice('先勾选至少两个组件');componentRemember();const p=componentCurrent(),items=indexes.map(i=>p.components[i]);const x=Math.min(...items.map(c=>c.target[0])),y=Math.min(...items.map(c=>c.target[1])),r=Math.max(...items.map(c=>c.target[0]+c.target[2])),b=Math.max(...items.map(c=>c.target[1]+c.target[3]));p.components=p.components.filter((_,i)=>!indexes.includes(i));p.components.push({id:crypto.randomUUID(),name:'合并组件',target:[x,y,r-x,b-y],before:items[0].before,text:items.map(c=>c.text).filter(Boolean).join('\n').slice(0,2000)});componentChanged();};
$('targetBoard').onpointerdown=e=>{if(!drawingRegion||!componentCurrent())return;e.preventDefault();const board=$('targetBoard'),rect=board.getBoundingClientRect();const point=ev=>[Math.max(0,Math.min(1,(ev.clientX-rect.left)/rect.width)),Math.max(0,Math.min(1,(ev.clientY-rect.top)/rect.height))];const a=point(e);let b=a;const ghost=document.createElement('div');ghost.className='component-region';board.append(ghost);board.setPointerCapture(e.pointerId);board.onpointermove=ev=>{b=point(ev);ghost.style.cssText=rectStyle([Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])]);};board.onpointerup=()=>{board.onpointermove=null;board.onpointerup=null;const target=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])];if(target[2]>=.01&&target[3]>=.01&&componentCurrent().components.length<40){componentRemember();componentCurrent().components.push({id:crypto.randomUUID(),name:'手动框选',text:'',target,before:[.05,.05,.4,.25]});}drawingRegion=false;componentChanged();};};
$('plainBoard').onpointerdown=e=>{const box=e.target.closest('[data-move-component]');if(!box)return;e.preventDefault();const board=$('plainBoard'),rect=board.getBoundingClientRect(),c=componentCurrent().components[Number(box.dataset.moveComponent)],a=[...c.before],x=e.clientX,y=e.clientY,resize=!!e.target.closest('.component-resize');let moved=false;box.setPointerCapture(e.pointerId);box.onpointermove=ev=>{if(!moved){componentRemember();moved=true;}const dx=(ev.clientX-x)/rect.width,dy=(ev.clientY-y)/rect.height;c.before=resize?[a[0],a[1],Math.max(.02,Math.min(1-a[0],a[2]+dx)),Math.max(.02,Math.min(1-a[1],a[3]+dy))]:[Math.max(0,Math.min(1-a[2],a[0]+dx)),Math.max(0,Math.min(1-a[3],a[1]+dy)),a[2],a[3]];box.style.cssText=rectStyle(c.before);};box.onpointerup=()=>{box.onpointermove=null;box.onpointerup=null;if(moved)componentChanged();};};
$('componentPreview').onclick=safe(async()=>{const v=componentVideoData();$('componentNotice').textContent='正在生成实际预览…';const result=await api('/api/components/preview',{project:current.id,video:v});$('componentStill').innerHTML=result.pages.map((p,i)=>'<h3>第 '+v.pages[i].number+' 页 · 普通版 / 成品版</h3><img src="'+p.before+'" alt="普通版实际预览"><img src="'+esc(p.after)+'" alt="成品版实际预览"><h4>组件运动过程</h4><img src="'+p.motion+'" alt="六个时点的真实运动预览">').join('');$('componentNotice').textContent='请检查实际预览，确认后勾选各页的核对选项，再点击“制作并预览视频”。';});

function plainComponentContent(p,c){
 if(c.text)return '<div>'+esc(c.text)+'</div>';
 const h=1000/(p.aspect||16/9),r=c.target;
 const clip='plain-clip-'+p.components.indexOf(c);
 return '<svg class="plain-crop" viewBox="'+[r[0]*1000,r[1]*h,r[2]*1000,r[3]*h].join(' ')+'" preserveAspectRatio="xMidYMid meet"><defs><clipPath id="'+clip+'"><rect x="'+r[0]*1000+'" y="'+r[1]*h+'" width="'+r[2]*1000+'" height="'+r[3]*h+'"/></clipPath></defs><image clip-path="url(#'+clip+')" href="'+esc(p.source)+'" width="1000" height="'+h+'" preserveAspectRatio="none"/></svg>';
}
