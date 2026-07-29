# Tao shortcut "Học từ qua bộ thủ" tren Desktop, kem icon.
# Chay lai nhieu lan duoc: no ghi de shortcut cu.
# Tep .bat goi tep nay va tu giu cua so, nen o day khong can Read-Host.

$ErrorActionPreference = "Stop"

try {
    $goc = Split-Path -Parent $MyInvocation.MyCommand.Path
    Write-Host "  Goc kho     : $goc"

    $bat = Join-Path $goc "chay-app.bat"
    if (-not (Test-Path $bat)) { throw "Khong thay chay-app.bat tai $goc" }

    $icon = Join-Path $goc "hoc-tu-bo-thu.ico"
    $coIcon = Test-Path $icon
    if ($coIcon) { Write-Host "  Icon        : $icon" }
    else         { Write-Host "  Icon        : khong co, dung icon mac dinh" }

    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not $desktop) { throw "Khong xac dinh duoc thu muc Desktop" }
    Write-Host "  Desktop     : $desktop"

    $shortcut = Join-Path $desktop "Học từ qua bộ thủ.lnk"

    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($shortcut)
    $lnk.TargetPath       = $bat
    $lnk.WorkingDirectory = $goc
    $lnk.Description      = "Hoc tu vung tieng Trung qua bo thu"
    if ($coIcon) { $lnk.IconLocation = "$icon,0" }
    $lnk.Save()

    if (-not (Test-Path $shortcut)) { throw "Da goi Save() nhung khong thay tep .lnk" }

    Write-Host ""
    Write-Host "  Da tao      : $shortcut" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host ""
    Write-Host "  LOI: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Dong lenh   : $($_.InvocationInfo.Line.Trim())"
    exit 1
}
