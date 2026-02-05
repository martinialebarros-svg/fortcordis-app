# Analise Completa do Sistema FortCordis

**Data:** 2026-02-05
**Versao do Sistema:** 2026-02-01

---

## 1. Visao Geral

O FortCordis e um sistema de gestao para cardiologia veterinaria construido com **Streamlit + SQLite + Python**. O sistema cobre:

- Dashboard com metricas em tempo real
- Agendamentos com integracao WhatsApp
- Laudos e exames (ecocardiograma, ECG, etc.)
- Prontuario eletronico
- Prescricoes com calculo automatico de dosagem
- Gestao financeira completa
- Cadastros de clinicas e servicos
- Controle de acesso por papeis (RBAC)

**Total:** ~10.748 linhas de Python em 27 arquivos.

---

## 2. Pontos Positivos (O que esta funcionando bem)

### Arquitetura
- Boa separacao em camadas: `app/pages/`, `app/services/`, `app/components/`
- Menu centralizado em `app/menu.py`
- CSS global centralizado em `app/config.py`
- Componentes reutilizaveis (`metricas.py`, `tabelas.py`)

### Seguranca
- Senhas com bcrypt (implementacao correta)
- Bloqueio de conta apos tentativas falhas de login
- Reset de senha com token temporario (expira em 1h)
- Template de secrets (`.streamlit/secrets.template.toml`)

### Funcionalidades
- Cobertura funcional ampla para o dominio
- Integracao com dispositivos medicos (XML/Vivid)
- Geracao de PDF profissional para laudos
- Tabelas de referencia para caninos e felinos

### Banco de Dados
- WAL mode para concorrencia
- Foreign keys habilitadas via PRAGMA
- Recuperacao automatica em caso de corrupcao

---

## 3. Problemas Criticos (Corrigir Imediatamente)

### 3.1 SQL Injection via f-strings (20+ instancias)

**Severidade: CRITICA**

Multiplos arquivos usam f-strings para montar queries SQL com nomes de tabelas/colunas:

| Arquivo | Linhas | Exemplo |
|---------|--------|---------|
| `app/laudos_helpers.py` | 463, 480, 484 | `f"SELECT COUNT(*) FROM {tabela}"` |
| `app/laudos_banco.py` | 146 | f-string com nome de tabela |
| `app/pages/configuracoes.py` | 953, 998, 1011, 1062 | `f"SELECT COUNT(*) FROM {tabela}"` |
| `app/db.py` | 90, 95, 210, 249 | `f"ALTER TABLE ... ADD COLUMN {col}"` |

**Recomendacao:** Criar whitelist de nomes de tabelas/colunas permitidos e validar antes de interpolar:

```python
TABELAS_PERMITIDAS = {"laudos_arquivos", "pacientes", "tutores", "clinicas_parceiras"}

def query_segura(tabela: str) -> str:
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError(f"Tabela nao permitida: {tabela}")
    return f"SELECT COUNT(*) FROM {tabela}"
```

### 3.2 Backup do banco de dados no repositorio

**Severidade: CRITICA**

O arquivo `backup_fortcordis_20260201_1136.sqlite` esta no repositorio. Contem todos os dados da aplicacao, incluindo hashes de senha e dados de pacientes.

**Recomendacao:** Remover do git com `git rm --cached` e verificar se `.gitignore` cobre o padrao `*.sqlite`.

### 3.3 ID de admin hardcoded

**Severidade: ALTA**

Em `modules/rbac.py` (linhas 443, 464):
```python
if usuario_id == 1:
    return  # Concede todas as permissoes
```

**Recomendacao:** Verificar o papel do usuario no banco ao inves de comparar ID numerico.

### 3.4 Sem timeout de sessao

**Severidade: ALTA**

Sessoes de usuario nunca expiram. Uma vez autenticado, o token persiste indefinidamente.

**Recomendacao:** Implementar expiracao de sessao (30-60 minutos de inatividade).

---

## 4. Problemas de Qualidade de Codigo

### 4.1 Conexoes ao banco duplicadas (46+ instancias)

Cada funcao cria sua propria conexao com `sqlite3.connect(str(DB_PATH))` ao inves de usar a funcao centralizada `_db_conn()` de `app/db.py`.

**Recomendacao:** Criar um context manager reutilizavel:

```python
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 4.2 Tratamento de erros fraco

- **8 blocos `except:` vazios** (silenciam erros completamente)
- **58 blocos `except Exception as e:`** genericos demais
- Mensagens de erro expondo detalhes internos: `st.error(f"Erro ao salvar: {e}")`

**Recomendacao:**
- Substituir `except:` por excecoes especificas (`sqlite3.IntegrityError`, `ValueError`, etc.)
- Logar erros no servidor, mostrar mensagens genericas ao usuario
- Nunca usar `except: pass`

### 4.3 Gerenciamento de estado desorganizado (256+ chaves)

O `st.session_state` e usado com 256+ strings magicas sem padrao:
- `"novo_agend_paciente"`, `"presc_paciente_selecionado"`, `"cad_peso"`, etc.
- Sem validacao dos valores
- Sem schema centralizado

**Recomendacao:** Criar constantes centralizadas:

```python
# app/state_keys.py
class SK:
    USUARIO_ID = "usuario_id"
    USUARIO_NOME = "usuario_nome"
    AGEND_PACIENTE = "novo_agend_paciente"
    PRESC_PACIENTE = "presc_paciente_selecionado"
    # ...
```

### 4.4 SQL direto nas paginas

Queries SQL aparecem diretamente nos modulos de pagina (`dashboard.py`, `prontuario.py`, `cadastros.py`) ao inves de estar na camada de servicos.

**Recomendacao:** Mover todas as queries para `app/services/` e manter paginas apenas com logica de UI.

### 4.5 Type hints inconsistentes

- `app/services/consultas.py` e `pacientes.py`: bem tipados
- `app/utils.py`, `app/menu.py`, `app/laudos_helpers.py`: sem type hints

**Recomendacao:** Adicionar type hints progressivamente, comecando pelos servicos e utilitarios.

### 4.6 Imports duplicados

Alguns arquivos importam `sqlite3` mais de uma vez (ex: `cadastros.py`, `configuracoes.py`).

---

## 5. Problemas de Seguranca (Medio/Baixo)

| Problema | Severidade | Arquivo | Recomendacao |
|----------|-----------|---------|--------------|
| Senha so exige 8 caracteres | Media | `auth.py:190` | Exigir maiuscula, numero, caractere especial |
| Lockout de apenas 30min | Media | `auth.py:283` | Implementar backoff exponencial |
| Upload so valida extensao | Media | `configuracoes.py:916` | Validar magic bytes do arquivo |
| Sem audit trail | Media | Geral | Logar operacoes sensiveis (criacao de usuario, mudanca de permissao) |
| Erro exibe stack trace | Media | Multiplos | Usar mensagens genericas na UI |
| Email admin hardcoded | Media | `auth.py:597` | Configurar via variavel de ambiente |
| Sem security headers | Baixa | Limitacao Streamlit | Usar reverse proxy (nginx) |
| Cache de conexao global | Baixa | `db.py:54` | Verificar isolamento entre sessoes |

---

## 6. Melhorias de Performance

### 6.1 Indices no banco de dados

Verificar se existem indices para as queries mais frequentes:
- `pacientes.tutor_id` (busca por tutor)
- `agendamentos.data_agendamento` (filtro por data)
- `financeiro.data_vencimento` (contas a receber)
- `consultas.paciente_id` (historico do paciente)

### 6.2 Caching de dados frequentes

Usar `@st.cache_data` com TTL para:
- Lista de clinicas parceiras
- Catalogo de servicos
- Tabela de medicamentos
- Tabelas de referencia (caninos/felinos)

### 6.3 Queries N+1

Verificar se ha loops fazendo queries individuais que poderiam ser substituidos por JOINs.

---

## 7. Melhorias de Arquitetura

### 7.1 Testes automatizados (PRIORIDADE ALTA)

O projeto nao possui framework de testes. Recomendacoes:

```
tests/
  test_services/
    test_consultas.py
    test_pacientes.py
    test_financeiro.py
  test_auth/
    test_login.py
    test_rbac.py
  test_db/
    test_migrations.py
    test_upserts.py
```

Ferramentas: `pytest` + `pytest-cov`

### 7.2 Migracao de banco de dados

Atualmente as migracoes sao feitas com `ALTER TABLE` ad-hoc. Implementar sistema de migracoes versionadas:

```python
MIGRATIONS = {
    1: "ALTER TABLE pacientes ADD COLUMN chip TEXT",
    2: "CREATE INDEX idx_agend_data ON agendamentos(data_agendamento)",
    3: "ALTER TABLE financeiro ADD COLUMN nfse_id INTEGER",
}
```

### 7.3 Validacao de entrada

Criar camada de validacao para dados de entrada:

```python
# app/validators.py
def validar_telefone(tel: str) -> tuple[bool, str]:
    tel_limpo = re.sub(r'\D', '', tel)
    if len(tel_limpo) not in (10, 11):
        return False, "Telefone deve ter 10 ou 11 digitos"
    return True, tel_limpo

def validar_email(email: str) -> tuple[bool, str]:
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return False, "Email invalido"
    return True, email.strip().lower()
```

### 7.4 Logging estruturado

Expandir logging para todos os modulos com niveis adequados:
- `ERROR`: falhas de operacao
- `WARNING`: tentativas de acesso negadas, dados invalidos
- `INFO`: operacoes CRUD principais
- `DEBUG`: queries executadas (apenas em desenvolvimento)

### 7.5 Pinagem de dependencias

Trocar `requirements.txt` de ranges para versoes exatas com lock file:

```
streamlit==1.40.0
pandas==2.2.0
beautifulsoup4==4.12.2
lxml==4.9.3
fpdf2==2.7.0
Pillow==10.1.0
bcrypt==4.1.1
psutil==5.9.6
```

---

## 8. Plano de Acao Priorizado

### Fase 1 - Critico (Imediato)
1. Corrigir SQL injection (whitelist de tabelas/colunas)
2. Remover backup do repositorio
3. Substituir `usuario_id == 1` por verificacao de papel
4. Implementar timeout de sessao

### Fase 2 - Alta Prioridade (Curto prazo)
5. Centralizar conexoes ao banco (context manager)
6. Mover SQL das paginas para servicos
7. Substituir `except: pass` por tratamento adequado
8. Adicionar validacao de entrada nos formularios
9. Fortalecer requisitos de senha

### Fase 3 - Media Prioridade (Medio prazo)
10. Implementar testes automatizados (pytest)
11. Criar constantes para chaves de session_state
12. Adicionar type hints progressivamente
13. Implementar sistema de migracoes versionadas
14. Expandir logging estruturado

### Fase 4 - Baixa Prioridade (Longo prazo)
15. Adicionar audit trail
16. Implementar MFA para admins
17. Configurar reverse proxy com security headers
18. Pinar dependencias com lock file
19. Criar indices de performance no banco

---

## 9. Resumo Executivo

| Categoria | Nota | Observacao |
|-----------|------|-----------|
| Funcionalidade | 8/10 | Cobertura ampla e funcional |
| Arquitetura | 6/10 | Boa separacao, mas inconsistente |
| Qualidade de Codigo | 5/10 | Duplicacao, erros silenciados, falta de tipos |
| Seguranca | 4/10 | SQL injection critico, sem audit trail |
| Testes | 1/10 | Sem framework de testes automatizados |
| Performance | 6/10 | Funcional, mas sem otimizacoes |
| Documentacao | 7/10 | Boa documentacao de usuario e modulos |

**Nota Geral: 5.3/10**

O sistema tem uma base funcional solida e cobre bem o dominio de cardiologia veterinaria. Os problemas principais sao de seguranca (SQL injection) e manutencao (falta de testes, tratamento de erros fraco). Corrigir as vulnerabilidades criticas e prioridade antes de qualquer deploy em producao.
