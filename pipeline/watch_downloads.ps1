# What If Studio - Downloads watcher.
# Runs quietly in the background. When the app's "Export queue (.json)"
# lands in Downloads, this picks it up and renders the whole queue with
# free AI visuals - no clicks needed. Opens the output folder when done.
#
# Started automatically at login via a shortcut in shell:startup
# ("WhatIfStudio Watcher"). Delete that shortcut to uninstall.

# Only one watcher at a time.
$created = $false
$mutex = New-Object System.Threading.Mutex($false, "WhatIfStudioWatcher", [ref]$created)
if (-not $created) { exit }

$pipeline = Split-Path -Parent $MyInvocation.MyCommand.Path
$downloads = Join-Path $env:USERPROFILE "Downloads"
$log = Join-Path $pipeline "watcher.log"

function Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Add-Content -Path $log
}

Log "watcher started (pid $PID)"

while ($true) {
    $exports = Get-ChildItem -Path $downloads -Filter "whatifstudio-queue*.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime
    foreach ($f in $exports) {
        Start-Sleep -Seconds 1   # let the browser finish writing
        $dest = Join-Path $pipeline "whatifstudio-queue.json"
        try {
            Move-Item -Path $f.FullName -Destination $dest -Force -ErrorAction Stop
        } catch {
            Log "could not move $($f.Name): $_"
            continue
        }
        Log "picked up $($f.Name) - rendering queue..."
        Set-Location $pipeline
        & python make_videos.py whatifstudio-queue.json --ai-visuals 2>&1 |
            ForEach-Object { Add-Content -Path $log -Value "    $_" }
        Log "render finished (exit code $LASTEXITCODE)"
        Invoke-Item (Join-Path $pipeline "output")
    }
    Start-Sleep -Seconds 5
}
