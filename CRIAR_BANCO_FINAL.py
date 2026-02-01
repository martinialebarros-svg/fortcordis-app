import sqlite3
from pathlib import Path

# Caminho do banco
DB_PATH = Path(r"C:\Users\marti\Desktop\FortCordis_Novo\fortcordis.db")

print(f"🗑️ Removendo banco antigo (se existir)...")
if DB_PATH.exists():
    DB_PATH.unlink()
    print("✅ Banco antigo removido")

print(f"\n🔧 Criando banco em: {DB_PATH}")

# Cria conexão
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("📋 Criando TODAS as tabelas...")

# ============================================================================
# TABELA 1: CLÍNICAS PARCEIRAS
# ============================================================================
cursor.execute("""
    CREATE TABLE clinicas_parceiras (
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
print("✅ Tabela 'clinicas_parceiras' criada")

# ============================================================================
# TABELA 2: AGENDAMENTOS
# ============================================================================
cursor.execute("""
    CREATE TABLE agendamentos (
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
print("✅ Tabela 'agendamentos' criada")

# ============================================================================
# TABELA 3: SERVIÇOS
# ============================================================================
cursor.execute("""
    CREATE TABLE servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        valor_base REAL NOT NULL,
        duracao_minutos INTEGER DEFAULT 60,
        ativo INTEGER DEFAULT 1,
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Tabela 'servicos' criada")

# ============================================================================
# TABELA 4: FINANCEIRO
# ============================================================================
cursor.execute("""
    CREATE TABLE financeiro (
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
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Tabela 'financeiro' criada")

# ============================================================================
# TABELA 5: ACOMPANHAMENTOS
# ============================================================================
cursor.execute("""
    CREATE TABLE acompanhamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agendamento_id INTEGER NOT NULL,
        paciente_nome TEXT NOT NULL,
        tutor_nome TEXT NOT NULL,
        tutor_whatsapp TEXT,
        data_ultimo_exame TEXT NOT NULL,
        proxima_avaliacao TEXT,
        dias_retorno INTEGER,
        status TEXT DEFAULT 'no_prazo',
        observacoes TEXT,
        lembrete_enviado INTEGER DEFAULT 0,
        data_lembrete TEXT,
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Tabela 'acompanhamentos' criada")

# Commit e fecha
conn.commit()
conn.close()

print("\n" + "=" * 80)
print("✅ BANCO CRIADO COM SUCESSO!")
print("=" * 80)

# Verifica
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tabelas = cursor.fetchall()
conn.close()

print(f"\n📊 Total de tabelas: {len(tabelas)}")
for t in tabelas:
    print(f"   ✅ {t[0]}")

print(f"\n📂 Arquivo criado em: {DB_PATH.absolute()}")
print(f"📏 Tamanho: {DB_PATH.stat().st_size} bytes")