# 给 Codex / WorkBuddy：从任意课件制作原生组件重组视频

**本工具明确配合 AI 使用。** 用户给你工具包和 PPT/PPTX/PDF，由你阅读课件、理解内容、设计两版并写方案；用户不需要手写 JSON。工具负责原件隔离导入、真实 Motion Canvas 预览、同内容映射检查、组件聚合渲染、普通 PPT 与交付文件。不要把辅助 OCR 或候选对象当已经完成的设计。

准确入口：本文 → `docs/AI视频方案协议.md` → `examples/agent-video/ai-native-plan.json`。已认可动势保留在 `video/src/v7/`，当前独立普通版聚合实现为 `video/src/semantic.tsx`。不要另造截图动画，不要用 Python 逐帧排字替代核心动画。

## 必须做成什么

上方固定显示**同内容、真正独立的简陋 PPT**：白底黑字，默认标题、连续编号或项目正文、基础表格、单独朴素摆放的照片。不能把成品卡片去边框/缩小/拆散就叫普通版，不能继承成品组内标题条、夹图、卡片阅读布局。

下方从这批普通文字、表格和照片出发，短促抬起 → 图文迅速按语义聚合 → 整组穿行 → 轻回弹落位。允许过程穿插，不追求零碰撞；避免散字漂移、卡顿、逐帧换行、字格裂开、蛇行绕远和落位时换成整张截图。文字采用稳定短句或行节点，照片保持比例。

成品参考原页层级、结构和配色做原生重建，内容完整优先；允许装饰与渐变差异，但不能擅自改原文、数字、单位、编号或流程方向。源图本身有异常词形时先如实记录，不能按常识偷偷改成正常词。纯装饰可省略，关键结构、照片、表格全行列不能省略。不得承诺任意文件都能零失败。

## 1. 环境

Python 3.11+、LibreOffice、Node.js 20+、FFmpeg、Motion Canvas、Playwright Chromium。原素材只读，不覆盖历史输出。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent.txt
cd video
npm ci
npx playwright install chromium
cd ..
.venv/bin/python agent_video.py doctor
```

已有 `.venv` 直接复用。Windows 命令中的 Python 改成 `.venv\Scripts\python.exe`；Windows 尚未真机验收。缺 LibreOffice 时先安装，或让用户提供 PDF。`doctor.ready:true` 才继续。

本地 OCR 是**可选辅助**：需要时安装 `requirements-ocr.txt`；RapidOCR 使用随 wheel 附带的本地 ONNX 模型，macOS 可额外用 Vision 提供独立证据。不会上传课件到第三方；识别可能误读或遗漏，不能代替你看原图。没有 OCR 也可由你读图并转录，不能因此把整页截图作普通版。

## 2. 导入并读完整课件

选择一个尚不存在的 `WORK`，使用用户真实原件：

```sh
.venv/bin/python agent_video.py prepare --ppt "SOURCE.pptx" --work "WORK" --pages 5
```

可选 `--ocr` 生成本地识别证据；非必需。默认初始取前三页，仅为占位，不代表自动选品或成品。

导入会产生：

- `project.json`：完整页号、原页 PNG、本地原生对象/表格/素材建议；来源和辅助分析状态。
- `contact-*.jpg`：全册总览，每张最多12页。先看全部总览，再打开候选页原图；复杂小字需放大读，不能只凭缩略图。
- `assets/`：能够原生提取的独立图片，供你查看；图片里的字仍要核实，聊天截图/业务截图不能一概称照片。
- `plan.json`：待你完成的方案骨架，`workflow: ai-native-v1`；不是自动完成的设计。
- `data/`、`source-hashes.json`：隔离原始导入与指纹，不要修改。

用户指定页号/范围优先，否则从全册选2–3页，默认至少一页内容页；一次1–6页，每页4秒。图片型课件候选对象为空或 OCR 受限时，你仍应直接读原页继续构建方案；无法辨认的具体字/数字必须记录并补齐，不能臆造或整页复用。

## 3. AI 动态制定方案：先静态，后运动

你应直接用文件工具/脚本编写 `WORK/plan.json`，不让用户手填。**复杂真实页推荐主路是显式 `scene` + 每个文字/照片的 `node.before`**，格式见 `docs/AI视频方案协议.md`。`components` 是内容真源和源页核对范围，`scene` 是原生目标画面；同一节点用独立 before 页坐标呈现普通端。显式 scene 永远优先，辅助自动候选不会覆盖它。

按以下顺序完成：

1. 逐项转录标题、正文、每个表格单元格、编号、流程方向和独立照片；保持所有来源内容可追查。
2. 先设计普通端为文档阅读布局：标题 + 连续段落/基础表格，照片独立集中摆放。不要复用成品7卡片/4模块等内部布局。
3. 原生重建成品：清楚标题层级、面板/表头、对齐、合适图文比例，使用源页主题配色与结构；不要求像素复刻。排版验收须避免词语断裂、单字孤行和标点孤行；按自然语义重新分行、调整宽度或图文比例，不能以缩水字号代替重排。
4. 将短句/图片分别放入目标语义父组。组内坐标固定为终态，`node.before` 使用整页绝对坐标。工具自动完成聚合与整组运动，你不逐帧改字号阈值或换行。
5. 填写每页 `aiReview`：`sourceRead/ordinaryIndependent/contentChecked:true` 和具体 `notes`，如实记录读了哪些页、核对什么、装饰差异/仍有何限制。它是AI审阅记录，不代表用户批准。

每条文字必须有稳定 `id` 与 `sourceRef`；每张照片也必须映射到 `plain` 的图片 `asset`。不要拿聊天/评分表/图表的整块截图当 image，业务文字与数据必须核对重建；图表可重建图形或完整基础数据表，保留含义和方向。

照片可使用节点 `sourceCrop:[x,y,w,h]` 从本页源图提取**独立照片/标志**，无需手抄 base64。也可用原始素材的 `imageData`；不要引用工作目录绝对 `src`。普通端用 `before.w/h` 槽，工具保持比例。不可裁整页或成品卡片充数。

原生对象、OCR、照片候选都是辅助证据，可能有误。AI核实并重建后，显式方案配合 `aiReview` 可接管辅助阻塞；不需要篡改原件或关掉校验。修复你自己写错的输入，不绕过内容映射/预览指纹。

## 4. 查看实际首尾，再检查运动

```sh
.venv/bin/python agent_video.py preview --work "WORK"
```

这是实际 Motion Canvas 帧，不是静态模拟。先打开所有 `before-after.png`：普通端是否独立、完整可读，成品是否清楚有设计，原文字数/表格/照片/方向是否对应。普通版 PPT 与真实首帧共用节点状态。再看 `motion.png` 和视频运动段连续帧；少量快照不证明流畅。

`regions.png` 只用于源页框选核对；GUI中的框和布局概览也不是最终渲染。实际 MC 首尾才是画面依据。修改 components/scene/node.before/字体/源页后必须重新 preview，旧 token 失效。

源图不清、节点越界、文字小于内容槽有效8px、照片映射缺失或文字不同源会明确失败。不要为了过检查删字或把字缩成小点；重新分配空间、合并合理语义或换清晰源件。

## 5. 渲染、逐帧审片和交付

```sh
.venv/bin/python agent_video.py render --work "WORK" --reviewed "PREVIEW_TOKEN" --review-note "具体核对内容与两版差异"
.venv/bin/python agent_video.py verify --work "WORK"
```

输出1080×1440、30fps、H.264/AAC；每页120帧。渲染独立新目录，不覆盖旧作品。完整解码、帧数、资源/字体与 plan→scene 文字映射是技术检查，**不能自动证明对原课件转录完整，也不能证明好看**。

普通PPT也要实际转图验收：用本任务fontconfig，不只检查提取文字。执行`.venv/bin/python docs/检查普通PPT字体.py --work "WORK" --ppt "OUTPUT/普通排版版.pptx"`后逐页看PNG；字体环境边界见`docs/普通PPT字体与检查.md`。外部编辑器依赖可用Noto CJK或中文替代字体，未做所有Office/平台保证。可把已检查的PDF随交付附上。

实际观看 MP4；不能实时播放时明确限制，并按30fps检查每页约0.6–2.3秒全部连续帧及终态。重点：普通端始终不动，下方同批图文迅速成组、连贯穿行、自然回弹、成品停留足够。允许穿插，避免文字格子裂开/裁切/突然替换/二次拖走。

交付 MP4、普通PPTX、两版实际图片、可编辑方案与ZIP，保留审阅与SHA证据。只称本地完成，不称已发布、Windows已实测或像素级复刻。没有实际审片不得宣布视觉通过。

## 6. GUI 与 Agent 互通

用户在GUI导入同一个原始文件后，点击“导入AI方案”，选择你生成的完整 `plan.json`。`input_sha256` 必须保留原件指纹；工具绑定当前项目的源页并替换外部 source 路径。失败不会覆盖现有作品；成功也清除旧确认，仍需实际预览和逐页确认。

新API为 `POST /api/components/import-plan`，输入 `{project,plan}`。不要通过改 project.data 伪造源页，不把另一作品的路径放入计划。GUI上传本身不自动生成低质量成品；辅助识别按钮只供AI准备材料。

## 7. 无历史自测

阅读 `examples/agent-video/ai-native-plan.json` 学习完整、可执行的文字映射和独立 before 布局。可用 `examples/agent-video/示例课件.pptx` 在新 WORK prepare 后，将该示例方案复制为 plan.json，走 preview → 看首尾/运动 → render → verify。它是虚构示范；真实新课件必须由你重新读图、动态编排，不套用示例坐标或把历史样片当唯一场景。

`native-reference-plan.json`、旧 `reference.mp4` 是较早的兼容示例；不会代表你新课件已验收。当前AI协作示例另用 `ai-native-plan.json`，配套 `ai-reference.mp4`、`ai-reference-before.png`、`ai-reference-after.png` 来自同次240帧实际导出，详见 `ai-reference-result.json`。不要回到退役截图切块/擦除替换路线。
