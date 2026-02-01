import sqlite3
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent / "fortcordis.db"

print(f"🔧 Criando banco em: {DB_PATH.absolute()}")

# Remove se já existir
if DB_PATH.exists():
    DB_PATH.unlink()
    print("🗑️ Banco antigo removido")

# Cria conexão
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("📋 Criando tabelas...")

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
        atualizado_em TEXT
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
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
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
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
conn.close()

print("✅ Banco criado com sucesso!")

# Verifica
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tabelas = cursor.fetchall()
conn.close()

print(f"\n📊 Total de tabelas criadas: {len(tabelas)}")
for tabela in tabelas:
    print(f"  ✅ {tabela[0]}")

print(f"\n✅ Arquivo criado em: {DB_PATH.absolute()}")