# Fort Cordis - Script para preparar e publicar o deploy no Streamlit Community Cloud
# Execute no PowerShell: .\fazer_deploy.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fort Cordis - Deploy no Streamlit Cloud" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Adicionar arquivos (respeitando .gitignore)
Write-Host "[1/4] Adicionando arquivos ao Git..." -ForegroundColor Yellow
git add -A
$status = git status --short
if (-not $status) {
    Write-Host "      Nenhuma alteracao para commitar (tudo ja commitado)." -ForegroundColor Gray
} else {
    Write-Host "[2/4] Criando commit..." -ForegroundColor Yellow
    git commit -m "Deploy Fort Cordis - Streamlit Community Cloud"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "      Commit criado." -ForegroundColor Green
}

# 2. Verificar se tem remote
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host ""
    Write-Host "[3/4] Repositorio GitHub ainda nao conectado." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Faca o seguinte:" -ForegroundColor White
    Write-Host "  1. Abra: https://github.com/new" -ForegroundColor White
    Write-Host "  2. Nome do repositorio: fortcordis-app (ou outro)" -ForegroundColor White
    Write-Host "  3. Publico, sem README. Clique em Create repository." -ForegroundColor White
    Write-Host "  4. No PowerShell, execute (troque SEU_USUARIO pelo seu usuario GitHub):" -ForegroundColor White
    Write-Host ""
    Write-Host '     git remote add origin https://github.com/SEU_USUARIO/fortcordis-app.git' -ForegroundColor Cyan
    Write-Host '     git branch -M main' -ForegroundColor Cyan
    Write-Host '     git push -u origin main' -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[3/4] Remote encontrado: $remote" -ForegroundColor Green
    Write-Host "      Enviando para GitHub..." -ForegroundColor Yellow
    git branch -M main 2>$null
    git push -u origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      Erro no push. Confirme que o repo existe no GitHub e que voce fez login (git push)." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "      Push concluido." -ForegroundColor Green
}

Write-Host ""
Write-Host "[4/4] Abrindo Streamlit Community Cloud no navegador..." -ForegroundColor Yellow
Start-Process "https://share.streamlit.io"
Write-Host ""
Write-Host "  No site:" -ForegroundColor White
Write-Host "  1. Faca login com GitHub (se ainda nao estiver)." -ForegroundColor White
Write-Host "  2. Clique em 'Create app'." -ForegroundColor White
Write-Host "  3. Escolha 'Yup, I have an app'." -ForegroundColor White
Write-Host "  4. Repository: seu-usuario/fortcordis-app" -ForegroundColor White
Write-Host "  5. Branch: main" -ForegroundColor White
Write-Host "  6. Main file path: fortcordis_app.py" -ForegroundColor White
Write-Host "  7. (Opcional) App URL: fortcordis" -ForegroundColor White
Write-Host "  8. Clique em 'Deploy'." -ForegroundColor White
Write-Host ""
Write-Host "Pronto. Aguarde alguns minutos e seu app estara no ar." -ForegroundColor Green
Write-Host ""
