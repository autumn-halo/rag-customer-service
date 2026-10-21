# Docker Desktop 前置依赖：开启 WSL 所需的两个 Windows 功能
# 需要管理员权限运行；开启后需重启电脑生效
Write-Host "正在开启 VirtualMachinePlatform ..."
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart | Out-Null
Write-Host "正在开启 Microsoft-Windows-Subsystem-Linux ..."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart | Out-Null
Write-Host ""
Write-Host "完成！请重启电脑，然后重新打开 Docker Desktop。"
Write-Host ""
Read-Host "按回车键关闭本窗口"
