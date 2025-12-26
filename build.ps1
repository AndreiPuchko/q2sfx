# -----------------------------
# 1. check git-status
# -----------------------------

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Error "❌ The working directory is not clean! Commit or revert the changes:"
    git status -s
    exit 1
}

Write-Host "✅ Git working tree clean" -ForegroundColor Green

# -----------------------------
# bump project version
# -----------------------------

poetry version patch

# -----------------------------
# read pyproject.toml and write version.py
# -----------------------------

$ProjectName = Split-Path (Get-Location) -Leaf
Write-Host "=== $ProjectName build & release ===" -ForegroundColor DarkYellow

$versionFile = "pyproject.toml"
$content = Get-Content $versionFile

$versionLine = $content | Where-Object { $_ -match '^version\s*=' }
if (-not $versionLine) {
    Write-Error "❌ version not found in pyproject.toml"
    exit 1
}

$newVersion = ($versionLine -split '"')[1]
Write-Host "Current version: $newVersion"

$versionPyPath = "$ProjectName/version.py"
$versionPyContent = "__version__ = ""$newVersion"""
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($versionPyPath, $versionPyContent, $utf8NoBom)

Write-Host "$versionPyPath generated: $versionPyPath"


# commit new version files
# exit 0
git add pyproject.toml $VersionPyPath
git commit -m "chore: bump version to v$newVersion"

# -----------------------------
# 7. Build
# -----------------------------

if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

# --- 2. Build & Publish to PyPI ---
poetry build
# poetry publish

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Build failed"
    exit 1
}

# -----------------------------
# 8. make latest-wheel
# -----------------------------

$wheel = Get-ChildItem dist\*-py3-none-any.whl | Select-Object -First 1

Copy-Item $ProjectName\version.py dist\version.py -Force
$latestFilePath = "dist\latest"
Set-Content -Path $latestFilePath -Value $wheel.Name -Encoding UTF8


# -----------------------------
# 9. Git tag
# -----------------------------

$tag = "v$newVersion"

git tag $tag
git push
git push origin $tag

# -----------------------------
# 10. Generate Release Notes
# -----------------------------

$previousTag = git describe --tags --abbrev=0 $tag~1 2>$null

if ($LASTEXITCODE -eq 0 -and $previousTag) {
    $commits = git log $previousTag..HEAD --pretty=format:"%s"
} else {
    $commits = git log --pretty=format:"%s"
}

$added = @()
$fixed = @()
$changed = @()
$others = @()

foreach ($c in $commits) {
    if ($c -match "^feat") { $added += "- $c" }
    elseif ($c -match "^fix") { $fixed += "- $c" }
    elseif ($c -match "^refactor|^chore") { $changed += "- $c" }
    else { $others += "- $c" }
}

$releaseNotes = "## Release v$newVersion`n`n"
if ($added.Count -gt 0)   { $releaseNotes += "### Added`n"   + ($added -join "`n")   + "`n`n" }
if ($fixed.Count -gt 0)   { $releaseNotes += "### Fixed`n"   + ($fixed -join "`n")   + "`n`n" }
if ($changed.Count -gt 0) { $releaseNotes += "### Changed`n" + ($changed -join "`n") + "`n`n" }
if ($others.Count -gt 0)  { $releaseNotes += "### Other`n"   + ($others -join "`n")  + "`n`n" }

# -----------------------------
# 11. Collect ALL latest dist assets ✅
# -----------------------------

$assets = Get-ChildItem dist -File | ForEach-Object { $_.FullName }

if ($assets.Count -eq 0) {
    Write-Error "❌ No files found in dist/ for release!"
    exit 1
}

Write-Host "✅ Release assets:"
$assets | ForEach-Object { Write-Host " - $_" }

# -----------------------------
# 12. Create GitHub Release via gh ✅
# -----------------------------

$ghExists = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghExists) {
    Write-Host "ERROR: GitHub CLI (gh) is not installed. Skipping GitHub Release."
    Write-Host "Install with: winget install --id GitHub.cli"
    exit 0
}

# ✅ Properly check if release already exists
$releaseExists = gh release view $tag 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ GitHub Release $tag already exists. Skipping creation."
} else {
    Write-Host "🚀 Creating GitHub Release $tag ..."

    gh release create $tag $assets `
        --title "v$newVersion" `
        --notes "$releaseNotes"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ GitHub Release $tag successfully created."
    } else {
        Write-Host "❌ ERROR: Failed to create GitHub Release."
    }
}