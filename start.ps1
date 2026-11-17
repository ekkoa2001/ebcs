$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$port = 8875
$url = "http://127.0.0.1:$port/"
$running = $false
try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
    $running = $response.Content -match 'Ekko Brand Content Strategy'
} catch {}
if (-not $running) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $pythonExecutable = $bundledPython }
    else {
        $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $candidate -or $candidate.Source -like '*WindowsApps*') { throw '请先安装 Python 3.11 或更新版本，并加入 PATH。' }
        $pythonExecutable = $candidate.Source
    }
    $serviceDir = Join-Path $PSScriptRoot 'server'
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'data\sana_data.sqlite3'))) {
        & $pythonExecutable (Join-Path $serviceDir 'initialize.py')
        if ($LASTEXITCODE -ne 0) { throw '初始化未完成。' }
    }
    $logDir = Join-Path $PSScriptRoot 'logs'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $process = Start-Process -FilePath $pythonExecutable -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$port" -WorkingDirectory $serviceDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'server-output.log') -RedirectStandardError (Join-Path $logDir 'server-error.log') -PassThru
    $process.Id | Set-Content -LiteralPath (Join-Path $logDir 'server.pid')
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try { $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; if ($response.Content -match 'Ekko Brand Content Strategy') { $running = $true; break } } catch {}
        if ($process.HasExited) { break }
    }
    if (-not $running) { throw '启动失败，请查看 logs\server-error.log。' }
}
Start-Process $url
