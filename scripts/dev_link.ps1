param([string]$Profile = "copilot-dev")

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repoRoot "geoutility_copilot"
$pluginsDir = Join-Path $env:APPDATA "QGIS\QGIS3\profiles\$Profile\python\plugins"
$target = Join-Path $pluginsDir "geoutility_copilot"

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Plugin package not found: $source"
}

New-Item -ItemType Directory -Force -Path $pluginsDir | Out-Null

if (Test-Path -LiteralPath $target) {
    $existing = Get-Item -LiteralPath $target
    if ($existing.LinkType -eq "Junction" -and $existing.Target -contains $source) {
        Write-Host "Development link already exists: $target"
        exit 0
    }
    throw "Target already exists and is not this repository's junction: $target"
}

New-Item -ItemType Junction -Path $target -Target $source | Out-Null
Write-Host "Linked $target -> $source"
