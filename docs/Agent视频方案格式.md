# Agent 视频方案 v1

入口见 `../AGENT_START.md`。CLI 使用页号，不使用开发机器的绝对地址或 `/files/` URL。工作目录可以整体移动后继续预览与渲染。`schemaVersion` 固定 1；`input_sha256` 必须保留 prepare 生成的值，不能改成其他 PPT 的指纹来绕过校验。

```json
{
  "schemaVersion": 1,
  "input_sha256": "保留prepare生成的值",
  "motion": "stagger",
  "music": true,
  "pages": [
    {
      "number": 2,
      "components": [
        {
          "id": "title",
          "name": "页标题",
          "text": "从原页准确读取的标题",
          "target": [0.06, 0.06, 0.88, 0.12],
          "before": [0.04, 0.04, 0.92, 0.16]
        },
        {
          "id": "chart",
          "name": "完整图表含图例",
          "text": "",
          "target": [0.08, 0.24, 0.84, 0.64],
          "before": [0.08, 0.26, 0.84, 0.66]
        }
      ]
    }
  ]
}
```

- `pages`：1–6 个不重复的实际页号。每页 2–40 个组件；推荐 3–8 个。
- `target`：原页裁剪位置，也是最终归位位置 `[左,上,宽,高]`，均相对原页归一化。像素框 `(x,y,w,h)` 除以原图宽高得到 `[x/W,y/H,w/W,h/H]`。
- `before`：普通版中的位置与大小，同样归一化。不是绝对像素，也不是右下角坐标。
- `text`：普通版替换文字，最多 2000 字。空串表示使用原页裁剪。字体自动缩小，仍放不下时会报错，不会自动删字。成品版始终来自原截图。
- `motion`：`smooth` 同步平滑；`stagger` 错峰移动；`lift` 轻抬归位。
- `music`：布尔值，默认 true；false 输出静音音轨。
- 标签和主题色当前组件模式固定，不要自行添加未实现的参数并宣称生效。

该文件不是 GUI 导出方案的同一种 schema。CLI 会转换成 GUI 共用引擎接受的组件结构，最终的 `组件方案.json` 保留引擎结构；跨工作目录迁移用此处按页号的 `agent-plan.json`，不要复制旧 `/files/` 地址。
