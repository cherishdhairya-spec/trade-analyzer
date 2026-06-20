$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $project "run_app.bat"

try {
    $action = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $project
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName "StockAnalyzerLocalApp" -Action $action -Trigger $trigger -Settings $settings -Description "Starts local stock analyzer dashboard at login." -Force
    Write-Host "Installed Scheduled Task. The app will start whenever you log in to Windows."
}
catch {
    $startup = [Environment]::GetFolderPath("Startup")
    $shortcut = Join-Path $startup "Stock Analyzer Local App.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($shortcut)
    $lnk.TargetPath = $bat
    $lnk.WorkingDirectory = $project
    $lnk.WindowStyle = 7
    $lnk.Save()
    Write-Host "Scheduled Task was blocked, so a Startup folder shortcut was installed instead: $shortcut"
}
