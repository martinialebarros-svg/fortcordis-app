"""
Serviço de Restore Points - Fort Cordis
Cria, lista, restaura e exclui snapshots do banco de dados.
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH

# Pasta para armazenar restore points
RESTORE_DIR = DB_PATH.parent / "restore_points"

# Limite de restore points mantidos (os mais antigos são removidos automaticamente)
MAX_RESTORE_POINTS = 10


def _garantir_pasta():
    """Cria a pasta de restore points se não existir."""
    RESTORE_DIR.mkdir(parents=True, exist_ok=True)


def criar_restore_point(descricao=""):
    """
    Cria um restore point (cópia do banco de dados atual).
    Retorna (sucesso: bool, mensagem: str, nome_arquivo: str | None).
    """
    if not DB_PATH.exists():
        return False, "Banco de dados não encontrado.", None

    _garantir_pasta()

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H%M%S")
    desc_safe = descricao.strip().replace(" ", "_")[:30] if descricao.strip() else ""
    nome = f"restore_{timestamp}"
    if desc_safe:
        nome += f"_{desc_safe}"
    nome += ".db"
    destino = RESTORE_DIR / nome

    try:
        # Usar backup API do SQLite para garantir integridade (sem WAL residual)
        conn_src = sqlite3.connect(str(DB_PATH))
        conn_dst = sqlite3.connect(str(destino))
        conn_src.backup(conn_dst)
        conn_dst.close()
        conn_src.close()
    except Exception as e:
        return False, f"Erro ao criar restore point: {e}", None

    # Limpeza: remover os mais antigos se ultrapassar o limite
    _limpar_antigos()

    tamanho_kb = destino.stat().st_size / 1024
    return True, f"Restore point criado: {nome} ({tamanho_kb:.0f} KB)", nome


def listar_restore_points():
    """
    Lista todos os restore points disponíveis.
    Retorna lista de dicts: [{nome, data_criacao, tamanho_kb, caminho}, ...]
    Ordenados do mais recente para o mais antigo.
    """
    _garantir_pasta()
    pontos = []
    for arq in sorted(RESTORE_DIR.glob("restore_*.db"), reverse=True):
        stat = arq.stat()
        # Extrair timestamp do nome (restore_YYYYMMDD_HHMMSS_...)
        partes = arq.stem.split("_")
        data_str = ""
        if len(partes) >= 3:
            try:
                dt = datetime.strptime(f"{partes[1]}_{partes[2]}", "%Y%m%d_%H%M%S")
                data_str = dt.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                data_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
        else:
            data_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")

        # Extrair descricao do nome (após o terceiro _)
        descricao = ""
        if len(partes) > 3:
            descricao = " ".join(partes[3:]).replace("_", " ")

        pontos.append({
            "nome": arq.name,
            "data_criacao": data_str,
            "tamanho_kb": stat.st_size / 1024,
            "caminho": str(arq),
            "descricao": descricao,
        })
    return pontos


def restaurar_restore_point(nome_arquivo):
    """
    Restaura o banco de dados a partir de um restore point.
    Cria um restore point automático do estado atual antes de restaurar.
    Retorna (sucesso: bool, mensagem: str).
    """
    caminho = RESTORE_DIR / nome_arquivo
    if not caminho.exists():
        return False, f"Restore point '{nome_arquivo}' não encontrado."

    # Validar que o arquivo é um banco SQLite válido
    try:
        conn_test = sqlite3.connect(str(caminho))
        conn_test.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        conn_test.close()
    except Exception:
        return False, "O arquivo não é um banco de dados SQLite válido."

    # Criar restore point automático antes de restaurar (segurança)
    ok_auto, msg_auto, _ = criar_restore_point("antes_restauracao")
    if not ok_auto:
        return False, f"Não foi possível criar backup de segurança: {msg_auto}"

    try:
        # Usar backup API do SQLite para restauração segura
        conn_src = sqlite3.connect(str(caminho))
        conn_dst = sqlite3.connect(str(DB_PATH))
        conn_src.backup(conn_dst)
        conn_dst.close()
        conn_src.close()
    except Exception as e:
        return False, f"Erro ao restaurar: {e}"

    return True, f"Banco restaurado com sucesso a partir de '{nome_arquivo}'. Um backup de segurança foi criado automaticamente."


def excluir_restore_point(nome_arquivo):
    """
    Exclui um restore point específico.
    Retorna (sucesso: bool, mensagem: str).
    """
    caminho = RESTORE_DIR / nome_arquivo
    if not caminho.exists():
        return False, f"Restore point '{nome_arquivo}' não encontrado."

    try:
        caminho.unlink()
        return True, f"Restore point '{nome_arquivo}' excluído."
    except Exception as e:
        return False, f"Erro ao excluir: {e}"


def _limpar_antigos():
    """Remove os restore points mais antigos se ultrapassar MAX_RESTORE_POINTS."""
    pontos = sorted(RESTORE_DIR.glob("restore_*.db"), key=lambda p: p.stat().st_mtime)
    while len(pontos) > MAX_RESTORE_POINTS:
        mais_antigo = pontos.pop(0)
        try:
            mais_antigo.unlink()
        except Exception:
            pass
