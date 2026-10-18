import data from '../../input.json';
const T=(s:string)=>(data.texts as any)?.[s] ?? s;
import {Node,Rect,Txt,Line,Circle,Img,Gradient} from '@motion-canvas/2d';
import {all,delay,waitFor,easeInOutCubic,easeOutBack} from '@motion-canvas/core';
export const blue=data.color,light='#edf7ff',black='#111111';
export const xy=(x:number,y:number)=>[x-836,y-470.5] as [number,number];
export function stage(view:any){
 view.fill('#eeeeed');
 const gradient=(from:any,to:any,colors:string[])=>new Gradient({from,to,stops:colors.map((color,i)=>({offset:i/(colors.length-1),color}))});
 view.add(new Rect({size:[1080,1440],fill:gradient([-540,-720],[540,720],['#f4f4f3','#eaeaea','#f7f7f6'])}));
 const facets=[
  {points:[[-540,-720],[-240,-720],[540,590],[540,720],[350,720]],from:[-400,-500],to:[180,500],colors:['#ffffffaa','#ffffff00','#dfdfdf55']},
  {points:[[-540,-720],[-505,-720],[510,720],[300,720],[-540,-445]],from:[-460,-500],to:[-190,-260],colors:['#ffffffff','#f5f5f520','#e7e7e735']},
  {points:[[-50,-720],[290,-720],[540,-335],[540,590]],from:[80,-660],to:[500,-60],colors:['#ffffff90','#ffffff00','#e4e4e440']},
  {points:[[-540,80],[-175,330],[15,720],[-540,720]],from:[-500,180],to:[-10,720],colors:['#ececec20','#ffffff70','#ffffff10']}
 ];
 for(const f of facets)view.add(new Line({points:f.points as any,closed:true,fill:gradient(f.from,f.to,f.colors)}));
 view.add(new Txt({text:T('自己瞎做的'),position:[0,-635],fontSize:82,fontFamily:'ToolboxLabel',fontWeight:700,fill:'#050505'}));
 view.add(new Txt({text:T('护士长想要的'),position:[0,52],fontSize:78,fontFamily:'ToolboxLabel',fontWeight:700,fill:'#b50008'}));
 view.add(new Txt({text:T('普通版为排版演示'),position:[0,692],fontSize:16,fontFamily:'Toolbox',fill:'#999999'}));
}
export function page(view:any,y:number,title:string,subtitle:string){
 const width=y<0?956:972;view.add(new Rect({width,height:width*941/1672,position:[0,y],fill:'#fff',shadowColor:'rgba(0,0,0,0.25)',shadowBlur:5,shadowOffset:[0,5]}));
 const root=new Rect({width:1672,height:941,position:[0,y],scale:width/1672,fill:'#fff',clip:true});view.add(root);const jobs:any[]=[],nodes:any[]=[];
 const add=(id:string,n:any,target:any={})=>{root.add(n);nodes.push({id,key:n.key,text:n instanceof Txt?n.text():null});for(const [k,v]of Object.entries(target)){
  const isHeading=id==='page_title'||id.endsWith('_heading');const isDecoration=k==='opacity';
  let start=id==='page_title'?0:id==='page_summary'?.06:.08;
  if(isDecoration)start=id==='header_background'?.12:.20;
  if(k==='fill'&&n instanceof Txt)start=isHeading?.24:.22;
  const duration=isDecoration?.24:k==='fill'&&n instanceof Txt?.14:id==='page_title'?.45:.48;
  const f:any=()=>n[k](v,duration,easeInOutCubic);f.start=start;f.id=id;f.property=k;f.node=n;jobs.push(f);
 }return n};
 const text=(id:string,s:string,x:number,y:number,w:number,size:number,target:any={})=>add(id,new Txt({text:s,position:xy(x,y),offset:[-1,-1],width:w,fontSize:size,fontFamily:'Toolbox',textWrap:true,lineHeight:'130%',fill:black,textAlign:'left'}),target);
 const rect=(id:string,x:number,y:number,w:number,h:number,props:any={},target:any={})=>add(id,new Rect({position:xy(x,y),offset:[-1,-1],width:w,height:h,fill:'#fff',stroke:'#888888',lineWidth:1,...props}),target);
 rect('header_background',0,0,1672,88,{fill:blue,stroke:null,opacity:0},{opacity:1});
 rect('blue_title_marker',30,18,6,51,{fill:'#ffffff',stroke:null,opacity:0},{opacity:1});
 text('page_title',title,30,20,1100,42,{position:xy(58,12),fontSize:48,fill:'#ffffff',fontWeight:700});
 text('page_summary',subtitle,30,82,1600,23,{position:xy(50,113),fontSize:25,fill:'#163f70'});
 return {root,add,text,rect,jobs,nodes};
}
export function panel(p:any,id:string,label:string,b:number[],a:number[],size=25){
 p.rect(id+'_card',b[0],b[1],b[2],b[3],{}, {position:xy(a[0],a[1]),width:a[2],height:a[3],radius:10,fill:'#ffffff',stroke:'#c9d5df',lineWidth:1,shadowColor:'rgba(17,45,75,0.10)',shadowBlur:6,shadowOffset:[0,3]});
 p.rect(id+'_label_band',a[0],a[1],a[2],48,{fill:blue,stroke:null,opacity:0,radius:10},{opacity:1});
 p.text(id+'_heading',label,b[0]+10,b[1]+8,b[2]-20,size,{position:xy(a[0]+18,a[1]+8),fill:'#fff',fontSize:27,fontWeight:700});
}
export function regroup(p:any,start:number,delta:number[],scale=1,index=0){
 const children=p.root.children().slice(start);const group=new Node({position:delta,scale});p.root.add(group);for(const child of children)group.add(child);
 const f:any=function*(){const lane=index%2?45:-45;yield* all(group.position([delta[0]+lane,delta[1]-24],.20,easeInOutCubic),group.scale(scale*.93,.20));yield* all(group.position([lane,0],.53,easeInOutCubic),group.scale(.86,.53,easeInOutCubic));yield* all(group.position([0,0],.35,easeOutBack),group.scale(1,.35,easeOutBack));};f.start=index*.07;p.jobs.push(f);return group;
}
export function* animate(p:any,hold=1.1){console.log('MC_OBJECT_MAP',JSON.stringify(p.nodes));yield* waitFor(.65);yield* all(waitFor(1.4),...p.jobs.map((f:any)=>delay(f.start??.08,f())));yield* waitFor(hold);}
