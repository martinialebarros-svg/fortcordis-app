"""
Módulo RBAC (Role-Based Access Control) - Fort Cordis
Controle de permissões baseado em papéis

Este módulo gerencia quem pode fazer o quê no sistema.
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import streamlit as st
import os

logger = logging.getLogger(__name__)

# Caminho do banco: pasta do projeto (funciona no Streamlit Cloud) ou variável de ambiente
if os.environ.get("FORTCORDIS_DB_PATH"):
    DB_PATH = Path(os.environ["FORTCORDIS_DB_PATH"])
else:
    _root = Path(__file__).resolve().parent.parent
    DB_PATH = _root / "data" / "fortcordis.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============================================================================
# DEFINIÇÃO DE PERMISSÕES DO SISTEMA
# ============================================================================

PERMISSOES_SISTEMA = {
    "dashboard": {
        "descricao": "Dashboard principal",
        "acoes": ["ver"]
    },
    "agendamentos": {
        "descricao": "Gestão de agendamentos",
        "acoes": ["ver", "criar", "editar", "excluir", "confirmar", "cancelar"]
    },
    "prontuario": {
        "descricao": "Prontuário eletrônico",
        "acoes": ["ver", "criar", "editar", "ver_outros"]
    },
    "laudos": {
        "descricao": "Laudos veterinários",
        "acoes": ["ver", "criar", "editar", "assinar", "excluir", "ver_rascunhos"]
    },
    "prescricoes": {
        "descricao": "Prescrições e receitas",
        "acoes": ["ver", "criar", "editar", "excluir"]
    },
    "financeiro": {
        "descricao": "Gestão financeira",
        "acoes": ["ver", "criar", "editar", "aprovar", "cancelar", "exportar"]
    },
    "cadastros": {
        "descricao": "Cadastros gerais",
        "acoes": ["ver", "criar", "editar", "excluir"]
    },
    "relatorios": {
        "descricao": "Relatórios e análises",
        "acoes": ["ver", "gerar", "exportar"]
    },
    "configuracoes": {
        "descricao": "Configurações do sistema",
        "acoes": ["ver", "editar"]
    },
    "usuarios": {
        "descricao": "Gestão de usuários",
        "acoes": ["ver", "criar", "editar", "desativar", "alterar_permissoes"]
    },
    "auditoria": {
        "descricao": "Logs de auditoria",
        "acoes": ["ver", "exportar"]
    }
}


# ============================================================================
# PERMISSÕES POR PAPEL (ROLE)
# ============================================================================

PERMISSOES_POR_PAPEL = {
    "admin": {
        # Admin tem TUDO
        "dashboard": ["ver"],
        "agendamentos": ["ver", "criar", "editar", "excluir", "confirmar", "cancelar"],
        "prontuario": ["ver", "criar", "editar", "ver_outros"],
        "laudos": ["ver", "criar", "editar", "assinar", "excluir", "ver_rascunhos"],
        "prescricoes": ["ver", "criar", "editar", "excluir"],
        "financeiro": ["ver", "criar", "editar", "aprovar", "cancelar", "exportar"],
        "cadastros": ["ver", "criar", "editar", "excluir"],
        "relatorios": ["ver", "gerar", "exportar"],
        "configuracoes": ["ver", "editar"],
        "usuarios": ["ver", "criar", "editar", "desativar", "alterar_permissoes"],
        "auditoria": ["ver", "exportar"]
    },
    
    "recepcao": {
        # Recepção: foco em agenda, cadastros e financeiro básico
        "dashboard": ["ver"],
        "agendamentos": ["ver", "criar", "editar", "confirmar", "cancelar"],
        "prontuario": ["ver"],  # Só visualizar, não editar
        "laudos": ["ver"],  # Só visualizar laudos finalizados
        "prescricoes": ["ver"],
        "financeiro": ["ver", "criar"],  # Pode criar OS, mas não aprovar
        "cadastros": ["ver", "criar", "editar"],
        "relatorios": ["ver"],
        "configuracoes": ["ver"],
        "usuarios": [],  # Sem acesso
        "auditoria": []
    },
    
    "veterinario": {
        # Veterinário: foco em atendimento clínico
        "dashboard": ["ver"],
        "agendamentos": ["ver"],
        "prontuario": ["ver", "criar", "editar"],  # Só seus próprios
        "laudos": ["ver"],  # Pode ver, mas não assinar laudos cardio
        "prescricoes": ["ver", "criar", "editar", "excluir"],
        "financeiro": ["ver"],  # Só visualizar
        "cadastros": ["ver", "criar", "editar"],
        "relatorios": ["ver"],
        "configuracoes": ["ver"],
        "usuarios": [],
        "auditoria": []
    },
    
    "cardiologista": {
        # Cardiologista: foco em laudos cardio
        "dashboard": ["ver"],
        "agendamentos": ["ver"],
        "prontuario": ["ver", "criar", "editar"],
        "laudos": ["ver", "criar", "editar", "assinar", "ver_rascunhos"],  # Pode assinar!
        "prescricoes": ["ver", "criar", "editar", "excluir"],
        "financeiro": ["ver"],
        "cadastros": ["ver"],
        "relatorios": ["ver"],
        "configuracoes": ["ver"],
        "usuarios": [],
        "auditoria": []
    },
    
    "financeiro": {
        # Financeiro: foco em contas
        "dashboard": ["ver"],
        "agendamentos": ["ver"],
        "prontuario": [],  # Sem acesso a prontuários
        "laudos": [],
        "prescricoes": [],
        "financeiro": ["ver", "criar", "editar", "aprovar", "cancelar", "exportar"],
        "cadastros": ["ver"],
        "relatorios": ["ver", "gerar", "exportar"],
        "configuracoes": ["ver"],
        "usuarios": [],
        "auditoria": ["ver"]  # Pode ver auditoria financeira
    }
}


# ============================================================================
# FUNÇÕES DE GERENCIAMENTO DE PERMISSÕES
# ============================================================================

def inicializar_tabelas_permissoes() -> None:
    """
    Cria as tabelas de permissões no banco.
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        # Tabela de permissões disponíveis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modulo TEXT NOT NULL,
                acao TEXT NOT NULL,
                descricao TEXT,
                UNIQUE(modulo, acao)
            )
        """)

        # Tabela de permissões por papel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papel_permissao (
                papel_id INTEGER NOT NULL,
                permissao_id INTEGER NOT NULL,
                PRIMARY KEY (papel_id, permissao_id),
                FOREIGN KEY (papel_id) REFERENCES papeis(id),
                FOREIGN KEY (permissao_id) REFERENCES permissoes(id)
            )
        """)

        # Tabela de permissões customizadas por usuário
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuario_permissao (
                usuario_id INTEGER NOT NULL,
                permissao_id INTEGER NOT NULL,
                concedida INTEGER DEFAULT 1,
                PRIMARY KEY (usuario_id, permissao_id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (permissao_id) REFERENCES permissoes(id)
            )
        """)

        conn.commit()
    logger.info("Tabelas de permissões criadas com sucesso")


def inserir_permissoes_padrao() -> None:
    """
    Insere todas as permissões definidas em PERMISSOES_SISTEMA.
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        for modulo, config in PERMISSOES_SISTEMA.items():
            for acao in config["acoes"]:
                try:
                    cursor.execute(
                        """
                        INSERT INTO permissoes (modulo, acao, descricao)
                        VALUES (?, ?, ?)
                        """,
                        (modulo, acao, f"{acao.title()} em {config['descricao']}")
                    )
                except sqlite3.IntegrityError:
                    # Permissão já existe
                    pass

        conn.commit()
    logger.info("Permissões padrão inseridas com sucesso")


def associar_permissoes_papeis() -> None:
    """
    Associa as permissões aos papéis conforme PERMISSOES_POR_PAPEL.
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        for papel_nome, permissoes in PERMISSOES_POR_PAPEL.items():
            # Busca ID do papel
            cursor.execute("SELECT id FROM papeis WHERE nome = ?", (papel_nome,))
            papel_row = cursor.fetchone()
            if not papel_row:
                logger.warning(f"Papel '{papel_nome}' não encontrado")
                continue
            papel_id = papel_row[0]

            # Para cada módulo
            for modulo, acoes in permissoes.items():
                for acao in acoes:
                    # Busca ID da permissão
                    cursor.execute(
                        "SELECT id FROM permissoes WHERE modulo = ? AND acao = ?",
                        (modulo, acao)
                    )
                    perm_row = cursor.fetchone()
                    if not perm_row:
                        logger.warning(f"Permissão {modulo}.{acao} não encontrada")
                        continue
                    perm_id = perm_row[0]

                    # Associa
                    try:
                        cursor.execute(
                            """
                            INSERT INTO papel_permissao (papel_id, permissao_id)
                            VALUES (?, ?)
                            """,
                            (papel_id, perm_id)
                        )
                    except sqlite3.IntegrityError:
                        # Já associado
                        pass

        conn.commit()
    logger.info("Permissões associadas aos papéis com sucesso")


# ============================================================================
# FUNÇÕES DE VERIFICAÇÃO DE PERMISSÕES
# ============================================================================

def usuario_tem_permissao(usuario_id: int, modulo: str, acao: str) -> bool:
    """
    Verifica se um usuário tem permissão para executar uma ação em um módulo.

    Args:
        usuario_id: ID do usuário
        modulo: Nome do módulo (ex: "laudos")
        acao: Nome da ação (ex: "assinar")

    Returns:
        True se tem permissão, False caso contrário
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        # Busca permissão através dos papéis do usuário
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM usuario_papel up
            JOIN papel_permissao pp ON up.papel_id = pp.papel_id
            JOIN permissoes p ON pp.permissao_id = p.id
            WHERE up.usuario_id = ? AND p.modulo = ? AND p.acao = ?
            """,
            (usuario_id, modulo, acao)
        )

        tem_por_papel = cursor.fetchone()[0] > 0

        # Verifica permissões customizadas (podem revogar ou conceder)
        cursor.execute(
            """
            SELECT up.concedida
            FROM usuario_permissao up
            JOIN permissoes p ON up.permissao_id = p.id
            WHERE up.usuario_id = ? AND p.modulo = ? AND p.acao = ?
            """,
            (usuario_id, modulo, acao)
        )

        custom = cursor.fetchone()

    # Se tem permissão customizada, ela prevalece
    if custom is not None:
        return bool(custom[0])

    # Senão, vai pelo papel
    return tem_por_papel


def obter_permissoes_usuario(usuario_id: int) -> Dict[str, List[str]]:
    """
    Retorna todas as permissões de um usuário organizadas por módulo.
    Se as tabelas de permissões não existirem (ex.: primeiro deploy), cria e tenta de novo.
    
    Args:
        usuario_id: ID do usuário
        
    Returns:
        Dicionário {modulo: [acoes]}
    """
    def _buscar():
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT p.modulo, p.acao
                FROM usuario_papel up
                JOIN papel_permissao pp ON up.papel_id = pp.papel_id
                JOIN permissoes p ON pp.permissao_id = p.id
                WHERE up.usuario_id = ?
                """,
                (usuario_id,)
            )
            permissoes = {}
            for modulo, acao in cursor.fetchall():
                if modulo not in permissoes:
                    permissoes[modulo] = []
                permissoes[modulo].append(acao)
            cursor.execute(
                """
                SELECT p.modulo, p.acao, up.concedida
                FROM usuario_permissao up
                JOIN permissoes p ON up.permissao_id = p.id
                WHERE up.usuario_id = ?
                """,
                (usuario_id,)
            )
            for modulo, acao, concedida in cursor.fetchall():
                if modulo not in permissoes:
                    permissoes[modulo] = []
                if concedida and acao not in permissoes[modulo]:
                    permissoes[modulo].append(acao)
                elif not concedida and acao in permissoes[modulo]:
                    permissoes[modulo].remove(acao)
            return permissoes

    try:
        return _buscar()
    except sqlite3.OperationalError:
        # Tabelas de permissões podem não existir no primeiro deploy; cria e tenta de novo
        try:
            inicializar_tabelas_permissoes()
            inserir_permissoes_padrao()
            associar_permissoes_papeis()
            return _buscar()
        except Exception:
            return {}


def usuario_tem_papel(usuario_id: int, papel: str) -> bool:
    """
    Verifica se usuário tem um papel específico.

    Args:
        usuario_id: ID do usuário
        papel: Nome do papel (ex: "admin")

    Returns:
        True se tem o papel, False caso contrário
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM usuario_papel up
            JOIN papeis p ON up.papel_id = p.id
            WHERE up.usuario_id = ? AND p.nome = ?
            """,
            (usuario_id, papel)
        )

        return cursor.fetchone()[0] > 0


# ============================================================================
# FUNÇÕES DE INTERFACE (para usar no Streamlit)
# ============================================================================

def exigir_permissao(modulo: str, acao: str) -> None:
    """
    Decorator/função para exigir permissão antes de executar código.
    Se não tiver permissão, mostra mensagem e para.
    """
    if not st.session_state.get("autenticado"):
        st.error("❌ Você precisa estar logado")
        st.stop()

    usuario_id = st.session_state.get("usuario_id")

    # Admin tem acesso total (verificação por papel, não por ID)
    if usuario_tem_papel(usuario_id, "admin"):
        return

    if not usuario_tem_permissao(usuario_id, modulo, acao):
        st.error(f"❌ Você não tem permissão para: {acao} em {modulo}")
        st.info("💡 Entre em contato com o administrador se precisar desta permissão")
        st.stop()


def verificar_permissao(modulo: str, acao: str) -> bool:
    """
    Verifica se o usuário logado tem uma permissão.
    Não para a execução, apenas retorna True/False.
    """
    if not st.session_state.get("autenticado"):
        return False

    usuario_id = st.session_state.get("usuario_id")

    # Admin tem acesso total (verificação por papel, não por ID)
    if usuario_tem_papel(usuario_id, "admin"):
        return True

    return usuario_tem_permissao(usuario_id, modulo, acao)



def mostrar_permissoes_usuario() -> None:
    """
    Exibe as permissões do usuário logado de forma legível.
    """
    # ✅ CORRIGIDO
    if not st.session_state.get("autenticado"):
        st.warning("Você não está logado")
        return
    
    usuario_id = st.session_state.get("usuario_id")
    
    st.subheader("🔐 Suas Permissões")
    
    permissoes = obter_permissoes_usuario(usuario_id)
    
    if not permissoes:
        st.warning("Você não tem permissões atribuídas")
        return
    
    for modulo, acoes in sorted(permissoes.items()):
        with st.expander(f"📋 {modulo.title().replace('_', ' ')}"):
            if acoes:
                for acao in sorted(acoes):
                    st.write(f"✅ {acao.replace('_', ' ').title()}")
            else:
                st.caption("Sem permissões específicas")


def atribuir_permissao_customizada(
    usuario_id: int,
    modulo: str,
    acao: str,
    conceder: bool = True
) -> Tuple[bool, str]:
    """
    Atribui ou revoga uma permissão customizada para um usuário.

    Args:
        usuario_id: ID do usuário
        modulo: Nome do módulo
        acao: Nome da ação
        conceder: True para conceder, False para revogar

    Returns:
        (sucesso, mensagem)
    """
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Busca ID da permissão
            cursor.execute(
                "SELECT id FROM permissoes WHERE modulo = ? AND acao = ?",
                (modulo, acao)
            )
            perm = cursor.fetchone()
            if not perm:
                return False, f"❌ Permissão {modulo}.{acao} não existe"

            perm_id = perm[0]

            # Insere ou atualiza
            cursor.execute(
                """
                INSERT INTO usuario_permissao (usuario_id, permissao_id, concedida)
                VALUES (?, ?, ?)
                ON CONFLICT(usuario_id, permissao_id) DO UPDATE SET concedida = ?
                """,
                (usuario_id, perm_id, 1 if conceder else 0, 1 if conceder else 0)
            )

            conn.commit()

        acao_texto = "concedida" if conceder else "revogada"
        return True, f"✅ Permissão {modulo}.{acao} {acao_texto} com sucesso"

    except Exception as e:
        return False, f"❌ Erro ao modificar permissão: {e}"


def remover_permissao_customizada(usuario_id: int, modulo: str, acao: str) -> Tuple[bool, str]:
    """
    Remove uma permissão customizada (volta para as permissões do papel).

    Args:
        usuario_id: ID do usuário
        modulo: Nome do módulo
        acao: Nome da ação

    Returns:
        (sucesso, mensagem)
    """
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Busca ID da permissão
            cursor.execute(
                "SELECT id FROM permissoes WHERE modulo = ? AND acao = ?",
                (modulo, acao)
            )
            perm = cursor.fetchone()
            if not perm:
                return False, f"❌ Permissão {modulo}.{acao} não existe"

            perm_id = perm[0]

            # Remove
            cursor.execute(
                """
                DELETE FROM usuario_permissao
                WHERE usuario_id = ? AND permissao_id = ?
                """,
                (usuario_id, perm_id)
            )

            conn.commit()

            if cursor.rowcount > 0:
                return True, f"✅ Permissão customizada removida (volta ao padrão do papel)"
            else:
                return False, "⚠️ Permissão customizada não existia"

    except Exception as e:
        return False, f"❌ Erro ao remover permissão: {e}"


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    print("🔧 Inicializando sistema de permissões (RBAC)...")
    
    # Garante que a pasta existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Cria tabelas
    inicializar_tabelas_permissoes()
    
    # Insere permissões
    inserir_permissoes_padrao()
    
    # Associa permissões aos papéis
    associar_permissoes_papeis()
    
    print("\n✅ Sistema RBAC configurado com sucesso!")
    print("\nPermissões por papel:")
    print("- Admin: Acesso total")
    print("- Recepção: Agenda, cadastros, financeiro básico")
    print("- Veterinário: Prontuário, prescrições")
    print("- Cardiologista: Laudos, assinaturas")
    print("- Financeiro: Contas a receber/pagar, relatórios\n")
