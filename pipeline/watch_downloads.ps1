# What If Studio - Downloads watcher.
# Runs quietly in the background. When the app's "Export queue (.json)" or
# "Export .json" lands in Downloads, this picks it up and renders videos
# with free AI visuals - no clicks needed. Shows a notification when
# rendering starts, and opens the output folder when done.
#
# Started per-session via start-watcher.bat. Stops at logoff. Not installed.

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

function Notify($title, $text) {
    # Tray balloon notification (shows as a Windows toast). Best-effort.
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $ni = New-Object System.Windows.Forms.NotifyIcon
        $ni.Icon = [System.Drawing.SystemIcons]::Information
        $ni.Visible = $true
        $ni.BalloonTipTitle = $title
        $ni.BalloonTipText = $text
        $ni.ShowBalloonTip(8000)
        Start-Sleep -Seconds 6
        $ni.Dispose()
    } catch { Log "notify failed: $_" }
}

Log "watcher started (pid $PID)"

while ($true) {
    $exports = Get-ChildItem -Path $downloads -Filter "whatifstudio-*.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime
    foreach ($f in $exports) {
        Start-Sleep -Seconds 1   # let the browser finish writing
        # Archive every export under a unique dated name - the Produce page
        # lists this folder as the permanent history, nothing is overwritten.
        $exportDir = Join-Path $pipeline "exports"
        if (-not (Test-Path $exportDir)) { New-Item -ItemType Directory -Path $exportDir | Out-Null }
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $destName = "$($f.BaseName)-$stamp.json"
        $dest = Join-Path $exportDir $destName
        try {
            Move-Item -Path $f.FullName -Destination $dest -Force -ErrorAction Stop
        } catch {
            Log "could not move $($f.Name): $_"
            continue
        }

        $count = 1
        try {
            $data = Get-Content $dest -Raw | ConvertFrom-Json
            if ($data.items) { $count = @($data.items).Count }
        } catch {}

        Log "picked up $($f.Name) -> exports\$destName - rendering $count video(s)..."
        Notify "What If Studio" "Rendering $count video(s) now. New scenarios take 2-5 minutes each - the output folder opens when everything is ready."

        Set-Location $pipeline
        & python make_videos.py "exports/$destName" --ai-visuals 2>&1 |
            ForEach-Object { Add-Content -Path $log -Value "    $_" }
        $code = $LASTEXITCODE
        Log "render finished (exit code $code)"

        if ($code -eq 0) {
            Invoke-Item (Join-Path $pipeline "output")
        } else {
            Notify "What If Studio" "Something went wrong during rendering. Details are in pipeline\watcher.log"
            Invoke-Item $log
        }
    }
    Start-Sleep -Seconds 5
}
