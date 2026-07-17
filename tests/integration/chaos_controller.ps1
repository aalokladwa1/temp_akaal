param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("kill-sut", "restart-pg-src", "restart-pg-tgt", "inject-latency", "clear-latency", "exhaust-disk", "clear-disk")]
    [string]$Action
)

# Configuration mapping values for target operations
$PG_SRC_SERVICE = "postgresql-x64-16"
$PG_TGT_SERVICE = "postgresql-x64-17"
$MOCK_DISK_FILE = "A:\temp_akaal\tests\integration\disk_saturation_pressure.tmp"

switch ($Action) {
    "kill-sut" {
        Write-Host "[!] Simulating SUT hard-kill crash event..." -ForegroundColor Red
        # Terminates any active execution layers associated with the migration binary
        Stop-Process -Name "akaal" -Force -ErrorAction SilentlyContinue
        Stop-Process -Name "akaal-engine" -Force -ErrorAction SilentlyContinue
        Write-Host "? SUT process spaces terminated." -ForegroundColor Green
    }
    
    "restart-pg-src" {
        Write-Host "[!] Crashing PostgreSQL 16 Source Instance..." -ForegroundColor Yellow
        Restart-Service -Name $PG_SRC_SERVICE -Force -Verbose
        Write-Host "? Source database engine cleanly recovered." -ForegroundColor Green
    }
    
    "restart-pg-tgt" {
        Write-Host "[!] Crashing PostgreSQL 17 Target Instance..." -ForegroundColor Yellow
        Restart-Service -Name $PG_TGT_SERVICE -Force -Verbose
        Write-Host "? Target database engine cleanly recovered." -ForegroundColor Green
    }
    
    "inject-latency" {
        Write-Host "[!] Simulating degraded network paths (introducing local interface latency rules)..." -ForegroundColor Yellow
        # Utilizes native Windows network isolation layers to throttle throughput
        New-NetQosPolicy -Name "AkaalThrottle" -IPProtocol MatchAny -IPSrcPortStart 5432 -IPSrcPortEnd 5433 -ThrottleRateActionBitsPerSecond 512KB -ErrorAction SilentlyContinue
        Write-Host "? Bandwidth constraints and artificial latency profile deployed." -ForegroundColor Green
    }
    
    "clear-latency" {
        Write-Host "[*] Restoring standard network bandwidth capacity rules..." -ForegroundColor Cyan
        Remove-NetQosPolicy -Name "AkaalThrottle" -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "? Network latency constraints cleared." -ForegroundColor Green
    }
    
    "exhaust-disk" {
        Write-Host "[!] Injecting extreme local storage drive volume saturation..." -ForegroundColor Red
        # Generates a fast 5GB sparse binary block to trigger immediate filesystem warning parameters
        $file = [System.IO.File]::Create($MOCK_DISK_FILE)
        $file.SetLength(5GB)
        $file.Close()
        Write-Host "? Disk storage limitation boundaries saturated." -ForegroundColor Green
    }
    
    "clear-disk" {
        Write-Host "[*] Releasing storage pressure constraints..." -ForegroundColor Cyan
        if (Test-Path $MOCK_DISK_FILE) {
            Remove-Item $MOCK_DISK_FILE -Force
            Write-Host "? Saturation file deleted. Local disk pool space recovered." -ForegroundColor Green
        } else {
            Write-Host "No active storage pressure files found." -ForegroundColor Gray
        }
    }
}
