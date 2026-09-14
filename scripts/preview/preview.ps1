param(
    [ValidateSet('prepare', 'import-local', 'start', 'stop', 'status')]
    [string]$Action = 'status',
    [ValidateSet('auto', 'demo', 'local')]
    [string]$ReviewSource = 'auto',
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$previewRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$previewData = Join-Path $previewRoot '.preview'
$previewRegistry = Join-Path $previewData 'servers.json'
if (-not $Python) {
    $Python = Join-Path (Split-Path $previewRoot -Parent) 'news_portal\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found: $Python" }
$Python = [IO.Path]::GetFullPath($Python)

if ($Action -in @('prepare', 'import-local')) {
    Push-Location $previewRoot
    try {
        $preparationScript = if ($Action -eq 'prepare') { 'prepare.py' } else { 'import_local_content.py' }
        & $Python -B (Join-Path $PSScriptRoot $preparationScript)
        if ($LASTEXITCODE -ne 0) { throw 'Preview preparation failed.' }
    } finally { Pop-Location }
    exit
}
$previewServers = @()
if (Test-Path -LiteralPath $previewRegistry) {
    $previewServers = @(Get-Content -Raw -LiteralPath $previewRegistry | ConvertFrom-Json)
}
if ($Action -eq 'status') {
    foreach ($entry in $previewServers) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.pid)"
        [pscustomobject]@{ Scenario=$entry.scenario; URL=$entry.url; PID=$entry.pid; Running=([bool]$proc -and $proc.CreationDate.ToUniversalTime().Ticks -eq ([datetime]$entry.created).ToUniversalTime().Ticks) }
    }
    exit
}
if ($Action -eq 'stop') {
    foreach ($entry in $previewServers) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.pid)"
        if ($proc -and $proc.CreationDate.ToUniversalTime().Ticks -eq ([datetime]$entry.created).ToUniversalTime().Ticks -and $proc.CommandLine.Contains($previewRoot) -and $proc.CommandLine.Contains('config.settings.design_preview')) {
            # Windows venv python.exe launches a second interpreter process.
            $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($entry.pid)")
            foreach ($child in $children) {
                if ($child.Name -eq 'python.exe' -and $child.CommandLine.Contains($previewRoot) -and $child.CommandLine.Contains('config.settings.design_preview')) {
                    Stop-Process -Id $child.ProcessId
                }
            }
            if (Get-Process -Id $entry.pid -ErrorAction SilentlyContinue) { Stop-Process -Id $entry.pid }
            Write-Output "Stopped $($entry.url)"
        }
    }
    exit
}
foreach ($port in @(8011,8012)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Check status before starting another preview."
    }
}
if ($ReviewSource -eq 'auto') {
    $ReviewSource = if (Test-Path -LiteralPath (Join-Path $previewData 'local-source.json')) { 'local' } else { 'demo' }
}
foreach ($scenario in @('current', $ReviewSource)) {
    if (-not (Test-Path -LiteralPath (Join-Path $previewData "$scenario.sqlite3"))) {
        throw "Missing $scenario database. Run -Action prepare first."
    }
}
$previewServers = @()
$previousScenario = $env:KOMUNIKI_PREVIEW_SCENARIO
try {
    foreach ($scenario in @('current', $ReviewSource)) {
        $port = if ($scenario -eq 'current') { 8011 } else { 8012 }
        $env:KOMUNIKI_PREVIEW_SCENARIO = $scenario
        $arguments = @('-B', ('"' + (Join-Path $previewRoot 'manage.py') + '"'), 'runserver', "127.0.0.1:$port", '--noreload', '--settings=config.settings.design_preview')
        $proc = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $previewRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $previewData "$scenario.stdout.log") -RedirectStandardError (Join-Path $previewData "$scenario.stderr.log")
        $details = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)"
        $previewServers += [pscustomobject]@{ scenario=$scenario; pid=$proc.Id; url="http://127.0.0.1:$port/"; created=$details.CreationDate.ToUniversalTime().ToString('o') }
    }
} finally {
    $env:KOMUNIKI_PREVIEW_SCENARIO = $previousScenario
    $previewServers | ConvertTo-Json | Set-Content -LiteralPath $previewRegistry -Encoding utf8
}
$previewServers | Format-Table scenario,url,pid
