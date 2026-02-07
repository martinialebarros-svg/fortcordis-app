# Revisão do Código — Fort Cordis

Documento gerado a partir da análise do sistema: **correções necessárias**, **melhorias recomendadas** e **sugestões de otimização e aprimoramento**.

---

## 1. Correções recomendadas (prioridade alta)

### 1.1 Tratamento de exceções — evitar `except:` sem tipo

**Problema:** Vários arquivos usam `except:` (ou `except Exception: pass`), o que engole erros e dificulta diagnóstico.

**Arquivos afetados:**
- `app/pages/laudos.py` (linhas ~419, 546, 551, 1276)
- `app/pages/cadastros.py` (~232)
- `app/pages/prescricoes.py` (~63, 126, 215, 574, 822)
- `app/pages/prontuario.py` (~181)

**Recomendação:** Trocar por `except Exception as e:` e pelo menos registrar no log:
```python
except Exception as e:
    logger.exception("Contexto: falha ao ...")
    # ou st.warning() se for erro recuperável para o usuário
```

---

### 1.2 Configuração de paths para deploy (Streamlit Cloud)

**Problema:** `PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"` em `app/config.py` usa o diretório home do servidor. Em ambientes como Streamlit Cloud o home pode ser efêmero ou restrito.

**Recomendação:**
- Permitir override por variável de ambiente, por exemplo:
  ```python
  import os
  PASTA_LAUDOS = Path(os.environ.get("FORTCORDIS_PASTA_LAUDOS", str(Path.home() / "FortCordis" / "Laudos")))
  ```
- Em deploy, definir `FORTCORDIS_PASTA_LAUDOS` (ou usar volume persistente conforme `ONDE_LAUDOS_SAO_SALVOS.md`).

---

### 1.3 Duplicação de definição de PASTA_LAUDOS

**Problema:** Em `app/pages/prescricoes.py` (linha ~449) e `app/pages/prontuario.py` (linha ~167) há:
```python
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
```
Isso duplica a regra e quebra se a pasta for configurável.

**Recomendação:** Importar de `app.config`: `from app.config import PASTA_LAUDOS` e usar essa constante.

---

### 1.4 Caminho do banco no módulo de auth

**Problema:** Em `modules/auth.py` o `DB_PATH` é definido localmente (com fallback para `FORTCORDIS_DB_PATH`), enquanto o restante do app usa `app.config.DB_PATH`. Dois pontos de configuração podem divergir.

**Recomendação:** Usar um único ponto de verdade, por exemplo importar de `app.config` em `modules/auth.py` (ou definir em um único módulo de config compartilhado).

---

### 1.5 Senha padrão em texto no fluxo de “Resetar senha”

**Problema:** Em `app/pages/configuracoes.py` a senha padrão "Senha123" aparece em código e é exibida ao usuário após reset.

**Recomendação:**
- Não hardcodar senha padrão em produção; ou usar apenas em ambiente de desenvolvimento (checando algo como `os.environ.get("FORTCORDIS_DEV")`).
- Em produção, preferir fluxo “esqueci minha senha” (token por e-mail) ou geração de senha temporária aleatória exibida uma vez.

---

## 2. Melhorias de robustez e manutenção

### 2.1 Conexões SQLite — uso consistente de timeout e fechamento

**Situação:** Em `app/db.py` a conexão principal usa `timeout=10` e `check_same_thread=False`; em vários outros módulos (`app/services/*.py`, `app/pages/*.py`, `app/laudos_banco.py`) usa-se `sqlite3.connect(str(DB_PATH))` sem timeout. Em carga ou travamento, isso pode gerar locks.

**Recomendação:**
- Criar em `app/db.py` um helper, por exemplo `get_connection(timeout=10)`, que devolve uma conexão com parâmetros padrão.
- Onde for adequado, usar context manager (`with get_connection() as conn:`) para garantir `close()` mesmo em exceção. Serviços e páginas que abrem conexão própria podem passar a usar esse helper.

---

### 2.2 Uso de exceções customizadas

**Situação:** `app/exceptions.py` define `AppError`, `DBError`, `LaudoNotFoundError`, `ConfigError`, mas o código ainda retorna tuplas `(None, "mensagem")` ou faz `logger.exception` sem lançar exceção.

**Recomendação:** Em novos trechos e refatorações, lançar `DBError` ou `LaudoNotFoundError` em falhas de banco/laudo e tratar no boundary (páginas), exibindo mensagem amigável. Isso padroniza o tratamento e facilita testes.

---

### 2.3 Queries com f-string — garantir que nomes de tabelas/colunas são controlados

**Situação:** Em vários pontos há `cursor.execute(f"... {tabela} ...")`. Quando `tabela` vem de dicionário fixo (ex.: `laudos_banco.py`: `tabelas.get(tipo_exame)`), o risco de SQL injection é baixo. Onde o nome de tabela/coluna vier de entrada do usuário ou de outra fonte não confiável, não usar f-string.

**Recomendação:** Manter lista/whitelist explícita de nomes de tabelas/colunas permitidos e usar apenas esses valores na montagem da query (como já feito em `laudos_banco`). Em scripts de manutenção (ex.: `exportar_backup.py`, `configuracoes.py`) garantir que `tabela`/`col` vêm de `sqlite_master` ou de listas fixas.

---

### 2.4 Cache de dados e recursos

**Situação:** Já existem `@st.cache_resource` em `app/db.py` e `@st.cache_data` em `app/laudos_refs.py`. Outras funções que leem tabelas de referência ou listas pesadas são chamadas a cada rerun.

**Recomendação:** Avaliar cache para:
- Carregamento de tabelas de referência (caninos/felinos) quando já não estiverem em `laudos_refs`.
- Listas estáticas (ex.: medicamentos, frases) com TTL curto para refletir alterações após alguns minutos.

---

## 3. Otimizações sugeridas

### 3.1 Arquivos legados na raiz

**Situação:** Vários scripts na raiz parecem ser de migração, correção ou teste (ex.: `corrigir_*.py`, `verificar_*.py`, `fortcordis_app OLD.py`, `fortcordis_app copy.py`, `fortcordis_app_ORIGINAL.py`).

**Recomendação:** Mover para uma pasta `scripts/` ou `manutencao/` e documentar no README o propósito de cada um. Reduz ruído e deixa claro o que é o app principal.

---

### 3.2 Página Laudos — tamanho do arquivo

**Situação:** `app/pages/laudos.py` tem mais de 2300 linhas, concentrando cadastro, medidas, qualitativa, PDF, referências, busca e pressão arterial.

**Recomendação:** A médio prazo, quebrar em submódulos, por exemplo:
- `app/pages/laudos/__init__.py` (exporta `render_laudos`)
- `app/pages/laudos/cadastro.py`, `medidas.py`, `qualitativa.py`, `pdf.py`, `referencias.py`, `busca.py`, `pressao_arterial.py`
Cada um com uma função que recebe `deps` e o estado necessário. O `render_laudos` orquestraria as tabs chamando esses módulos. Facilita testes e manutenção.

---

### 3.3 Testes automatizados

**Situação:** Não há pasta `tests/` nem pytest no `requirements.txt`.

**Recomendação:** Adicionar `pytest` (e opcionalmente `pytest-cov`) e criar testes para:
- Funções puras em `app/laudos_refs.py` (ex.: `interpretar`, `calcular_referencia_tabela`, formatação de dados).
- Serviços em `app/services/` (ex.: `criar_consulta`, `buscar_pacientes`) usando SQLite em memória.
- `app/utils.py` e `formatar_data_br` em `app/config.py`.

---

### 3.4 Type hints

**Situação:** Parte do código já tem type hints (services, laudos_banco); outras funções e páginas não.

**Recomendação:** Introduzir anotações gradualmente em funções públicas de `app/db.py`, `app/laudos_banco.py`, `app/laudos_refs.py` e nos `render_*` das páginas (retorno `None` ou tipo simples). Melhora IDE e detecção de erros.

---

## 4. Sugestões de funcionalidades / aprimoramento

### 4.1 Configuração

- **Variáveis de ambiente documentadas:** Criar um `.env.example` (ou secção no README) listando `DB_PATH`, `PASTA_LAUDOS`, `FORTCORDIS_PASTA_LAUDOS`, etc., para deploy e desenvolvimento.
- **Versão única:** Manter `VERSAO_DEPLOY` em `app/config.py` e exibir no rodapé ou na sidebar (já próximo do que existe) para facilitar suporte.

### 4.2 Usabilidade

- **Confirmação em ações destrutivas:** Onde houver “excluir”, “resetar” ou “arquivar definitivamente”, usar `st.dialog` ou checkbox “Confirmo que desejo…” para reduzir cliques acidentais.
- **Feedback de carregamento:** Em operações longas (gerar PDF, importar backup, buscar laudos), usar `st.spinner` ou `st.status` com mensagem clara.

### 4.3 Laudos e exames

- **Paginação ou limite na busca:** Se a lista de exames/laudos puder crescer muito, limitar a exibição (ex.: 50 por página) e oferecer “Carregar mais” ou paginação.
- **Validação de medidas:** Na aba Medidas, validar faixas plausíveis (ex.: peso > 0, valores numéricos onde obrigatório) e exibir aviso antes de gerar PDF.

### 4.4 Segurança e auditoria

- **Log de ações sensíveis:** Registrar em log (ou tabela de auditoria) ações como: alteração de senha, reset de senha de usuário, exclusão de laudo, importação/exportação de dados.
- **Política de senha:** Reforçar no código (e na UI) requisitos de senha (tamanho mínimo, caracteres especiais, etc.) alinhados à política desejada.

### 4.5 Performance

- **Leitura de DataFrames grandes:** Onde houver `pd.read_sql_query` sem `LIMIT` em tabelas que podem crescer (ex.: consultas, financeiro), considerar limite padrão ou paginação no SQL.
- **Blobs no banco:** Para laudos com PDF/JSON grandes, avaliar se o volume de leitura/escrita justifica guardar arquivos em disco e só referenciar path no banco (depende do ambiente de deploy).

---

## 5. Resumo por prioridade

| Prioridade | Item |
|-----------|------|
| **Alta** | Substituir `except:` por `except Exception` + log; centralizar e configurar `PASTA_LAUDOS` (env); usar uma única fonte para `DB_PATH` (auth + app); remover ou condicionar senha padrão "Senha123"; usar `PASTA_LAUDOS` de config em prescricoes e prontuario. |
| **Média** | Helper de conexão SQLite com timeout/context manager; uso de exceções de `app.exceptions`; revisar f-strings em SQL (só com nomes controlados); cache onde fizer sentido; organizar scripts de manutenção. |
| **Baixa** | Quebrar `laudos.py` em submódulos; adicionar pytest e testes iniciais; ampliar type hints; documentar variáveis de ambiente; confirmação em ações destrutivas; paginação em listas grandes; auditoria de ações sensíveis. |

---

*Documento gerado com base na análise do repositório FortCordis_Novo. Recomenda-se aplicar as correções de prioridade alta primeiro e depois evoluir itens de média e baixa conforme a capacidade da equipe.*
