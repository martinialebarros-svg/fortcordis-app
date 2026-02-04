# Snapshot do Sistema – Fort Cordis

**Data do snapshot:** 02/02/2026

Documento de referência do estado atual do projeto (estrutura, módulos, deploy e funcionalidades principais).

---

## 1. Visão geral

- **Aplicação:** Fort Cordis – sistema integrado de gestão para cardiologia veterinária (Streamlit).
- **Entrada:** `fortcordis_app.py` (Streamlit).
- **Banco:** SQLite (`fortcordis.db` na raiz do projeto).
- **Deploy:** Streamlit Community Cloud (GitHub → push → redeploy automático).

---

## 2. Estrutura de pastas (principais)

```
FortCordis_Novo/
├── fortcordis_app.py          # App principal (entrada Streamlit)
├── app/
│   ├── config.py              # VERSAO_DEPLOY, DB_PATH, PASTA_DB, CSS_GLOBAL
│   ├── db.py                  # Conexão e upserts (clínica, tutor, paciente)
│   ├── utils.py               # Utilitários (nome_proprio_ptbr, _norm_key, _clean_spaces)
│   ├── laudos_helpers.py      # Frases, schema det, listar/obter laudos do banco
│   ├── laudos_refs.py         # PARAMS, tabelas referência caninos/felinos, interpretar (Fase B)
│   ├── ESTRUTURA_MODULOS.md   # Detalhes da modularização
│   └── pages/
│       ├── dashboard.py       # render_dashboard()
│       ├── agendamentos.py    # render_agendamentos()
│       ├── laudos.py          # render_laudos(deps) — 8 abas Laudos e Exames
│       ├── prontuario.py      # render_prontuario()
│       ├── prescricoes.py     # render_prescricoes()
│       ├── financeiro.py      # render_financeiro()
│       ├── cadastros.py       # render_cadastros()
│       └── configuracoes.py   # render_configuracoes() — 7 abas
├── modules/
│   ├── auth.py                # Autenticação
│   └── rbac.py                # Permissões (verificar_permissao)
├── fortcordis_modules/
│   ├── database.py            # Inicialização e funções de banco (OS, cobrança, etc.)
│   ├── documentos.py
│   └── integrations.py
├── .streamlit/
│   ├── config.toml
│   └── secrets.template.toml
├── requirements.txt
├── fazer_deploy.sh            # Deploy: git add, commit, push
├── fazer_deploy.ps1
├── criar_ponto_restauracao.ps1
├── COMO_GERAR_BACKUP.md
├── RESTORE_INSTRUCTIONS.txt
└── SNAPSHOT_SISTEMA.md        # Este arquivo
```

Scripts auxiliares (migrações, correções, importação de laudos, etc.) ficam na raiz; não são necessários para rodar o app.

---

## 3. Menu principal e módulos

| Menu                    | Onde está                          | Observação |
|-------------------------|------------------------------------|------------|
| 🏠 Dashboard            | `app.pages.dashboard`              | `render_dashboard()` |
| 📅 Agendamentos         | `app.pages.agendamentos`           | `render_agendamentos()` |
| 📋 Prontuário           | `app.pages.prontuario`             | `render_prontuario()` |
| 🩺 Laudos e Exames      | `app.pages.laudos`                 | `render_laudos(laudos_deps)` |
| 💊 Prescrições          | `app.pages.prescricoes`            | `render_prescricoes()` |
| 💰 Financeiro           | `app.pages.financeiro`             | `render_financeiro()` |
| 🏢 Cadastros            | `app.pages.cadastros`              | `render_cadastros()` |
| ⚙️ Configurações        | `app.pages.configuracoes`          | `render_configuracoes()` |

Laudos usa `app.laudos_helpers` para frases, schema e listagem de laudos no banco; o restante (PARAMS, referências, PDF, etc.) vem do app principal via `laudos_deps`.

---

## 4. Configuração (app.config)

- **VERSAO_DEPLOY:** `2026-02-01`
- **DB_PATH:** `{raiz}/fortcordis.db`
- **PASTA_DB:** raiz do projeto
- **CSS_GLOBAL:** estilos aplicados ao Streamlit

Paths de laudos estão em `app.config`; referências (PARAMS, interpretar, tabelas caninos/felinos) estão em `app.laudos_refs`; o app repassa para Laudos via `laudos_deps`.

---

## 5. Banco de dados

- **Arquivo:** `fortcordis.db` (SQLite) na raiz.
- **Conexão:** `app.db` (`_db_conn`, `_db_init`) e uso direto em partes do `fortcordis_app.py` e em `fortcordis_modules.database`.
- Tabelas de laudos (ecocardiograma, eletro, pressão arterial), laudos_arquivos, clinicas_parceiras, pacientes, tutores, financeiro, agendamentos, etc.

---

## 6. Deploy

- **Script:** `bash fazer_deploy.sh` (Git Bash) ou comandos equivalentes no PowerShell.
- **Fluxo:** `git add -A` → `git commit` → `git push origin main` → Streamlit Cloud faz o redeploy.
- **Requisitos:** `requirements.txt` (streamlit, pandas, beautifulsoup4, lxml, fpdf2, Pillow, bcrypt, psutil).

---

## 7. Funcionalidades recentes (Laudos)

- **Página Laudos** extraída para `app/pages/laudos.py`; recebe `deps` do app principal (evita import circular e `StreamlitDuplicateElementId`).
- **PDF – Análise quantitativa:** na seção **"VE - Modo M"** do laudo ecocardiográfico, o PDF exibe apenas as colunas **Parâmetro** e **Valor**; Referência e Interpretação não aparecem nessa seção (continuam na aba Medidas da tela).

---

## 8. Como rodar localmente

```bash
streamlit run fortcordis_app.py
```

Git: configurar `user.name` e `user.email` se ainda não estiverem definidos.

---

## 9. Próximos passos (modularização e otimização)

- **Fase B (Laudos):** Mover a lógica de Laudos que ainda está no `fortcordis_app.py` (PARAMS, referências, PDF, frases, tabelas caninos/felinos, etc.) para módulos em `app/` (ex.: `app/laudos_refs.py`, `app/laudos_pdf.py`, ampliar `app/laudos_helpers.py`). Ver **SUGESTOES_OTIMIZACAO.md**.
- **Código duplicado:** Há funções definidas duas vezes no `fortcordis_app.py` (ex.: `frase_det`, `aplicar_frase_det_na_tela`); remover uma das cópias e centralizar em `app/`.
- Deixar o `fortcordis_app.py` apenas com: imports, set_page_config, CSS, auth, menu e chamadas `render_*()` (e `build_laudos_deps` até a Fase B estar concluída).

Ver também **GUIA_OTIMIZACAO.md** e **SUGESTOES_OTIMIZACAO.md** para prioridades e passos detalhados.

---

*Snapshot gerado para referência do estado do sistema em 02/02/2026.*
