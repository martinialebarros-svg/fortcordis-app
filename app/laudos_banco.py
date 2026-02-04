# Operações de banco para laudos (ecocardiograma, eletro, pressão arterial)
# Fase B: extraído do fortcordis_app.py
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH


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


def salvar_laudo_no_banco(tipo_exame, dados_laudo, caminho_json, caminho_pdf):
    """Salva o laudo no banco de dados."""
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

        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas_existentes = [col[1] for col in cursor.fetchall()]

        dados_possiveis = {
            'nome_paciente': dados_laudo.get('nome_animal', ''),
            'especie': dados_laudo.get('especie', ''),
            'raca': dados_laudo.get('raca', ''),
            'idade': dados_laudo.get('idade', ''),
            'peso': float(dados_laudo.get('peso', 0)) if dados_laudo.get('peso') else None,
            'data_exame': dados_laudo.get('data', datetime.now().strftime('%Y-%m-%d')),
            'tipo_exame': tipo_exame,
            'paciente_id': None,
            'clinica_id': None,
            'veterinario_id': None,
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
        return None, str(e)


def buscar_laudos(tipo_exame=None, nome_paciente=None):
    """Busca laudos no banco."""
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
            query = """
                SELECT
                    id, tipo_exame, nome_paciente, especie, data_exame,
                    nome_clinica, arquivo_xml AS arquivo_json, arquivo_pdf
                FROM {tabela}
                WHERE 1=1
            """.format(tabela=tabela)
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

            cursor.execute(f"""
                UPDATE {tabela}
                SET arquivo_pdf = ?, data_modificacao = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (str(novo_pdf_path), laudo_id))

            conn.commit()
            conn.close()

        return True, None

    except Exception as e:
        return False, str(e)
