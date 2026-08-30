Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-EnvOrDefault {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $false)][string]$Default = ""
    )

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($value)) {
        return $Default
    }

    return $value
}

function Get-ImageRef {
    param(
        [Parameter(Mandatory = $true)][string]$Image,
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $false)][string]$Registry = ""
    )

    if (-not [string]::IsNullOrEmpty($Registry)) {
        return "${Registry}/${Image}:${Version}"
    }

    return "${Image}:${Version}"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

$Registry = Get-EnvOrDefault "REGISTRY"
$BaseRegistry = Get-EnvOrDefault "BASE_REGISTRY" "docker.io"
$Platform = Get-EnvOrDefault "PLATFORM" "linux/amd64"
$BackendImage = Get-EnvOrDefault "BACKEND_IMAGE" "stock-calculator-backend"
$FrontendImage = Get-EnvOrDefault "FRONTEND_IMAGE" "stock-calculator-frontend"
$NoCache = Get-EnvOrDefault "NO_CACHE"

$BackendVersion = Get-EnvOrDefault "BACKEND_VERSION"
if ([string]::IsNullOrEmpty($BackendVersion)) {
    $BackendVersion = & node scripts/read-version.mjs backend
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read backend version."
    }
}

$FrontendVersion = Get-EnvOrDefault "FRONTEND_VERSION"
if ([string]::IsNullOrEmpty($FrontendVersion)) {
    $FrontendVersion = & node scripts/read-version.mjs frontend
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read frontend version."
    }
}

$ImageTag = Get-EnvOrDefault "IMAGE_TAG"
if (-not [string]::IsNullOrEmpty($ImageTag)) {
    $BackendVersion = $ImageTag
    $FrontendVersion = $ImageTag
}

$BackendRef = Get-ImageRef -Image $BackendImage -Version $BackendVersion -Registry $Registry
$FrontendRef = Get-ImageRef -Image $FrontendImage -Version $FrontendVersion -Registry $Registry
$CacheArgs = @()
if (-not [string]::IsNullOrEmpty($NoCache)) {
    $CacheArgs = @("--no-cache", "--pull")
}

Write-Host "Building backend image: $BackendRef"
Invoke-Checked docker build `
    @CacheArgs `
    --platform $Platform `
    --build-arg "BASE_REGISTRY=$BaseRegistry" `
    -t $BackendRef `
    ./backend

Write-Host "Building frontend image: $FrontendRef"
Invoke-Checked docker build `
    @CacheArgs `
    --platform $Platform `
    --build-arg "BASE_REGISTRY=$BaseRegistry" `
    -t $FrontendRef `
    ./frontend

Write-Host "Done."
Write-Host "Backend:  $BackendRef"
Write-Host "Frontend: $FrontendRef"
