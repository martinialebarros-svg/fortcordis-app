# Operações de banco para laudos (ecocardiograma, eletro, pressão arterial)
# Fase B: extraído do fortcordis_app.py
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from app.config import DB_PATH
from app.sql_safe import validar_tabela

logger = logging.getLogger(__name__)


def _criar_tabelas_laudos_se_nao_existirem(cursor):
    """Cria tabelas de laudos se não existirem (Streamlit Cloud / primeiro deploy)."""
    for nome_tabela, sql in [
        ("laudos_ecocardiograma", """
            CREATE TABLE IF NOT EXISTS laudos_ecocardiograma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'ecocardiograma',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                modo_m TEXT, modo_bidimensional TEXT, doppler TEXT, conclusao TEXT, observacoes TEXT,
                achados_normais TEXT, achados_alterados TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
        ("laudos_eletrocardiograma", """
            CREATE TABLE IF NOT EXISTS laudos_eletrocardiograma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'eletrocardiograma',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                ritmo TEXT, frequencia_cardiaca INTEGER, conclusao TEXT, observacoes TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
        ("laudos_pressao_arterial", """
            CREATE TABLE IF NOT EXISTS laudos_pressao_arterial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'pressao_arterial',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                pressao_sistolica INTEGER, pressao_diastolica INTEGER, conclusao TEXT, observacoes TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
    ]:
        cursor.execute(sql)


def salvar_laudo_no_banco(
    tipo_exame: str,
    dados_laudo: dict[str, Any],
    caminho_json: str,
    caminho_pdf: str,
) -> Tuple[Optional[int], Optional[str]]:
    """Salva o laudo no banco de dados. Retorna (laudo_id, None) ou (None, mensagem_erro)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        _criar_tabelas_laudos_se_nao_existirem(cursor)
        conn.commit()

        tabelas = {
            "ecocardiograma": "laudos_ecocardiograma",
            "eletrocardiograma": "laudos_eletrocardiograma",
            "pressao_arterial": "laudos_pressao_arterial"
        }

        tabela = tabelas.get(tipo_exame.lower())

        if not tabela:
            return None, f"Tipo inválido: {tipo_exame}"

        tabela = validar_tabela(tabela)
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas_existentes = [col[1] for col in cursor.fetchall()]

        # Aceita dados no topo ou dentro de dados_laudo["paciente"] (ex.: JSON da página Laudos)
        _pac = dados_laudo.get('paciente') or {}
        _nome = dados_laudo.get('nome_animal') or _pac.get('nome', '')
        _data = dados_laudo.get('data') or _pac.get('data_exame', '') or datetime.now().strftime('%Y-%m-%d')
        _peso_raw = dados_laudo.get('peso') or _pac.get('peso', 0)
        try:
            _peso = float(_peso_raw) if _peso_raw is not None and str(_peso_raw).strip() else None
        except (TypeError, ValueError):
            _peso = None
        paciente_id = dados_laudo.get('paciente_id')
        if paciente_id is not None and not isinstance(paciente_id, int):
            try:
                paciente_id = int(paciente_id)
            except (TypeError, ValueError):
                paciente_id = None
        clinica_id = dados_laudo.get('clinica_id')
        if clinica_id is not None and not isinstance(clinica_id, int):
            try:
                clinica_id = int(clinica_id)
            except (TypeError, ValueError):
                clinica_id = None

        dados_possiveis = {
            'nome_paciente': _nome,
            'especie': dados_laudo.get('especie') or _pac.get('especie', ''),
            'raca': dados_laudo.get('raca') or _pac.get('raca', ''),
            'idade': dados_laudo.get('idade') or _pac.get('idade', ''),
            'peso': _peso,
            'data_exame': _data,
            'tipo_exame': tipo_exame,
            'paciente_id': paciente_id,
            'clinica_id': clinica_id,
            'veterinario_id': dados_laudo.get('veterinario_id'),
            'criado_por': None,
            'modo_m': dados_laudo.get('modo_m', ''),
            'modo_bidimensional': dados_laudo.get('modo_2d', ''),
            'doppler': dados_laudo.get('doppler', ''),
            'achados_normais': dados_laudo.get('achados_normais', ''),
            'achados_alterados': dados_laudo.get('achados_alterados', ''),
            'conclusao': dados_laudo.get('conclusao', ''),
            'observacoes': dados_laudo.get('observacoes', ''),
            'arquivo_xml': str(caminho_json),
            'arquivo_pdf': str(caminho_pdf),
            'status': 'finalizado'
        }

        colunas_usar = []
        valores_usar = []

        for col in colunas_existentes:
            if col in ['id', 'data_criacao', 'data_modificacao']:
                continue
            if col in dados_possiveis:
                valor = dados_possiveis[col]
                colunas_usar.append(col)
                valores_usar.append(valor)

        if not colunas_usar:
            conn.close()
            return None, "Nenhuma coluna para inserir"

        placeholders = ', '.join(['?' for _ in colunas_usar])
        colunas_str = ', '.join(colunas_usar)
        query = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
        cursor.execute(query, valores_usar)

        laudo_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return laudo_id, None

    except Exception as e:
        logger.exception("Falha ao salvar laudo no banco: tipo=%s", tipo_exame)
        return None, str(e)


def listar_animais_tutores_de_laudos(termo: Optional[str] = None, limite: int = 15) -> list:
    """
    Lista pares (animal, tutor) distintos que aparecem em laudos (arquivos ou ecocardiograma),
    opcionalmente filtrados por termo (nome do animal ou tutor).
    Para vincular um novo agendamento a um paciente que já tem exame no sistema.
    Retorna lista de dicts: [{"paciente": str, "tutor": str, "fonte": "laudo"}, ...].
    """
    if not termo or not str(termo).strip():
        return []
    termo = f"%{str(termo).strip()}%"
    out = []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        # laudos_arquivos
        cursor.execute(
            """SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_arquivos'"""
        )
        if cursor.fetchone():
            cursor.execute("""
                SELECT DISTINCT TRIM(COALESCE(nome_animal,'')) AS animal, TRIM(COALESCE(nome_tutor,'')) AS tutor
                FROM laudos_arquivos
                WHERE (UPPER(COALESCE(nome_animal,'')) LIKE UPPER(?) OR UPPER(COALESCE(nome_tutor,'')) LIKE UPPER(?))
                  AND (TRIM(COALESCE(nome_animal,'')) != '' OR TRIM(COALESCE(nome_tutor,'')) != '')
                LIMIT ?
            """, (termo, termo, limite))
            for row in cursor.fetchall():
                out.append({"paciente": row[0] or "", "tutor": row[1] or "", "fonte": "laudo"})
        # laudos_ecocardiograma (nome_paciente = animal)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_ecocardiograma'"
        )
        if cursor.fetchone():
            cursor.execute("""
                SELECT DISTINCT TRIM(COALESCE(nome_paciente,'')) AS animal, '' AS tutor
                FROM laudos_ecocardiograma
                WHERE UPPER(COALESCE(nome_paciente,'')) LIKE UPPER(?)
                  AND TRIM(COALESCE(nome_paciente,'')) != ''
                LIMIT ?
            """, (termo, limite))
            for row in cursor.fetchall():
                entry = {"paciente": row[0] or "", "tutor": row[1] or "", "fonte": "laudo"}
                if entry not in out and not any(
                    o["paciente"] == entry["paciente"] and o["tutor"] == entry["tutor"] for o in out
                ):
                    out.append(entry)
        conn.close()
    except Exception as e:
        logger.exception("Falha ao listar animais/tutores de laudos: %s", e)
    return out[:limite]


def buscar_laudos(
    tipo_exame: Optional[str] = None,
    nome_paciente: Optional[str] = None,
) -> Tuple[list, Optional[str]]:
    """Busca laudos no banco. Retorna (lista_laudos, None) ou ([], mensagem_erro)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        tabelas = [
            "laudos_ecocardiograma",
            "laudos_eletrocardiograma",
            "laudos_pressao_arterial"
        ]

        laudos = []

        for tabela in tabelas:
            tab = validar_tabela(tabela)
            query = """
                SELECT
                    id, tipo_exame, nome_paciente, especie, data_exame,
                    nome_clinica, arquivo_xml AS arquivo_json, arquivo_pdf
                FROM {tabela}
                WHERE 1=1
            """.format(tabela=tab)
            params = []

            if nome_paciente:
                query += " AND UPPER(nome_paciente) LIKE UPPER(?)"
                params.append(f"%{nome_paciente}%")

            query += " ORDER BY data_exame DESC, id DESC"

            cursor.execute(query, params)

            for row in cursor.fetchall():
                laudos.append(dict(row))

        conn.close()

        laudos.sort(key=lambda x: x.get('data_exame', ''), reverse=True)

        return laudos, None

    except Exception as e:
        logger.exception("Falha ao buscar laudos no banco")
        return [], str(e)


def carregar_laudo_para_edicao(caminho_json):
    """Carrega JSON do laudo para editar."""
    try:
        json_path = Path(caminho_json)

        if not json_path.exists():
            return None, "Arquivo não encontrado"

        with open(json_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        return dados, None

    except Exception as e:
        logger.exception("Falha ao carregar laudo para edição: %s", caminho_json)
        return None, str(e)


def atualizar_laudo_editado(laudo_id, tipo_exame, caminho_json, dados_atualizados, novo_pdf_path=None):
    """Atualiza laudo após edição."""
    try:
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(dados_atualizados, f, ensure_ascii=False, indent=2)

        if novo_pdf_path:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            tabelas = {
                "ecocardiograma": "laudos_ecocardiograma",
                "eletrocardiograma": "laudos_eletrocardiograma",
                "pressao_arterial": "laudos_pressao_arterial"
            }

            tabela = tabelas.get(tipo_exame.lower())
            if not tabela:
                return False, f"Tipo de exame inválido: {tipo_exame}"

            tabela = validar_tabela(tabela)
            cursor.execute(f"""
                UPDATE {tabela}
                SET arquivo_pdf = ?, data_modificacao = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (str(novo_pdf_path), laudo_id))

            conn.commit()
            conn.close()

        return True, None

    except Exception as e:
        logger.exception("Falha ao atualizar laudo editado id=%s", laudo_id)
        return False, str(e)


def salvar_laudo_arquivo_no_banco(
    nome_base: str,
    data_exame: str,
    nome_animal: str,
    nome_tutor: str,
    nome_clinica: str,
    tipo_exame: str,
    conteudo_json: Union[bytes, str],
    conteudo_pdf: bytes,
    imagens: Optional[List[Tuple[str, bytes]]] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Salva laudo completo (JSON + PDF + imagens) na tabela laudos_arquivos.
    Tudo fica no banco em um único lugar; na nuvem, use um DB persistente (volume ou DB externo).
    Retorna (id_laudo_arquivo, None) ou (None, mensagem_erro).
    """
    try:
        if isinstance(conteudo_json, str):
            conteudo_json = conteudo_json.encode("utf-8")
        imagens = imagens or []

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_arquivos'"
        )
        if not cursor.fetchone():
            from app.db import _db_init
            _db_init()
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

        cursor.execute(
            """INSERT OR REPLACE INTO laudos_arquivos
               (data_exame, nome_animal, nome_tutor, nome_clinica, tipo_exame, nome_base, conteudo_json, conteudo_pdf, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data_exame,
                nome_animal or "",
                nome_tutor or "",
                nome_clinica or "",
                tipo_exame or "ecocardiograma",
                nome_base,
                conteudo_json,
                conteudo_pdf,
                datetime.now().isoformat(),
            ),
        )
        laudo_arquivo_id = cursor.lastrowid
        if laudo_arquivo_id == 0:
            cursor.execute("SELECT id FROM laudos_arquivos WHERE nome_base = ?", (nome_base,))
            row = cursor.fetchone()
            laudo_arquivo_id = row[0] if row else None

        if laudo_arquivo_id:
            cursor.execute("DELETE FROM laudos_arquivos_imagens WHERE laudo_arquivo_id = ?", (laudo_arquivo_id,))
            for ordem, (nome_arquivo, img_bytes) in enumerate(imagens):
                cursor.execute(
                    "INSERT INTO laudos_arquivos_imagens (laudo_arquivo_id, ordem, nome_arquivo, conteudo) VALUES (?, ?, ?, ?)",
                    (laudo_arquivo_id, ordem, nome_arquivo, img_bytes),
                )

        conn.commit()
        conn.close()
        return (laudo_arquivo_id, None)
    except Exception as e:
        logger.exception("Falha ao salvar laudo em laudos_arquivos: nome_base=%s", nome_base)
        return (None, str(e))
