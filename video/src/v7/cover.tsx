import data from '../../input.json';
const T=(s:string)=>(data.texts as any)?.[s] ?? s;
import {stage} from './shared';
import {makeScene2D, Node, Rect, Txt, Circle, Line} from '@motion-canvas/2d';
import {all,delay,waitFor,easeInOutCubic,easeOutBack} from '@motion-canvas/core';
const title=T('基于5E护理模式的QCC活动\n缩短门诊增强CT患者\n检查等候总时长');
const subtitle=T('门诊流程优化与患者体验提升实践');
function makeCover(view:any,y:number){
 const width=y<0?956:972;view.add(new Rect({width,height:width*941/1672,position:[0,y],fill:'#fff',shadowColor:'rgba(0,0,0,0.25)',shadowBlur:5,shadowOffset:[0,5]}));
 const root=new Rect({position:[0,y],scale:width/1672,width:1672,height:941,clip:true});view.add(root);
 const paper=new Rect({width:1672,height:941,fill:'#ffffff'});root.add(paper);
 const hero=new Rect({width:1672,height:675,position:[0,-133],fill:'#073b7d',opacity:0});root.add(hero);
 const art=new Node({opacity:0});root.add(art);
 for(let i=0;i<4;i++)art.add(new Line({points:[[-836,140+i*8],[-360,100+i*7],[350,150+i*4],[836,70+i*12]],stroke:i%2?'#35c2f3':'#88dcff',lineWidth:1.5,opacity:.28}));
 art.add(new Circle({size:380,position:[650,-70],stroke:'#6ec3ee',lineWidth:28,opacity:.18}));art.add(new Circle({size:260,position:[650,-70],stroke:'#b9e8ff',lineWidth:10,opacity:.12}));
 for(let i=0;i<3;i++)art.add(new Rect({size:[340,22],position:[-690+i*180,-345+i*11],rotation:12,fill:'#329cdd',opacity:.11}));
 const main=new Txt({text:title,fontFamily:'Toolbox',fontSize:60,lineHeight:'130%',fill:'#111111',position:[-730,-195],offset:[-1,0],textAlign:'left'});root.add(main);
 const sub=new Txt({text:subtitle,fontFamily:'Toolbox',fontSize:36,fill:'#111111',position:[-730,75],offset:[-1,0]});root.add(sub);
 const fields=[T('汇报人：XXX'),T('科室：XXX科'),T('活动时间：2026年X月'),T('类别：QCC成果汇报')];
 const infos:any[]=[],cards:any[]=[];
 for(let i=0;i<4;i++){
  const card=new Rect({position:[-570+i*380,345],width:350,height:100,radius:20,fill:'#ffffff',stroke:'#c9d9e8',lineWidth:1,shadowColor:'rgba(15,50,82,0.09)',shadowBlur:6,shadowOffset:[0,3],opacity:0});root.add(card);cards.push(card);
  const tx=new Txt({text:fields[i],fontFamily:'Toolbox',fontSize:31,fill:'#111111',position:[-730,180+i*60],offset:[-1,0]});root.add(tx);infos.push(tx);
 }
 return {root,hero,art,main,sub,infos,cards};
}
export default makeScene2D(function*(view){
 stage(view);
 makeCover(view,-290.5);const p=makeCover(view,387.5);
 yield* waitFor(.65);
 p.main.textAlign("center");
 yield* all(waitFor(1.4),
  p.main.position([0,-125],1.12,easeOutBack),p.main.offset([0,0],1.12,easeInOutCubic),p.main.fontSize(88,1.12,easeInOutCubic),p.main.fontWeight(700,1.12),delay(.30,p.main.fill('#ffffff',.14)),
  delay(.07,p.sub.position([0,155],1.10,easeOutBack)),delay(.07,p.sub.offset([0,0],1.10)),delay(.07,p.sub.fontSize(42,.48)),delay(.30,p.sub.fill('#f0dfa4',.14)),
  ...p.infos.flatMap((tx,i)=>[delay(.13+i*.07,tx.position([-570+i*380,345],.95,easeOutBack)),delay(.13+i*.07,tx.offset([0,0],.95)),delay(.12,tx.fontSize(i===2?28:30,.47)),delay(.27,tx.fill('#0756a1',.14))]),
  delay(.55,p.hero.opacity(1,.25)),delay(.85,p.art.opacity(1,.27)),...p.cards.map(card=>delay(.95,card.opacity(1,.30)))
 );
 yield* waitFor(1.45);
});
