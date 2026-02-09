"""
Serviço de Restore Points - Fort Cordis
Cria, lista, restaura e exclui snapshots do banco de dados.

Os snapshots são armazenados como BLOBs comprimidos (zlib) dentro do
próprio banco, na tabela `restore_points`. Isso garante que sobrevivam
a reboots em ambientes com storage efêmero (Streamlit Cloud).
"""

import sqlite3
import tempfile
import zlib
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH

# Limite de restore points mantidos (os mais antigos são removidos automaticamente)
MAX_RESTORE_POINTS = 10


def _garantir_tabela(conn):
    """Cria a tabela restore_points se não existir."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS restore_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            criado_em TEXT NOT NULL,
            tamanho_original INTEGER NOT NULL,
            dados BLOB NOT NULL
        )
    """)
    conn.commit()


def criar_restore_point(descricao=""):
    """
    Cria um restore point (snapshot comprimido do banco de dados atual).
    Retorna (sucesso: bool, mensagem: str, nome: str | None).
    """
    if not DB_PATH.exists():
        return False, "Banco de dados não encontrado.", None

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    desc_safe = descricao.strip()[:60] if descricao.strip() else ""
    nome = f"restore_{timestamp}"

    try:
        # 1) Fazer backup consistente para arquivo temporário usando a API do SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        conn_src = sqlite3.connect(str(DB_PATH))
        conn_tmp = sqlite3.connect(tmp_path)
        conn_src.backup(conn_tmp)
        conn_tmp.close()
        conn_src.close()

        # 2) Ler o arquivo temporário e comprimir com zlib
        raw = Path(tmp_path).read_bytes()
        tamanho_original = len(raw)
        dados_comprimidos = zlib.compress(raw, level=6)

        # 3) Limpar arquivo temporário
        Path(tmp_path).unlink(missing_ok=True)

        # 4) Salvar no banco principal
        conn = sqlite3.connect(str(DB_PATH))
        _garantir_tabela(conn)
        conn.execute(
            "INSERT INTO restore_points (nome, descricao, criado_em, tamanho_original, dados) VALUES (?, ?, ?, ?, ?)",
            (nome, desc_safe, agora.isoformat(), tamanho_original, dados_comprimidos),
        )
        conn.commit()

        # 5) Limpar antigos
        _limpar_antigos(conn)
        conn.close()

        tamanho_kb = tamanho_original / 1024
        comprimido_kb = len(dados_comprimidos) / 1024
        return True, (
            f"Restore point criado: {nome} "
            f"({tamanho_kb:.0f} KB original, {comprimido_kb:.0f} KB comprimido)"
        ), nome

    except Exception as e:
        # Limpar tmp se existir
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"Erro ao criar restore point: {e}", None


def listar_restore_points():
    """
    Lista todos os restore points disponíveis.
    Retorna lista de dicts ordenados do mais recente para o mais antigo.
    """
    if not DB_PATH.exists():
        return []

    try:
        conn = sqlite3.connect(str(DB_PATH))
        _garantir_tabela(conn)
        cursor = conn.execute(
            "SELECT id, nome, descricao, criado_em, tamanho_original, LENGTH(dados) as tamanho_comprimido "
            "FROM restore_points ORDER BY id DESC"
        )
        pontos = []
        for row in cursor.fetchall():
            rp_id, nome, descricao, criado_em, tamanho_original, tamanho_comprimido = row
            # Formatar data
            try:
                dt = datetime.fromisoformat(criado_em)
                data_str = dt.strftime("%d/%m/%Y %H:%M:%S")
            except (ValueError, TypeError):
                data_str = criado_em or ""

            pontos.append({
                "id": rp_id,
                "nome": nome,
                "descricao": descricao or "",
                "data_criacao": data_str,
                "tamanho_kb": tamanho_original / 1024,
                "tamanho_comprimido_kb": (tamanho_comprimido or 0) / 1024,
            })
        conn.close()
        return pontos
    except Exception:
        return []


def restaurar_restore_point(rp_id):
    """
    Restaura o banco de dados a partir de um restore point.
    Cria um restore point automático do estado atual antes de restaurar.
    Retorna (sucesso: bool, mensagem: str).
    """
    if not DB_PATH.exists():
        return False, "Banco de dados não encontrado."

    try:
        conn = sqlite3.connect(str(DB_PATH))
        _garantir_tabela(conn)
        row = conn.execute(
            "SELECT nome, dados FROM restore_points WHERE id = ?", (rp_id,)
        ).fetchone()
        conn.close()
    except Exception as e:
        return False, f"Erro ao ler restore point: {e}"

    if not row:
        return False, "Restore point não encontrado."

    nome_rp, dados_comprimidos = row

    # Descomprimir
    try:
        dados_raw = zlib.decompress(dados_comprimidos)
    except Exception:
        return False, "Erro ao descomprimir o restore point. Arquivo corrompido."

    # Validar que é um banco SQLite válido (magic bytes)
    if not dados_raw[:16].startswith(b"SQLite format 3"):
        return False, "O restore point não contém um banco SQLite válido."

    # Criar restore point automático antes de restaurar (segurança)
    ok_auto, msg_auto, _ = criar_restore_point("antes_restauracao")
    if not ok_auto:
        return False, f"Não foi possível criar backup de segurança: {msg_auto}"

    # Gravar o snapshot descomprimido em arquivo temporário e fazer backup para o banco
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp.write(dados_raw)
            tmp_path = tmp.name

        conn_src = sqlite3.connect(tmp_path)
        conn_dst = sqlite3.connect(str(DB_PATH))
        conn_src.backup(conn_dst)
        conn_dst.close()
        conn_src.close()
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"Erro ao restaurar: {e}"

    return True, (
        f"Banco restaurado com sucesso a partir de '{nome_rp}'. "
        "Um backup de segurança foi criado automaticamente."
    )


def excluir_restore_point(rp_id):
    """
    Exclui um restore point por ID.
    Retorna (sucesso: bool, mensagem: str).
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        _garantir_tabela(conn)
        cursor = conn.execute("DELETE FROM restore_points WHERE id = ?", (rp_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return False, "Restore point não encontrado."
        conn.close()
        # VACUUM para liberar espaço ocupado pelo BLOB removido
        try:
            conn2 = sqlite3.connect(str(DB_PATH))
            conn2.execute("VACUUM")
            conn2.close()
        except Exception:
            pass
        return True, "Restore point excluído com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir: {e}"


def _limpar_antigos(conn):
    """Remove os restore points mais antigos se ultrapassar MAX_RESTORE_POINTS."""
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM restore_points")
        total = cursor.fetchone()[0]
        if total > MAX_RESTORE_POINTS:
            excesso = total - MAX_RESTORE_POINTS
            conn.execute(
                "DELETE FROM restore_points WHERE id IN "
                "(SELECT id FROM restore_points ORDER BY id ASC LIMIT ?)",
                (excesso,),
            )
            conn.commit()
    except Exception:
        pass
