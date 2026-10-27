# 普通PPT字体与实际检查

普通PPT保留可编辑文字与独立图片，但不内嵌整套字体。视频与实际MC图片已经使用工具字体正常渲染；外部PPT编辑器仍依赖可用的Noto Sans CJK SC或合适的中文替代字体。没有验证所有Office/平台直接打开的表现，不作跨平台字体保证。

本机曾复现：默认headless LibreOffice成功转PDF、还能提取出中文文本，实际PNG却没有中文字形，只剩英文数字；使用本任务`WORK/fontconfig.xml`后中文完整。这不是文字数据消失，也不能只拿“PDF文字全部命中”宣布可见。请使用任务配置并实际打开转图，检查中文、换行、边界和照片比例。

在工具根目录执行（替换两个路径；Windows把Python入口换成`.venv\Scripts\python.exe`）：

```sh
.venv/bin/python docs/检查普通PPT字体.py --work "WORK" --ppt "OUTPUT/普通排版版.pptx"
```

该脚本仅对子进程设置`FONTCONFIG_FILE=WORK/fontconfig.xml`，用独立LibreOffice用户目录转换到新的`WORK/ppt-font-check-*`，输出PDF和逐页PNG。不会安装系统字体、改源PPT或覆盖旧验收。需逐页打开PNG；文字提取不是字形验收。若搬动工具或工作目录后fontconfig内的字体路径失效，应在新环境重新prepare生成本地配置。

移交时可附经过实际检查、已正确嵌入字体的PDF和普通版PNG，供接收者直接查看。需要编辑PPT时，可由接收者自行安装工具`engine/fonts/`中的Noto CJK字体或使用已确认的中文替代字体；不要未经请求改用户系统字体。Windows/其他Office未做真机兼容保证。
