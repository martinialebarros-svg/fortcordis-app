# Estrutura de Módulos do FortCordis

O `fortcordis_app.py` foi parcialmente quebrado em módulos. Esta pasta `app/` concentra config, banco e páginas.

## Estrutura atual

```
app/
  __init__.py
  config.py          # VERSAO_DEPLOY, DB_PATH, PASTA_DB, CSS_GLOBAL
  utils.py            # nome_proprio_ptbr, _norm_key, _clean_spaces (uso em db e laudos)
  db.py               # _db_conn_safe, _db_conn, _db_init, db_upsert_clinica/tutor/paciente/consultas
  laudos_helpers.py  # QUALI_DET, frases, listar/obter laudos do banco, schema det
  laudos_deps.py     # build_laudos_deps(**kwargs), LAUDOS_DEPS_KEYS — contrato da página Laudos (Fase B)
  menu.py             # MENU_ITEMS, get_menu_labels() — registro central do menu (Fase A otimização)
  services/           # Camada de serviços reutilizáveis (Fase C)
    __init__.py
    consultas.py      # listar_consultas_recentes, criar_consulta
    pacientes.py      # listar_pacientes_com_tutor, listar_pacientes_tabela, buscar_pacientes, atualizar_peso_paciente
  components/         # Componentes de UI reutilizáveis (Fase D)
    __init__.py
    tabelas.py        # tabela_tabular(df, caption, drop_colunas, empty_message)
    metricas.py       # metricas_linha(metricas)
  ESTRUTURA_MODULOS.md
  pages/
    __init__.py        # exporta render_dashboard, ..., render_cadastros, render_configuracoes
    dashboard.py       # render_dashboard()
    agendamentos.py    # render_agendamentos()
    laudos.py          # render_laudos(deps) — 8 abas Laudos e Exames
    prontuario.py      # render_prontuario()
    prescricoes.py     # render_prescricoes()
    financeiro.py      # render_financeiro()
    cadastros.py       # render_cadastros()
    configuracoes.py   # render_configuracoes() — 7 abas (permissões, usuários, papéis, sistema, importar, assinatura, diagnóstico)
```

## O que já foi extraído

- **Config**: versão, caminho do banco e CSS vêm de `app.config`.
- **Banco local**: conexão segura e upserts de clínicas/tutores/pacientes em `app.db`; o `fortcordis_app.py` importa e usa.
- **Dashboard**: tela "🏠 Dashboard" está em `app.pages.dashboard`; o app chama `render_dashboard()`.
- **Agendamentos**: tela "📅 Agendamentos" está em `app.pages.agendamentos`; o app chama `render_agendamentos()`.
- **Laudos e Exames**: tela "🩺 Laudos e Exames" está em `app.pages.laudos`; o app chama `render_laudos(laudos_deps)`. Helpers em `app.laudos_helpers`.
- **Prontuário**: tela "📋 Prontuário" está em `app.pages.prontuario`; o app chama `render_prontuario()`.
- **Prescrições**: tela "💊 Prescrições" está em `app.pages.prescricoes`; o app chama `render_prescricoes()`.
- **Financeiro**: tela "💰 Financeiro" está em `app.pages.financeiro`; o app chama `render_financeiro()`.
- **Cadastros**: tela "🏢 Cadastros" está em `app.pages.cadastros`; o app chama `render_cadastros()`.
- **Configurações**: tela "⚙️ Configurações" está em `app.pages.configuracoes`; o app chama `render_configuracoes()`.

## O que ainda está no fortcordis_app.py

- Funções de laudos usadas pela página Laudos (PARAMS, referências, PDF, etc.) permanecem no `fortcordis_app.py` e são passadas via `laudos_deps`.

## Próximos passos (quebrar mais)

1. **Prontuário**  
   Criar `app/pages/prontuario.py` com `render_prontuario()`, movendo o bloco correspondente e importando o que for necessário (por exemplo `verificar_permissao`, `DB_PATH`, funções de listagem de laudos se usadas).

2. **Laudos**  
   ✅ Feito: `app/laudos_helpers.py` (frases, schema, listar/obter laudos) e `app/pages/laudos.py` com `render_laudos()` (8 abas). O app chama `render_laudos()` quando o menu é Laudos e Exames.

3. **Prescrições, Financeiro, Cadastros, Configurações**  
   ✅ Feito: todos em `app.pages` com `render_*()`.

4. **Enxugar o app principal**  
   Quando todas as telas estiverem em `app.pages`, o `fortcordis_app.py` deve ficar só com:
   - imports e `set_page_config`
   - CSS e botões de emergência
   - path e auth (login, `mostrar_info_usuario`)
   - menu na sidebar
   - sequência de `if menu_principal == ...: render_*()`.

## Como adicionar uma nova página

1. Criar `app/pages/nome.py` com `def render_nome():` (e, se precisar, checar permissão com `verificar_permissao`).
2. Em **`app/menu.py`**: adicionar uma linha em `MENU_ITEMS`, por exemplo:  
   `("🆕 Minha Página", "app.pages.nome", "render_nome", None)`  
   (o último `None` é para páginas normais; use `"laudos"` só para Laudos).
3. Em **`app/pages/__init__.py`**: adicionar `from app.pages.nome import render_nome` e incluir `"render_nome"` em `__all__`.
4. Rodar o app: a nova opção aparece no menu e é despachada automaticamente.

Ver também **GUIA_OTIMIZACAO.md** (raiz do projeto) para diretrizes de onde colocar tabelas, serviços e componentes.

## Como rodar

Nada muda para o usuário:

```bash
streamlit run fortcordis_app.py
```

O app continua funcionando; o menu e o dispatch vêm de `app.menu` e `app.pages/`.
