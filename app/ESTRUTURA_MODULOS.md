# Estrutura de Módulos do FortCordis

O `fortcordis_app.py` foi parcialmente quebrado em módulos. Esta pasta `app/` concentra config, banco e páginas.

## Estrutura atual

```
app/
  __init__.py
  config.py          # VERSAO_DEPLOY, DB_PATH, PASTA_DB, CSS_GLOBAL
  utils.py            # nome_proprio_ptbr, _norm_key, _clean_spaces (uso em db e laudos)
  db.py               # _db_conn_safe, _db_conn, _db_init, db_upsert_clinica/tutor/paciente
  laudos_helpers.py  # QUALI_DET, frases, listar/obter laudos do banco, schema det
  ESTRUTURA_MODULOS.md
  pages/
    __init__.py      # exporta render_dashboard, render_agendamentos, render_laudos
    dashboard.py     # render_dashboard()
    agendamentos.py  # render_agendamentos()
    laudos.py        # render_laudos() — Cadastro, Medidas, Qualitativa, Imagens, Frases, Referências, Buscar, Pressão Arterial
```

## O que já foi extraído

- **Config**: versão, caminho do banco e CSS vêm de `app.config`.
- **Banco local**: conexão segura e upserts de clínicas/tutores/pacientes em `app.db`; o `fortcordis_app.py` importa e usa.
- **Dashboard**: tela "🏠 Dashboard" está em `app.pages.dashboard`; o app chama `render_dashboard()`.
- **Agendamentos**: tela "📅 Agendamentos" está em `app.pages.agendamentos`; o app chama `render_agendamentos()`.
- **Laudos e Exames**: tela "🩺 Laudos e Exames" está em `app.pages.laudos`; o app chama `render_laudos()`. Helpers de frases/banco em `app.laudos_helpers`.

## O que ainda está no fortcordis_app.py

- Prontuário, Prescrições, Financeiro, Cadastros e Configurações continuam como blocos `elif menu_principal == ...` no arquivo principal.
- Funções de laudos usadas pela página (PARAMS, referências, PDF, tabelas, etc.) permanecem no `fortcordis_app.py` e são importadas via lazy import em `render_laudos()`.

## Próximos passos (quebrar mais)

1. **Prontuário**  
   Criar `app/pages/prontuario.py` com `render_prontuario()`, movendo o bloco correspondente e importando o que for necessário (por exemplo `verificar_permissao`, `DB_PATH`, funções de listagem de laudos se usadas).

2. **Laudos**  
   ✅ Feito: `app/laudos_helpers.py` (frases, schema, listar/obter laudos) e `app/pages/laudos.py` com `render_laudos()` (8 abas). O app chama `render_laudos()` quando o menu é Laudos e Exames.

3. **Prescrições, Financeiro, Cadastros, Configurações**  
   Seguir o mesmo padrão: novo arquivo em `app/pages/` com `render_*()` e movendo o bloco do menu do `fortcordis_app.py` para esse módulo.

4. **Enxugar o app principal**  
   Quando todas as telas estiverem em `app.pages`, o `fortcordis_app.py` deve ficar só com:
   - imports e `set_page_config`
   - CSS e botões de emergência
   - path e auth (login, `mostrar_info_usuario`)
   - menu na sidebar
   - sequência de `if menu_principal == ...: render_*()`.

## Como rodar

Nada muda para o usuário:

```bash
streamlit run fortcordis_app.py
```

O app continua funcionando; Dashboard e Agendamentos passam a ser renderizados pelos módulos em `app/pages/`.
