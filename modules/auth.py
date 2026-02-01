"""
Módulo de Autenticação - Fort Cordis
Sistema de login, gestão de usuários e sessões

IMPORTANTE: Este módulo usa bcrypt para hash de senhas.
Instalar: pip install bcrypt --break-system-packages
"""

import sqlite3
import bcrypt
import hashlib
import secrets  # ✅ PARA criar_token_persistente
import json 
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
import streamlit as st
import os

# Caminho do banco: pasta do projeto (funciona no Streamlit Cloud) ou variável de ambiente
if os.environ.get("FORTCORDIS_DB_PATH"):
    DB_PATH = Path(os.environ["FORTCORDIS_DB_PATH"])
else:
    _root = Path(__file__).resolve().parent.parent
    DB_PATH = _root / "fortcordis.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def inicializar_tabelas_auth():
    """
    Cria as tabelas necessárias para autenticação e permissões.
    Executa apenas uma vez, na primeira inicialização.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            ultimo_acesso TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            criado_por INTEGER,
            tentativas_login INTEGER DEFAULT 0,
            bloqueado_ate TEXT
        )
    """)
    
    # Tabela de papéis (roles)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papeis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            descricao TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de relacionamento usuário-papel
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuario_papel (
            usuario_id INTEGER NOT NULL,
            papel_id INTEGER NOT NULL,
            atribuido_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atribuido_por INTEGER,
            PRIMARY KEY (usuario_id, papel_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (papel_id) REFERENCES papeis(id)
        )
    """)
    
    # Tabela de sessões (opcional, para controle mais fino)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            criada_em TEXT DEFAULT CURRENT_TIMESTAMP,
            expira_em TEXT NOT NULL,
            ativa INTEGER DEFAULT 1,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Tabelas de autenticação criadas com sucesso!")


def inserir_papeis_padrao():
    """
    Insere os papéis padrão do sistema.
    Executar apenas uma vez.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    papeis_padrao = [
        ("admin", "Administrador - Acesso total ao sistema"),
        ("recepcao", "Recepção - Agenda, cadastros, financeiro básico"),
        ("veterinario", "Veterinário - Prontuário, prescrições, exames"),
        ("cardiologista", "Cardiologista - Laudos cardiológicos, assinaturas"),
        ("financeiro", "Financeiro - Contas a receber/pagar, relatórios"),
    ]
    
    for nome, descricao in papeis_padrao:
        try:
            cursor.execute(
                "INSERT INTO papeis (nome, descricao) VALUES (?, ?)",
                (nome, descricao)
            )
        except sqlite3.IntegrityError:
            # Papel já existe, ignora
            pass
    
    conn.commit()
    conn.close()
    print("✅ Papéis padrão inseridos com sucesso!")


def hash_senha(senha: str) -> str:
    """
    Gera hash seguro da senha usando bcrypt.
    
    Args:
        senha: Senha em texto plano
        
    Returns:
        Hash da senha em formato string
    """
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return hash_bytes.decode('utf-8')


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """
    Verifica se a senha corresponde ao hash.
    
    Args:
        senha: Senha em texto plano
        senha_hash: Hash armazenado no banco
        
    Returns:
        True se a senha está correta, False caso contrário
    """
    try:
        return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception as e:
        print(f"❌ Erro ao verificar senha: {e}")
        return False


def criar_usuario(
    nome: str,
    email: str,
    senha: str,
    papel: str = "veterinario",
    criado_por: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Cria um novo usuário no sistema.
    
    Args:
        nome: Nome completo do usuário
        email: Email (usado para login)
        senha: Senha em texto plano (será hasheada)
        papel: Nome do papel a atribuir
        criado_por: ID do usuário que está criando (para auditoria)
        
    Returns:
        (sucesso, mensagem)
    """
    # Validações
    if len(senha) < 8:
        return False, "❌ Senha deve ter no mínimo 8 caracteres"
    
    if not "@" in email:
        return False, "❌ Email inválido"
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Verifica se papel existe
        cursor.execute("SELECT id FROM papeis WHERE nome = ?", (papel,))
        papel_row = cursor.fetchone()
        if not papel_row:
            return False, f"❌ Papel '{papel}' não existe"
        papel_id = papel_row[0]
        
        # Cria hash da senha
        senha_hash = hash_senha(senha)
        
        # Insere usuário
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, criado_por)
            VALUES (?, ?, ?, ?)
            """,
            (nome, email.lower(), senha_hash, criado_por)
        )
        usuario_id = cursor.lastrowid
        
        # Atribui papel
        cursor.execute(
            """
            INSERT INTO usuario_papel (usuario_id, papel_id, atribuido_por)
            VALUES (?, ?, ?)
            """,
            (usuario_id, papel_id, criado_por)
        )
        
        conn.commit()
        return True, f"✅ Usuário '{nome}' criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, f"❌ Email '{email}' já está cadastrado"
    except Exception as e:
        return False, f"❌ Erro ao criar usuário: {e}"
    finally:
        conn.close()


def autenticar(email: str, senha: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Autentica um usuário.
    
    Args:
        email: Email do usuário
        senha: Senha em texto plano
        
    Returns:
        (sucesso, dados_usuario, mensagem)
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Busca usuário
        cursor.execute(
            """
            SELECT id, nome, email, senha_hash, ativo, tentativas_login, bloqueado_ate
            FROM usuarios
            WHERE email = ?
            """,
            (email.lower(),)
        )
        usuario = cursor.fetchone()
        
        if not usuario:
            return False, None, "❌ Email ou senha incorretos"
        
        user_id, nome, email, senha_hash, ativo, tentativas, bloqueado_ate = usuario
        
        # Verifica se está ativo
        if not ativo:
            return False, None, "❌ Usuário desativado. Contate o administrador."
        
        # Verifica se está bloqueado
        if bloqueado_ate:
            bloqueio = datetime.fromisoformat(bloqueado_ate)
            if datetime.now() < bloqueio:
                minutos = int((bloqueio - datetime.now()).total_seconds() / 60)
                return False, None, f"❌ Usuário bloqueado por {minutos} minutos devido a tentativas excessivas"
        
        # Verifica senha
        if not verificar_senha(senha, senha_hash):
            # Incrementa tentativas
            tentativas += 1
            if tentativas >= 3:
                # Bloqueia por 30 minutos
                bloqueio = datetime.now() + timedelta(minutes=30)
                cursor.execute(
                    "UPDATE usuarios SET tentativas_login = ?, bloqueado_ate = ? WHERE id = ?",
                    (tentativas, bloqueio.isoformat(), user_id)
                )
                conn.commit()
                return False, None, "❌ Muitas tentativas incorretas. Usuário bloqueado por 30 minutos."
            else:
                cursor.execute(
                    "UPDATE usuarios SET tentativas_login = ? WHERE id = ?",
                    (tentativas, user_id)
                )
                conn.commit()
                return False, None, f"❌ Email ou senha incorretos ({3-tentativas} tentativas restantes)"
        
        # Login bem-sucedido
        # Reseta tentativas e atualiza último acesso
        cursor.execute(
            """
            UPDATE usuarios 
            SET tentativas_login = 0, bloqueado_ate = NULL, ultimo_acesso = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), user_id)
        )
        
        # Busca papéis do usuário
        cursor.execute(
            """
            SELECT p.nome, p.descricao
            FROM papeis p
            JOIN usuario_papel up ON p.id = up.papel_id
            WHERE up.usuario_id = ?
            """,
            (user_id,)
        )
        papeis = [{"nome": row[0], "descricao": row[1]} for row in cursor.fetchall()]
        
        conn.commit()
        
        dados_usuario = {
            "id": user_id,
            "nome": nome,
            "email": email,
            "papeis": papeis
        }
        
        return True, dados_usuario, f"✅ Bem-vindo, {nome}!"
        
    except Exception as e:
        return False, None, f"❌ Erro ao autenticar: {e}"
    finally:
        conn.close()


def obter_usuario_logado() -> Optional[Dict]:
    """
    Retorna os dados do usuário logado via Streamlit session_state.
    
    Returns:
        Dicionário com dados do usuário ou None
    """
    return st.session_state.get("usuario_logado")


def fazer_logout():
    """
    Remove o usuário da sessão.
    """
    if "usuario_logado" in st.session_state:
        del st.session_state["usuario_logado"]
    st.success("✅ Logout realizado com sucesso!")
    st.rerun()


def atualizar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> Tuple[bool, str]:
    """
    Atualiza a senha de um usuário.
    
    Args:
        usuario_id: ID do usuário
        senha_atual: Senha atual para confirmação
        nova_senha: Nova senha
        
    Returns:
        (sucesso, mensagem)
    """
    if len(nova_senha) < 8:
        return False, "❌ Nova senha deve ter no mínimo 8 caracteres"
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Busca senha atual
        cursor.execute(
            "SELECT senha_hash FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False, "❌ Usuário não encontrado"
        
        senha_hash_atual = row[0]
        
        # Verifica senha atual
        if not verificar_senha(senha_atual, senha_hash_atual):
            return False, "❌ Senha atual incorreta"
        
        # Gera hash da nova senha
        novo_hash = hash_senha(nova_senha)
        
        # Atualiza
        cursor.execute(
            "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
            (novo_hash, usuario_id)
        )
        
        conn.commit()
        return True, "✅ Senha atualizada com sucesso!"
        
    except Exception as e:
        return False, f"❌ Erro ao atualizar senha: {e}"
    finally:
        conn.close()



def desativar_usuario(usuario_id: int, admin_id: int) -> Tuple[bool, str]:
    """
    Desativa um usuário (não deleta, apenas marca como inativo).
    
    Args:
        usuario_id: ID do usuário a desativar
        admin_id: ID do admin que está desativando
        
    Returns:
        (sucesso, mensagem)
    """
    if usuario_id == admin_id:
        return False, "❌ Você não pode desativar sua própria conta"
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE usuarios SET ativo = 0 WHERE id = ?",
            (usuario_id,)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            return False, "❌ Usuário não encontrado"
        
        return True, "✅ Usuário desativado com sucesso"
        
    except Exception as e:
        return False, f"❌ Erro ao desativar usuário: {e}"
    finally:
        conn.close()


def reativar_usuario(usuario_id: int) -> Tuple[bool, str]:
    """
    Reativa um usuário desativado.
    
    Args:
        usuario_id: ID do usuário a reativar
        
    Returns:
        (sucesso, mensagem)
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE usuarios SET ativo = 1, tentativas_login = 0, bloqueado_ate = NULL WHERE id = ?",
            (usuario_id,)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            return False, "❌ Usuário não encontrado"
        
        return True, "✅ Usuário reativado com sucesso"
        
    except Exception as e:
        return False, f"❌ Erro ao reativar usuário: {e}"
    finally:
        conn.close()


def listar_usuarios() -> list:
    """
    Lista todos os usuários do sistema.
    
    Returns:
        Lista de dicionários com dados dos usuários
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT 
            u.id, u.nome, u.email, u.ativo, u.ultimo_acesso, u.criado_em,
            GROUP_CONCAT(p.nome, ', ') as papeis
        FROM usuarios u
        LEFT JOIN usuario_papel up ON u.id = up.usuario_id
        LEFT JOIN papeis p ON up.papel_id = p.id
        GROUP BY u.id
        ORDER BY u.nome
        """
    )
    
    usuarios = []
    for row in cursor.fetchall():
        usuarios.append({
            "id": row[0],
            "nome": row[1],
            "email": row[2],
            "ativo": bool(row[3]),
            "ultimo_acesso": row[4],
            "criado_em": row[5],
            "papeis": row[6] or ""
        })
    
    conn.close()
    return usuarios


def contar_usuarios():
    """Retorna a quantidade de usuários no banco (0 se tabela não existir)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def criar_usuario_admin_inicial():
    """
    Cria o usuário admin padrão se não existir nenhum.
    ATENÇÃO: Executar apenas na primeira instalação!
    
    Credenciais:
        Email: admin@fortcordis.com
        Senha: Admin@2026
        
    ⚠️ ALTERE ESTA SENHA IMEDIATAMENTE APÓS O PRIMEIRO LOGIN!
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Verifica se já existe algum usuário
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    count = cursor.fetchone()[0]
    
    if count > 0:
        conn.close()
        print("ℹ️ Já existem usuários no sistema. Admin inicial não criado.")
        return False, "Já existem usuários"
    
    conn.close()
    
    # Cria admin
    sucesso, msg = criar_usuario(
        nome="Administrador",
        email="admin@fortcordis.com",
        senha="Admin@2026",
        papel="admin"
    )
    
    if sucesso:
        print("\n" + "="*70)
        print("🔐 USUÁRIO ADMIN CRIADO COM SUCESSO!")
        print("="*70)
        print("Email: admin@fortcordis.com")
        print("Senha: Admin@2026")
        print("\n⚠️  ALTERE ESTA SENHA IMEDIATAMENTE APÓS O PRIMEIRO LOGIN!")
        print("="*70 + "\n")
    
    return sucesso, msg


# ============================================================================
# FUNÇÕES DE INTERFACE (para usar no Streamlit)
# ============================================================================

def mostrar_info_usuario():
    """
    Exibe informações do usuário logado na sidebar.
    """
    usuario = obter_usuario_logado()
    if not usuario:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 {usuario['nome']}**")
    st.sidebar.caption(f"📧 {usuario['email']}")
    
    papeis = ", ".join([p["nome"].title() for p in usuario["papeis"]])
    st.sidebar.caption(f"🎭 {papeis}")
    
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        fazer_logout()


# ============================================================================
# INICIALIZAÇÃO (executar uma vez)
# ============================================================================

if __name__ == "__main__":
    print("🔧 Inicializando sistema de autenticação...")
    
    # Garante que a pasta existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Cria tabelas
    inicializar_tabelas_auth()
    
    # Insere papéis padrão
    inserir_papeis_padrao()
    
    # Cria admin inicial
    criar_usuario_admin_inicial()
    
    print("\n✅ Sistema de autenticação pronto para uso!")
    print("\nPróximos passos:")
    print("1. Execute o fortcordis_app.py")
    print("2. Faça login com admin@fortcordis.com / Admin@2026")
    print("3. ALTERE A SENHA IMEDIATAMENTE!")
    print("4. Crie outros usuários conforme necessário\n")

# ============================================================================
# FUNÇÕES DE TOKEN
# ============================================================================

def criar_token_persistente(usuario_id, duracao_dias=30):
    """Cria token para manter login"""
    try:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expira_em = datetime.now() + timedelta(days=duracao_dias)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessoes_persistentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expira_em TIMESTAMP NOT NULL,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO sessoes_persistentes (usuario_id, token_hash, expira_em)
            VALUES (?, ?, ?)
        """, (usuario_id, token_hash, expira_em))
        
        conn.commit()
        conn.close()
        
        return token
    except Exception as e:
        print(f"Erro ao criar token: {e}")
        return None

def validar_token_persistente(token):
    """Valida token e retorna usuario_id"""
    if not token:
        return None
    
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usuario_id
            FROM sessoes_persistentes
            WHERE token_hash = ?
            AND ativo = 1
            AND expira_em > datetime('now')
        """, (token_hash,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        return resultado[0] if resultado else None
    except:
        return None

def invalidar_token_persistente(token):
    """Remove token (logout)"""
    if not token:
        return
    
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessoes_persistentes
            SET ativo = 0
            WHERE token_hash = ?
        """, (token_hash,))
        
        conn.commit()
        conn.close()
    except:
        pass

def limpar_tokens_expirados():
    """Remove tokens expirados"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sessoes_persistentes
            WHERE expira_em < datetime('now')
        """)
        
        conn.commit()
        conn.close()
    except:
        pass

def carregar_sessao_por_token(token):
    """Carrega dados do usuário pelo token"""
    usuario_id = validar_token_persistente(token)
    
    if not usuario_id:
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nome, email
            FROM usuarios
            WHERE id = ? AND ativo = 1
        """, (usuario_id,))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            conn.close()
            return False
        
        conn.close()
        
        # ✅ Salva apenas dados básicos
        # As permissões serão carregadas pelo rbac.py quando necessário
        st.session_state["autenticado"] = True
        st.session_state["usuario_id"] = usuario_id
        st.session_state["usuario_nome"] = usuario[0]
        st.session_state["usuario_email"] = usuario[1]
        st.session_state["auth_token"] = token
        st.session_state["permissoes"] = carregar_permissoes_usuario(usuario_id)
        
        return True
        
    except Exception as e:
        print(f"Erro ao carregar sessão: {e}")
        return False
    
def carregar_permissoes_usuario(usuario_id):
    """Carrega permissões do usuário (papéis + diretas)"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        permissoes_set = set()
        
        # 1. Permissões via PAPÉIS
        cursor.execute("""
            SELECT DISTINCT p.modulo || '.' || p.acao as permissao
            FROM usuarios u
            JOIN usuario_papel up ON u.id = up.usuario_id
            JOIN papel_permissao pp ON up.papel_id = pp.papel_id
            JOIN permissoes p ON pp.permissao_id = p.id
            WHERE u.id = ?
        """, (usuario_id,))
        
        for row in cursor.fetchall():
            permissoes_set.add(row[0])
        
        # 2. Permissões DIRETAS
        cursor.execute("""
            SELECT DISTINCT p.modulo || '.' || p.acao as permissao
            FROM usuario_permissao up
            JOIN permissoes p ON up.permissao_id = p.id
            WHERE up.usuario_id = ?
            AND (up.concedida = 1 OR up.concedida IS NULL)
        """, (usuario_id,))
        
        for row in cursor.fetchall():
            permissoes_set.add(row[0])
        
        conn.close()
        
        return list(permissoes_set)
        
    except Exception as e:
        print(f"Erro ao carregar permissões: {e}")
        return []    

# ============================================================================
# TELA DE LOGIN
# ============================================================================
# ============================================================================
# SISTEMA DE SESSÃO PERSISTENTE COM ARQUIVO LOCAL
# Funciona melhor que cookies no Streamlit
# ============================================================================

import json
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

# ============================================================================
# FUNÇÕES DE SESSÃO LOCAL
# ============================================================================

def obter_caminho_sessao():
    """Retorna caminho do arquivo de sessão persistente"""
    # Usa pasta temporária do usuário
    pasta_sessao = Path.home() / ".fortcordis"
    pasta_sessao.mkdir(exist_ok=True)
    return pasta_sessao / "sessao.json"

def salvar_sessao_persistente(token):
    """Salva token em arquivo local"""
    try:
        arquivo_sessao = obter_caminho_sessao()
        
        dados = {
            "token": token,
            "criado_em": datetime.now().isoformat(),
            "expira_em": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        with open(arquivo_sessao, 'w') as f:
            json.dump(dados, f)
        
        print(f"✅ Sessão salva em: {arquivo_sessao}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar sessão: {e}")
        return False

def carregar_sessao_persistente():
    """Carrega token do arquivo local se ainda válido"""
    try:
        arquivo_sessao = obter_caminho_sessao()
        
        if not arquivo_sessao.exists():
            return None
        
        with open(arquivo_sessao, 'r') as f:
            dados = json.load(f)
        
        # Verifica se expirou
        expira_em = datetime.fromisoformat(dados["expira_em"])
        
        if datetime.now() > expira_em:
            # Expirado, remove arquivo
            arquivo_sessao.unlink()
            return None
        
        print(f"✅ Sessão recuperada de: {arquivo_sessao}")
        return dados["token"]
        
    except Exception as e:
        print(f"❌ Erro ao carregar sessão: {e}")
        return None

def remover_sessao_persistente():
    """Remove arquivo de sessão (logout)"""
    try:
        arquivo_sessao = obter_caminho_sessao()
        
        if arquivo_sessao.exists():
            arquivo_sessao.unlink()
            print(f"✅ Sessão removida de: {arquivo_sessao}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao remover sessão: {e}")
        return False

# ============================================================================
# MODIFICAR mostrar_tela_login()
# ============================================================================

def mostrar_tela_login():
    """Tela de login com sessão persistente via arquivo"""
    
    limpar_tokens_expirados()
    
    # Garante que tabelas e papéis existem (primeira vez / deploy novo)
    try:
        inicializar_tabelas_auth()
        inserir_papeis_padrao()
        num_usuarios = contar_usuarios()
    except Exception:
        num_usuarios = 0
    
    # Forçar tela de primeiro usuário: adicione ?primeiro_usuario=1 na URL
    try:
        # Streamlit 1.28+: st.query_params.get("key") retorna string
        q = getattr(st, "query_params", None)
        if q is not None:
            p1 = q.get("primeiro_usuario") or q.get("criar_admin")
            force_criar = p1 == "1" if isinstance(p1, str) else (p1 and "1" in (p1 if isinstance(p1, (list, tuple)) else [p1]))
        else:
            # Versão antiga: experimental_get_query_params retorna dict de listas
            exp = getattr(st, "experimental_get_query_params", lambda: {})
            params = exp() or {}
            p1 = (params.get("primeiro_usuario") or params.get("criar_admin")) or []
            force_criar = "1" in (p1 if isinstance(p1, list) else [p1])
    except Exception:
        force_criar = False
    
    # Também forçar pela session_state (botão "Primeiro acesso?" na tela de login)
    if st.session_state.get("mostrar_criar_primeiro_usuario"):
        force_criar = True
        st.session_state.pop("mostrar_criar_primeiro_usuario", None)
    
    # Se não existe nenhum usuário (ou forçou pela URL), mostra tela "Criar primeiro usuário (admin)"
    if num_usuarios == 0 or force_criar:
        st.markdown("### 👤 Criar primeiro usuário (administrador)")
        st.caption("Não há usuários no sistema. Crie o primeiro para acessar.")
        with st.form("form_primeiro_usuario", clear_on_submit=True):
            nome = st.text_input("Nome completo", key="primeiro_nome")
            email = st.text_input("E-mail (será usado para login)", key="primeiro_email")
            senha = st.text_input("Senha (mínimo 8 caracteres)", type="password", key="primeiro_senha")
            senha2 = st.text_input("Confirmar senha", type="password", key="primeiro_senha2")
            if st.form_submit_button("Criar e entrar"):
                if not nome or not email or not senha:
                    st.error("Preencha nome, e-mail e senha.")
                elif len(senha) < 8:
                    st.error("A senha deve ter no mínimo 8 caracteres.")
                elif senha != senha2:
                    st.error("As senhas não coincidem.")
                else:
                    ok, msg = criar_usuario(nome=nome.strip(), email=email.strip().lower(), senha=senha, papel="admin")
                    if ok:
                        st.success(msg + " Faça login abaixo.")
                        st.rerun()
                    else:
                        st.error(msg)
        return False
    
    # ✅ VERIFICA SESSÃO PERSISTENTE
    if "auth_token" not in st.session_state:
        token_arquivo = carregar_sessao_persistente()
        
        if token_arquivo:
            print(f"🔍 Token encontrado no arquivo: {token_arquivo[:20]}...")
            
            if carregar_sessao_por_token(token_arquivo):
                st.session_state["auth_token"] = token_arquivo
                print("✅ Login automático realizado!")
                st.rerun()
            else:
                print("❌ Token inválido, removendo arquivo")
                remover_sessao_persistente()
    
    if st.session_state.get("autenticado"):
        return True
    
    # ========================================================================
    # FORMULÁRIO
    # ========================================================================
    
    st.markdown("### 🔐 Acesso ao Sistema")
    
    # Botão para abrir tela "Criar primeiro usuário" (útil quando ?primeiro_usuario=1 não funciona)
    if st.button("👤 Primeiro acesso? Criar usuário administrador", type="secondary", use_container_width=True):
        st.session_state["mostrar_criar_primeiro_usuario"] = True
        st.rerun()
    
    st.markdown("---")
    
    with st.form("form_login", clear_on_submit=False):
        email = st.text_input("📧 E-mail", key="input_email")
        senha = st.text_input("🔑 Senha", type="password", key="input_senha")
        
        lembrar_me = st.checkbox(
            "🔄 Manter-me conectado por 30 dias",
            value=False,
            help="Você não precisará fazer login novamente neste computador"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            btn_entrar = st.form_submit_button(
                "🚀 Entrar",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.form_submit_button("🧹 Limpar", use_container_width=True):
                st.session_state.clear()
                st.rerun()
    
    if btn_entrar:
        if not email or not senha:
            st.error("❌ Por favor, preencha e-mail e senha")
            return False
        
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nome, senha_hash
                FROM usuarios
                WHERE email = ? AND ativo = 1
            """, (email,))
            
            resultado = cursor.fetchone()
            
            if resultado:
                usuario_id, nome, senha_hash = resultado
                
                if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                    
                    cursor.execute("""
                        UPDATE usuarios
                        SET ultimo_acesso = ?, tentativas_login = 0
                        WHERE id = ?
                    """, (datetime.now().isoformat(), usuario_id))
                    
                    conn.commit()
                    conn.close()
                    
                    # Limpa sessão antiga
                    token_antigo = st.session_state.get("auth_token")
                    st.session_state.clear()
                    if token_antigo:
                        st.session_state["auth_token"] = token_antigo
                    
                    # Salva dados
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_id"] = usuario_id
                    st.session_state["usuario_nome"] = nome
                    st.session_state["usuario_email"] = email
                    st.session_state["permissoes"] = carregar_permissoes_usuario(usuario_id)
                    
                    # ✅ LEMBRAR-ME COM ARQUIVO
                    if lembrar_me:
                        token = criar_token_persistente(usuario_id, duracao_dias=30)
                        
                        if token:
                            st.session_state["auth_token"] = token
                            
                            # ✅ SALVA EM ARQUIVO
                            if salvar_sessao_persistente(token):
                                st.success("✅ Login realizado! Você permanecerá conectado neste computador.")
                            else:
                                st.warning("⚠️ Login realizado, mas não foi possível salvar a sessão persistente.")
                    else:
                        st.success("✅ Login realizado com sucesso!")
                    
                    st.rerun()
                else:
                    cursor.execute("""
                        UPDATE usuarios
                        SET tentativas_login = tentativas_login + 1
                        WHERE id = ?
                    """, (usuario_id,))
                    conn.commit()
                    conn.close()
                    
                    st.error("❌ E-mail ou senha incorretos")
                    return False
            else:
                conn.close()
                st.error("❌ E-mail ou senha incorretos")
                return False
                
        except Exception as e:
            st.error(f"❌ Erro ao fazer login: {e}")
            return False
    
    return False

# ============================================================================
# MODIFICAR fazer_logout()
# ============================================================================

def fazer_logout():
    """Logout com remoção de sessão persistente"""
    
    if "auth_token" in st.session_state:
        invalidar_token_persistente(st.session_state["auth_token"])
    
    # ✅ REMOVE ARQUIVO DE SESSÃO
    remover_sessao_persistente()
    
    st.session_state.clear()
    
    st.success("✅ Você saiu do sistema")
    st.rerun()

# ============================================================================
# ADICIONAR DEBUG (opcional, para testar)
# ============================================================================

def debug_sessao():
    """Mostra informações de debug da sessão"""
    arquivo = obter_caminho_sessao()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 DEBUG SESSÃO")
    st.sidebar.write(f"**Arquivo:** {arquivo}")
    st.sidebar.write(f"**Existe:** {arquivo.exists()}")
    
    if arquivo.exists():
        try:
            with open(arquivo, 'r') as f:
                dados = json.load(f)
            st.sidebar.write(f"**Token:** {dados['token'][:20]}...")
            st.sidebar.write(f"**Expira:** {dados['expira_em']}")
        except:
            st.sidebar.write("Erro ao ler arquivo")

# ============================================================================
# INSTRUÇÕES DE USO
# ============================================================================

