# Deploy agora – 3 passos

Tudo já está pronto no projeto. Só falta você fazer **3 coisas** (a primeira é única vez no PC).

---

## Usar Git Bash (não o PowerShell)

Se no **PowerShell** aparecer *"git não é reconhecido"*, use o **Git Bash** (menu Iniciar → Git Bash). No Git Bash o comando `git` funciona.

No Git Bash, entre na pasta do projeto:
```bash
cd /c/Users/marti/Desktop/FortCordis_Novo
```

Depois use os comandos desta página (git add, commit, remote, push).

---

## Passo 0 – Só uma vez: configurar o Git

Abra o **PowerShell** na pasta do projeto e rode (troque pelo seu e-mail e nome):

```powershell
git config --global user.email "seu@email.com"
git config --global user.name "Seu Nome"
```

---

## Passo 1 – Subir o código no GitHub

1. **Crie o repositório no GitHub**
   - Acesse: **https://github.com/new**
   - Nome do repositório: `fortcordis-app` (ou outro)
   - Deixe **público**, **sem** README, .gitignore ou licença
   - Clique em **Create repository**

2. **No PowerShell**, na pasta do projeto (`FortCordis_Novo`), rode o script:

   ```powershell
   .\fazer_deploy.ps1
   ```

   O script vai:
   - Adicionar os arquivos e fazer o commit
   - Se ainda não tiver `origin`, mostrar os comandos para conectar ao GitHub
   - Abrir o site do Streamlit Community Cloud no navegador

3. **Se o script pedir**, rode (troque `SEU_USUARIO` pelo seu usuário do GitHub e `fortcordis-app` pelo nome do repo):

   ```bash
   git remote add origin https://github.com/SEU_USUARIO/fortcordis-app.git
   git branch -M main
   git push -u origin main
   ```

   **Importante:** troque `SEU_USUARIO` pelo seu **usuário do GitHub** (sem espaços). Ex.: se sua página é `github.com/MartinianoBarros`, use `MartinianoBarros` na URL.

   Se pedir usuário/senha, use um **Personal Access Token** do GitHub (Settings → Developer settings → Personal access tokens) em vez da senha.

---

## Passo 2 – Deploy no Streamlit Community Cloud

1. O script já deve ter aberto **https://share.streamlit.io**. Se não, abra esse link.
2. Faça **login com a sua conta do GitHub**.
3. Clique em **“Create app”**.
4. Escolha **“Yup, I have an app”**.
5. Preencha:
   - **Repository:** `SEU_USUARIO/fortcordis-app`
   - **Branch:** `main`
   - **Main file path:** `fortcordis_app.py`
6. (Opcional) Em **App URL**, coloque algo como: `fortcordis`.
7. Clique em **“Deploy”**.

Aguarde alguns minutos. O app ficará em:  
**https://fortcordis.streamlit.app** (ou a URL que aparecer no painel).

---

## Se o app passar do limite de memória (resource limits)

Para **reduzir consumo e voltar a trabalhar rápido**:

1. **Commit e push** das alterações (o código já está otimizado: importação em lotes, caches limitados, marca d'água só ao gerar PDF).
2. No **Streamlit Community Cloud** (share.streamlit.io) → seu app → **⋮ (menu)** → **Reboot app**. Isso limpa a memória e sobe o código novo.
3. Se o backup for grande, use **backup em partes** (ver `COMO_GERAR_BACKUP.md`): execute `python exportar_backup_partes.py` no PC e importe os arquivos na ordem indicada.

---

## Resumo

| O que                | Onde / Como |
|----------------------|-------------|
| Configurar Git       | Uma vez: `git config --global user.email` e `user.name` |
| Subir código         | `.\fazer_deploy.ps1` + `git remote add` + `git push` |
| Publicar o app       | share.streamlit.io → Create app → seu repo → Deploy |

Se der erro no `git push`, confira se o repositório foi criado no GitHub e se o nome do usuário/repo está certo no `git remote add origin`.
