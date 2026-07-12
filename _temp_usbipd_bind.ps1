# TouchGlove USB → WSL2 直通（usbipd-win 5.3.0+ 新语法）
# 用法：以管理员身份运行此脚本
# 注：新脚本已迁移至 D:\Dev\data-collection\scripts\bind_glove.ps1（自动查 BUSID，无需手敲）

$ErrorActionPreference = "Stop"
$Usbipd = "C:\Program Files\usbipd-win\usbipd.exe"

Write-Host "=== TouchGlove USB → WSL2 ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: 列出所有 USB 设备，找到手套
Write-Host "[1/3] 查找 TouchGlove (VID:0483 PID:3039)..."
$list = & $Usbipd list 2>&1
$line = $list | Select-String "0483:3039" | Select-Object -First 1
if (-not $line) {
    Write-Host "  [FAIL] 未找到手套。请确认 USB 已插入且灯亮。" -ForegroundColor Red
    Write-Host "  tip: 重新插拔手套的 USB 线，然后重新运行本脚本。"
    exit 1
}
$busid = ($line -split '\s+')[0]
Write-Host "  BUSID=$busid (COM5)" -ForegroundColor Green

# Step 2: bind（管理员权限必需）
Write-Host "[2/3] bind --busid=$busid..."
& $Usbipd bind --busid=$busid 2>&1
if ($LASTEXITCODE -ne 0) { throw "bind failed" }
Write-Host "  [OK]" -ForegroundColor Green

# Step 3: attach（usbipd 5.x 新语法：--wsl 无需 =distro）
Write-Host "[3/3] attach --wsl --busid=$busid..."
$attachOut = & $Usbipd attach --wsl --busid=$busid 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($attachOut -match "error state") {
        Write-Host "  设备处于错误状态，尝试重启 WSL2..."
        wsl --shutdown
        Start-Sleep 5
        & $Usbipd attach --wsl --busid=$busid
    } else {
        throw "attach failed: $attachOut"
    }
}
Write-Host "  [OK]" -ForegroundColor Green

# 验证
Write-Host ""
Write-Host "验证 WSL2 内设备..."
wsl -d Ubuntu-22.04 -- bash -c "ls -la /dev/ttyACM* 2>&1; echo '---'; groups"
Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "下一步: wsl -d Ubuntu-22.04"
Write-Host "        cd /mnt/d/假肢机械臂/06_文献与参考资料/TouchGlove_SDK"
Write-Host "        python3 dense_preflight.py"