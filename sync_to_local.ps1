# sync_to_local.ps1
# Continuously mirrors Z:\cheatly -> C:\cheatly using robocopy.
# Run this in a separate terminal. Press Ctrl+C to stop.

param(
    [string]$Source = "Z:\cheatly",
    [string]$Dest   = "C:\cheatly",
    [int]$IntervalSeconds = 2
)

# Directories to exclude from sync (add more as needed)
$ExcludeDirs = @(
    "__pycache__"
    ".git"
    "node_modules"
    ".venv"
    "venv"
    ".mypy_cache"
    ".pytest_cache"
    ".ruff_cache"
    "dist"
    ".next"
    ".nuxt"
)

# Files to exclude
$ExcludeFiles = @(
    "*.pyc"
    "*.pyo"
    "sync_to_local.ps1"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Z:\cheatly -> C:\cheatly  LIVE SYNC"    -ForegroundColor Cyan
Write-Host "  Polling every ${IntervalSeconds}s"       -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop"                    -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Initial full mirror
Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Initial sync..." -ForegroundColor Yellow
robocopy $Source $Dest /MIR /NFL /NDL /NJH /NJS /NP /XD $ExcludeDirs /XF $ExcludeFiles | Out-Null
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Initial sync complete.`n" -ForegroundColor Green

# Loop: re-mirror on interval
try {
    while ($true) {
        # /MIR   = mirror (add + delete to keep identical)
        # /XO    = exclude older files (skip if dest is newer — shouldn't happen, but safety)
        # /NFL /NDL /NJH /NJS = quiet output
        # /NP    = no progress percentage
        # /FFT   = assume FAT file times (2-second granularity) — helps with cross-filesystem timestamps
        $output = robocopy $Source $Dest /MIR /FFT /NFL /NDL /NJH /NJS /NP /XD $ExcludeDirs /XF $ExcludeFiles 2>&1

        # Robocopy exit codes: 0 = no change, 1 = files copied, 2 = extra files removed, 3 = both
        # Codes >= 8 are errors
        $code = $LASTEXITCODE
        if ($code -ge 1 -and $code -le 7) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Synced changes (robocopy code $code)" -ForegroundColor Green
        }
        elseif ($code -ge 8) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Robocopy error (code $code)" -ForegroundColor Red
        }
        # code 0 = no changes, stay silent

        Start-Sleep -Seconds $IntervalSeconds
    }
}
finally {
    Write-Host "`nSync stopped." -ForegroundColor Yellow
}
