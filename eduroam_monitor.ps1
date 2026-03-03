<#
.SYNOPSIS
    Hayatin Ritmi - Eduroam Auto-Reconnect & Network Monitor
.DESCRIPTION
    Bu script her 0.5 saniyede bir bagli oldugunuz "eduroam" aginin baglantisini kontrol eder.
    Fancy bir arayuzle (cesitli renkler ve animasyonlar) anlik durumu, pingi ve tahmini hizi gosterir.
    Eger baglanti duserse veya ping alinamassa otomatik olarak yeniden "eduroam" SSID'sine baglanma (netsh) komutu gonderir.
#>

$NetworkName = "eduroam"
$TargetHost = "8.8.8.8"      # Ping atacagimiz hedef (Google DNS)
$CheckIntervalMs = 500       # 0.5 saniye
$HistorySize = 40            # Ekranda kac adetlik bir bar grafigi cizelim
$PingHistory = New-Object int[] $HistorySize

# Konsol ayarlarini hazirlayalim
$Console = $Host.UI.RawUI
$Console.WindowTitle = "Eduroam Auto-Reconnect - Hayatin Ritmi"
Clear-Host
[Console]::CursorVisible = $false

# Cizim karakterleri
$BlockFull = "█"
$BlockHigh = "▆"
$BlockMid  = "▄"
$BlockLow  = "▂"
$BlockZero = " "

function Get-PingTime {
    # 1 adet ping paketini hizlica yolla (-n 1) ve timeout'u 400ms ver (-w 400)
    $pingResult = Test-Connection -ComputerName $TargetHost -Count 1 -Quiet -BufferSize 32
    if ($pingResult) {
        # Normal Test-Connection 'Quiet' yalnizca True/False doner PowerShell 5.1'de, 
        # O yuzden detayli obje icin -Quiet kaldirip ResponseTime'i alalim.
        try {
            $p = Test-Connection -ComputerName $TargetHost -Count 1 -ErrorAction SilentlyContinue
            if ($p.ResponseTime -ge 0) {
                return $p.ResponseTime
            }
        } catch { }
    }
    return -1 # Timeout veya baglanti yok
}

function Connect-Wifi {
    Write-Host "`n[!]" -ForegroundColor Red -NoNewline
    Write-Host " BAGLANTI KOPTU! " -ForegroundColor Yellow -BackgroundColor Red -NoNewline
    Write-Host " $NetworkName agina yeniden baglaniliyor..." -ForegroundColor Gray
    
    # Mevcut baglantiyi kesip hemen yeniden baslatiyoruz
    netsh wlan disconnect > $null
    Start-Sleep -Milliseconds 500
    netsh wlan connect name=$NetworkName > $null
    
    # Baglanmasi icin kisa bir sure taniyalim
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
            $graphString += "X" # Baglanti yok
        } elseif ($val -eq 0) {
            $graphString += $BlockLow
        } elseif ($val -lt 20) {
            $graphString += $BlockFull
        } elseif ($val -lt 50) {
            $graphString += $BlockHigh
        } elseif ($val -lt 150) {
            $graphString += $BlockMid
        } else {
            $graphString += $BlockLow
        }
    }
    return $graphString
}

# -------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------
try {
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           EDUROAM AUTO-CONNECT & NETWORK MONITOR             ║" -ForegroundColor Cyan
    Write-Host "║           Hedef Ag: " -ForegroundColor Cyan -NoNewline
    Write-Host "$NetworkName".PadRight(40) -ForegroundColor Yellow -NoNewline
    Write-Host " ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    $loopCount = 0
    $yPos = $Console.CursorPosition.Y
    
    while ($true) {
        $loopCount++
        $ping = Get-PingTime
        
        # Ping gecmisini kaydir
        for ($i = 0; $i -lt ($HistorySize - 1); $i++) {
            $PingHistory[$i] = $PingHistory[$i+1]
        }
        $PingHistory[$HistorySize - 1] = $ping
        
        # Imleci sabit yere alalim (sayfayi asagi kaydirmamak icin)
        if ($Console.CursorPosition.Y -gt $yPos + 5) {
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
        }
        
        # Ekranin o bolumunu temizlemek icin bosluk basalim (trick)
        Write-Host "".PadRight(60) -NoNewline "`r"
        
        if ($ping -ge 0) {
            $statusColor = if ($ping -lt 50) { "Green" } elseif ($ping -lt 150) { "Yellow" } else { "Red" }
            Write-Host " [OK] " -ForegroundColor Black -BackgroundColor Green -NoNewline
            Write-Host " `PING: " -ForegroundColor Gray -NoNewline
            Write-Host "$ping ms".PadRight(8) -ForegroundColor $statusColor -NoNewline
            
            # Tahmini Hiz Modeli (Ping'e gore afaki bir bandwidth gostergesi)
            $speed = if ($ping -lt 10) { ">>> MUKEMMEL" } elseif ($ping -lt 30) { ">> YUKSEK   " } elseif ($ping -lt 80) { "> ORTA      " } else { "- DUSUK     " }
            Write-Host " | HIZ: $speed" -ForegroundColor Cyan -NoNewline
            
        } else {
            Write-Host " [!!] " -ForegroundColor White -BackgroundColor Red -NoNewline
            Write-Host " BAGLANTI YOK (TIMEOUT)               " -ForegroundColor Red -NoNewline
        }
        
        Write-Host " | " -NoNewline -ForegroundColor DarkGray
        $graph = Draw-Graph $PingHistory
        
        # Grafigin rengini belirle (Son ping'e gore)
        if ($ping -lt 0) {
            Write-Host $graph -ForegroundColor Red
        } elseif ($ping -lt 50) {
            Write-Host $graph -ForegroundColor Green
        } elseif ($ping -lt 150) {
            Write-Host $graph -ForegroundColor Yellow
        } else {
            Write-Host $graph -ForegroundColor DarkYellow
        }
        
        # Eger ard arda ping alamadiysak agdan dusmusuzdur, tetikle.
        # Son 3 ping de -1 ise mudahale edelim
        $failCount = 0
        for ($i = $HistorySize - 3; $i -lt $HistorySize; $i++) {
            if ($PingHistory[$i] -lt 0) { $failCount++ }
        }
        
        if ($failCount -eq 3) {
            Connect-Wifi
            
            # Yeniden baglanma komutundan sonra cizimleri sifirlayalim ki hemen tekrar baglanmaya calismasin
            for ($i = 0; $i -lt $HistorySize; $i++) {
                $PingHistory[$i] = 10 # dummy deger
            }
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
            Write-Host "".PadRight(60," ")
            Write-Host "".PadRight(60," ")
            $Console.CursorPosition = New-Object System.Management.Automation.Host.Coordinates(0, $yPos)
        }

        Start-Sleep -Milliseconds $CheckIntervalMs
    }
}
finally {
    # Script durduruldugunda bazi temizlik islemleri
    [Console]::CursorVisible = $true
    Write-Host "`n`nMonitor durduruldu." -ForegroundColor Gray
}
