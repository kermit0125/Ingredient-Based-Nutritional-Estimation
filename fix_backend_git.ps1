# Run from repo root once if GitHub shows no backend/ code:
#   powershell -ExecutionPolicy Bypass -File .\fix_backend_git.ps1
# Cause: accidental `git init` inside backend/ creates backend/.git and the parent repo ignores those files.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$nested = Join-Path $root "backend\.git"
if (Test-Path $nested) {
    Remove-Item -LiteralPath $nested -Recurse -Force
    Write-Host "Removed nested repository: backend\.git"
} else {
    Write-Host "No nested backend\.git found (ok)."
}

git add backend/configs backend/scripts backend/requirements.txt backend/README.md backend/data/README.md backend/data/DATA_SOURCES.md
git add .gitignore README.md Documents fix_backend_git.ps1 2>$null
git status

Write-Host ""
Write-Host "Next: git commit -m ""Add backend to main repo"" && git push origin main"
