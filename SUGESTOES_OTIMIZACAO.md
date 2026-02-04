# Sugestões para otimizar, organizar e melhorar o sistema

Documento complementar ao **GUIA_OTIMIZACAO.md** e ao **SNAPSHOT_SISTEMA.md**, com prioridades e passos concretos.

---

## 1. Prioridade alta

### 1.1 Remover código duplicado no `fortcordis_app.py` ✅ Feito

Havia **funções definidas duas vezes** no mesmo arquivo (a segunda definição sobrescrevia a primeira):

- `frase_det` — linhas ~1816 e ~4120  
- `aplicar_frase_det_na_tela` — linhas ~1865 e ~4169  
- E possivelmente outras (ex.: `garantir_schema_det_frase`, `migrar_txt_para_det`, `det_para_txt`, `complementar_regurgitacao_valvar`, `montar_qualitativa`, `interpretar`, `calcular_referencia_tabela`, `analisar_criterios_clinicos`, classe `PDF`, etc.).

**Ação:** O bloco duplicado (linhas 4102–5381) foi removido; restou uma única definição de cada função.

### 1.2 Fase B — Mover lógica de Laudos para `app/` (parcialmente feito)

O `fortcordis_app.py` ainda tem **dezenas de funções e constantes** só para Laudos (PARAMS, referências, PDF, tabelas caninos/felinos, interpretar, analisar_criterios_clinicos, etc.). Objetivo: deixar o app principal só com entrada, auth, menu e chamadas `render_*()`.

**Sugestão de divisão em `app/`:**

| Módulo | Conteúdo sugerido |
|--------|--------------------|
| **`app/laudos_refs.py`** ✅ | PARAMS, GRUPOS_CANINO/FELINO, tabelas de referência (caninos/felinos), `gerar_tabela_padrao`, `carregar_tabela_referencia_cached`, `limpar_e_converter_tabela`, `calcular_referencia_tabela`, `interpretar`, `interpretar_divedn`, `DIVEDN_REF_TXT`, `especie_is_felina`, `get_grupos_por_especie`, `normalizar_especie_label` — **já criado**; o app importa daqui e repassa via `laudos_deps`. |
| **`app/laudos_pdf.py`** | Classe `PDF`, `obter_imagens_para_pdf`, `_caminho_marca_dagua`, funções de nome de arquivo e data (`montar_nome_base_arquivo`, `_normalizar_data_str`, `_limpar_texto_filename`, etc.) |
| **`app/laudos_qualitativa.py`** (ou dentro de `laudos_helpers.py`) | `montar_qualitativa`, `montar_chave_frase`, `carregar_frases`, `frase_det`, `aplicar_frase_det_na_tela`, `obter_entry_frase`, `aplicar_entry_salva`, `analisar_criterios_clinicos`, complementos de regurgitação, etc. |
| **`app/laudos_banco.py`** (ou ampliar `laudos_helpers.py`) | `_criar_tabelas_laudos_se_nao_existirem`, `salvar_laudo_no_banco`, `buscar_laudos`, `carregar_laudo_para_edicao`, `atualizar_laudo_editado`, `listar_registros_arquivados_cached`, `listar_laudos_do_banco`, `contar_laudos_do_banco`, etc. |

Depois de mover:

- Em **`app/laudos_deps.py`**, o `build_laudos_deps` passa a **importar** essas funções/constantes dos novos módulos e montar o `SimpleNamespace`. O `fortcordis_app.py` só chama `build_laudos_deps()` (podendo passar só `DB_PATH`, `PASTA_LAUDOS`, etc., se ainda estiverem no config).
- Atualizar **`LAUDOS_DEPS_KEYS`** em `laudos_deps.py` para refletir o contrato atual.

**Benefício:** `fortcordis_app.py` cai para algumas centenas de linhas; alterações em laudos ficam concentradas em `app/laudos_*.py`.

---

## 2. Prioridade média

### 2.1 Logging em vez de print / st para diagnóstico

- Introduzir o módulo **`logging`** e um logger por módulo (ex.: `logger = logging.getLogger(__name__)`).
- Para erros e eventos importantes (falha ao salvar laudo, falha de conexão ao banco), usar `logger.exception` ou `logger.error` em vez de só `st.error` ou `print`.
- Manter `st.error`/`st.warning` para mensagens ao usuário; usar logging para rastreio em arquivo/console em desenvolvimento e em logs do Streamlit Cloud.

### 2.2 Tratamento de erros padronizado

- Definir exceções customizadas (ex.: `app.exceptions.LaudoNotFoundError`, `app.exceptions.DBError`) se fizer sentido.
- Em serviços (`app/services/*.py`), usar `try/except` com log e re-raise ou retorno estruturado (ex.: `{"ok": False, "error": "..."}`) em pontos críticos.
- Na UI, exibir mensagem amigável e, em modo debug, o detalhe (já parcialmente feito com o excepthook no app principal).

### 2.3 Type hints

- Adicionar anotações de tipo nas assinaturas de `app/services/*`, `app/laudos_helpers.py` e nos novos `app/laudos_*.py` (retornos e parâmetros principais).
- Facilita manutenção e uso de ferramentas (IDE, mypy) sem mudar comportamento.

### 2.4 Config completo em `app/config.py`

- Já existem `PASTA_LAUDOS`, `ARQUIVO_REF`, `ARQUIVO_REF_FELINOS` em `app.config`.
- Remover o bloco `try/except ImportError` de fallback no `fortcordis_app.py` assim que o deploy estiver sempre com `app/config.py` atualizado (evita dois caminhos de configuração).

---

## 3. Prioridade menor (melhorias contínuas)

### 3.1 Testes automatizados

- **`tests/`** na raiz (ou dentro de `app/`) com pytest.
- Testes unitários para:
  - `app.services.consultas` (listar_consultas_recentes, criar_consulta)
  - `app.services.pacientes` (buscar_pacientes, atualizar_peso_paciente)
  - Funções puras de laudos (interpretar, calcular_referencia_tabela, normalização de texto) em `app/laudos_refs.py` ou equivalente.
- Teste de integração opcional: subir SQLite em memória, chamar `_db_init` e um fluxo mínimo (ex.: criar consulta e listar).

### 3.2 Componentes de UI adicionais

- Se outras páginas repetirem o mesmo padrão (filtro por data, seletor de clínica, card de resumo), extrair para **`app/components/`** (ex.: `filtro_data.py`, `seletor_clinica.py`) para manter consistência e reduzir duplicação.

### 3.3 Documentação de APIs internas

- Docstrings em funções públicas de `app/services/` e `app/laudos_*.py` (parâmetros, retorno, exceções).
- Manter **ESTRUTURA_MODULOS.md** e **SNAPSHOT_SISTEMA.md** atualizados quando surgirem novos módulos ou páginas.

---

## 4. Ordem sugerida de execução

1. **Remover duplicação** no `fortcordis_app.py` (bloco duplicado de frase_det, aplicar_frase_det_na_tela e funções relacionadas).
2. **Fase B:** Criar `app/laudos_refs.py`, `app/laudos_pdf.py`, ampliar `app/laudos_helpers.py` (ou criar `laudos_qualitativa.py` e `laudos_banco.py`) e mover funções/constantes; atualizar `build_laudos_deps` para importar de lá.
3. Padronizar **logging** e **tratamento de erros** nos serviços e em laudos.
4. Adicionar **type hints** nos módulos novos e nos serviços.
5. Introduzir **testes** para serviços e funções puras de laudos.
6. Atualizar **SNAPSHOT_SISTEMA.md** e **GUIA_OTIMIZACAO.md** após cada etapa relevante.

---

*Sugestões geradas em 02/02/2026 para evolução do Fort Cordis.*
