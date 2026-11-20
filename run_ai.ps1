param([string]$Question = '2011年11月销售额最高的五个国家是哪些？')
$ErrorActionPreference = 'Stop'
$bundledPython = Get-ChildItem 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime*/dependencies/python/python.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $bundledPython) { $bundledPython = (Get-Command python -ErrorAction Stop).Source }
Push-Location $PSScriptRoot
try { & $bundledPython ai_assistant.py $Question; if ($LASTEXITCODE -ne 0) { throw '查询失败，请查看上方错误。' } }
finally { Pop-Location }
