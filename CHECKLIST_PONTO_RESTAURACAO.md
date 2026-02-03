# Checklist — Ponto de Restauração FortCordis

Implementação conforme o plano de backup/migração (2026-02-02). Use este checklist para criar e validar o ponto de restauração.

---

## O que já foi implementado no código

- **.gitignore** atualizado: `*.sqlite`, `*.sqlite3`, `backup_*.sqlite`, `FORTCORDIS_RESTORE_POINT_*/`, `fortcordis_code_restore_*.zip`
- **.streamlit/secrets.template.toml** — modelo de secrets (sem credenciais)
- **RESTORE_INSTRUCTIONS.txt** — instruções de restauração
- **criar_ponto_restauracao.ps1** — script que monta o pacote (código ZIP, DB, config, instruções)
- **Admin inicial** — senha não é mais hardcoded; use variável de ambiente `ADMIN_INITIAL_PASSWORD` ou crie o primeiro usuário pela tela de login
- **fortcordis_modules/database.py** — função `get_conn()` com `foreign_keys=ON`, `journal_mode=WAL` e timeout 15s

---

## Passos manuais (você faz no terminal)

### 1) Remover backup de banco do repositório (se já foi commitado)

Se `backup_fortcordis_20260201_1136.sqlite` (ou outro `.sqlite`/`.db`) já estiver no Git:

```powershell
git rm --cached backup_fortcordis_20260201_1136.sqlite
# ou, para qualquer backup: git rm --cached "backup_*"
```

O arquivo continua no disco, mas deixa de ser versionado. Faça commit depois.

### 2) Commit do estado funcional

```powershell
git status
git add -A
git commit -m "restore point: estado funcional antes da migracao"
```

### 3) TAG (ponto de restauração do código)

```powershell
git tag -a restore-2026-02-02-cloud-ok -m "Ponto de restauracao funcional"
git push origin main
git push --tags
```

### 4) ZIP do código (opcional; o script também gera)

```powershell
git archive --format=zip --output=fortcordis_code_restore_2026-02-02.zip HEAD
```

### 5) Criar o ponto de restauração (pacote completo)

Pare o app (se estiver rodando). Depois:

```powershell
.\criar_ponto_restauracao.ps1
```

Com data específica e incluindo pastas de dados (uploads/anexos/templates):

```powershell
.\criar_ponto_restauracao.ps1 -Data "2026-02-02" -IncluirData
```

Isso cria a pasta `FORTCORDIS_RESTORE_POINT_2026-02-02` com:

- `code_snapshot.zip`
- `db/fortcordis_prod_*.sqlite`
- `config/config.toml` e `config/secrets.template.toml`
- `RESTORE_INSTRUCTIONS.txt`
- (opcional) `data/` se usou `-IncluirData`

### 6) Teste de restauração (obrigatório)

- Copie a pasta do ponto de restauração para outro diretório (ou outra máquina).
- Siga o `RESTORE_INSTRUCTIONS.txt`: descompacte o código, coloque o banco como `fortcordis.db`, configure `.streamlit/`.
- Rode `streamlit run fortcordis_app.py` e confira: login, dados (agenda/financeiro/pacientes), geração de documentos.

### 7) Estratégia 3-2-1

- **3** cópias do pacote
- **2** locais diferentes (ex.: notebook + nuvem)
- **1** fora do ambiente (HD externo / pendrive)

---

## Primeira execução após as mudanças (admin)

- Se quiser que o sistema crie o admin automaticamente na primeira execução, defina a variável de ambiente antes de rodar o app ou o `python -m modules.auth`:

  ```powershell
  $env:ADMIN_INITIAL_PASSWORD = "SuaSenhaSeguraMin8Chars"
  streamlit run fortcordis_app.py
  ```

- Se não definir `ADMIN_INITIAL_PASSWORD`, use na tela de login a opção **"Criar primeiro usuário (administrador)"** para criar o admin.

Depois do primeiro login, **altere a senha imediatamente**.
