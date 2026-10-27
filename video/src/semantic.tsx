import data from '../input.json';
import {makeScene2D,Node,Rect,Txt,Img,Line} from '@motion-canvas/2d';
import {all,delay,waitFor,easeInOutCubic,easeOutBack,createSignal} from '@motion-canvas/core';
import {stage} from './v7/shared';

function independentGroup(root:any,g:any,spec:any,jobs:any[],animate:boolean,staggerStep:number){
 const visible=(which:string)=>g.nodes.map((n:any)=>n.states[which]).filter((s:any)=>s.opacity>0);
 const bounds=(states:any[])=>{const x=Math.min(...states.map(s=>s.x)),y=Math.min(...states.map(s=>s.y));const r=Math.max(...states.map(s=>s.x+s.w)),b=Math.max(...states.map(s=>s.y+s.h));return {x,y,w:r-x,h:b-y,cx:(x+r)/2,cy:(y+b)/2};};
 const av=visible('before'),bv=visible('after');if(!av.length&&!bv.length)return;
 const a=bounds(av.length?av:bv),b=bounds(bv.length?bv:av);const progress=createSignal(0),gather=createSignal(0),scale=createSignal(1),offset=createSignal([0,0]);
 const mix=(x:number,y:number,q:number)=>x+(y-x)*q;
 const parent=new Node({scale:()=>scale(),position:()=>{
  const q=progress(),s=scale(),of:any=offset();let left=Infinity,top=Infinity,right=-Infinity,bottom=-Infinity;
  for(const n of g.nodes){if(n.states.before.opacity<=0&&q<.999)continue;const aa=n.states.before,bb=n.states.after;
   const x=mix(aa.x-a.cx,bb.x-b.cx,gather()),y=mix(aa.y-a.cy,bb.y-b.cy,gather());left=Math.min(left,x*s);top=Math.min(top,y*s);right=Math.max(right,(x+mix(aa.w,bb.w,gather()))*s);bottom=Math.max(bottom,(y+mix(aa.h,bb.h,gather()))*s);
  }
  const cx=mix(a.cx,b.cx,q),cy=mix(a.cy,b.cy,q);const margin=8;
  const dx=Math.max(margin-cx-left,Math.min(spec.width-margin-cx-right,of[0]));const dy=Math.max(margin-cy-top,Math.min(spec.height-margin-cy-bottom,of[1]));
  // Endpoints are the authored page coordinates, not a separately composed static page.
  const settled=q===0&&s===1&&of[0]===0&&of[1]===0||q===1&&s===1&&of[0]===0&&of[1]===0;
  return [-spec.width/2+cx+(settled?0:dx),-spec.height/2+cy+(settled?0:dy)];
 }});root.add(parent);
 const locals:any[]=[];
 for(const n of g.nodes){const aa=n.states.before,bb=n.states.after;const common:any={position:()=>[mix(aa.x-a.cx,bb.x-b.cx,gather()),mix(aa.y-a.cy,bb.y-b.cy,gather())],offset:[-1,-1],opacity:aa.opacity};let child:any;
  if(n.kind==='text')child=new Txt({...common,text:n.text,fontFamily:'Toolbox',fontSize:()=>mix(aa.fontSize,bb.fontSize,gather()),fontWeight:aa.fontWeight,fill:aa.fill,textWrap:false});
  else if(n.kind==='rect')child=new Rect({...common,width:()=>mix(aa.w,bb.w,gather()),height:()=>mix(aa.h,bb.h,gather()),fill:aa.fill,stroke:aa.stroke??null,lineWidth:aa.lineWidth,radius:aa.radius});
  else if(n.kind==='image')child=new Img({...common,src:'/'+n.src,width:()=>mix(aa.w,bb.w,gather()),height:()=>mix(aa.h,bb.h,gather()),smoothing:true});
  else if(n.kind==='line')child=new Line({...common,points:aa.points,stroke:aa.stroke??'#888888',fill:n.closed?aa.fill:null,closed:n.closed??false,lineWidth:aa.lineWidth});
  if(!child)throw Error('Invalid independent semantic node');parent.add(child);locals.push({n,child,aa,bb});
 }
 if(!animate)return;
 const index=Math.max(0,g.index??0),start=.65+index*staggerStep;const lane=index%2?26:-26,up=index%2?-22:18;
 const margin=Math.min(b.x,b.y,spec.width-b.x-b.w,spec.height-b.y-b.h);const settle=margin>=Math.max(12,Math.max(b.w,b.h)*.025)?easeOutBack:easeInOutCubic;
 jobs.push(function*(){yield* waitFor(start);yield* all(offset([lane,-14],.20,easeInOutCubic),scale(.93,.20,easeInOutCubic));yield* all(progress(1,.53,easeInOutCubic),gather(1,.24,easeInOutCubic),offset([lane,up],.53,easeInOutCubic),scale(.86,.53,easeInOutCubic));yield* all(offset([0,0],.35,settle),scale(1,.35,settle));});
 for(const {n,child,aa,bb} of locals){
  jobs.push(function*(){yield* waitFor(start+.44);const tasks:any[]=[];
   if(n.kind==='text'||n.kind==='rect'){if(bb.fill!==aa.fill)tasks.push(child.fill(bb.fill,.14,easeInOutCubic));}
   if(n.kind==='rect'||n.kind==='line'){if(bb.stroke!==aa.stroke)tasks.push(child.stroke(bb.stroke??null,.14,easeInOutCubic));if(bb.lineWidth!==aa.lineWidth)tasks.push(child.lineWidth(bb.lineWidth,.14,easeInOutCubic));}
   if(n.kind==='rect'&&bb.radius!==aa.radius)tasks.push(child.radius(bb.radius,.24,easeInOutCubic));
   if(n.kind==='text'&&bb.fontWeight!==aa.fontWeight)tasks.push(child.fontWeight(bb.fontWeight,.14,easeInOutCubic));
   if(bb.opacity!==aa.opacity)tasks.push(child.opacity(bb.opacity,.24,easeInOutCubic));
   if(n.kind==='line')child.points(bb.points);
   yield* all(...tasks);
  });
 }
}

export default makeScene2D(function*(view){
 const cfg:any=data;
 for(let pi=0;pi<cfg.pages.length;pi++){
  view.removeChildren();stage(view);const spec=cfg.pages[pi];const jobs:any[]=[];const maxIndex=Math.max(0,...spec.groups.map((g:any)=>g.index??0));const staggerStep=Math.min(.07,.42/Math.max(1,maxIndex));
  const page=(cy:number,animate:boolean)=>{
   const pageScale=Math.min((cy<0?956:972)/spec.width,(cy<0?538:547)/spec.height);const width=spec.width*pageScale;const height=spec.height*pageScale;
   view.add(new Rect({width,height,position:[0,cy],fill:'#ffffff',shadowColor:'rgba(0,0,0,.23)',shadowBlur:6,shadowOffset:[0,5]}));
   const root=new Rect({width:spec.width,height:spec.height,position:[0,cy],scale:pageScale,clip:true,fill:'#ffffff'});view.add(root);
   for(const g of spec.groups){
    if(g.nodeBefore){independentGroup(root,g,spec,jobs,animate,staggerStep);continue;}
    const a=g.before,b=g.after;const base=[-spec.width/2,-spec.height/2];
    const parent=new Node({position:[base[0]+a[0],base[1]+a[1]],scale:a[2]});root.add(parent);
    for(let ni=0;ni<g.nodes.length;ni++){
     const n=g.nodes[ni];let child:any;
     const common:any={position:[n.x,n.y],offset:[-1,-1],opacity:n.opacity??1};
     if(n.kind==='text')child=new Txt({...common,text:n.text,fontFamily:'Toolbox',fontSize:n.fontSize,fontWeight:n.fontWeight??400,fill:n.fill??'#222222',textWrap:false});
     else if(n.kind==='rect')child=new Rect({...common,width:n.w,height:n.h,fill:n.fill??'#ffffff',stroke:n.stroke??null,lineWidth:n.lineWidth??0,radius:n.radius??0});
     else if(n.kind==='image')child=new Img({...common,src:'/'+n.src,width:n.w,height:n.h,smoothing:true});
     else if(n.kind==='line')child=new Line({...common,points:n.points,fill:n.closed?n.fill:null,closed:n.closed??false,stroke:n.stroke??'#888888',lineWidth:n.lineWidth??1});
     if(!child)throw new Error('Unknown semantic node '+n.kind);parent.add(child);
     if(animate){
      const tween:any[]=[],start=.65+(g.index??0)*staggerStep;
      if(n.afterFill&&n.afterFill!==n.fill)tween.push(()=>child.fill(n.afterFill,.14,easeInOutCubic));
      if(n.afterStroke&&n.afterStroke!==n.stroke)tween.push(()=>child.stroke(n.afterStroke,.24,easeInOutCubic));
      if(n.afterRadius!==undefined)tween.push(()=>child.radius(n.afterRadius,.24,easeInOutCubic));
      if(n.afterOpacity!==undefined)tween.push(()=>child.opacity(n.afterOpacity,.24,easeInOutCubic));
      if(tween.length)jobs.push(()=>delay(Math.max(.65,start)+.22,all(...tween.map(f=>f()))));
     }
    }
    if(animate&&g.index!==-1){
     const index=g.index??0;const lane=index%2?26:-26;const up=index%2?-22:18;
     const fit=(x:number,y:number,scale:number)=>{const mx=Math.min(12,Math.max(0,(spec.width-g.size[0]*scale)/2));const my=Math.min(12,Math.max(0,(spec.height-g.size[1]*scale)/2));return [base[0]+Math.max(mx,Math.min(spec.width-g.size[0]*scale-mx,x)),base[1]+Math.max(my,Math.min(spec.height-g.size[1]*scale-my,y))] as [number,number]};
     const target=[base[0]+b[0],base[1]+b[1]] as [number,number];
     const raised=fit(a[0]+lane,a[1]-14,a[2]*.93);
     const travel=fit(b[0]+lane,b[1]+up,b[2]*.80);
     const margin=Math.min(b[0],b[1],spec.width-b[0]-g.size[0]*b[2],spec.height-b[1]-g.size[1]*b[2]);
     const settle=margin>=Math.max(12,Math.max(...g.size)*b[2]*.025)?easeOutBack:easeInOutCubic;
     jobs.push(function*(){
      yield* waitFor(.65+index*staggerStep);
      yield* all(parent.position(raised,.20,easeInOutCubic),parent.scale(a[2]*.93,.20,easeInOutCubic));
      // Whole semantic group travels on a separate vertical lane. Child geometry is constant.
      yield* all(parent.position(travel,.53,easeInOutCubic),parent.scale(b[2]*.80,.53,easeInOutCubic));
      yield* all(parent.position(target,.35,settle),parent.scale(b[2],.35,settle));
     });
    }
   }
  };
  page(-290.5,false);page(387.5,true);
  console.log('MC_SEMANTIC_PAGE',JSON.stringify({page:pi+1,groups:spec.groups.length,nodes:spec.groups.reduce((n:any,g:any)=>n+g.nodes.length,0)}));
  yield* all(waitFor(cfg.secondsPerPage??4),...jobs.map(f=>f()));
 }
});
