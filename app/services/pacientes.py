# Serviço de pacientes: listar, buscar, atualizar peso
import logging
import sqlite3
from typing import Optional

import pandas as pd

from app.config import DB_PATH

logger = logging.getLogger(__name__)


def listar_pacientes_com_tutor() -> pd.DataFrame:
    """
    Lista pacientes ativos com dados do tutor (para select em consultas, etc.).
    Colunas: id, paciente, especie, raca, nascimento, peso_kg, tutor_id, tutor, telefone.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql_query("""
            SELECT 
                p.id,
                p.nome as paciente,
                p.especie,
                p.raca,
                p.nascimento,
                p.peso_kg,
                t.id as tutor_id,
                t.nome as tutor,
                t.telefone
            FROM pacientes p
            JOIN tutores t ON p.tutor_id = t.id
            WHERE (p.ativo = 1 OR p.ativo IS NULL)
            ORDER BY p.nome
        """, conn)
        return df
    finally:
        conn.close()


def listar_pacientes_tabela() -> pd.DataFrame:
    """
    Lista pacientes para exibição em tabela (aba Pacientes do prontuário).
    Colunas: id, Paciente, Espécie, Raça, Nascimento, Tutor, Contato.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql_query("""
            SELECT 
                p.id,
                p.nome as 'Paciente',
                p.especie as 'Espécie',
                p.raca as 'Raça',
                COALESCE(p.nascimento, '-') as 'Nascimento',
                t.nome as 'Tutor',
                t.telefone as 'Contato'
            FROM pacientes p
            JOIN tutores t ON p.tutor_id = t.id
            WHERE (p.ativo = 1 OR p.ativo IS NULL)
            ORDER BY t.nome, p.nome
        """, conn)
        return df
    finally:
        conn.close()


def buscar_pacientes(
    nome: Optional[str] = None,
    tutor: Optional[str] = None,
    limite: int = 20,
) -> pd.DataFrame:
    """
    Busca pacientes por nome e/ou nome do tutor (ex.: prescrições).
    Colunas: id, paciente, especie, raca, sexo, nascimento, tutor, telefone.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        query = """
            SELECT p.id, p.nome as paciente, p.especie, p.raca, p.sexo, p.nascimento,
                   t.nome as tutor, t.telefone
            FROM pacientes p
            LEFT JOIN tutores t ON p.tutor_id = t.id
            WHERE 1=1
        """
        params = []
        if nome:
            query += " AND UPPER(p.nome) LIKE UPPER(?)"
            params.append(f"%{nome}%")
        if tutor:
            query += " AND UPPER(t.nome) LIKE UPPER(?)"
            params.append(f"%{tutor}%")
        query += " ORDER BY p.nome LIMIT ?"
        params.append(limite)
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


def buscar_pacientes_para_vinculo(
    nome_animal: Optional[str] = None,
    nome_tutor: Optional[str] = None,
    limite: int = 15,
) -> list:
    """
    Busca pacientes por nome do animal e/ou nome do tutor para vincular exame
    a um cadastro existente (evitar duplicata ao importar XML).
    Retorna lista de dicts: [{"id": paciente_id, "tutor_id": int, "paciente": str, "tutor": str}, ...].
    """
    if not nome_animal and not nome_tutor:
        return []
    conn = sqlite3.connect(str(DB_PATH))
    try:
        query = """
            SELECT p.id, p.tutor_id, p.nome as paciente, t.nome as tutor
            FROM pacientes p
            LEFT JOIN tutores t ON p.tutor_id = t.id
            WHERE (p.ativo = 1 OR p.ativo IS NULL)
        """
        params = []
        if nome_animal:
            query += " AND (UPPER(p.nome) LIKE UPPER(?) OR UPPER(p.nome) = UPPER(?))"
            termo = (nome_animal.strip() if nome_animal else "")
            params.append(f"%{termo}%")
            params.append(termo)
        if nome_tutor:
            query += " AND (UPPER(t.nome) LIKE UPPER(?) OR UPPER(t.nome) = UPPER(?))"
            termo_t = (nome_tutor.strip() if nome_tutor else "")
            params.append(f"%{termo_t}%")
            params.append(termo_t)
        query += " ORDER BY t.nome, p.nome LIMIT ?"
        params.append(limite)
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [
            {"id": r[0], "tutor_id": r[1], "paciente": r[2] or "", "tutor": r[3] or ""}
            for r in rows
        ]
    finally:
        conn.close()


def buscar_pacientes_por_termo_livre(
    termo: Optional[str] = None,
    limite: int = 20,
) -> list:
    """
    Busca pacientes por um único termo que pode ser nome do animal ou do tutor
    (para vincular agendamento a paciente já cadastrado).
    Retorna lista de dicts: [{"id", "tutor_id", "paciente", "tutor", "telefone", "fonte": "cadastro"}, ...].
    """
    if not termo or not str(termo).strip():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    try:
        t = f"%{str(termo).strip()}%"
        cursor = conn.execute("""
            SELECT p.id, p.tutor_id, p.nome, t.nome, COALESCE(t.telefone, '')
            FROM pacientes p
            JOIN tutores t ON p.tutor_id = t.id
            WHERE (p.ativo = 1 OR p.ativo IS NULL)
              AND (UPPER(p.nome) LIKE UPPER(?) OR UPPER(t.nome) LIKE UPPER(?))
            ORDER BY t.nome, p.nome
            LIMIT ?
        """, (t, t, limite))
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "tutor_id": r[1],
                "paciente": r[2] or "",
                "tutor": r[3] or "",
                "telefone": (r[4] or "").strip(),
                "fonte": "cadastro",
            }
            for r in rows
        ]
    finally:
        conn.close()


def atualizar_peso_paciente(paciente_id: int, peso_kg: float) -> bool:
    """Atualiza o peso do paciente. Retorna True se ok."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("UPDATE pacientes SET peso_kg = ? WHERE id = ?", (peso_kg, paciente_id))
        conn.commit()
        return True
    except Exception as e:
        logger.exception("Falha ao atualizar peso do paciente id=%s: %s", paciente_id, e)
        return False
    finally:
        conn.close()
