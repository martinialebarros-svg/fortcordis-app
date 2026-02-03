# FortCordis — Script para criar ponto de restauração (backup restaurável)
# Uso: .\criar_ponto_restauracao.ps1 [-Data "2026-02-02"] [-IncluirData]
# -Data: data no formato YYYY-MM-DD (padrão: hoje)
# -IncluirData: inclui pasta data/ (uploads, anexos, templates) se existir

param(
    [string]$Data = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$IncluirData
)

$ErrorActionPreference = "Stop"
$pastaProjeto = $PSScriptRoot
$nomePasta = "FORTCORDIS_RESTORE_POINT_$Data"
$destino = Join-Path $pastaProjeto $nomePasta

Write-Host "=== FortCordis: criando ponto de restauracao ===" -ForegroundColor Cyan
Write-Host "Data: $Data | Destino: $destino" -ForegroundColor Gray

# 1) Criar estrutura de pastas
New-Item -ItemType Directory -Force -Path (Join-Path $destino "db") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $destino "config") | Out-Null
if ($IncluirData) { New-Item -ItemType Directory -Force -Path (Join-Path $destino "data") | Out-Null }

# 2) Snapshot do código (git archive ou zip da pasta)
$zipCode = Join-Path $destino "code_snapshot.zip"
$gitDir = Join-Path $pastaProjeto ".git"
if (Test-Path $gitDir) {
    Push-Location $pastaProjeto
    try {
        git archive --format=zip --output=$zipCode HEAD
        if ($LASTEXITCODE -ne 0) { throw "git archive falhou" }
        Write-Host "OK: code_snapshot.zip (git archive)" -ForegroundColor Green
    } finally { Pop-Location }
} else {
    Write-Host "AVISO: pasta nao e um repositorio git. code_snapshot.zip nao foi gerado." -ForegroundColor Yellow
    Write-Host "  Rode: git archive --format=zip --output=$zipCode HEAD" -ForegroundColor Gray
    Write-Host "  Ou compacte manualmente a pasta do projeto (sem .git, venv, *.db, *.sqlite)." -ForegroundColor Gray
}

# 3) Backup do banco (localizar e copiar com timestamp)
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$bancos = Get-ChildItem -Path $pastaProjeto -Include "fortcordis.db","*.sqlite","*.sqlite3" -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*FORTCORDIS_RESTORE_POINT_*" -and $_.FullName -notlike "*\.git\*" }
$bancoPrincipal = $bancos | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($bancoPrincipal) {
    $nomeDb = "fortcordis_prod_${Data}_${timestamp}.sqlite"
    Copy-Item $bancoPrincipal.FullName (Join-Path $destino "db" $nomeDb)
    Write-Host "OK: db/$nomeDb" -ForegroundColor Green
} else {
    Write-Host "AVISO: Nenhum banco fortcordis.db/*.sqlite encontrado na pasta do projeto." -ForegroundColor Yellow
}

# 4) Config
Copy-Item (Join-Path $pastaProjeto ".streamlit\config.toml") (Join-Path $destino "config\config.toml") -Force
Copy-Item (Join-Path $pastaProjeto ".streamlit\secrets.template.toml") (Join-Path $destino "config\secrets.template.toml") -Force
Write-Host "OK: config/config.toml e config/secrets.template.toml" -ForegroundColor Green

# 5) Instruções de restauração
Copy-Item (Join-Path $pastaProjeto "RESTORE_INSTRUCTIONS.txt") (Join-Path $destino "RESTORE_INSTRUCTIONS.txt") -Force
Write-Host "OK: RESTORE_INSTRUCTIONS.txt" -ForegroundColor Green

# 6) Pastas de dados (opcional)
if ($IncluirData) {
    foreach ($sub in @("uploads","anexos","templates","assets","static","data")) {
        $origem = Join-Path $pastaProjeto $sub
        if (Test-Path $origem) {
            Copy-Item -Path $origem -Destination (Join-Path $destino "data" $sub) -Recurse -Force
            Write-Host "OK: data/$sub" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "Ponto de restauracao criado: $destino" -ForegroundColor Cyan
Write-Host "Proximos passos: teste a restauracao em outra pasta antes de confiar neste backup." -ForegroundColor Gray
