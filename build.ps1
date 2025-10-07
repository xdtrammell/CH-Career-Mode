param([switch]$Clean)

$ErrorActionPreference = "Stop"
cd $PSScriptRoot

# Ensure virtual environment
if (!(Test-Path .\.venv\Scripts\Activate.ps1)) {
    py -3 -m venv .venv
}

# Activate venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
if (Test-Path ".\requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt..."
    pip install -U pip
    pip install -r requirements.txt
} else {
    Write-Host "requirements.txt not found, skipping dependency install"
}

# Clean old build artifacts if requested
if ($Clean) {
    Write-Host ""
    Write-Host "Performing clean build..."

    # Backup most recent EXE before wiping dist
    $distDir = Join-Path $PSScriptRoot "dist"
    if (Test-Path $distDir) {
        $allExes = Get-ChildItem $distDir -Filter "CH_Career_Builder_v*.exe" -ErrorAction SilentlyContinue
        if ($allExes.Count -gt 0) {
            $latestExe = $allExes | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            Write-Host ("Keeping backup: {0}" -f $latestExe.Name)
            $backupDir = Join-Path $PSScriptRoot "backup_builds"
            if (!(Test-Path $backupDir)) {
                New-Item -ItemType Directory -Path $backupDir | Out-Null
            }
            Copy-Item $latestExe.FullName -Destination $backupDir -Force
        }
    }

    # Remove everything else
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    Remove-Item *.spec -ErrorAction SilentlyContinue
}

# Ensure dist exists after cleaning
$distDir = Join-Path $PSScriptRoot "dist"
if (!(Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

# Auto-increment version
$existing = Get-ChildItem $distDir -Filter "CH_Career_Builder_v*.exe" -ErrorAction SilentlyContinue
$nextVersion = "0.17" # default next version after v0_16

if ($existing) {
    $versions = $existing | ForEach-Object {
        if ($_ -match "CH_Career_Builder_v(\d+)_(\d+).exe") {
            return ("{0}.{1}" -f $Matches[1], $Matches[2])
        }
    }

    if ($versions) {
        $max = ($versions | Sort-Object {[version]$_} | Select-Object -Last 1)
        $parts = $max.Split(".")
        $major = [int]$parts[0]
        $minor = [int]$parts[1] + 1
        if ($minor -ge 100) {
            $major++
            $minor = 0
        }
        $nextVersion = ("{0}.{1}" -f $major, $minor)
    }
}

$exeName = ("CH_Career_Builder_v{0}" -f ($nextVersion -replace '\.','_'))

Write-Host ""
Write-Host ("Building version {0} ..." -f $nextVersion)
Write-Host ""

# Run PyInstaller
pyinstaller --clean --noconfirm -w -F app_entry.py `
    --name $exeName `
    --hidden-import mido

Write-Host ""
Write-Host "Build complete!"
Write-Host ("Output: dist\\{0}.exe" -f $exeName)
