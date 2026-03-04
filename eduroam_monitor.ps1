<#
.SYNOPSIS
    Hayatin Ritmi - Eduroam Auto-Reconnect & Network Monitor
.DESCRIPTION
    Bu script her 0.5 saniyede bir bagli oldugunuz "eduroam" aginin baglantisini kontrol eder.
    Fancy bir arayuzle anlik durumu, pingi ve tahmini hizi gosterir.
    Eger baglanti duserse otomatik olarak yeniden baglanma (netsh) komutu gonderir.
#>

$NetworkName = "eduroam"
$TargetHost = "8.8.8.8"
$CheckIntervalMs = 500
$HistorySize = 40
$PingHistory = New-Object int[] $HistorySize

$Console = $Host.UI.RawUI
$Console.WindowTitle = "Eduroam Auto-Reconnect - Hayatin Ritmi"
Clear-Host
[Console]::CursorVisible = $false

# ASCII karakterle cizim (UTF-8 encoding hatalarini onlemek icin normal blok karakterler)
$BlockFull = "#"
$BlockHigh = "="
$BlockMid = "-"
$BlockLow = "."
$BlockZero = " "

function Get-PingTime {
    $pingResult = Test-Connection -ComputerName $TargetHost -Count 1 -Quiet -BufferSize 32
    if ($pingResult) {
        try {
            $p = Test-Connection -ComputerName $TargetHost -Count 1 -ErrorAction SilentlyContinue
            if ($null -ne $p -and $p.ResponseTime -ge 0) {
                return $p.ResponseTime
            }
        }
        catch { }
    }
    return -1
}

function Connect-Wifi {
    Write-Host "`n[!]" -ForegroundColor Red -NoNewline
    Write-Host " BAGLANTI KOPTU! " -ForegroundColor Yellow -BackgroundColor Red -NoNewline
    Write-Host " $NetworkName agina yeniden baglaniliyor..." -ForegroundColor Gray
    
    netsh wlan disconnect > $null
    Start-Sleep -Milliseconds 500
    netsh wlan connect name=$NetworkName > $null
    
    for ($i = 0; $i -lt 5; $i++) {
        Write-Host "." -ForegroundColor Cyan -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host " islem tamam.`n" -ForegroundColor Green
}

function Draw-Graph {
    param([int[]]$dataBox)
    
    $graphString = ""
    foreach ($val in $dataBox) {
        if ($val -lt 0) {
            $graphString += "X"
        }
        elseif ($val -eq 0) {
            $graphString += $BlockLow
        }
        elseif ($val -lt 20) {
            $graphString += $BlockFull
        }
        elseif ($val -lt 50) {
            $graphString += $BlockHigh
        }
        elseif ($val -lt 150) {
            $graphString += $BlockMid
        }
        else {
            $graphString += $BlockLow
        }
    }
    return $graphString
}

try {
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host "           EDUROAM AUTO-CONNECT & NETWORK MONITOR             " -ForegroundColor Cyan
    Write-Host "           Hedef Ag: " -ForegroundColor Cyan -NoNewline
    Write-Host "$NetworkName" -ForegroundColor Yellow
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $loopCount = 0
    $yPos = $Console.CursorPosition.Y
    
    while ($true) {
        $loopCount++
        $ping = Get-PingTime
        
        for ($i = 0; $i -lt ($HistorySize - 1); $i++) {
            $PingHistory[$i] = $PingHistory[$i + 1]
        }
        $PingHistory[$HistorySize - 1] = $ping
        
        if ($Console.CursorPosition.Y -gt $yPos + 5) {
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
        }
        
        Write-Host "                                                            " -NoNewline "`r"
        
        if ($ping -ge 0) {
            $statusColor = if ($ping -lt 50) { "Green" } elseif ($ping -lt 150) { "Yellow" } else { "Red" }
            Write-Host " [OK] " -ForegroundColor Black -BackgroundColor Green -NoNewline
            Write-Host " PING: " -ForegroundColor Gray -NoNewline
            Write-Host "$ping ms".PadRight(8) -ForegroundColor $statusColor -NoNewline
            
            $speed = if ($ping -lt 10) { ">>> MUKEMMEL" } elseif ($ping -lt 30) { ">> YUKSEK   " } elseif ($ping -lt 80) { "> ORTA      " } else { "- DUSUK     " }
            Write-Host " | HIZ: $speed" -ForegroundColor Cyan -NoNewline
        }
        else {
            Write-Host " [!!] " -ForegroundColor White -BackgroundColor Red -NoNewline
            Write-Host " BAGLANTI YOK (TIMEOUT)               " -ForegroundColor Red -NoNewline
        }
        
        Write-Host " | " -NoNewline -ForegroundColor DarkGray
        $graph = Draw-Graph $PingHistory
        
        if ($ping -lt 0) {
            Write-Host $graph -ForegroundColor Red
        }
        elseif ($ping -lt 50) {
            Write-Host $graph -ForegroundColor Green
        }
        elseif ($ping -lt 150) {
            Write-Host $graph -ForegroundColor Yellow
        }
        else {
            Write-Host $graph -ForegroundColor DarkYellow
        }
        
        $failCount = 0
        for ($i = $HistorySize - 3; $i -lt $HistorySize; $i++) {
            if ($PingHistory[$i] -lt 0) { $failCount++ }
        }
        
        if ($failCount -eq 3) {
            Connect-Wifi
            
            for ($i = 0; $i -lt $HistorySize; $i++) {
                $PingHistory[$i] = 10
            }
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
            Write-Host "                                                            "
            Write-Host "                                                            "
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
        }

        Start-Sleep -Milliseconds $CheckIntervalMs
    }
}
finally {
    [Console]::CursorVisible = $true
    Write-Host "`nMonitor durduruldu." -ForegroundColor Gray
}
