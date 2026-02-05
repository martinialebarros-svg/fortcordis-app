# Conexão SQLite e upserts (clinicas, tutores, pacientes) usados pelo app
import logging
import sqlite3
import time
from pathlib import Path
from datetime import datetime

import streamlit as st

from app.config import DB_PATH
from app.utils import nome_proprio_ptbr, _norm_key
from app.sql_safe import validar_coluna

logger = logging.getLogger(__name__)


def _db_conn_safe():
    """Abre o banco; se corrompido/travado, reinicia o arquivo para o app voltar a abrir."""
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
        conn.execute("SELECT 1")
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.exception("Falha ao conectar ao banco: %s", e)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        try:
            path = Path(DB_PATH)
            backup_path = None
            if path.exists():
                backup_path = path.parent / (path.stem + ".corrupted." + str(int(time.time())) + path.suffix)
                try:
                    path.rename(backup_path)
                except Exception:
                    try:
                        path.unlink()
                    except Exception:
                        pass
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            if "db_was_recovered" not in st.session_state:
                st.session_state["db_was_recovered"] = True
            logger.warning("Banco reiniciado após falha; backup em %s", backup_path or "N/A")
            return conn
        except Exception:
            raise


@st.cache_resource(show_spinner=False, max_entries=1)
def _db_conn():
    return _db_conn_safe()


def _db_init():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS clinicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nome_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tutores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nome_key TEXT NOT NULL UNIQUE,
            telefone TEXT,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tutor_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            nome_key TEXT NOT NULL,
            especie TEXT NOT NULL DEFAULT '',
            raca TEXT,
            sexo TEXT,
            nascimento TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(tutor_id, nome_key, especie),
            FOREIGN KEY(tutor_id) REFERENCES tutores(id)
        )""")
        for col, tipo in [("ativo", "INTEGER DEFAULT 1"), ("peso_kg", "REAL"), ("microchip", "TEXT"), ("observacoes", "TEXT")]:
            try:
                c = validar_coluna(col)
                conn.execute(f"ALTER TABLE pacientes ADD COLUMN {c} {tipo}")
            except (sqlite3.OperationalError, ValueError):
                pass
        for col, tipo in [("whatsapp", "TEXT"), ("ativo", "INTEGER DEFAULT 1")]:
            try:
                c = validar_coluna(col)
                conn.execute(f"ALTER TABLE tutores ADD COLUMN {c} {tipo}")
            except (sqlite3.OperationalError, ValueError):
                pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS laudos_arquivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_exame TEXT NOT NULL,
                nome_animal TEXT,
                nome_tutor TEXT,
                nome_clinica TEXT,
                tipo_exame TEXT DEFAULT 'ecocardiograma',
                nome_base TEXT UNIQUE,
                conteudo_json BLOB,
                conteudo_pdf BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS laudos_arquivos_imagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                laudo_arquivo_id INTEGER NOT NULL,
                ordem INTEGER DEFAULT 0,
                nome_arquivo TEXT,
                conteudo BLOB,
                FOREIGN KEY(laudo_arquivo_id) REFERENCES laudos_arquivos(id)
            )
        """)
        # Tabela consultas (prontuário — aba Consultas)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER NOT NULL,
                tutor_id INTEGER NOT NULL,
                data_consulta TEXT NOT NULL,
                hora_consulta TEXT,
                tipo_atendimento TEXT,
                motivo_consulta TEXT,
                anamnese TEXT,
                historico_atual TEXT,
                alimentacao TEXT,
                ambiente TEXT,
                comportamento TEXT,
                peso_kg REAL,
                temperatura_c REAL,
                frequencia_cardiaca INTEGER,
                frequencia_respiratoria INTEGER,
                tpc TEXT,
                mucosas TEXT,
                hidratacao TEXT,
                linfonodos TEXT,
                auscultacao_cardiaca TEXT,
                auscultacao_respiratoria TEXT,
                palpacao_abdominal TEXT,
                exame_fisico_geral TEXT,
                diagnostico_presuntivo TEXT,
                diagnostico_diferencial TEXT,
                diagnostico_definitivo TEXT,
                conduta_terapeutica TEXT,
                prescricao_id INTEGER,
                exames_solicitados TEXT,
                procedimentos_realizados TEXT,
                orientacoes TEXT,
                prognostico TEXT,
                data_retorno TEXT,
                observacoes TEXT,
                veterinario_id INTEGER NOT NULL,
                status TEXT DEFAULT 'finalizado',
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                data_modificacao TEXT,
                FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
                FOREIGN KEY (tutor_id) REFERENCES tutores(id),
                FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def db_upsert_clinica(nome: str):
    _db_init()
    conn = _db_conn()
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    if not key:
        return None
    row = conn.execute("SELECT id, nome FROM clinicas WHERE nome_key=?", (key,)).fetchone()
    if row:
        if nome and row["nome"] != nome:
            conn.execute("UPDATE clinicas SET nome=? WHERE id=?", (nome, row["id"]))
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO clinicas(nome, nome_key, created_at) VALUES(?,?,?)", (nome, key, now))
    conn.commit()
    return conn.execute("SELECT id FROM clinicas WHERE nome_key=?", (key,)).fetchone()["id"]


def db_upsert_tutor(nome: str, telefone: str = None):
    _db_init()
    conn = _db_conn()
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    if not key:
        return None
    row = conn.execute("SELECT id, nome, telefone FROM tutores WHERE nome_key=?", (key,)).fetchone()
    if row:
        updates = []
        params = []
        if nome and row["nome"] != nome:
            updates.append("nome=?"); params.append(nome)
        if telefone and (row["telefone"] or "") != telefone:
            updates.append("telefone=?"); params.append(telefone)
        if updates:
            params.append(row["id"])
            conn.execute(f"UPDATE tutores SET {', '.join(updates)} WHERE id=?", params)
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO tutores(nome, nome_key, telefone, created_at) VALUES(?,?,?,?)",
                 (nome, key, telefone, now))
    conn.commit()
    return conn.execute("SELECT id FROM tutores WHERE nome_key=?", (key,)).fetchone()["id"]


def db_upsert_paciente(tutor_id: int, nome: str, especie: str = None, raca: str = None,
                       sexo: str = None, nascimento: str = None):
    _db_init()
    conn = _db_conn()
    if not tutor_id:
        return None
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    especie = (especie or "").strip()
    raca = nome_proprio_ptbr(raca or "")
    sexo = (sexo or "").strip()
    nascimento = (nascimento or "").strip()
    if not key:
        return None
    row = conn.execute(
        "SELECT id, especie, raca, sexo, nascimento FROM pacientes WHERE tutor_id=? AND nome_key=? AND especie=?",
        (tutor_id, key, especie)
    ).fetchone()
    if row:
        updates = []
        params = []
        if raca and (row["raca"] or "") != raca:
            updates.append("raca=?"); params.append(raca)
        if sexo and (row["sexo"] or "") != sexo:
            updates.append("sexo=?"); params.append(sexo)
        if nascimento and (row["nascimento"] or "") != nascimento:
            updates.append("nascimento=?"); params.append(nascimento)
        if updates:
            params.append(row["id"])
            conn.execute(f"UPDATE pacientes SET {', '.join(updates)} WHERE id=?", params)
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO pacientes(tutor_id, nome, nome_key, especie, raca, sexo, nascimento, created_at) VALUES(?,?,?,?,?,?,?,?)",
                 (tutor_id, nome, key, especie, raca, sexo, nascimento, now))
    conn.commit()
    return conn.execute(
        "SELECT id FROM pacientes WHERE tutor_id=? AND nome_key=? AND especie=?",
        (tutor_id, key, especie)
    ).fetchone()["id"]
