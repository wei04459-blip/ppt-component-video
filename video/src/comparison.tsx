import {makeScene2D,Rect,Txt,Node,Line} from '@motion-canvas/2d';
import {all,delay,waitFor,easeInOutCubic,easeOutBack} from '@motion-canvas/core';
import data from '../input.json';
// Data drives both layouts; no duplicate before/after text to drift apart.
export default makeScene2D(function*(view){
 for(const page of data.pages){
  view.removeChildren();view.fill('#eeeeed');
  view.add(new Line({points:[[-540,-720],[540,720],[-540,720]],closed:true,fill:'#f6f6f5'}));
  view.add(new Txt({text:data.topLabel,position:[0,-635],fontFamily:'Toolbox',fontSize:68,fontWeight:700,fill:'#111'}));
  view.add(new Txt({text:data.bottomLabel,position:[0,52],fontFamily:'Toolbox',fontSize:68,fontWeight:700,fill:'#b50008'}));
  view.add(new Txt({text:'普通版为排版演示',position:[0,692],fontFamily:'Toolbox',fontSize:16,fill:'#888'}));
  function slide(y:number){
   const root=new Rect({position:[0,y],size:[960,540],fill:'#fff',clip:true,shadowColor:'#0002',shadowBlur:5,shadowOffset:[0,5]});view.add(root);
   const band=new Rect({position:[0,-211],size:[960,118],fill:data.color,opacity:0});root.add(band);
   const title=new Txt({text:page.title,position:[-444,-225],offset:[-1,0],width:885,fontFamily:'Toolbox',fontSize:34,fontWeight:700,fill:'#181818'});root.add(title);
   const sub=new Txt({text:page.subtitle,position:[-444,-169],offset:[-1,0],fontFamily:'Toolbox',fontSize:21,width:880,fill:'#444'});root.add(sub);
   const cards:any[]=[];
   page.items.forEach((item:any,i:number)=>{
    const group=new Node({position:[-225+(i%2)*450,-55+Math.floor(i/2)*138]});root.add(group);
    const box=new Rect({size:[420,120],fill:'#fff',stroke:'#d9d9d9',lineWidth:1,radius:0});group.add(box);
    const heading=new Txt({text:item.heading,position:[-190,-33],offset:[-1,0],width:380,fontFamily:'Toolbox',fontSize:23,fontWeight:700,fill:'#222'});group.add(heading);
    const body=new Txt({text:item.body,position:[-190,15],offset:[-1,0],width:380,fontFamily:'Toolbox',fontSize:21,lineHeight:28,textWrap:true,fill:'#444'});group.add(body);
    cards.push({group,box,heading,body});
   });return {root,band,title,sub,cards};
  }
  slide(-290);const p=slide(387);
  yield* waitFor(.65);
  const n=p.cards.length;
  yield* all(waitFor(1.4),p.band.opacity(1,.35),p.title.position([-430,-225],.6,easeInOutCubic),p.title.fill('#fff',.2),p.sub.fill('#d8e9ff',.2),p.sub.position([-430,-172],.6),...p.cards.map((c,i)=>delay(i*.07,(function*(){
   const target=page.layout==='columns'?[(-1+(i%3))*300,-30+Math.floor(i/3)*174]:[-225+(i%2)*450,-48+Math.floor(i/2)*140];
   if(page.layout==='reverse'){target[0]=-target[0];target[1]=-48+Math.floor((n-1-i)/2)*140;}
   const start=c.group.position();
   yield* all(c.group.position([start.x+(i%2?32:-32),start.y-18],.20,easeInOutCubic),c.group.scale(.9,.20));
   yield* all(c.group.position(target,.53,easeInOutCubic),c.group.scale(page.layout==='columns'?.67:.9,.53),c.box.fill('#edf5ff',.25),c.box.radius(14,.25),c.box.stroke('#c4d8ee',.25),c.heading.fill(data.color,.2));
   yield* c.group.scale(page.layout==='columns'?.67:1,.35,easeOutBack);
  })())));
  yield* waitFor(1.45);
 }
});
