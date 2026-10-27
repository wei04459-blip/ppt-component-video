# AI 视频方案协议：显式原生场景与独立普通版

这是 Codex / WorkBuddy 编写文件用的接口，不要求用户手填。完整可运行示例为 `examples/agent-video/ai-native-plan.json`。先读根目录 `AGENT_START.md`。

## 顶层与每页

```json
{
  "schemaVersion":1,
  "workflow":"ai-native-v1",
  "input_sha256":"保留prepare给出的原件SHA256",
  "motion":"stagger",
  "music":true,
  "pages":[{
    "number":5,
    "aiReview":{"sourceRead":true,"ordinaryIndependent":true,"contentChecked":true,"notes":"具体记录读图范围、数字/照片/方向核对和样式差异"},
    "components":[],
    "scene":{"width":1600,"height":900,"groups":[]}
  }]
}
```

一次1–6个不同页号；新AI协作方案每页必须有明确scene、AI审阅记录和独立node.before。旧兼容方案仍可在原工作目录使用；不能借旧协议回避本轮独立普通版要求。

components每页2–40项，id独立稳定，before/target为0–1归一化矩形。它们用于内容和源页范围核对；显式scene下，实际画面位置以节点坐标为准。plain支持：

- `text`：完整`text`，可选`title`和`role:title/body/caption`。
- `table`：完整矩形二维字符串`rows`（1–30行、1–12列），可选正数`columns`相对列宽。
- `image`：只用于独立照片/标志，`assetRole:photo/logo`。
- `group`：`parts`为1–20个**非嵌套**text/table/image，每项有组内归一化`box`。超过20项拆为多个语义组，不能嵌套group。

不要为适应版面改动原文或丢空以外的单元格。数字与单位不得交换。原图若有异常词形，记录并保留，不擅自纠正。

## 父组和稳定文字

```json
{"id":"stage1","size":[200,340],"before":[40,180,1],"after":[40,180,1],"index":0,"nodes":[
  {"kind":"rect","x":0,"y":0,"w":200,"h":340,"fill":"#eff7fc","before":{"opacity":0}},
  {"kind":"text","id":"stage1-heading","text":"01 术前评估","x":12,"y":12,"fontSize":24,"fontWeight":700,"fill":"#ffffff","sourceRef":{"component":"stage1","path":"title"},"before":{"x":40,"y":160,"fontSize":22,"fontWeight":400,"fill":"#111111"}},
  {"kind":"text","id":"stage1-body1","text":"病情评估","x":18,"y":216,"fontSize":20,"fill":"#103758","sourceRef":{"component":"stage1","path":"text"},"before":{"x":53,"y":190,"fontSize":20,"fontWeight":400,"fill":"#111111"}}
]}
```

示意片段必须与你自己的components完整内容相匹配，不能直接把片段当完整页。scene需要2–40父组，节点在容器内；size为正数。after是终态父组位置+比例。常用before父组与after相同，真正普通端使用每个语义节点的before绝对页坐标。

静态验收须避免词语断裂、单字孤行和标点孤行；优先按自然语义重分行、调整宽度与图文比例，不能用缩水字号代替重排。

文字节点的`text`不在动画中变化。拆成稳定短句或固定行段；同一个来源分成多个节点时，按nodes顺序拼接核对。普通端可相邻排成连续段落，终态落入不同位置；**不要逐字符飞行、逐帧重新换行**。

`sourceRef.component`对应components.id，path：根文字`text`/`title`；表格`rows/行号/列号`（从0起）；组合子项`parts/序号/text`等。标题与正文合为一节点可用有序path数组`["title","text"]`。每段原文/非空单元格须且只须绑定一次。

node.before允许x/y、fontSize/fontWeight、fill/stroke、opacity、radius/lineWidth，图片/矩形可w/h。每个文字/照片必须明确before.x/y。所有值有限数；有效字号≥8px（内容槽宽972高547适配），业务文字/照片不能靠opacity隐藏。装饰rect/line可before.opacity=0。

## 照片：可移交、保持比例、逐张对应

组件：

```json
{"id":"photo1","before":[0.05,0.65,0.2,0.15],"target":[0.4,0.3,0.2,0.2],"plain":{"kind":"image","assetRole":"photo"}}
```

对应节点：

```json
{"kind":"image","id":"photo1-node","x":8,"y":60,"w":180,"h":120,"sourceCrop":[0.4,0.3,0.2,0.2],"sourceRef":{"component":"photo1","path":"asset"},"before":{"x":40,"y":650,"w":225,"h":105}}
```

sourceCrop从**本页源PNG**按0–1裁独立照片/标志；不要选整页、成品卡片、文字表格或主要图表。工具保持图片比例，before.w/h是contain槽。若用原始素材可填`imageData`（PNG/JPEG base64），不能把外部绝对src路径写进可移交方案。节点可选fit:contain/cover与cropPosition，默认contain；不能stretch。

每张图片也有sourceRef：根image用`asset`，组合内用`parts/0/asset`等。照片数与映射逐项检查，不能漏一张或重复绑定。imageData不会自动证明该图就是照片，AI须看原图。

## 原生图形和结构

rect字段x/y/w/h、fill/afterFill、stroke/afterStroke、radius/afterRadius、lineWidth。line字段x/y、points局部点列表、stroke、lineWidth；closed:true可绘制简单填色多边形。连线/箭头是业务流程时必须准确保留起终点和方向。不要把OCR残余像素描成碎片形状；用清楚矩形面板、标题条、基础图表、箭头重建，纯装饰可简化并说明。

默认聚合节奏：静止约.65秒→.20抬升→穿行前半约.24秒完成组内聚合、整个穿行.53秒→.35回弹；错峰总量封顶，仍留成品阅读时间。不需要你写逐帧代码。过程可以穿插，重点是成组、连贯和清楚落位，不追求零碰撞。

## 同一入口、明确边界

CLI使用prepare/preview/render/verify。GUI先导入同原件，再通过`/api/components/import-plan`导入同一JSON；后端按原件SHA和页号绑定本项目source，清掉旧确认，外来source路径不会被信任。显式scene优先，辅助OCR草稿不能替代AI方案。

aiReview是AI的具体审阅记录，不是用户批准，也不代替真实预览。plan→scene映射只证明方案内部相同，不能自动证明你对源图读全/抄对。先看实际首尾，再看运动连续帧。失败后修输入并重新preview，不绕过指纹或改源文件。
