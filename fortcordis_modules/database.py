"""
Módulo de Banco de Dados - Fort Cordis
Inicializa e gerencia todas as tabelas do sistema
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime

# Banco: pasta do projeto (fortcordis_modules/../fortcordis.db) ou variável de ambiente
if os.environ.get("FORTCORDIS_DB_PATH"):
    DB_PATH = Path(os.environ["FORTCORDIS_DB_PATH"])
else:
    _root = Path(__file__).resolve().parent.parent
    DB_PATH = _root / "fortcordis.db"

# Garante que a pasta do banco existe (para ambientes de deploy)
if DB_PATH.parent != Path("."):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def inicializar_banco():
    """Inicializa todas as tabelas do banco de dados"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Tabela de Clínicas Parceiras
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinicas_parceiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            telefone TEXT,
            whatsapp TEXT,
            email TEXT,
            cnpj TEXT,
            inscricao_estadual TEXT,
            responsavel_veterinario TEXT,
            crmv_responsavel TEXT,
            observacoes TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Serviços
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            valor_base REAL NOT NULL,
            duracao_minutos INTEGER DEFAULT 60,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Pacotes (combos de serviços)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            valor_promocional REAL NOT NULL,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Relação Pacote-Serviços
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacote_servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pacote_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            FOREIGN KEY (pacote_id) REFERENCES pacotes(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id)
        )
    """)
    
    # Tabela de Descontos por Clínica
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parcerias_descontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinica_id INTEGER NOT NULL,
            servico_id INTEGER,
            tipo_desconto TEXT CHECK(tipo_desconto IN ('percentual', 'valor_fixo')) DEFAULT 'percentual',
            valor_desconto REAL NOT NULL,
            ativo INTEGER DEFAULT 1,
            data_inicio TEXT,
            data_fim TEXT,
            observacoes TEXT,
            FOREIGN KEY (clinica_id) REFERENCES clinicas_parceiras(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id)
        )
    """)
    
    # Tabelas de preço (Clínicas Fortaleza, Região Metropolitana, Atendimento Domiciliar, Plantão)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tabelas_preco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Valor do serviço por tabela de preço
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servico_preco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL,
            tabela_preco_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            UNIQUE(servico_id, tabela_preco_id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (tabela_preco_id) REFERENCES tabelas_preco(id)
        )
    """)
    
    # Tabela de Agendamentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            paciente TEXT NOT NULL,
            tutor TEXT,
            telefone TEXT,
            servico TEXT NOT NULL,
            clinica TEXT,
            observacoes TEXT,
            status TEXT DEFAULT 'Agendado',
            criado_em TEXT,
            criado_por_id INTEGER,
            criado_por_nome TEXT,
            confirmado_em TEXT,
            confirmado_por_id INTEGER,
            confirmado_por_nome TEXT,
            atualizado_em TEXT
        )
    """)
    
    # Serviços do Agendamento
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamento_servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            pacote_id INTEGER,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (pacote_id) REFERENCES pacotes(id)
        )
    """)
    
    # Tabela Financeiro
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER,
            clinica_id INTEGER NOT NULL,
            numero_os TEXT UNIQUE,
            descricao TEXT,
            valor_bruto REAL NOT NULL,
            valor_desconto REAL DEFAULT 0,
            valor_final REAL NOT NULL,
            status_pagamento TEXT CHECK(status_pagamento IN ('pendente', 'pago', 'cancelado')) DEFAULT 'pendente',
            forma_pagamento TEXT,
            data_competencia TEXT NOT NULL,
            data_vencimento TEXT,
            data_pagamento TEXT,
            observacoes TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id),
            FOREIGN KEY (clinica_id) REFERENCES clinicas_parceiras(id)
        )
    """)
    
    # Tabela de Medicamentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            principio_ativo TEXT,
            concentracao TEXT,
            unidade_concentracao TEXT,
            forma_farmaceutica TEXT,
            dose_padrao_mg_kg REAL,
            dose_min_mg_kg REAL,
            dose_max_mg_kg REAL,
            frequencia_padrao TEXT,
            via_administracao TEXT,
            observacoes TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Templates de Prescrição
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescricoes_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_template TEXT NOT NULL,
            indicacao TEXT,
            texto_prescricao TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Prescrições Realizadas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER,
            paciente_nome TEXT NOT NULL,
            tutor_nome TEXT NOT NULL,
            especie TEXT,
            peso_kg REAL,
            data_prescricao TEXT NOT NULL,
            texto_prescricao TEXT NOT NULL,
            medico_veterinario TEXT,
            crmv TEXT,
            caminho_pdf TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id)
        )
    """)
    
    # Tabela de Acompanhamento/Retornos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acompanhamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            paciente_nome TEXT NOT NULL,
            tutor_nome TEXT NOT NULL,
            tutor_whatsapp TEXT,
            data_ultimo_exame TEXT NOT NULL,
            proxima_avaliacao TEXT,
            dias_retorno INTEGER,
            status TEXT CHECK(status IN ('no_prazo', 'proximo', 'atrasado')) DEFAULT 'no_prazo',
            observacoes TEXT,
            lembrete_enviado INTEGER DEFAULT 0,
            data_lembrete TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id)
        )
    """)
    
    # Coluna tabela_preco_id em clinicas_parceiras (qual tabela de preço usar para a clínica)
    try:
        cursor.execute("PRAGMA table_info(clinicas_parceiras)")
        cols_cp = [r[1].lower() for r in cursor.fetchall()]
        if "tabela_preco_id" not in cols_cp:
            cursor.execute("ALTER TABLE clinicas_parceiras ADD COLUMN tabela_preco_id INTEGER REFERENCES tabelas_preco(id)")
    except sqlite3.OperationalError:
        pass
    
    # Seed tabelas de preço e valores (uma vez)
    cursor.execute("SELECT COUNT(*) FROM tabelas_preco")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO tabelas_preco (id, nome, descricao) VALUES (?, ?, ?)",
            [
                (1, "Clínicas Fortaleza", "Tabela padrão clínicas em Fortaleza"),
                (2, "Região Metropolitana", "Tabela região metropolitana"),
                (3, "Atendimento Domiciliar", "Atendimento domiciliar particular"),
                (4, "Clínicas Fortaleza - Plantão", "Semana após 18h | Sáb após 16h | Dom e Feriados"),
            ],
        )
        # Serviços (INSERT OR IGNORE para não duplicar)
        servicos_nomes = [
            ("Consulta", "Consulta cardiológica", 230),
            ("ECG", "Eletrocardiograma", 120),
            ("Ecocardiograma", "Ecocardiograma", 180),
            ("Pressão Arterial", "Aferição de pressão arterial", 40),
            ("Drenagem Efusão", "Drenagem de efusão", 280),
            ("Combo ECG + ECO", "ECG + Ecocardiograma", 250),
            ("Consulta Plantão", "Consulta em horário de plantão", 290),
            ("Eco Plantão", "Ecocardiograma plantão", 230),
            ("ECG Plantão", "ECG plantão", 170),
        ]
        for nome, desc, vb in servicos_nomes:
            cursor.execute(
                "INSERT OR IGNORE INTO servicos (nome, descricao, valor_base, ativo) VALUES (?, ?, ?, 1)",
                (nome, desc, vb),
            )
        cursor.execute("SELECT id, nome FROM servicos")
        servicos_map = {nome: sid for sid, nome in cursor.fetchall()}
        # servico_preco: (servico_id, tabela_preco_id, valor)
        # Tabela 1 = Clínicas Fortaleza
        precos_fortaleza = [
            ("Consulta", 230), ("ECG", 120), ("Ecocardiograma", 180), ("Pressão Arterial", 40),
            ("Drenagem Efusão", 280), ("Combo ECG + ECO", 250),
        ]
        # Tabela 2 = Região Metropolitana
        precos_metropolitana = [
            ("Consulta", 230), ("ECG", 150), ("Ecocardiograma", 200), ("Pressão Arterial", 60),
            ("Combo ECG + ECO", 300),
        ]
        # Tabela 3 = Atendimento Domiciliar
        precos_domiciliar = [
            ("Consulta", 290), ("Ecocardiograma", 290), ("ECG", 175), ("Pressão Arterial", 60),
        ]
        # Tabela 4 = Plantão
        precos_plantao = [
            ("Consulta Plantão", 290), ("Eco Plantão", 230), ("ECG Plantão", 170), ("Pressão Arterial", 60),
        ]
        for nome, valor in precos_fortaleza:
            sid = servicos_map.get(nome)
            if sid:
                cursor.execute("INSERT OR IGNORE INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, 1, ?)", (sid, valor))
        for nome, valor in precos_metropolitana:
            sid = servicos_map.get(nome)
            if sid:
                cursor.execute("INSERT OR IGNORE INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, 2, ?)", (sid, valor))
        for nome, valor in precos_domiciliar:
            sid = servicos_map.get(nome)
            if sid:
                cursor.execute("INSERT OR IGNORE INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, 3, ?)", (sid, valor))
        for nome, valor in precos_plantao:
            sid = servicos_map.get(nome)
            if sid:
                cursor.execute("INSERT OR IGNORE INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, 4, ?)", (sid, valor))
    
    conn.commit()
    conn.close()


def garantir_colunas_financeiro():
    """
    Garante que a tabela financeiro exista e tenha as colunas usadas pelo sistema.
    Útil quando o banco foi criado por outra versão ou em outro path.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financeiro'")
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agendamento_id INTEGER,
                    clinica_id INTEGER NOT NULL,
                    numero_os TEXT UNIQUE,
                    descricao TEXT,
                    valor_bruto REAL NOT NULL,
                    valor_desconto REAL DEFAULT 0,
                    valor_final REAL NOT NULL,
                    status_pagamento TEXT DEFAULT 'pendente',
                    forma_pagamento TEXT,
                    data_competencia TEXT NOT NULL,
                    data_vencimento TEXT,
                    data_pagamento TEXT,
                    observacoes TEXT,
                    data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id),
                    FOREIGN KEY (clinica_id) REFERENCES clinicas_parceiras(id)
                )
            """)
            conn.commit()
            conn.close()
            return
        cursor.execute("PRAGMA table_info(financeiro)")
        cols = [row[1].lower() for row in cursor.fetchall()]
    except Exception:
        conn.close()
        return
    colunas_adicionar = [
        ("numero_os", "TEXT"),
        ("data_pagamento", "TEXT"),
        ("forma_pagamento", "TEXT"),
        ("data_competencia", "TEXT"),
        ("descricao", "TEXT"),
        ("valor_final", "REAL"),
        ("valor_bruto", "REAL"),
        ("valor_desconto", "REAL"),
        ("status_pagamento", "TEXT"),
        ("clinica_id", "INTEGER"),
        ("agendamento_id", "INTEGER"),
    ]
    # Garantir coluna tabela_preco_id em clinicas_parceiras
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas_parceiras'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(clinicas_parceiras)")
            cols_cp = [r[1].lower() for r in cursor.fetchall()]
            if "tabela_preco_id" not in cols_cp:
                cursor.execute("ALTER TABLE clinicas_parceiras ADD COLUMN tabela_preco_id INTEGER")
    except sqlite3.OperationalError:
        pass
    for nome, tipo in colunas_adicionar:
        if nome.lower() not in cols:
            try:
                cursor.execute(f"ALTER TABLE financeiro ADD COLUMN {nome} {tipo}")
            except sqlite3.OperationalError:
                pass
    conn.commit()
    conn.close()


def garantir_colunas_agendamentos():
    """
    Garante que a tabela agendamentos exista e tenha as colunas usadas pelo sistema.
    Útil quando o banco foi criado por outra versão (ex.: coluna data_agendamento em vez de data).
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agendamentos'")
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agendamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    paciente TEXT NOT NULL,
                    tutor TEXT,
                    telefone TEXT,
                    servico TEXT NOT NULL,
                    clinica TEXT,
                    observacoes TEXT,
                    status TEXT DEFAULT 'Agendado',
                    criado_em TEXT,
                    criado_por_id INTEGER,
                    criado_por_nome TEXT,
                    confirmado_em TEXT,
                    confirmado_por_id INTEGER,
                    confirmado_por_nome TEXT,
                    atualizado_em TEXT
                )
            """)
            conn.commit()
            conn.close()
            return
        cursor.execute("PRAGMA table_info(agendamentos)")
        cols = [row[1].lower() for row in cursor.fetchall()]
    except Exception:
        conn.close()
        return
    # Se a tabela tem data_agendamento mas não tem data, adiciona data e copia ou usa alias na query
    if "data" not in cols and "data_agendamento" in cols:
        try:
            cursor.execute("ALTER TABLE agendamentos ADD COLUMN data TEXT")
            cursor.execute("UPDATE agendamentos SET data = data_agendamento WHERE data IS NULL OR data = ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    elif "data" not in cols:
        try:
            cursor.execute("ALTER TABLE agendamentos ADD COLUMN data TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    for col, tipo in [("hora", "TEXT"), ("paciente", "TEXT"), ("tutor", "TEXT"), ("telefone", "TEXT"),
                      ("servico", "TEXT"), ("clinica", "TEXT"), ("observacoes", "TEXT"), ("status", "TEXT"),
                      ("criado_por_id", "INTEGER"), ("criado_por_nome", "TEXT"),
                      ("confirmado_em", "TEXT"), ("confirmado_por_id", "INTEGER"), ("confirmado_por_nome", "TEXT")]:
        if col.lower() not in cols:
            try:
                cursor.execute(f"ALTER TABLE agendamentos ADD COLUMN {col} {tipo}")
            except sqlite3.OperationalError:
                pass
    conn.commit()
    conn.close()


def gerar_numero_os():
    """Gera número único de Ordem de Serviço"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM financeiro")
    count = cursor.fetchone()[0]
    conn.close()
    return f"OS-{datetime.now().year}-{(count + 1):05d}"

def calcular_valor_final(servico_id, clinica_id):
    """
    Calcula o valor final do serviço aplicando descontos da clínica.
    Retorna: (valor_base, valor_desconto, valor_final)
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Busca valor base do serviço
    cursor.execute("SELECT valor_base FROM servicos WHERE id = ?", (servico_id,))
    resultado = cursor.fetchone()
    if not resultado:
        conn.close()
        return (0.0, 0.0, 0.0)
    
    valor_base = resultado[0]
    
    # Verifica se há desconto específico para este serviço e clínica
    cursor.execute("""
        SELECT tipo_desconto, valor_desconto 
        FROM parcerias_descontos 
        WHERE clinica_id = ? 
        AND (servico_id = ? OR servico_id IS NULL)
        AND ativo = 1
        AND (data_inicio IS NULL OR date(data_inicio) <= date('now'))
        AND (data_fim IS NULL OR date(data_fim) >= date('now'))
        ORDER BY servico_id DESC
        LIMIT 1
    """, (clinica_id, servico_id))
    
    desconto = cursor.fetchone()
    conn.close()
    
    if not desconto:
        return (valor_base, 0.0, valor_base)
    
    tipo_desconto, valor_desconto = desconto
    
    if tipo_desconto == 'percentual':
        desconto_aplicado = valor_base * (valor_desconto / 100)
        valor_final = valor_base - desconto_aplicado
    else:  # valor_fixo
        desconto_aplicado = valor_desconto
        valor_final = valor_base - valor_desconto
    
    return (valor_base, desconto_aplicado, max(valor_final, 0.0))

def registrar_cobranca_automatica(agendamento_id, clinica_id, servicos_ids):
    """Registra cobrança automaticamente após conclusão do atendimento"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    valor_bruto = 0.0
    valor_final = 0.0
    valor_desconto_total = 0.0
    descricao_servicos = []
    
    for servico_id in servicos_ids:
        cursor.execute("SELECT nome FROM servicos WHERE id = ?", (servico_id,))
        servico = cursor.fetchone()
        if servico:
            nome_servico = servico[0]
            vb, vd, vf = calcular_valor_final(servico_id, clinica_id)
            valor_bruto += vb
            valor_desconto_total += vd
            valor_final += vf
            descricao_servicos.append(nome_servico)
    
    descricao = "Serviços: " + ", ".join(descricao_servicos)
    numero_os = gerar_numero_os()
    data_competencia = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        INSERT INTO financeiro (
            agendamento_id, clinica_id, numero_os, descricao,
            valor_bruto, valor_desconto, valor_final,
            status_pagamento, data_competencia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente', ?)
    """, (agendamento_id, clinica_id, numero_os, descricao,
          valor_bruto, valor_desconto_total, valor_final, data_competencia))
    
    conn.commit()
    conn.close()
    return numero_os


def dar_baixa_os(financeiro_id, data_pagamento=None, forma_pagamento=None):
    """
    Marca uma OS como paga (dar baixa no pagamento).
    data_pagamento: str YYYY-MM-DD ou None para hoje.
    forma_pagamento: str (ex: 'PIX', 'Transferência', 'Dinheiro', 'Cartão').
    Retorna True se atualizou, False se não encontrou ou já estava paga.
    """
    garantir_colunas_financeiro()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    data_pag = data_pagamento or datetime.now().strftime("%Y-%m-%d")
    forma = forma_pagamento or "Não informado"
    cursor.execute("""
        UPDATE financeiro
        SET status_pagamento = 'pago', data_pagamento = ?, forma_pagamento = ?
        WHERE id = ? AND (status_pagamento IS NULL OR status_pagamento = 'pendente')
    """, (data_pag, forma, financeiro_id))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def excluir_os(financeiro_id):
    """Remove uma ordem de serviço (OS) do financeiro. Retorna True se removeu, False caso contrário."""
    garantir_colunas_financeiro()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM financeiro WHERE id = ?", (financeiro_id,))
        conn.commit()
        ok = cursor.rowcount > 0
    except sqlite3.OperationalError:
        conn.rollback()
        ok = False
    finally:
        conn.close()
    return ok


def listar_financeiro_pendentes():
    """Retorna lista de OS pendentes (para cobrança / dar baixa)."""
    garantir_colunas_financeiro()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(financeiro)")
        col_names = [row[1] for row in cursor.fetchall()]
    except Exception:
        conn.close()
        return []
    has_numero_os = "numero_os" in col_names
    has_data_competencia = "data_competencia" in col_names
    select_numero = "f.numero_os" if has_numero_os else "f.id as numero_os"
    select_data = "f.data_competencia" if has_data_competencia else "NULL as data_competencia"
    order_by = "f.data_competencia DESC" if has_data_competencia else "f.id DESC"
    try:
        cursor.execute(f"""
            SELECT f.id, {select_numero}, f.clinica_id, c.nome as clinica_nome, c.whatsapp,
                   f.descricao, f.valor_final, f.status_pagamento, {select_data}
            FROM financeiro f
            LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
            WHERE f.status_pagamento = 'pendente' OR f.status_pagamento IS NULL
            ORDER BY {order_by}
        """)
        rows = cursor.fetchall()
        out = [dict(r) for r in rows]
        if not has_numero_os:
            for row in out:
                if row.get("numero_os") is None or str(row.get("numero_os")).isdigit():
                    row["numero_os"] = f"OS-{row.get('id', '')}"
    except sqlite3.OperationalError:
        out = []
    conn.close()
    return out


def atualizar_status_acompanhamentos():
    """Atualiza status dos acompanhamentos baseado nas datas"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    hoje = datetime.now().date()
    
    # Atualiza todos os acompanhamentos
    cursor.execute("SELECT id, proxima_avaliacao FROM acompanhamentos WHERE proxima_avaliacao IS NOT NULL")
    acompanhamentos = cursor.fetchall()
    
    for acomp_id, proxima_data in acompanhamentos:
        if proxima_data:
            try:
                data_obj = datetime.strptime(proxima_data, "%Y-%m-%d").date()
                dias_ate = (data_obj - hoje).days
                
                if dias_ate < 0:
                    status = 'atrasado'
                elif dias_ate <= 30:
                    status = 'proximo'
                else:
                    status = 'no_prazo'
                
                cursor.execute("UPDATE acompanhamentos SET status = ? WHERE id = ?", (status, acomp_id))
            except:
                pass
    
    conn.commit()
    conn.close()

# ============================================================================
# AGENDAMENTOS
# ============================================================================

def _col_data_agendamentos(cursor):
    """Retorna o nome da coluna de data na tabela agendamentos: 'data' ou 'data_agendamento'."""
    try:
        cursor.execute("PRAGMA table_info(agendamentos)")
        cols = [row[1] for row in cursor.fetchall()]
        return "data" if "data" in cols else ("data_agendamento" if "data_agendamento" in cols else "data")
    except Exception:
        return "data"


def criar_agendamento(data, hora, paciente, tutor, telefone, servico, clinica, observacoes="", status="Agendado", criado_por_id=None, criado_por_nome=None):
    """Cria um novo agendamento. Usa a coluna de data existente (data ou data_agendamento). Registra quem criou e quando."""
    garantir_colunas_agendamentos()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    col_data = _col_data_agendamentos(cursor)
    criado_em = datetime.now().isoformat()
    try:
        cursor.execute(f"""
            INSERT INTO agendamentos (
                {col_data}, hora, paciente, tutor, telefone, servico,
                clinica, observacoes, status, criado_em, criado_por_id, criado_por_nome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data, hora, paciente, tutor, telefone, servico, clinica,
              observacoes, status, criado_em, criado_por_id, criado_por_nome or ""))
    except sqlite3.OperationalError:
        conn.close()
        raise
    conn.commit()
    agendamento_id = cursor.lastrowid
    conn.close()
    return agendamento_id


def listar_agendamentos(data_inicio=None, data_fim=None, status=None, clinica=None):
    """Lista agendamentos com filtros opcionais. Tolerante a coluna data ou data_agendamento."""
    garantir_colunas_agendamentos()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(agendamentos)")
        col_names = [row[1] for row in cursor.fetchall()]
    except Exception:
        conn.close()
        return []
    col_data = "data" if "data" in col_names else ("data_agendamento" if "data_agendamento" in col_names else None)
    if not col_data:
        conn.close()
        return []
    query = f"SELECT * FROM agendamentos WHERE 1=1"
    params = []
    if data_inicio:
        query += f" AND {col_data} >= ?"
        params.append(data_inicio)
    if data_fim:
        query += f" AND {col_data} <= ?"
        params.append(data_fim)
    if status:
        query += " AND status = ?"
        params.append(status)
    if clinica:
        query += " AND clinica = ?"
        params.append(clinica)
    query += f" ORDER BY {col_data}, hora"
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    # Nomes das colunas reais (na ordem do SELECT *)
    cursor.execute("SELECT * FROM agendamentos LIMIT 0")
    real_cols = [d[0] for d in cursor.description]
    conn.close()
    # Normalizar para o app: sempre devolver chave 'data' (valor de data ou data_agendamento)
    agendamentos = []
    for row in rows:
        d = dict(zip(real_cols, row))
        if "data" not in d and "data_agendamento" in d:
            d["data"] = d["data_agendamento"]
        elif "data_agendamento" not in d and "data" in d:
            d["data_agendamento"] = d["data"]
        agendamentos.append(d)
    return agendamentos


def atualizar_agendamento(agendamento_id, **kwargs):
    """Atualiza um agendamento existente. Usa a coluna de data existente (data ou data_agendamento)."""
    garantir_colunas_agendamentos()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    col_data = _col_data_agendamentos(cursor)
    # Campos permitidos: mapear 'data' para o nome real da coluna; inclui confirmação (quem e quando)
    campos_permitidos = ['data', 'hora', 'paciente', 'tutor', 'telefone',
                        'servico', 'clinica', 'observacoes', 'status',
                        'confirmado_em', 'confirmado_por_id', 'confirmado_por_nome']
    updates = {k: v for k, v in kwargs.items() if k in campos_permitidos}
    if not updates:
        conn.close()
        return False
    # Nome real da coluna de data na tabela
    col_keys = list(updates.keys())
    if "data" in col_keys and col_data != "data":
        updates[col_data] = updates.pop("data")
    updates["atualizado_em"] = datetime.now().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    query = f"UPDATE agendamentos SET {set_clause} WHERE id = ?"
    params = list(updates.values()) + [agendamento_id]
    try:
        cursor.execute(query, params)
    except sqlite3.OperationalError:
        conn.close()
        return False
    conn.commit()
    sucesso = cursor.rowcount > 0
    conn.close()
    return sucesso


def deletar_agendamento(agendamento_id):
    """Deleta um agendamento e as OS (cobranças) vinculadas no financeiro."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM financeiro WHERE agendamento_id = ?", (agendamento_id,))
        cursor.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))
        conn.commit()
        sucesso = cursor.rowcount > 0
    except sqlite3.OperationalError:
        conn.rollback()
        sucesso = False
    finally:
        conn.close()
    return sucesso


def buscar_agendamento_por_id(agendamento_id):
    """Busca um agendamento específico por ID. Retorna dict com chave 'data' (normalizado)."""
    garantir_colunas_agendamentos()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    real_cols = [d[0] for d in cursor.description]
    conn.close()
    d = dict(zip(real_cols, row))
    if "data" not in d and "data_agendamento" in d:
        d["data"] = d["data"]
    elif "data_agendamento" not in d and "data" in d:
        d["data_agendamento"] = d["data"]
    return d


def _mapear_servico_agendamento_para_nome(servico_texto):
    """Mapeia o nome do serviço do agendamento para o nome usado em servicos/servico_preco."""
    s = (servico_texto or "").strip()
    mapeamento = {
        "consulta cardiológica": "Consulta",
        "consulta cardiologica": "Consulta",
        "eletrocardiograma": "ECG",
        "ecocardiograma": "Ecocardiograma",
        "pressão arterial": "Pressão Arterial",
        "pressao arterial": "Pressão Arterial",
        "retorno": "Consulta",
        "raio-x": "Consulta",  # fallback
        "outro": "Consulta",
    }
    return mapeamento.get(s.lower(), s)


def criar_os_ao_marcar_realizado(agendamento_id):
    """
    Cria uma OS (ordem de serviço) no financeiro quando o agendamento é marcado como realizado.
    Usa a tabela de preço da clínica (tabela_preco_id) e o valor do serviço em servico_preco.
    Retorna (numero_os, None) em sucesso ou (None, mensagem_erro) em falha.
    """
    garantir_colunas_financeiro()
    agend = buscar_agendamento_por_id(agendamento_id)
    if not agend:
        return None, "Agendamento não encontrado."
    servico_texto = (agend.get("servico") or "").strip()
    clinica_nome = (agend.get("clinica") or "").strip()
    if not clinica_nome:
        return None, "Agendamento sem clínica informada."
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, COALESCE(tabela_preco_id, 1) as tabela_preco_id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL) LIMIT 1",
            (clinica_nome,),
        )
        row_cli = cursor.fetchone()
        if not row_cli:
            conn.close()
            return None, f"Clínica '{clinica_nome}' não encontrada em Cadastros > Clínicas Parceiras."
        clinica_id, tabela_preco_id = row_cli[0], row_cli[1]
        nome_servico = _mapear_servico_agendamento_para_nome(servico_texto)
        cursor.execute("SELECT id, valor_base FROM servicos WHERE (ativo = 1 OR ativo IS NULL) AND (nome = ? OR nome LIKE ?) LIMIT 1", (nome_servico, f"%{nome_servico}%"))
        row_serv = cursor.fetchone()
        if not row_serv:
            conn.close()
            return None, f"Serviço '{servico_texto}' não encontrado em Cadastros > Serviços. Cadastre o serviço e a tabela de preço."
        servico_id, valor_base_fallback = row_serv[0], float(row_serv[1] or 0)
        cursor.execute(
            "SELECT valor FROM servico_preco WHERE servico_id = ? AND tabela_preco_id = ? LIMIT 1",
            (servico_id, tabela_preco_id),
        )
        row_preco = cursor.fetchone()
        valor_final = float(row_preco[0]) if row_preco else valor_base_fallback
        numero_os = gerar_numero_os()
        data_comp = datetime.now().strftime("%Y-%m-%d")
        descricao = f"{servico_texto} - {agend.get('paciente', '')}"
        cursor.execute("""
            INSERT INTO financeiro (agendamento_id, clinica_id, numero_os, descricao, valor_bruto, valor_desconto, valor_final, status_pagamento, data_competencia)
            VALUES (?, ?, ?, ?, ?, 0, ?, 'pendente', ?)
        """, (agendamento_id, clinica_id, numero_os, descricao, valor_final, valor_final, data_comp))
        conn.commit()
        conn.close()
        return numero_os, None
    except Exception as e:
        conn.rollback()
        conn.close()
        return None, str(e)


def contar_agendamentos_por_status():
    """Retorna contagem de agendamentos por status. Usa coluna data ou data_agendamento."""
    garantir_colunas_agendamentos()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    col_data = _col_data_agendamentos(cursor)
    try:
        cursor.execute(f"""
            SELECT status, COUNT(*) as total
            FROM agendamentos
            WHERE {col_data} >= date('now')
            GROUP BY status
        """)
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    
    resultado = {}
    for status, total in rows:
        resultado[status] = total
    
    return resultado

# Executa atualização ao carregar
if __name__ != "__main__":
    inicializar_banco()
