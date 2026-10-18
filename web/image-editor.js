let imageEdit=null,editorSequence=0,editorPending=Promise.resolve(),editorValid=true;
const editorMessage=text=>$('editorStatus').textContent=text;
function editorSnapshot(){return JSON.stringify(imageEdit.doc.layers)}
function editorRemember(){imageEdit.history.push(editorSnapshot());if(imageEdit.history.length>30)imageEdit.history.shift()}
function editorSelected(){return imageEdit?.doc.layers.find(l=>l.id===imageEdit.selected)}
function editorDraw(){
 const doc=imageEdit.doc,canvas=$('editorCanvas');canvas.style.aspectRatio=doc.size.join('/');
 canvas.innerHTML='<img class="editor-background" draggable="false" alt="画布背景" src="'+esc(doc.background)+'">'+doc.layers.map(l=>'<div class="image-layer '+(l.textCount?'editable ':'')+(l.id===imageEdit.selected?'selected':'')+'" data-layer="'+l.id+'" style="left:'+l.x/doc.size[0]*100+'%;top:'+l.y/doc.size[1]*100+'%;width:'+l.width/doc.size[0]*100+'%;height:'+l.height/doc.size[1]*100+'%" '+(l.textCount?'tabindex="0" role="button" aria-label="编辑 '+esc(l.texts.join(' '))+'"':'')+'><img draggable="false" alt="" src="'+esc(l.image)+'">'+(l.textCount?'<span class="layer-resize" aria-hidden="true"></span>':'')+'</div>').join('');
 const selected=editorSelected();$('editorSize').value=selected?Math.round(selected.fontSize):'';$('editorSize').disabled=$('editorText').disabled=!selected;
 $('editorUndo').disabled=!imageEdit.history.length;
}
async function openImageEditor(url){
 if(activeJob)throw Error('请等待当前任务完成');
 const doc=await api('/api/editor/open',{project:current.id,image:url});
 imageEdit={project:current.id,image:url,doc,original:JSON.stringify(doc),history:[],selected:doc.layers.find(l=>l.textCount)?.id};
 editorValid=true;editorPending=Promise.resolve();$('editorSave').disabled=false;editorSequence++;editorDraw();editorMessage(doc.layers.some(l=>l.textCount)?'选中文字后即可调整；保存只修改这一张图。':'这张图没有模板文字层，课件原图可在源 PPT 中修改。');$('imageEditor').showModal();
}
async function editorRefreshLayer(layer){
 const sequence=++editorSequence;editorValid=false;$('editorSave').disabled=true;editorMessage('正在更新文字…');
 const promise=api('/api/editor/preview',{project:imageEdit.project,image:imageEdit.image,layer});editorPending=promise;
 try{const result=await promise;if(sequence!==editorSequence)return;Object.assign(layer,result);editorValid=true;editorDraw();editorMessage('修改尚未保存。');}
 catch(e){if(sequence===editorSequence)editorMessage(e.message);}
 finally{if(sequence===editorSequence)$('editorSave').disabled=!editorValid;}
}
function editTextOnCanvas(){
 const layer=editorSelected();if(!layer)return;
 const box=$('editorCanvas').querySelector('[data-layer="'+layer.id+'"]');if(box.querySelector('textarea'))return;
 const field=document.createElement('textarea');field.className='canvas-text-input';field.value=layer.texts.join('\n');field.setAttribute('aria-label','直接修改图内文字');field.style.fontSize=Math.max(16,Math.min(42,box.clientHeight/Math.max(1,layer.textCount)*.65))+'px';box.append(field);field.focus();field.select();
 editorMessage(layer.textCount===2?'两行分别为主题和奖项；可分别修改。Ctrl/⌘ + Enter 完成。':'直接输入文字，按 Enter 完成，Esc 取消。');
 let done=false;
 const finish=cancel=>{if(done)return;done=true;const value=field.value;field.remove();if(cancel)return;const texts=layer.textCount===1?[value.replace(/\n/g,'')]:value.split('\n');if(texts.length!==layer.textCount){editorMessage('请保留 '+layer.textCount+' 行，每行对应一段文字。');return;}if(JSON.stringify(texts)!==JSON.stringify(layer.texts)){editorRemember();layer.texts=texts;editorRefreshLayer(layer);}};
 field.onblur=()=>finish(false);field.onkeydown=e=>{e.stopPropagation();if(e.key==='Escape'){e.preventDefault();finish(true);}else if(e.key==='Enter'&&(layer.textCount===1||e.ctrlKey||e.metaKey)){e.preventDefault();finish(false);}};
}
$('editorCanvas').ondblclick=e=>{const box=e.target.closest('.editable');if(box){imageEdit.selected=box.dataset.layer;editTextOnCanvas()}};
$('editorCanvas').onpointerdown=e=>{
 if(e.target.closest('textarea'))return;const box=e.target.closest('.editable');if(!box)return;
 const layer=imageEdit.doc.layers.find(l=>l.id===box.dataset.layer);imageEdit.selected=layer.id;
 $('editorCanvas').querySelectorAll('.image-layer').forEach(el=>el.classList.toggle('selected',el===box));$('editorSize').disabled=$('editorText').disabled=false;$('editorSize').value=Math.round(layer.fontSize);
 const rect=$('editorCanvas').getBoundingClientRect(),factor=imageEdit.doc.size[0]/rect.width,start={x:e.clientX,y:e.clientY,lx:layer.x,ly:layer.y,w:layer.width,h:layer.height,font:layer.fontSize},resize=!!e.target.closest('.layer-resize');let moved=false;
 box.setPointerCapture(e.pointerId);
 box.onpointermove=ev=>{const dx=(ev.clientX-start.x)*factor,dy=(ev.clientY-start.y)*factor;if(!moved&&Math.abs(dx)+Math.abs(dy)<4)return;if(!moved){editorRemember();moved=true;}
 if(resize){const max=Math.min((imageEdit.doc.size[0]-layer.x)/start.w,(imageEdit.doc.size[1]-layer.y)/start.h,300/start.font);const scale=Math.min(max,Math.max(8/start.font,(start.w+dx)/start.w));layer.fontSize=start.font*scale;layer.width=Math.round(start.w*scale);layer.height=Math.round(start.h*scale);box.style.width=layer.width/imageEdit.doc.size[0]*100+'%';box.style.height=layer.height/imageEdit.doc.size[1]*100+'%';$('editorSize').value=Math.round(layer.fontSize);}
 else{layer.x=Math.round(Math.max(0,Math.min(imageEdit.doc.size[0]-layer.width,start.lx+dx)));layer.y=Math.round(Math.max(0,Math.min(imageEdit.doc.size[1]-layer.height,start.ly+dy)));box.style.left=layer.x/imageEdit.doc.size[0]*100+'%';box.style.top=layer.y/imageEdit.doc.size[1]*100+'%';}
 };
 const finish=()=>{box.onpointermove=null;box.onpointerup=null;box.onpointercancel=null;if(moved){editorMessage('修改尚未保存。');if(resize||!editorValid)editorRefreshLayer(layer);else editorDraw();}};box.onpointerup=finish;box.onpointercancel=finish;
};
$('editorCanvas').onkeydown=e=>{if(e.target.matches('textarea'))return;const l=editorSelected();if(!l)return;if(e.key==='Enter'){e.preventDefault();editTextOnCanvas();}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();editorRemember();const d=e.shiftKey?10:1;l.x=Math.max(0,Math.min(imageEdit.doc.size[0]-l.width,l.x+({'ArrowLeft':-d,'ArrowRight':d}[e.key]||0)));l.y=Math.max(0,Math.min(imageEdit.doc.size[1]-l.height,l.y+({'ArrowUp':-d,'ArrowDown':d}[e.key]||0)));editorDraw();$('editorCanvas').querySelector('[data-layer="'+l.id+'"]').focus();}};
$('editorText').onclick=editTextOnCanvas;
$('editorSize').onchange=()=>{const l=editorSelected();if(!l)return;editorRemember();l.fontSize=$('editorSize').valueAsNumber;editorRefreshLayer(l);};
$('editorUndo').onclick=()=>{if(!imageEdit.history.length)return;editorSequence++;imageEdit.doc.layers=JSON.parse(imageEdit.history.pop());editorValid=true;$('editorSave').disabled=false;editorDraw();editorMessage('已撤销。');};
$('editorReset').onclick=()=>{editorRemember();editorSequence++;imageEdit.doc=JSON.parse(imageEdit.original);editorValid=true;$('editorSave').disabled=false;editorDraw();editorMessage('已还原至打开时的版本。');};
function closeImageEditor(){if(imageEdit&&JSON.stringify(imageEdit.doc)!==imageEdit.original&&!confirm('还有修改未保存，确定放弃这次修改吗？'))return;editorSequence++;$('imageEditor').close();imageEdit=null;}
$('editorClose').onclick=closeImageEditor;$('imageEditor').oncancel=e=>{e.preventDefault();closeImageEditor();};
$('editorSave').onclick=async()=>{try{
 const field=$('editorCanvas').querySelector('textarea');if(field)field.blur();await editorPending.catch(()=>{});if(!editorValid)throw Error('请先修正文字或位置，再保存');
 const edit=imageEdit;$('editorSave').disabled=true;editorMessage('正在保存新版本…');await run('edit',{image:edit.image,layers:edit.doc.layers.filter(l=>l.textCount)});
 if($('notice').textContent){editorMessage($('notice').textContent);return;}$('imageEditor').close();imageEdit=null;notice('图内修改已保存为新版本，旧版仍保留。');
 }catch(e){editorMessage(e.message);}finally{$('editorSave').disabled=false;}};
document.addEventListener('click',safe(async e=>{const img=e.target.closest('[data-edit]');if(img)await openImageEditor(img.dataset.edit);}));
