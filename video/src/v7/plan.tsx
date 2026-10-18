import data from '../../input.json';
const T=(s:string)=>(data.texts as any)?.[s] ?? s;
import {makeScene2D,Node,Rect,Txt} from '@motion-canvas/2d';
import {page,stage,panel,animate,xy,blue,regroup} from './shared';
import {delay} from '@motion-canvas/core';
const subtitle=T('以PDCA循环为主线，科学制定活动计划，明确时间节点与责任分工，确保项目有序推进');
const steps=[T('主题选定'),T('活动计划拟定'),T('现状把握'),T('目标设定'),T('原因分析'),T('对策拟定'),T('对策实施与检讨'),T('效果确认'),T('标准化'),T('检讨与改进')];
const phases=[T('P 计划'),T('P 计划'),T('P 计划'),T('P 计划'),T('P 计划'),T('P 计划'),T('D 实施'),T('C 确认'),T('A 处置'),T('A 处置')];
const tools=[T('头脑风暴、评价法'),T('甘特图'),T('查检表、流程图'),T('柱状图'),T('鱼骨图、柏拉图'),T('头脑风暴、评价法'),T('PDCA、流程图、查检表'),T('柱状图、雷达图'),T('流程图、标准书'),T('头脑风暴')];
const defaultRanges=[[354,399],[399,473],[481,620],[525,651],[560,684],[606,773],[677,1005],[925,1075],[1028,1148],[1085,1185]];
const ranges=(data.scheduleRanges?.length===10?data.scheduleRanges.map((r:number[])=>r.map(v=>340+v/24*861)):defaultRanges);
function make(view:any,y:number){
 const p=page(view,y,T('活动计划拟定'),subtitle);
 const group=new Node({});p.root.add(group);p.jobs.push(()=>group.position([4,32],.48));
 const x=[30,140,365,1165,1300,1400,1640];
 const tx=(id:string,s:string,xx:number,yy:number,w:number,size:number,head=false)=>{const node=new Txt({text:s,position:xy(xx,yy),offset:[-1,-1],width:w,fontSize:size,fontFamily:'Toolbox',textWrap:true,fill:'#111',lineHeight:T('115%')});group.add(node);p.nodes.push({id,key:node.key,text:s});p.jobs.push(()=>delay(.16,node.fill(head?'#fff':'#10385e',.14)));return node};
 const cell=(id:string,xx:number,yy:number,w:number,h:number,header=false,row=0)=>{const node=new Rect({position:xy(xx,yy),offset:[-1,-1],width:w,height:h,fill:header?'#eeeeee':'#ffffff',stroke:'#888',lineWidth:1});group.add(node);p.jobs.push(()=>node.fill(header?blue:row%2?'#f0f8ff':'#ffffff',.48),()=>node.stroke('#c9e0ef',.48));return node};
 for(let j=0;j<6;j++){cell('header'+j,x[j],150,x[j+1]-x[j],76,true);if(j!==2)tx('header_text'+j,[T('活动阶段'),T('步骤'),'',T('负责人'),T('地点'),T('应用工具')][j],x[j]+5,176,x[j+1]-x[j]-10,22,true);}
 tx('year',T('2026年'),715,155,220,22,true);
 for(let m=0;m<6;m++)tx('month'+m,`${(m+(data.startMonth??3)-1)%12+1}月`,400+m*800/6,181,75,21,true);
 for(let k=0;k<24;k++){cell('week'+k,365+k*800/24,206,800/24,22);tx('week_label'+k,`${k%4+1}周`,365+k*800/24+2,206,32,14);}
 for(let i=0;i<10;i++){
  const yy=228+i*37;
  for(let j=0;j<6;j++)cell(`r${i}c${j}`,x[j],yy,x[j+1]-x[j],37,false,i);
  tx('phase'+i,phases[i],35,yy+7,100,20);tx('step'+i,steps[i],145,yy+7,210,20);tx('owner'+i,T('XXX'),1172,yy+7,115,20);tx('site'+i,T('CT室'),1308,yy+7,86,20);tx('tool'+i,tools[i],1405,yy+7,230,20);
  for(let k=0;k<24;k++){const line=new Rect({position:xy(365+k*800/24,yy),offset:[-1,-1],width:1,height:37,fill:'#cccccc'});group.add(line);}
  const [a,b]=ranges[i];const bar=new Rect({position:xy(365+(a-340)/861*800,yy+13),offset:[-1,-1],width:(b-a)/861*800,height:10,fill:'#4472c4'});group.add(bar);p.jobs.push(()=>bar.fill(i<6?'#168ff4':i===6?'#fa6870':i===7?'#43b965':'#ffa000',.48),()=>bar.radius(5,.48));
 }
 regroup(p,4,[-330,85],.58,0);
 const planStart=p.root.children().length;
 panel(p,'plan',T('计划说明'),[30,645,630,270],[34,676,520,240]);
 p.text('plan_contents',T('活动时间：2026年03月01日—2026年08月31日（共6个月）\n活动方式：运用PDCA循环，结合QCC工具，分阶段实施\n活动目标：缩短门诊增强CT患者检查等候总时长，提升检查效率与患者就医体验'),42,695,600,22,{position:xy(50,732),width:485,fontSize:22,fill:'#10385e'});
 regroup(p,planStart,[879,-454],.85,1);
 const stageStart=p.root.children().length;
 panel(p,'stages',T('阶段目标'),[675,645,550,270],[566,676,666,240]);
 p.text('phase_targets',T('P 计划：明确主题、分析现状、设定目标、找出要因、拟定对策\nD 实施：落实对策、跟踪执行、持续改进\nC 确认：数据收集、效果评价、目标达成\nA 处置：形成标准、巩固成果、检讨改进'),688,695,525,22,{position:xy(582,732),width:632,fontSize:22,fill:'#10385e'});
 regroup(p,stageStart,[331,-209],.85,2);
 const guaranteeStart=p.root.children().length;
 panel(p,'guarantees',T('保障措施'),[1260,645,380,270],[1244,676,400,240]);
 p.text('support_contents',T('组织保障：科室支持、多部门协作\n制度保障：完善流程、明确职责\n资源保障：人力、设备、信息系统支持\n质量保障：定期督查、持续改进'),1272,695,355,22,{position:xy(1260,732),width:368,fontSize:22,fill:'#10385e'});
 regroup(p,guaranteeStart,[-166,36],.85,3);
 return p;
}
export default makeScene2D(function*(view){stage(view);make(view,-290.5);const p=make(view,387.5);yield* animate(p,1.45);});
