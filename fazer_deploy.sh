#!/bin/bash
# Fort Cordis - Deploy (use no Git Bash: bash fazer_deploy.sh)

set -e
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  Fort Cordis - Deploy no Streamlit Cloud"
echo "========================================"
echo ""

# Git precisa de nome e email (só uma vez no PC)
if ! git config --global user.email &>/dev/null; then
    echo "Configure o Git (só uma vez):"
    echo '  git config --global user.email "seu@email.com"'
    echo '  git config --global user.name "Seu Nome"'
    echo ""
    echo "Depois execute: bash fazer_deploy.sh"
    exit 1
fi

echo "[1/4] Adicionando arquivos ao Git..."
git add -A
if [ -z "$(git status --short)" ]; then
    echo "      Nenhuma alteração para commitar (tudo já commitado)."
else
    echo "[2/4] Criando commit..."
    git commit -m "Deploy Fort Cordis - Streamlit Community Cloud"
    echo "      Commit criado."
fi

echo "[3/4] Verificando remote..."
if ! git remote get-url origin &>/dev/null; then
    echo ""
    echo "Repositório GitHub ainda não conectado."
    echo ""
    echo "  1. Crie o repo em: https://github.com/new (ex.: fortcordis-app)"
    echo "  2. Depois rode (troque SEU_USUARIO pelo seu usuário GitHub):"
    echo ""
    echo '     git remote add origin https://github.com/SEU_USUARIO/fortcordis-app.git'
    echo '     git branch -M main'
    echo '     git push -u origin main'
    echo ""
    exit 0
fi

git branch -M main 2>/dev/null || true
echo "      Enviando para GitHub..."
if ! git push -u origin main; then
    echo "      Erro no push. Confira o repo no GitHub e o login."
    exit 1
fi
echo "      Push concluído."

echo ""
echo "[4/4] Pronto. Abra https://share.streamlit.io para redeploy (ou aguarde o automático)."
echo ""
