# 给第一次接手的 Agent：从原始 PPT 制作组件重组视频

你不需要知道本工具的历史，也不需要寻找以前的聊天或代码库。用户给你的输入是这个完整工具包和一份 PPT。先读本文件，再查看 `examples/agent-video/` 的参考图片、视频和方案。使用包内现有引擎执行，输出视频文件；不要仅给用户操作建议。

## 要做成什么

制作一条竖屏 PPT 排版对比视频。上半部分始终显示**同内容的普通排版**，下半部分的组件从普通版位置移动、缩放、渐变回原 PPT 的成品位置。成品版以用户原页为准；普通版是你重新排版的演示，不代表作者的历史初稿。

- 默认选择 2–3 页适合展示的页面，每页 4 秒；用户指定页数/页号优先。一次最多 6 页。
- 输出 1080×1440、24 fps、H.264/AAC MP4，以及普通版 PPTX、两版图片、可编辑组件方案和交付 ZIP。
- 尽量每页 3–8 个有意义组件。标题、整张图表、完整流程、图片组分别成组；不要把图表中的每个数字拆开。
- 普通版保留原文、数字、单位和图表含义。纯装饰可以省略，业务内容不能为了突出美化效果故意删减。
- 不允许用整页图片平移或整页淡入替代组件重组。CLI 至少要求每页两个组件；这只是底线，你仍需检查真实效果。
- 组件最后回到原 PPT 画面。最后会短暂补全整页背景和未选装饰；这不能掩盖遗漏的正文。

## 你需要具备的能力

需要能读取/修改本地文件、运行 Python 命令，并查看图片（最好也能观看视频）。只支持文字聊天、没有文件/执行权限的 Agent 无法完成这项任务。无需指定品牌模型或 API Key。用户素材不应未经授权发给第三方网站。

工作目录和路径由你选择。下面的 `WORK` 代表一个**尚不存在的新目录**，`SOURCE.pptx` 换成用户提供的真实路径。命令在工具包根目录执行；路径有空格时加引号。不要复制本项目开发机器的路径。

## 1. 准备环境

Python 3.11+，LibreOffice 和 FFmpeg（可由 imageio-ffmpeg 提供）。此组件视频入口**不需要 Node.js 或浏览器**。

Mac/Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --timeout 120 --retries 5 -r requirements-agent.txt
.venv/bin/python agent_video.py doctor
```

Windows PowerShell：

```powershell
python -m venv .venv
& .venv\Scripts\python.exe -m pip install --timeout 120 --retries 5 -r requirements-agent.txt
& .venv\Scripts\python.exe agent_video.py doctor
```

如果已经有 `.venv`，直接复用，不要重建。下载较慢时可用已安装的 uv 执行 `uv pip install --python .venv/bin/python -r requirements-agent.txt`（Windows 换成对应 Python 路径）。`doctor` 返回 `ready:true` 且退出码 0 才继续。缺 LibreOffice 时：Windows 可运行随包的 `安装PPT支持Windows.cmd`；Mac 可在已安装 Homebrew 时用 `brew install --cask libreoffice`，否则安装 LibreOffice。Linux 安装发行版的 LibreOffice。首次依赖安装需要网络；之后处理在本地完成。包内不附 Python/LibreOffice，不是免环境安装包。Windows 尚未真机验收，不能声称已经通过。

以下命令以 Mac 的 `.venv/bin/python` 演示；Windows 换成 `.venv\Scripts\python.exe`。

## 2. 导入与读图

```sh
.venv/bin/python agent_video.py prepare --ppt "SOURCE.pptx" --work "WORK"
```

可以加 `--pages 2,5,8` 指定初始选页。没有指定时，初始方案只取前三页作为占位；你必须查看全册再选页。

输出：

- `project.json`：所有页面的页号、本地图片路径、原生对象边界与文本。
- `contact-*.jpg`：每张最多 12 页的总览，先全部查看，再打开候选页原图。
- `plan.json`：初始组件方案。原生对象只是建议，可能重叠、分组过碎、遗漏超过 40 个对象或被截断的长文本。
- `data/`：隔离保存的导入素材；不覆盖用户 PPT 或现有 GUI 作品。

根据内容选页。优先有清楚的标题、图表、流程或图片组的页面；不要只挑封面，默认至少选择一页内容页。原 PPT 缺页、损坏、加密或缺字体时，如实处理报错。字体替换可能改变排版，要在这里核对。

## 3. 编辑方案（你完成判断，工具完成渲染）

方案字段说明与完整例子见 `docs/Agent视频方案格式.md`。仅编辑 `plan.json`，不要改导入页、源指纹、源码或把确认步骤删掉。

- 原生 PPT：合并重复/相互覆盖的对象，删去纯装饰框；核对是否漏掉真实内容。合并区域使用包含全部相关内容的矩形。
- 图片型 PPT / PDF：`objects` 可能为空。直接查看原页，根据图像画出矩形边界，在 `components` 中填入 `target`；不要要求用户重新手动拆图才能继续。坐标按图像宽高换算为 0–1。
- 普通版的位置用 `before`。按阅读顺序做白底、对齐、留白的朴素布局，保留文字可读性。
- `text` 非空时，普通版显示独立黑字；留空则保留原图裁剪块。仅转录你能看清的内容，不能编造数据。完整图表通常留空，避免误把图表简化成几个数字。
- 图像组件是矩形裁剪，可能带背景或重叠对象。尽量用更完整的组合框解决，不能宣称得到透明矢量对象。若源截图本身无法辨认，记录具体位置，并只询问用户缺失的关键信息。

## 4. 生成实际预览并修正

```sh
.venv/bin/python agent_video.py preview --work "WORK"
```

打开返回目录下**所有** `before-after.png`、`regions.png` 和 `motion.png`。前者左侧普通版、右侧成品版；后者标明原页框选范围。检查文字/数字/单位对应、框选完整、普通版不重叠不截字。不要仅凭返回成功或图像存在就宣布检查通过。修改 `plan.json` 后重跑本步。

预览返回 `review_token`。它只代表当前方案的指纹，不代表用户批准或自动视觉验收。你看过预览并确认后，用自己的核对说明进入下一步。用户已经委托制作时，不需要每一步都问用户许可。

## 5. 导出和技术校验

```sh
.venv/bin/python agent_video.py render --work "WORK" --reviewed "上一步的review_token" --review-note "具体记录核对了哪些页、文字与数值、框选和布局，以及已知限制"
.venv/bin/python agent_video.py verify --work "WORK"
```

渲染会拒绝修改后未重新预览的方案。失败时读取 `import.log` / `render.log`；修正输入或布局后重试，不改源码绕过校验。每次渲染创建新输出目录，不覆盖旧视频。`latest-result.json` 指向最近一次成功结果。

常见问题：

| 报错或现象 | 处理 |
|---|---|
| 普通版文字放不下 | 扩大该组件、重新分配布局；必要时分成多个有意义组件。不要静默删关键内容 |
| 组件为空 / 少于两个 | 图片页需视觉框选；无法形成有意义对比时改选页，并说明原因 |
| 坐标越界 | 每个矩形满足 x≥0、y≥0、w/h≥0.005、x+w≤1、y+h≤1 |
| 指纹或预览失效 | 方案改动后重新 preview；源页改动则在新工作目录重新 prepare |
| 普通版仍像成品版 | 对适合转录的文字填入 text，调整 before；图表可保留原图，但不要声称整页彻底去除了样式 |
| 颜色块连带背景、重影 | 合并相关对象或重新框选；原引擎无法恢复被遮挡背景 |

## 6. 看成片，再交付

工具自动检查全片能解码，但不能替你判断视频好看或内容无误。观看 MP4；如不能播放，抽取每页连续运动阶段的多帧，至少覆盖起点、移动、归位、最终停留，检查是否只是整页闪现。包中已有 `预览_页_帧.png`（第 0/42/90 帧），它们可辅助检查，但不能单独证明运动连贯。需要更多帧时用 FFmpeg，例如 `ffmpeg -i 视频.mp4 -vf fps=6 核对-%03d.png`。

最终回复交付 MP4、ZIP 和普通版 PPTX 的可打开路径，说明选用页号、时长、视觉检查结果与剩余限制。保留 `agent-plan.json`、`agent-review.json` 和 `sha256.json` 供复查。只有技术校验而未看成片时必须明确说未完成视觉验收。不要声称视频已发布、Windows 已验证或截图已变成完整可编辑原生 PPT。

## 无背景自测

随包 `examples/agent-video/示例课件.pptx` 含一页原生对象、一页图片型内容，均为虚构演示素材。`reference-plan.json` 展示 Agent 整理后的方案，`reference.mp4` 与 `reference-preview.png` 展示引擎的实际效果边界。

用示例 PPT 在一个新 WORK 跑 prepare，然后用 reference-plan.json 替换 WORK/plan.json，依次 preview、看图、render、verify。该自测不依赖任何历史聊天、原开发目录、后台服务或已有作品。它检查工具包链路；用户真实 PPT 仍必须按上述步骤重新看图和调整方案。
