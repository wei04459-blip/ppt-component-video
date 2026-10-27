let componentPages=[],componentIndex=0,componentHistory=[],drawingRegion=false,componentPreviewRunning=false,componentAnalysisRunning=false;
const componentPreviewSnapshots=new Map();
const componentActualBefore=new Map();
function componentVideoData(){return {mode:'components',editorPages:componentPages,pages:componentPages.filter(p=>p.include).map(p=>({source:p.source,number:p.number,components:p.components,confirmed:p.confirmed,...(p.aiReview?{aiReview:p.aiReview}:{}),...(p.automation?{automation:p.automation}:{}),...(p.scene?{scene:p.scene}:{}),...(p.design?{design:p.design}:{})})),motion:$('componentMotion').value,music:$('music').checked,topLabel:$('topLabel').value,bottomLabel:$('bottomLabel').value,color:$('color').value};}
function loadComponentVideo(v){componentPages=v.mode==='components'?(v.editorPages||v.pages||[]).map(p=>({...p,include:p.include!==false,confirmed:false})):[];componentIndex=0;componentHistory=[];componentPreviewSnapshots.clear();componentActualBefore.clear();$('componentMotion').value='stagger';renderComponentPages();}
function componentCurrent(){return componentPages[componentIndex];}
function componentRemember(){componentHistory.push(JSON.stringify(componentPages));if(componentHistory.length>25)componentHistory.shift();}
function componentChanged(){const p=componentCurrent();if(p){p.confirmed=false;componentPreviewSnapshots.delete(p.number);componentActualBefore.delete(p.number);if(p.scene){delete p.scene;notice('内容已修改，将按当前组件重新生成画面，请重新核对实际预览。');}}dirty=true;$('componentStill').innerHTML='';renderComponentPages();}
function gridComponents(items){const cols=items.length<=3?1:items.length<=12?2:4,rows=Math.ceil(items.length/cols);items.forEach((item,i)=>{item.before=[.025+(i%cols)*.95/cols,.025+Math.floor(i/cols)*.95/rows,.95/cols-.025,.95/rows-.025];});}
function automationIssues(p){return (p.automation?.issues||[]).map(issue=>typeof issue==='string'?issue:[issue.location,issue.message].filter(Boolean).join('：')).join('；')||(['needs-ai','draft','evidence'].includes(p.automation?.status)?'请交给WorkBuddy或Codex核对并生成方案，再导入工具':'');}
function automationBlocked(p){return ['blocked','needs-ai','draft','evidence'].includes(p.automation?.status);}
function clearComponentPlanForNewSource(){
 componentPages=[];componentIndex=0;componentHistory=[];componentPreviewSnapshots.clear();componentActualBefore.clear();$('componentStill').innerHTML='';dirty=true;renderComponentPages();
 $('componentNotice').textContent='课件已导入。请让WorkBuddy或Codex理解课件并生成视频方案，再使用“导入AI方案”。辅助识别只提供草稿，不代替AI核对。';
}
async function analyseComponentProject({automatic=false}={}){
 if(componentAnalysisRunning)return;
 if(activeJob)throw Error('请等待当前任务完成');
 if(!automatic&&componentPages.some(p=>p.components.length)&&!confirm('辅助识别会替换当前方案为待AI核对的草稿，继续吗？'))return;
 const projectId=current.id,started=Date.now();componentAnalysisRunning=true;const timer=setInterval(()=>{if(current.id===projectId)$('componentNotice').textContent='正在辅助识别课件内容 · 已等待 '+Math.floor((Date.now()-started)/1000)+' 秒。图片型课件需要更久；无法完整识别的页面会列出具体原因。';},1000);
 $('readComponents').disabled=true;$('readComponents').textContent='正在辅助识别…';$('componentNotice').textContent='正在提取供AI核对的内容草稿，请稍候…';
 setVideoWorkLocked(true,'正在辅助识别内容，请稍候；识别结果需交给AI核对。');
 if(automatic){componentPages=[];componentPreviewSnapshots.clear();componentActualBefore.clear();$('componentStill').innerHTML='';renderComponentPages();}
 try{
  const result=await api('/api/components/analyse',{project:projectId});
  if(current.id!==projectId)return;
  componentRemember();componentPreviewSnapshots.clear();componentActualBefore.clear();
  componentPages=result.pages.map(p=>({...p,include:false,confirmed:false,automation:{...p.automation,status:p.automation?.status==='blocked'?'blocked':'needs-ai',summary:'辅助识别草稿，需由WorkBuddy或Codex核对内容并完成设计，不是最终成品方案。'},components:(p.objects||p.components||[]).map(o=>({...o}))}));
  componentPages.forEach(p=>{
   const suggestions=p.components.map(c=>c.before);gridComponents(p.components);
   p.components.forEach((c,i)=>{const r=suggestions[i];if(Array.isArray(r)&&r.length===4&&r.every(Number.isFinite)&&r[0]>=0&&r[1]>=0&&r[2]>0&&r[3]>0&&r[0]+r[2]<=1&&r[1]+r[3]<=1)c.before=[...r];});
  });

  componentIndex=Math.max(0,componentPages.findIndex(p=>p.include));dirty=true;renderComponentPages();
  const blocked=componentPages.filter(p=>p.automation?.status==='blocked');
  $('componentNotice').textContent='已生成 '+componentPages.length+' 页辅助内容草稿。请交给WorkBuddy或Codex核对并制作AI方案，再导入实际预览。'+(blocked.length?'识别问题：'+blocked.map(p=>'第 '+p.number+' 页 '+automationIssues(p)).join('；'):'');
 }catch(error){$('componentNotice').textContent='方案未生成：'+error.message+'。课件已保留，可重新生成方案。';throw error;}
 finally{clearInterval(timer);componentAnalysisRunning=false;setVideoWorkLocked(false);$('readComponents').disabled=false;$('readComponents').textContent='辅助识别课件（供AI核对）';}
}
$('readComponents').onclick=safe(()=>analyseComponentProject());
$('componentImportPlan').onclick=()=> $('planFile').click();
$('copyAIInstructions').onclick=safe(async()=>{await navigator.clipboard.writeText($('aiVideoInstructions').value);notice('制作说明已复制，请连同本工具文件夹和源PPT一起交给AI。');});

function renderComponentPageList(){
 $('componentPages').innerHTML=componentPages.map((p,i)=>'<div><label class="check"><input type="checkbox" data-include="'+i+'" '+(p.include?'checked':'')+'>第 '+p.number+' 页</label><button data-component-page="'+i+'" class="'+(componentIndex===i?'primary':'')+'">查看 '+p.components.length+' 项内容'+(p.confirmed?' ✓':automationBlocked(p)?' · 待处理':'')+'</button></div>').join('');
}
function componentPreviewSnapshot(p){return JSON.stringify({source:p.source,number:p.number,components:p.components,scene:p.scene,design:p.design,motion:$('componentMotion').value});}
function componentHasPreview(p){return componentPreviewSnapshots.get(p.number)===componentPreviewSnapshot(p);}
function componentExportIssue(){
 if(componentAnalysisRunning)return '正在辅助识别课件，请稍候';
 if(componentPreviewRunning)return '请等待实际预览完成，再制作视频';
 const pages=componentPages.filter(p=>p.include);
 if(!pages.length)return '请先选择要制作的页面';
 const blocked=pages.find(automationBlocked);if(blocked)return '第 '+blocked.number+' 页暂不能制作：'+automationIssues(blocked);
 if(pages.some(p=>p.components.length<2||p.components.some(c=>!plainContentReady(c.plain||(c.text?{kind:'text',text:c.text}:null)))))return '请先补全所选页面的普通版内容';
 if(pages.some(p=>!componentHasPreview(p)))return '请先查看两版实际预览';
 if(pages.some(p=>!p.confirmed))return '请核对实际预览，并逐页勾选确认';
 return '';
}
function updateComponentReadiness(){
 const p=componentCurrent();componentPages.forEach(page=>{if(!componentHasPreview(page))page.confirmed=false;});renderComponentPageList();
 if(p){
  const missing=p.components.filter(c=>!plainContentReady(c.plain||(c.text?{kind:'text',text:c.text}:null))).length,ready=componentHasPreview(p);
  if(!ready)p.confirmed=false;
  $('componentReadiness').textContent=automationBlocked(p)?'第 '+p.number+' 页需要AI核对：'+automationIssues(p):'第 '+p.number+' 页 · '+p.components.length+' 个组件'+(missing?' · '+missing+' 个待补全':!ready?' · 先查看两版实际预览':p.confirmed?' · 已核对实际预览':' · 实际预览已完成，请核对并勾选确认');
  $('componentReadiness').classList.toggle('needs-content',!!missing||!ready);
  $('componentsConfirmed').checked=!!p.confirmed;$('componentsConfirmed').disabled=!!missing||p.components.length<2||!ready||automationBlocked(p);
 }
 const aiReviewed=p?.scene&&p.aiReview?.sourceRead&&p.aiReview?.ordinaryIndependent&&p.aiReview?.contentChecked;
 $('componentAutomation').textContent=aiReviewed?'AI方案审阅记录：'+(p.aiReview.notes||'已记录原图、内容和独立普通版核对；仍需查看实际预览。'):(p?.automation?.summary||'');
 $('componentLayoutHint').textContent=p?.scene?'本页使用AI原生方案。此处显示源页内容范围与实际普通版画面，不能拖动修改布局。请在实际预览核对原文、表格与照片；需要调整时让AI修改方案后重新导入。原生重建的装饰样式可能与源页有差异。':'这里是普通组件的布局草图，可拖动调整位置、通过右下角缩放。草图不代表实际成片；请查看两版实际预览。独立照片和标志可保留原素材，不能用整页截图代替普通版。';
 $('componentUndo').disabled=!componentHistory.length;
 $('videoActionHint').textContent=componentExportIssue()||'内容已核对，可以制作视频';
}
function renderComponentPages(){
 updateComponentReadiness();
 const p=componentCurrent();$('componentWork').hidden=!p;if(!p)return;
 renderComponentBoards();
 $('componentList').innerHTML=p.components.map((c,i)=>'<div class="component-config"><label class="check"><input type="checkbox" data-merge="'+i+'">组件 '+(i+1)+' · '+esc(c.name||'手动框选')+'</label>'+plainEditor(c,i)+'<button data-remove-component="'+i+'">删除</button></div>').join('');
}
function renderComponentBoards(){
 const p=componentCurrent();if(!p)return;
 const target=$('targetBoard'),plain=$('plainBoard');
 target.innerHTML='<img class="component-source" src="'+esc(p.source)+'" alt="原课件参考页">'+p.components.map((c,i)=>'<div class="component-region" style="'+rectStyle(c.target)+'"><span>'+(i+1)+'</span></div>').join('');
 const image=target.querySelector('img');image.onload=()=>{p.aspect=image.naturalWidth/image.naturalHeight;if(!p.scene)plain.style.aspectRatio=image.naturalWidth+'/'+image.naturalHeight;};
 if(p.scene){
  const actual=componentHasPreview(p)&&componentActualBefore.get(p.number);
  plain.style.aspectRatio=(p.scene.width||960)+'/'+(p.scene.height||540);
  plain.innerHTML=actual?'<img class="component-source" src="'+esc(actual)+'" alt="AI方案普通版实际画面">':'<div class="actual-before-placeholder">本页使用AI独立布局。<br>请查看两版实际预览，生成真实普通版画面。<br>这里不会用组件框图代替实际效果。</div>';
 }else plain.innerHTML=p.components.map((c,i)=>'<div class="plain-component" data-move-component="'+i+'" style="'+rectStyle(c.before)+'"><b>'+(i+1)+'</b>'+plainComponentContent(p,c)+'<span class="component-resize"></span></div>').join('');
 $('drawRegion').textContent=drawingRegion?'在原课件拖出一个矩形…':'＋ 在原课件画框';target.classList.toggle('drawing',drawingRegion);
}
function rectStyle(r){return 'left:'+r[0]*100+'%;top:'+r[1]*100+'%;width:'+r[2]*100+'%;height:'+r[3]*100+'%';}
$('componentPages').onclick=e=>{const b=e.target.closest('[data-component-page]');if(b){componentIndex=Number(b.dataset.componentPage);renderComponentPages();}};
$('componentPages').onchange=e=>{if(!e.target.matches('[data-include]'))return;const p=componentPages[Number(e.target.dataset.include)];if(e.target.checked&&componentPages.filter(p=>p.include).length>=6){e.target.checked=false;return notice('每条视频最多选择 6 页');}if(e.target.checked&&automationBlocked(p)){e.target.checked=false;return notice('第 '+p.number+' 页需要AI核对：'+automationIssues(p));}p.include=e.target.checked;componentPreviewSnapshots.clear();componentActualBefore.clear();componentPages.forEach(page=>page.confirmed=false);$('componentStill').innerHTML='';dirty=true;updateComponentReadiness();};
$('componentList').oninput=e=>{
 const el=e.target;if(!['text','cell'].includes(el.dataset.plainField))return;
 componentRemember();const p=componentCurrent(),c=p.components[Number(el.dataset.plainIndex)];let v=c.plain||(c.plain={kind:'text',text:c.text||''});if(el.dataset.part!==undefined)v=v.parts[Number(el.dataset.part)];
 if(el.dataset.plainField==='cell')v.rows[Number(el.dataset.row)][Number(el.dataset.col)]=el.value;else v.text=el.value;
 p.confirmed=false;componentPreviewSnapshots.delete(p.number);componentActualBefore.delete(p.number);if(p.scene){delete p.scene;notice('内容已修改，将按当前组件重新生成画面，请重新核对实际预览。');}dirty=true;$('componentStill').innerHTML='';updateComponentReadiness();renderComponentBoards();
};
$('componentList').onchange=e=>{
 const el=e.target;if(el.dataset.plainIndex===undefined)return;if(['text','cell'].includes(el.dataset.plainField))return;componentRemember();
 const c=componentCurrent().components[Number(el.dataset.plainIndex)];
 if(el.dataset.plainField==='kind'){
  c.plain=el.value==='table'?{kind:'table',rows:[['','']]}:el.value==='text'?{kind:'text',text:c.text||''}:{kind:'image',assetRole:el.value};c.text='';
 }else{
  let v=c.plain||(c.plain={kind:'text',text:c.text||''});
  if(el.dataset.part!==undefined)v=v.parts[Number(el.dataset.part)];
  if(el.dataset.plainField==='cell')v.rows[Number(el.dataset.row)][Number(el.dataset.col)]=el.value;
  else if(el.dataset.plainField==='rows')v.rows=el.value.split('\n').map(line=>line.split('\t'));
  else v[el.dataset.plainField]=el.value;
 }
 componentChanged();
};
$('componentList').onclick=e=>{const action=e.target.closest('[data-table-action]');if(action){componentRemember();const c=componentCurrent().components[Number(action.dataset.plainIndex)];let v=c.plain;if(action.dataset.part!==undefined)v=v.parts[Number(action.dataset.part)];const rows=v.rows,cols=Math.max(1,...rows.map(r=>r.length));if(action.dataset.tableAction==='add-row')rows.push(Array(cols).fill(''));if(action.dataset.tableAction==='add-col')rows.forEach(r=>{while(r.length<cols)r.push('');r.push('');});if(action.dataset.tableAction==='remove-row'&&rows.length>1)rows.pop();if(action.dataset.tableAction==='remove-col'&&cols>1)rows.forEach(r=>r.splice(cols-1,1));componentChanged();return;}const b=e.target.closest('[data-remove-component]');if(b){componentRemember();componentCurrent().components.splice(Number(b.dataset.removeComponent),1);componentChanged();}};
$('resetPlain').onclick=()=>{componentRemember();gridComponents(componentCurrent().components);componentChanged();};
$('componentUndo').onclick=()=>{if(!componentHistory.length)return;componentPages=JSON.parse(componentHistory.pop());componentIndex=Math.min(componentIndex,Math.max(0,componentPages.length-1));dirty=true;$('componentStill').innerHTML='';componentPages.forEach(p=>p.confirmed=false);componentPreviewSnapshots.clear();componentActualBefore.clear();renderComponentPages();};
$('componentsConfirmed').onchange=()=>{componentCurrent().confirmed=componentHasPreview(componentCurrent())&&$('componentsConfirmed').checked;dirty=true;renderComponentPages();};
$('componentMotion').onchange=()=>{componentPreviewSnapshots.clear();componentActualBefore.clear();componentPages.forEach(p=>p.confirmed=false);$('componentStill').innerHTML='';dirty=true;updateComponentReadiness();};
$('drawRegion').onclick=()=>{drawingRegion=!drawingRegion;renderComponentBoards();};
$('mergeRegions').onclick=()=>{const indexes=[...document.querySelectorAll('[data-merge]:checked')].map(e=>Number(e.dataset.merge));if(indexes.length<2)return notice('先勾选至少两个组件');if(indexes.some(i=>componentCurrent().components[i].plain||componentCurrent().components[i].text))return notice('这些组件已有普通版内容。请保留各组件，避免合并时丢失文字或表格。');componentRemember();const p=componentCurrent(),items=indexes.map(i=>p.components[i]);const x=Math.min(...items.map(c=>c.target[0])),y=Math.min(...items.map(c=>c.target[1])),r=Math.max(...items.map(c=>c.target[0]+c.target[2])),b=Math.max(...items.map(c=>c.target[1]+c.target[3]));p.components=p.components.filter((_,i)=>!indexes.includes(i));p.components.push({id:crypto.randomUUID(),name:'合并组件',target:[x,y,r-x,b-y],before:items[0].before,text:items.map(c=>c.text).filter(Boolean).join('\n').slice(0,2000)});componentChanged();};
$('targetBoard').onpointerdown=e=>{if(!drawingRegion||!componentCurrent())return;e.preventDefault();const board=$('targetBoard'),rect=board.getBoundingClientRect();const point=ev=>[Math.max(0,Math.min(1,(ev.clientX-rect.left)/rect.width)),Math.max(0,Math.min(1,(ev.clientY-rect.top)/rect.height))];const a=point(e);let b=a;const ghost=document.createElement('div');ghost.className='component-region';board.append(ghost);board.setPointerCapture(e.pointerId);board.onpointermove=ev=>{b=point(ev);ghost.style.cssText=rectStyle([Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])]);};board.onpointerup=()=>{board.onpointermove=null;board.onpointerup=null;const target=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1])];if(target[2]>=.01&&target[3]>=.01&&componentCurrent().components.length<40){componentRemember();componentCurrent().components.push({id:crypto.randomUUID(),name:'手动框选',text:'',target,before:[.05,.05,.4,.25]});}drawingRegion=false;componentChanged();};};
$('plainBoard').onpointerdown=e=>{const box=e.target.closest('[data-move-component]');if(!box)return;e.preventDefault();const board=$('plainBoard'),rect=board.getBoundingClientRect(),c=componentCurrent().components[Number(box.dataset.moveComponent)],a=[...c.before],x=e.clientX,y=e.clientY,resize=!!e.target.closest('.component-resize');let moved=false;box.setPointerCapture(e.pointerId);box.onpointermove=ev=>{if(!moved){componentRemember();moved=true;}const dx=(ev.clientX-x)/rect.width,dy=(ev.clientY-y)/rect.height;c.before=resize?[a[0],a[1],Math.max(.02,Math.min(1-a[0],a[2]+dx)),Math.max(.02,Math.min(1-a[1],a[3]+dy))]:[Math.max(0,Math.min(1-a[2],a[0]+dx)),Math.max(0,Math.min(1-a[3],a[1]+dy)),a[2],a[3]];box.style.cssText=rectStyle(c.before);};box.onpointerup=()=>{box.onpointermove=null;box.onpointerup=null;if(moved)componentChanged();};};
$('componentPreview').onclick=safe(async()=>{
 if(componentPreviewRunning||componentAnalysisRunning)return;
 let v=componentVideoData();
 if(!v.pages.length)throw Error('请先选择至少一页');
 const blocked=componentPages.find(p=>p.include&&automationBlocked(p));if(blocked)throw Error('第 '+blocked.number+' 页需要AI核对：'+automationIssues(blocked));
 if(v.pages.some(p=>p.components.length<2||p.components.some(c=>!plainContentReady(c.plain||(c.text?{kind:'text',text:c.text}:null)))))throw Error('请先补全各页的普通版内容，每页至少保留两个组件');
 componentPages.filter(p=>p.include).forEach(p=>{p.confirmed=false;componentPreviewSnapshots.delete(p.number);componentActualBefore.delete(p.number);});$('componentStill').innerHTML='';v=componentVideoData();updateComponentReadiness();
 const button=$('componentPreview'),signature=JSON.stringify(v),started=Date.now();let timer;
 componentPreviewRunning=true;button.disabled=true;button.textContent='正在制作实际预览…';button.setAttribute('aria-busy','true');updateComponentReadiness();
 const progress=()=>{$('componentNotice').textContent='正在制作 '+v.pages.length+' 页实际预览 · 已等待 '+Math.floor((Date.now()-started)/1000)+' 秒。首次制作可能需要几分钟，请保持页面打开，无需重复点击。';};progress();timer=setInterval(progress,1000);
 try{
  const result=await api('/api/components/preview',{project:current.id,video:v});
  if(signature!==JSON.stringify(componentVideoData())){$('componentNotice').textContent='预览期间内容已修改，请重新生成预览后核对。';return;}
  v.pages.forEach((p,i)=>{componentPreviewSnapshots.set(p.number,componentPreviewSnapshot(p));componentActualBefore.set(p.number,result.pages[i].before);});updateComponentReadiness();renderComponentBoards();
  $('componentStill').innerHTML=result.pages.map((p,i)=>'<section class="actual-preview"><h3>第 '+v.pages[i].number+' 页 · 实际画面</h3><div class="actual-comparison"><figure><figcaption>普通版 · 同内容基础排版</figcaption><img src="'+esc(p.before)+'" alt="普通版实际预览"></figure><figure><figcaption>重建成品 · 组件重新排版</figcaption><img src="'+esc(p.after)+'" alt="重建成品实际预览"></figure></div><details class="source-reference"><summary>原页参考 · 用于核对内容</summary><img src="'+esc(p.source||p.reference||v.pages[i].source)+'" alt="原课件参考，不是重建成品"></details><details open><summary>运动过程 · 完成后仍需播放成片</summary><img src="'+esc(p.motion)+'" alt="运动过程预览"></details></section>').join('');
  $('componentNotice').textContent='实际预览已完成。请对照原页检查内容，确认后勾选各页的核对选项，再点击“制作并预览视频”。';
 }catch(error){$('componentNotice').textContent='预览未完成：'+error.message+'。内容已保留，可修正后重试。';throw error;}
 finally{clearInterval(timer);componentPreviewRunning=false;button.disabled=false;button.textContent='查看两版实际预览';button.removeAttribute('aria-busy');updateComponentReadiness();}
});

function plainEditor(c,i){
 const v=c.plain||(c.text?{kind:'text',text:c.text}:null);
 const selected=v?(v.kind==='image'?v.assetRole:v.kind):'';
 const options=[['','请选择普通版内容类型'],['text','原文 · 白底黑字'],['table','表格 · 基础线框'],['photo','独立照片'],['logo','独立标志']];
 if(selected==='group')options.push(['group','已重建的文字 / 表格 / 素材组合']);
 let html='<select data-plain-index="'+i+'" data-plain-field="kind">'+options.map(([k,label])=>'<option value="'+k+'" '+(selected===k?'selected':'')+' '+(!k?'disabled':'')+'>'+label+'</option>').join('')+'</select>';
 function fields(part,n){
  const attrs=' data-plain-index="'+i+'"'+(n===undefined?'':' data-part="'+n+'"');
  if(part.kind==='text')return '<textarea'+attrs+' data-plain-field="text" rows="3" maxlength="4000" placeholder="完整原文，不沿用成品排版">'+esc(part.text||'')+'</textarea>';
  if(part.kind==='table'){
   const rows=part.rows||[['','']],cols=Math.max(1,...rows.map(r=>r.length));
   return '<p class="hint">直接填写每个单元格，保留原表的数字与单位。</p><div class="plain-table-scroll"><table class="plain-table-editor"><tbody>'+rows.map((row,r)=>'<tr>'+Array.from({length:cols},(_,col)=>'<td><input'+attrs+' data-plain-field="cell" data-row="'+r+'" data-col="'+col+'" aria-label="第 '+(r+1)+' 行，第 '+(col+1)+' 列" value="'+esc(row[col]??'')+'"></td>').join('')+'</tr>').join('')+'</tbody></table></div><div class="table-actions">'+[['add-row','＋ 行'],['add-col','＋ 列'],['remove-row','减少一行'],['remove-col','减少一列']].map(([action,label])=>'<button type="button"'+attrs+' data-table-action="'+action+'">'+label+'</button>').join('')+'</div>';
  }
  if(part.kind==='group')return part.parts.map((p,n)=>fields(p,n)).join('');
  return '<p class="hint">仅保留独立照片或标志。请确保成品框内没有整块文字、表格或装饰排版。</p>';
 }
 return html+(v?fields(v):'<p class="hint">尚未重做普通版，不能用成品图块代替。</p>');
}
function plainContentReady(v){
 if(!v)return false;
 if(v.kind==='text')return !!String(v.text||'').trim();
 if(v.kind==='table')return Array.isArray(v.rows)&&v.rows.length>0&&v.rows.every(row=>Array.isArray(row)&&row.some(cell=>String(cell??'').trim()));
 if(v.kind==='group')return Array.isArray(v.parts)&&v.parts.length>0&&v.parts.every(plainContentReady);
 return v.kind==='image'&&['photo','logo'].includes(v.assetRole);
}
function plainComponentContent(p,c,value){
 const v=value||c.plain||(c.text?{kind:'text',text:c.text}:null);
 if(!v)return '<div class="plain-missing">待填写原文或表格</div>';
 let result=v.title?'<div>'+esc(v.title)+'</div>':'';
 if(v.kind==='text')return result+'<div>'+esc(v.text)+'</div>';
 if(v.kind==='table')return result+'<table style="border-collapse:collapse;color:#222;background:white">'+v.rows.map(row=>'<tr>'+row.map(cell=>'<td style="border:1px solid #555">'+esc(cell)+'</td>').join('')+'</tr>').join('')+'</table>';
 if(v.kind==='group')return v.parts.map(part=>'<div style="position:absolute;'+rectStyle(part.box)+'">'+plainComponentContent(p,c,part)+'</div>').join('');
 const h=1000/(p.aspect||16/9),base=c.target,sub=v.crop||[0,0,1,1];
 const r=[base[0]+sub[0]*base[2],base[1]+sub[1]*base[3],sub[2]*base[2],sub[3]*base[3]];
 return result+'<svg class="plain-crop" viewBox="'+[r[0]*1000,r[1]*h,r[2]*1000,r[3]*h].join(' ')+'" preserveAspectRatio="xMidYMid meet" style="overflow:hidden"><image href="'+esc(p.source)+'" width="1000" height="'+h+'" preserveAspectRatio="none"/></svg>';
}
