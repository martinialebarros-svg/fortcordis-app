# Guia de Otimização — Fort Cordis

Este documento orienta a evolução do sistema para **facilitar novas funcionalidades e alterações** no que já existe.

---

## 1. Estado atual (resumo)

| Camada | Onde está | Observação |
|--------|------------|------------|
| **Config** | `app/config.py` | VERSAO_DEPLOY, DB_PATH, PASTA_DB, CSS_GLOBAL |
| **Banco** | `app/db.py` | Conexão, `_db_init()` (tabelas: clinicas, tutores, pacientes, laudos_arquivos, consultas), upserts |
| **Utilitários** | `app/utils.py` | _norm_key, nome_proprio_ptbr, _clean_spaces |
| **Páginas** | `app/pages/*.py` | Uma função `render_*()` por tela do menu |
| **Laudos (lógica)** | `fortcordis_app.py` + `app/laudos_helpers.py` | PARAMS, referências, PDF, frases — ainda ~100+ definições no app principal |
| **Auth/RBAC** | `modules/auth.py`, `modules/rbac.py` | Login, permissões |

O **fortcordis_app.py** ainda concentra: sidebar do Laudos, todas as funções/constantes passadas em `laudos_deps`, e a sequência `if menu_principal == ...`.

---

## 2. Diretrizes para facilitar implementação e alterações

### 2.1 Onde colocar cada tipo de coisa

| O que você quer fazer | Onde colocar |
|------------------------|--------------|
| **Nova tela no menu** | `app/pages/nome.py` com `render_nome()`; registrar em `app/menu.py` (ou no `elif` em fortcordis_app.py) e em `app/pages/__init__.py` |
| **Nova tabela ou coluna** | `app/db.py` → `_db_init()` (CREATE TABLE IF NOT EXISTS ou ALTER TABLE com try/except) |
| **Lógica de negócio compartilhada** (ex: “listar consultas por paciente”) | `app/services/` (ex: `app/services/consultas.py`) ou funções em `app/db.py` |
| **Constantes globais** (paths, limites, textos padrão) | `app/config.py` |
| **Componente de UI reutilizável** (tabela, métricas, card, filtro) | `app/components/` — ex.: `tabela_tabular`, `metricas_linha` em `app/components/tabelas.py` e `metricas.py` |
| **Ajuste só em uma tela** | O arquivo correspondente em `app/pages/` |

### 2.2 Convenção para nova página

1. Criar `app/pages/minha_pagina.py`:
   - Uma função `def render_minha_pagina():` (ou `render_minha_pagina(deps=None)` se precisar de dependências).
   - No início: checar permissão com `verificar_permissao("modulo", "ver")` se a tela for restrita.
   - Usar `DB_PATH`, `_db_conn`, `_db_init` de `app.config` e `app.db`.

2. Registrar no menu:
   - Em `app/menu.py`: adicionar entrada na lista `MENU_ITEMS` (se o projeto usar menu data-driven).
   - Ou em `fortcordis_app.py`: novo `elif menu_principal == "🆕 Minha Página":` com import e chamada a `render_minha_pagina()`.

3. Exportar em `app/pages/__init__.py`:  
   `from app.pages.minha_pagina import render_minha_pagina` e incluir em `__all__`.

### 2.3 Alterações em tabelas existentes

- **Nova tabela:** em `app/db.py`, dentro de `_db_init()`, usar `CREATE TABLE IF NOT EXISTS ...`.
- **Nova coluna:** em `_db_init()`, após a criação da tabela, usar `ALTER TABLE ... ADD COLUMN ...` dentro de `try/except sqlite3.OperationalError` (para não falhar se a coluna já existir).

Assim, qualquer ambiente (local ou deploy) que rode o app terá o schema atualizado ao inicializar.

---

## 3. Próximos passos de otimização (prioridade sugerida)

### Fase A — Menu data-driven (rápido, alto impacto) ✅ Feito

- **`app/menu.py`** criado com `MENU_ITEMS` (rótulo, módulo, função, handler especial) e `get_menu_labels()`.
- No `fortcordis_app.py`, o `st.sidebar.radio` usa `get_menu_labels()` e um loop despacha para a página escolhida; Laudos continua com handler especial `"laudos"` (monta `laudos_deps` e chama `render_laudos(laudos_deps)`).
- **Benefício:** adicionar ou reordenar uma página = editar `app/menu.py` e criar `app/pages/nome.py` com `render_nome()`.

### Fase B — Mover lógica de Laudos para `app/` (em andamento)

- **Feito:** Paths de laudos centralizados em `app/config.py` (PASTA_LAUDOS, ARQUIVO_REF, ARQUIVO_REF_FELINOS). O app principal importa de `app.config` e não redefine mais esses paths.
- **Feito:** `app/laudos_deps.py` criado com `build_laudos_deps(**kwargs)` e lista `LAUDOS_DEPS_KEYS` (contrato da página Laudos). O app principal chama `build_laudos_deps(...)` em vez de montar o `SimpleNamespace` inline.
- **Próximo:** Mover para `app/` (ex.: `app/laudos_refs.py` ou ampliar `laudos_helpers`) as constantes e funções que hoje estão no `fortcordis_app.py` (PARAMS, interpretar, gerar_tabela_padrao, etc.) e fazer `build_laudos_deps` importá-las de lá, reduzindo o código no app principal.
- **Benefício:** app principal enxuto; alterações em laudos ficam concentradas em `app/laudos*`.

### Fase C — Camada de serviços (médio prazo) ✅ Feito

- **`app/services/`** criado com:
  - **consultas.py:** `listar_consultas_recentes(limite=10)`, `criar_consulta(...)` (insere consulta e opcionalmente atualiza peso do paciente).
  - **pacientes.py:** `listar_pacientes_com_tutor()`, `listar_pacientes_tabela()`, `buscar_pacientes(nome=..., tutor=..., limite=20)`, `atualizar_peso_paciente(paciente_id, peso_kg)`.
- **Prontuário** usa os serviços para lista de pacientes (aba Pacientes), select de pacientes e histórico de consultas (aba Consultas), e para registrar nova consulta.
- **Prescrições** usa `buscar_pacientes` na aba "Buscar Paciente".
- **Benefício:** reutilização, testes e mudanças de regra em um só lugar.

### Fase D — Componentes de UI (quando houver repetição) ✅ Feito

- **`app/components/`** criado com:
  - **tabelas.py:** `tabela_tabular(df, caption=None, drop_colunas="id", empty_message=None)` — exibe DataFrame com layout padrão (use_container_width, hide_index), opção de esconder colunas e mensagem quando vazio.
  - **metricas.py:** `metricas_linha(metricas)` — exibe uma linha de `st.metric` (lista de (label, value, delta)).
- **Prontuário** usa `tabela_tabular` para listas de tutores, pacientes e consultas recentes.
- **Cadastros** usa `tabela_tabular` para a lista de clínicas parceiras.
- **Dashboard** usa `metricas_linha` para as 4 métricas (Agendamentos Hoje, Pendentes Confirmação, Contas a Receber, Retornos Atrasados).
- **Benefício:** alterar layout/comportamento das tabelas ou métricas em um único lugar.

---

## 4. Checklist ao implementar um recurso novo

- [ ] Nova tela? → `app/pages/` + registro no menu + `__init__.py`.
- [ ] Nova tabela/coluna? → `app/db.py` em `_db_init()`.
- [ ] Constante global? → `app/config.py`.
- [ ] Lógica usada em mais de uma página? → considerar `app/services/`.
- [ ] Atualizar `ESTRUTURA_MODULOS.md` ou `SNAPSHOT_SISTEMA.md` se a estrutura mudar.

---

## 5. Como rodar e testar

```bash
streamlit run fortcordis_app.py
```

Após mudanças em `_db_init()`, reiniciar o app (ou recarregar a página, conforme o caso) para aplicar criação/alteração de tabelas.
