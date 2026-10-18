$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}
function Ensure-App($command, $package) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
      throw "首次安装需要 $command。请安装后重新打开；系统未找到 Windows 应用安装程序 winget。"
    }
    Write-Host "首次准备运行环境：$package"
    winget install --id $package --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw "安装未完成：$package，请完成安装后重试。" }
    Refresh-Path
  }
}
Ensure-App "python" "Python.Python.3.11"
Ensure-App "node" "OpenJS.NodeJS.LTS"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw "Python 环境创建失败，请安装 Python 3.11 或更新版。" }
}
if (-not (Test-Path ".venv\toolbox-ready")) {
  & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "处理组件安装失败，请检查网络后再次打开。" }
  New-Item ".venv\toolbox-ready" -ItemType File -Force | Out-Null
}
if (-not (Test-Path "video\node_modules")) {
  npm.cmd ci --prefix video --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw "视频组件安装失败，请检查网络后再次打开。" }
}
if (-not (Test-Path "video\.browser-ready")) {
  Push-Location video
  npx.cmd playwright install chromium
  Pop-Location
  if ($LASTEXITCODE -ne 0) { throw "视频浏览器组件安装失败。" }
  New-Item "video\.browser-ready" -ItemType File -Force | Out-Null
}
if (-not (Test-Path "$env:ProgramFiles\LibreOffice\program\soffice.exe")) {
  Write-Host "PPT 导入需要 LibreOffice；未安装时可先导入 PDF 或图片。"
}
& ".venv\Scripts\python.exe" start.py
