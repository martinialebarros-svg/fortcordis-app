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

### 1.2 Fase B — Mover lógica de Laudos para `app/` ✅ Feito

A lógica de Laudos foi movida para `app/` e o `fortcordis_app.py` foi reduzido.

**Divisão em `app/`:**

| Módulo | Conteúdo |
|--------|----------|
| **`app/laudos_refs.py`** ✅ | PARAMS, GRUPOS_CANINO/FELINO, tabelas de referência, `calcular_referencia_tabela`, `interpretar`, `interpretar_divedn`, `listar_registros_arquivados_cached`, `especie_is_felina`, etc. |
| **`app/laudos_pdf.py`** ✅ | `_caminho_marca_dagua`, `obter_imagens_para_pdf`, `montar_nome_base_arquivo`, `_normalizar_data_str`, etc. |
| **`app/laudos_helpers.py`** ✅ | `montar_qualitativa`, `montar_chave_frase`, `carregar_frases`, `frase_det`, `aplicar_frase_det_na_tela`, `obter_entry_frase`, `aplicar_entry_salva`, `analisar_criterios_clinicos`, `complementar_regurgitacoes_nas_valvas`, `_split_pat_grau`, etc. |
| **`app/laudos_banco.py`** ✅ | `_criar_tabelas_laudos_se_nao_existirem`, `salvar_laudo_no_banco`, `buscar_laudos`, `carregar_laudo_para_edicao`, `atualizar_laudo_editado`, etc. |
| **`app/laudos_deps.py`** ✅ | `build_laudos_deps()` **importa** de todos os módulos acima e monta o `SimpleNamespace`. O app chama `build_laudos_deps()` sem argumentos. |

**Benefício:** `fortcordis_app.py` ficou menor; alterações em laudos ficam em `app/laudos_*.py`.

---

## 2. Prioridade média

### 2.1 Logging em vez de print / st para diagnóstico ✅ Feito

- **`app/config.py`** chama `_setup_app_logging()` e configura o logger `app` (nível INFO, handler em stderr).
- **`app/db.py`**, **`app/laudos_banco.py`**, **`app/services/consultas.py`**, **`app/services/pacientes.py`** usam `logger = logging.getLogger(__name__)` e `logger.exception` em falhas (conexão ao banco, salvar laudo, criar consulta, atualizar peso).
- Mensagens ao usuário continuam com `st.error`/`st.warning`; logging serve para rastreio em desenvolvimento e nos logs do Streamlit Cloud.

### 2.2 Tratamento de erros padronizado ✅ Parcial

- **`app/exceptions.py`** criado com `AppError`, `DBError`, `LaudoNotFoundError`, `ConfigError` para uso futuro.
- Serviços e laudos_banco continuam com retorno estruturado `(resultado, None)` ou `(None, mensagem_erro)` e **log** em exceções; exceções customizadas podem ser usadas em refatorações futuras.
- UI e excepthook no app principal seguem exibindo mensagem amigável + detalhe em expander.

### 2.3 Type hints ✅ Parcial

- **`app/services/consultas.py`** e **`app/services/pacientes.py`** já tinham type hints; mantidos.
- **`app/laudos_banco.py`**: assinaturas e retornos de `salvar_laudo_no_banco`, `buscar_laudos` com `Tuple`, `Optional`.
- **`app/laudos_helpers.py`**: `obter_entry_frase`, `carregar_frases`, `montar_chave_frase` com tipos principais.
- Outros módulos podem ganhar anotações gradualmente.

### 2.4 Config completo em `app/config.py` ✅ Feito

- **`app/config.py`** já contém `PASTA_LAUDOS`, `ARQUIVO_REF`, `ARQUIVO_REF_FELINOS`.
- **`fortcordis_app.py`**: bloco `try/except ImportError` de fallback para esses paths foi **removido**; o app importa tudo diretamente de `app.config`.

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
