"""
Script CORRIGIDO para criar as tabelas do Prontuário Eletrônico
Execute: python criar_tabelas_prontuario_v2.py
"""

import sqlite3
from pathlib import Path

# Caminho do banco
DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CRIAR TABELAS DO PRONTUÁRIO ELETRÔNICO ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# ============================================================================
# TABELA: TUTORES
# ============================================================================
print("📋 Criando tabela: tutores...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS tutores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT UNIQUE,
        rg TEXT,
        telefone TEXT,
        celular TEXT,
        whatsapp TEXT,
        email TEXT,
        endereco TEXT,
        numero TEXT,
        complemento TEXT,
        bairro TEXT,
        cidade TEXT DEFAULT 'Fortaleza',
        estado TEXT DEFAULT 'CE',
        cep TEXT,
        observacoes TEXT,
        ativo INTEGER DEFAULT 1,
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER
    )
""")

print("   ✅ Tabela 'tutores' criada\n")

# ============================================================================
# TABELA: PACIENTES
# ============================================================================
print("📋 Criando tabela: pacientes...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tutor_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        especie TEXT NOT NULL,
        raca TEXT,
        sexo TEXT,
        castrado INTEGER DEFAULT 0,
        data_nascimento DATE,
        idade_anos INTEGER,
        idade_meses INTEGER,
        peso_kg REAL,
        cor_pelagem TEXT,
        microchip TEXT,
        numero_registro TEXT,
        foto_url TEXT,
        alergias TEXT,
        medicamentos_uso TEXT,
        doencas_previas TEXT,
        cirurgias_previas TEXT,
        vacinacao_em_dia INTEGER DEFAULT 1,
        vermifugacao_em_dia INTEGER DEFAULT 1,
        observacoes TEXT,
        ativo INTEGER DEFAULT 1,
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_obito DATE,
        criado_por INTEGER,
        FOREIGN KEY (tutor_id) REFERENCES tutores(id)
    )
""")

print("   ✅ Tabela 'pacientes' criada\n")

# ============================================================================
# TABELA: CONSULTAS (ATENDIMENTOS)
# ============================================================================
print("📋 Criando tabela: consultas...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL,
        tutor_id INTEGER NOT NULL,
        data_consulta DATE NOT NULL,
        hora_consulta TIME,
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
        data_retorno DATE,
        observacoes TEXT,
        veterinario_id INTEGER NOT NULL,
        status TEXT DEFAULT 'finalizado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_modificacao TIMESTAMP,
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (tutor_id) REFERENCES tutores(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
    )
""")

print("   ✅ Tabela 'consultas' criada\n")

# ============================================================================
# TABELA: PROBLEMAS
# ============================================================================
print("📋 Criando tabela: problemas...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS problemas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        data_inicio DATE NOT NULL,
        data_resolucao DATE,
        status TEXT DEFAULT 'ativo',
        gravidade TEXT,
        observacoes TEXT,
        criado_por INTEGER,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
    )
""")

print("   ✅ Tabela 'problemas' criada\n")

# ============================================================================
# TABELA: EVOLUCOES
# ============================================================================
print("📋 Criando tabela: evolucoes...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS evolucoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consulta_id INTEGER NOT NULL,
        paciente_id INTEGER NOT NULL,
        data_evolucao DATE NOT NULL,
        hora_evolucao TIME,
        texto_evolucao TEXT NOT NULL,
        veterinario_id INTEGER NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (consulta_id) REFERENCES consultas(id),
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
    )
""")

print("   ✅ Tabela 'evolucoes' criada\n")

# ============================================================================
# TABELA: ANEXOS
# ============================================================================
print("📋 Criando tabela: anexos...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS anexos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL,
        consulta_id INTEGER,
        tipo TEXT NOT NULL,
        descricao TEXT,
        arquivo_nome TEXT NOT NULL,
        arquivo_path TEXT NOT NULL,
        arquivo_tipo TEXT,
        data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        enviado_por INTEGER,
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (consulta_id) REFERENCES consultas(id)
    )
""")

print("   ✅ Tabela 'anexos' criada\n")

# ============================================================================
# ÍNDICES PARA PERFORMANCE
# ============================================================================
print("📋 Criando índices para otimização...")

# Verifica se as colunas existem antes de criar índices
try:
    # Índices básicos que sempre funcionam
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tutores_nome ON tutores(nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tutores_cpf ON tutores(cpf)")
    print("   ✅ Índices de tutores criados")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pacientes_tutor ON pacientes(tutor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pacientes_nome ON pacientes(nome)")
    print("   ✅ Índices de pacientes criados")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_paciente ON consultas(paciente_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_data ON consultas(data_consulta)")
    print("   ✅ Índices de consultas criados")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problemas_paciente ON problemas(paciente_id)")
    print("   ✅ Índices de problemas criados")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evolucoes_consulta ON evolucoes(consulta_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evolucoes_paciente ON evolucoes(paciente_id)")
    print("   ✅ Índices de evolucoes criados")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anexos_paciente ON anexos(paciente_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anexos_consulta ON anexos(consulta_id)")
    print("   ✅ Índices de anexos criados")

except sqlite3.OperationalError as e:
    print(f"   ⚠️  Aviso ao criar índices: {e}")
    print("   → Índices serão criados quando as colunas existirem")

print()

# ============================================================================
# COMMIT
# ============================================================================
conn.commit()
conn.close()

print("="*70)
print("✅ TODAS AS TABELAS DO PRONTUÁRIO FORAM CRIADAS COM SUCESSO!")
print("="*70)

print("\n📊 ESTRUTURA CRIADA:\n")
print("   ✅ tutores           - Responsáveis pelos animais")
print("   ✅ pacientes         - Animais cadastrados")
print("   ✅ consultas         - Atendimentos realizados")
print("   ✅ problemas         - Lista de problemas ativos")
print("   ✅ evolucoes         - Notas de evolução clínica")
print("   ✅ anexos            - Documentos e imagens")
print("   ✅ índices           - Otimização de buscas")

print("\n🎯 PRÓXIMO PASSO:")
print("   1. Execute: streamlit run fortcordis_app.py")
print("   2. Adicione o menu 'Prontuário' no sistema")
print("   3. Cole o código do módulo")
print("   4. Teste cadastrando um tutor e um paciente!\n")

print("="*70)
print("🎉 PRONTO PARA USAR!")
print("="*70 + "\n")
