import data from '../../input.json';
const T=(s:string)=>(data.texts as any)?.[s] ?? s;
import {makeScene2D,Node,Rect,Txt,Circle,Img} from '@motion-canvas/2d';
import {page,stage,panel,animate,xy,blue,regroup} from './shared';
import {delay,easeInOutCubic} from '@motion-canvas/core';
const summary=T('通过对策实施，门诊增强CT患者检查等候总时长显著缩短，目标达成，患者满意度、检查效率及医护工作效能均得到提升');
const rows=[[T('指标'),'改善前','改善后',T('趋势')],[T('预约检查成功率'),T('73.62%'),T('93.15%'),T('↑')],[T('按约检查率'),T('68.35%'),T('91.03%'),T('↑')],[T('检查前准备合格率'),T('72.41%'),T('95.62%'),T('↑')],[T('患者对流程满意度'),T('82.11%'),T('96.45%'),T('↑')],[T('医护人员满意度'),T('78.68%'),T('93.21%'),T('↑')]];
function make(view:any,y:number){
 const p=page(view,y,T('效果确认'),summary);
 let moduleStart=p.root.children().length;
 panel(p,'main',T('1. 主要指标改善情况'),[30,145,515,420],[34,185,542,380]);
 p.text('main_description',T('门诊增强CT患者平均检查等候总时长（min/例）'),40,195,500,22,{position:xy(52,241),width:506,fontSize:20,fill:'#10385e'});
 for(let tick=0;tick<=100;tick+=20){p.text('axis_'+tick,''+tick,40,475-tick*2.15,40,18,{position:xy(54,502-tick*2.05),fontSize:17,fill:'#4a6d86'});p.rect('grid_'+tick,83,482-tick*2.15,420,1,{fill:'#bbbbbb',stroke:null},{position:xy(90,508-tick*2.05),fill:'#d6e6f1'});}
 for(let i=0;i<3;i++){
  const value=(data.metrics ?? [84,50,35.6])[i],label=['改善前',T('目标值'),'改善后'][i];
  p.rect('bar_'+i,113+i*133,482-value*2.15,75,value*2.15,{fill:'#4472c4',stroke:null},{position:xy(120+i*140,508-value*2.05),width:84,height:value*2.05,fill:['#095fc2','#349dee','#7bbfea'][i],radius:5});
  p.text('value_'+i,value.toFixed(1),113+i*133,448-value*2.15,90,23,{position:xy(120+i*140,475-value*2.05),fontSize:25,fontWeight:700,fill:'#10385e'});
  p.text('axis_label_'+i,label,108+i*133,492,115,21,{position:xy(113+i*140,514),fontSize:20,fill:'#10385e'});
 }
 p.text('improvement_label',T('下降'),40,533,60,23,{position:xy(54,543),fontSize:20,fill:'#10385e'});
 p.text('improvement_percent',T('57.6%'),88,533,100,23,{position:xy(96,543),fontSize:20,fill:'#ba1b24',fontWeight:700});
 p.text('improvement_other',T('；低于目标28.8%'),160,533,340,23,{position:xy(170,543),fontSize:20,fill:'#10385e'});
 regroup(p,moduleStart,[0,362],.90,0);moduleStart=p.root.children().length;
 panel(p,'secondary',T('2. 次要指标对比'),[570,145,535,390],[588,185,525,380]);
 const table=new Node({});p.root.add(table);p.jobs.push(()=>table.position([18,50],.48));const widths=[235,115,115,70];
 for(let r=0;r<rows.length;r++){
  let xx=570;
  for(let j=0;j<4;j++){
   const cell=new Rect({position:xy(xx,195+r*48),offset:[-1,-1],width:widths[j],height:48,fill:r===0?'#eee':'#fff',stroke:'#888',lineWidth:1});table.add(cell);p.jobs.push(()=>cell.fill(r===0?blue:r%2?'#f2f9ff':'#fff',.48),()=>cell.stroke('#c9e0ef',.48));
   const text=new Txt({text:rows[r][j],position:xy(xx+6,204+r*48),offset:[-1,-1],width:widths[j]-10,fontSize:21,textWrap:true,fontFamily:'Toolbox',fill:'#111',lineHeight:T('110%')});table.add(text);p.nodes.push({id:`metric_${r}_${j}`,key:text.key,text:rows[r][j]});p.jobs.push(()=>delay(.16,text.fill(r===0?'#fff':j===2?'#0565c7':'#173c5c',.14)));xx+=widths[j];
  }
 }
 regroup(p,moduleStart,[0,362],.90,1);moduleStart=p.root.children().length;
 panel(p,'goal',T('3. 目标达成情况'),[1150,145,490,390],[1125,185,515,380]);
 const circle=new Circle({size:230,position:xy(1250,365),stroke:'#54b6ef',lineWidth:12,fill:'#f3fbff',opacity:0});p.root.add(circle);p.jobs.push(()=>circle.opacity(1,.48));
 const goalText=(id:string,s:string,x:number,y:number,w:number,size:number,target:any)=>{const node=p.text(id,s,x,y,w,size,target);const keep=p.jobs.filter((f:any)=>f.id!==id);p.jobs.splice(0,p.jobs.length,...keep);const delayed=id==='goal_rate';for(const [k,v] of Object.entries(target))p.jobs.push(()=>delayed?delay(.24,node[k](v,k==='fill'?.14:.33,easeInOutCubic)):node[k](v,k==='fill'?.14:.22,easeInOutCubic));return node;};
 const rateLabel=p.text('goal_rate_label',T('目标达成率'),1160,195,220,23,{position:xy(1155,299),fontSize:27,fill:blue,fontWeight:700});
 const kept=p.jobs.filter((f:any)=>f.id!=='goal_rate_label'&&!(f.id==='goal_label_band'&&f.property==='opacity')&&!(f.id==='goal_heading'&&['fill','position','fontSize','fontWeight'].includes(f.property)));p.jobs.splice(0,p.jobs.length,...kept);
 const late=(node:any,k:string,v:any,start:number,duration:number)=>{const f:any=()=>node[k](v,duration,easeInOutCubic);f.start=start;p.jobs.push(f);};
 late(rateLabel,'position',xy(1155,299),.65,.20);late(rateLabel,'fontSize',27,.65,.20);late(rateLabel,'fill',blue,.65,.14);late(rateLabel,'fontWeight',700,.65,.20);
 const goalBand=p.root.children().find((n:any)=>n.key===p.nodes.find((v:any)=>v.id==='goal_label_band').key);
 const goalHeading=p.root.children().find((n:any)=>n.key===p.nodes.find((v:any)=>v.id==='goal_heading').key);
 late(goalBand,'opacity',1,.75,.10);late(goalHeading,'position',xy(1143,193),.75,.10);late(goalHeading,'fontSize',27,.75,.10);late(goalHeading,'fontWeight',700,.75,.10);late(goalHeading,'fill','#ffffff',.83,.02);
 goalText('goal_rate',T('122.0%'),1322,195,280,23,{position:xy(1145,338),fontSize:56,fill:'#be1d25',fontWeight:700});
 goalText('goal_values',T('目标值：≤50.0 min/例\n改善后：35.6 min/例'),1160,244,460,23,{position:xy(1140,499),width:235,fontSize:19,fill:'#10385e'});
 goalText('goal_verdict',T('目标达成判定：达到既定目标\n平均等候总时长≤50.0 min/例'),1160,309,460,23,{position:xy(1377,245),width:240,fontSize:19,fill:'#10385e'});
 goalText('goal_improvement',T('改善幅度57.6%：较改善前下降'),1160,387,460,23,{position:xy(1377,375),width:240,fontSize:20,fill:'#bd242a'});
 goalText('goal_extension',T('持续改进空间：可进一步推广至其他检查项目'),1160,436,460,23,{position:xy(1377,464),width:240,fontSize:19,fill:'#10385e'});
 regroup(p,moduleStart,[0,362],.90,2);moduleStart=p.root.children().length;
 panel(p,'photos',T('4. 改善前后对比'),[30,582,545,334],[34,582,660,334]);
 const captions=[T('患者排队时间长、候诊秩序混乱\n检查前准备不充分、流程不清晰\n患者多次往返、满意度较低'),T('预约有序、候诊时间明显缩短\n检查前准备充分、流程顺畅\n患者体验感提升、满意度提高')];
 for(let i=0;i<2;i++){
  const bx=30+i*277,ax=i?397:50;
  p.text('photo_label_'+i,i?'改善后':'改善前',bx,632,265,21,{position:xy(ax,640),fill:blue,fontSize:22,fontWeight:700});
  const im=new Img({src:`/assets/${i?'改善后':'改善前'}照片.png`,position:xy(bx+132.5,728),width:265,height:144});p.root.add(im);p.nodes.push({id:'photo_'+i,key:im.key,text:null});p.jobs.push(()=>im.position(xy(ax+142,741),.48),()=>im.width(284,.48),()=>im.height(154,.48));
  p.text('photo_caption_'+i,captions[i],bx,811,265,16,{position:xy(ax,829),width:284,fontSize:16,fill:'#10385e'});
 }
 regroup(p,moduleStart,[0,-406],.90,3);moduleStart=p.root.children().length;
 panel(p,'outputs',T('5. 有形成果'),[600,582,530,334],[708,582,535,334]);
 const labels=[T('CT检查预约流程SOP'),T('检查前准备清单'),T('患者健康宣教手册'),T('标准化标识模板'),T('预约提醒模板'),T('质量监测表')];
 for(let i=0;i<6;i++){
  const bx=600+i%3*175,by=635+Math.floor(i/3)*142,ax=726+i%3*170,ay=640+Math.floor(i/3)*139;
  const im=new Img({src:`/assets/成果_${i+1}.png`,position:xy(bx+77.5,by+50),width:155,height:100});p.root.add(im);p.nodes.push({id:'output_image_'+i,key:im.key,text:null});p.jobs.push(()=>im.position(xy(ax+73,ay+48),.48),()=>im.width(146,.48),()=>im.height(96,.48));
  p.text('output_label_'+i,labels[i],bx,by+105,170,16,{position:xy(ax,ay+101),width:160,fontSize:16,fill:blue});
 }
 regroup(p,moduleStart,[0,-406],.90,4);moduleStart=p.root.children().length;
 panel(p,'benefits',T('6. 经济与社会效益'),[1150,582,490,334],[1254,582,386,334]);
 p.text('economic_benefits',T('经济效益\n• 减少患者无效等候\n• 优化检查资源利用\n• 降低因延误引发的退改约率'),1160,636,470,23,{position:xy(1270,641),width:354,fontSize:22,fill:'#10385e'});
 p.text('social_benefits',T('社会效益\n• 患者满意度提升\n• 检查效率提高\n• 提升医院服务质量与社会形象'),1160,791,470,23,{position:xy(1270,785),width:354,fontSize:22,fill:'#10385e'});
 regroup(p,moduleStart,[0,-406],.90,5);
 return p;
}
export default makeScene2D(function*(view){stage(view);make(view,-290.5);const p=make(view,387.5);yield* animate(p,1.45);});
