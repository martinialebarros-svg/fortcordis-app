"""
Script para criar tabelas de laudos e migrar clínicas
Execute: python corrigir_laudos_e_clinicas.py
"""

import sqlite3
from pathlib import Path
import shutil
from datetime import datetime

DB_PATH_NOVO = Path.home() / "FortCordis" / "data" / "fortcordis.db"
DB_PATH_ANTIGO = Path.home() / "FortCordis" / "DB" / "fortcordis.db"

print("\n" + "="*70)
print(" CORREÇÃO: LAUDOS E CLÍNICAS ".center(70))
print("="*70 + "\n")

# ============================================================================
# PARTE 1: CRIAR TABELAS DE LAUDOS NO BANCO NOVO
# ============================================================================

print("📋 PARTE 1: Criando tabelas de laudos no banco novo\n")
print("-" * 70 + "\n")

conn_novo = sqlite3.connect(str(DB_PATH_NOVO))
cursor_novo = conn_novo.cursor()

# Tabela de laudos de ecocardiograma
print("🔨 Criando tabela: laudos_ecocardiograma...")
cursor_novo.execute("""
    CREATE TABLE IF NOT EXISTS laudos_ecocardiograma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        data_exame DATE,
        clinica_id INTEGER,
        veterinario_id INTEGER,
        tipo_exame TEXT DEFAULT 'ecocardiograma',
        
        -- Dados do paciente
        nome_paciente TEXT,
        especie TEXT,
        raca TEXT,
        idade TEXT,
        peso REAL,
        
        -- Dados do exame
        modo_m TEXT,
        modo_bidimensional TEXT,
        doppler TEXT,
        conclusao TEXT,
        observacoes TEXT,
        
        -- Achados
        achados_normais TEXT,
        achados_alterados TEXT,
        
        -- Arquivo
        arquivo_xml TEXT,
        arquivo_pdf TEXT,
        
        -- Controle
        status TEXT DEFAULT 'finalizado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER,
        
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (clinica_id) REFERENCES clinicas(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id),
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
    )
""")
print("   ✅ Tabela laudos_ecocardiograma criada\n")

# Tabela de laudos de eletrocardiograma
print("🔨 Criando tabela: laudos_eletrocardiograma...")
cursor_novo.execute("""
    CREATE TABLE IF NOT EXISTS laudos_eletrocardiograma (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        data_exame DATE,
        clinica_id INTEGER,
        veterinario_id INTEGER,
        tipo_exame TEXT DEFAULT 'eletrocardiograma',
        
        -- Dados do paciente
        nome_paciente TEXT,
        especie TEXT,
        raca TEXT,
        idade TEXT,
        peso REAL,
        
        -- Dados do exame
        ritmo TEXT,
        frequencia_cardiaca INTEGER,
        eixo_eletrico TEXT,
        onda_p TEXT,
        intervalo_pr REAL,
        complexo_qrs TEXT,
        segmento_st TEXT,
        onda_t TEXT,
        intervalo_qt REAL,
        
        conclusao TEXT,
        observacoes TEXT,
        
        -- Arquivo
        arquivo_xml TEXT,
        arquivo_pdf TEXT,
        
        -- Controle
        status TEXT DEFAULT 'finalizado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER,
        
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (clinica_id) REFERENCES clinicas(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id),
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
    )
""")
print("   ✅ Tabela laudos_eletrocardiograma criada\n")

# Tabela de laudos de pressão arterial
print("🔨 Criando tabela: laudos_pressao_arterial...")
cursor_novo.execute("""
    CREATE TABLE IF NOT EXISTS laudos_pressao_arterial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER,
        data_exame DATE,
        clinica_id INTEGER,
        veterinario_id INTEGER,
        tipo_exame TEXT DEFAULT 'pressao_arterial',
        
        -- Dados do paciente
        nome_paciente TEXT,
        especie TEXT,
        raca TEXT,
        idade TEXT,
        peso REAL,
        
        -- Dados do exame
        pressao_sistolica INTEGER,
        pressao_diastolica INTEGER,
        pressao_media INTEGER,
        frequencia_cardiaca INTEGER,
        
        classificacao TEXT,
        conclusao TEXT,
        observacoes TEXT,
        
        -- Arquivo
        arquivo_xml TEXT,
        arquivo_pdf TEXT,
        
        -- Controle
        status TEXT DEFAULT 'finalizado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por INTEGER,
        
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (clinica_id) REFERENCES clinicas(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id),
        FOREIGN KEY (criado_por) REFERENCES usuarios(id)
    )
""")
print("   ✅ Tabela laudos_pressao_arterial criada\n")

conn_novo.commit()

print("=" * 70 + "\n")

# ============================================================================
# PARTE 2: MIGRAR CLÍNICAS DO BANCO ANTIGO PARA O NOVO
# ============================================================================

print("📋 PARTE 2: Migrando clínicas do banco antigo para o novo\n")
print("-" * 70 + "\n")

if not DB_PATH_ANTIGO.exists():
    print("⚠️  Banco antigo não existe. Pulando migração de clínicas.\n")
else:
    conn_antigo = sqlite3.connect(str(DB_PATH_ANTIGO))
    cursor_antigo = conn_antigo.cursor()
    
    # Verifica se existe tabela clinicas no banco antigo
    cursor_antigo.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas'")
    if cursor_antigo.fetchone():
        
        # Busca todas as clínicas do banco antigo
        print("📥 Buscando clínicas do banco antigo...")
        cursor_antigo.execute("""
            SELECT id, nome, endereco, telefone, email, cnpj, responsavel
            FROM clinicas
        """)
        clinicas_antigas = cursor_antigo.fetchall()
        print(f"   ✅ Encontradas {len(clinicas_antigas)} clínicas\n")
        
        # Verifica estrutura da tabela no banco novo
        print("🔍 Verificando estrutura da tabela clinicas no banco novo...")
        cursor_novo.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas'")
        
        if not cursor_novo.fetchone():
            # Tabela não existe, cria
            print("   ⚠️  Tabela 'clinicas' não existe. Criando...")
            cursor_novo.execute("""
                CREATE TABLE clinicas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    email TEXT,
                    cnpj TEXT,
                    responsavel TEXT,
                    ativo INTEGER DEFAULT 1,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn_novo.commit()
            print("   ✅ Tabela criada\n")
        
        # Migra clínicas (evitando duplicatas)
        print("📥 Migrando clínicas...")
        
        migradas = 0
        duplicadas = 0
        
        for clinica in clinicas_antigas:
            # Verifica se já existe (por nome ou CNPJ)
            cursor_novo.execute("""
                SELECT id FROM clinicas 
                WHERE nome = ? OR (cnpj = ? AND cnpj IS NOT NULL)
            """, (clinica[1], clinica[5]))
            
            if cursor_novo.fetchone():
                duplicadas += 1
            else:
                try:
                    cursor_novo.execute("""
                        INSERT INTO clinicas (nome, endereco, telefone, email, cnpj, responsavel)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, clinica[1:7])
                    migradas += 1
                except Exception as e:
                    print(f"   ⚠️  Erro ao migrar '{clinica[1]}': {e}")
        
        conn_novo.commit()
        
        print(f"\n   ✅ Migradas: {migradas} clínicas")
        print(f"   ⏭️  Duplicadas (ignoradas): {duplicadas} clínicas\n")
        
    else:
        print("   ⚠️  Tabela 'clinicas' não existe no banco antigo\n")
    
    conn_antigo.close()

print("=" * 70 + "\n")

# ============================================================================
# PARTE 3: VERIFICAR RESULTADO
# ============================================================================

print("📋 PARTE 3: Verificando resultado\n")
print("-" * 70 + "\n")

# Lista tabelas de laudos
print("🔍 Tabelas de laudos criadas:")
cursor_novo.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE 'laudos_%'
""")
tabelas_laudos = cursor_novo.fetchall()

for tab in tabelas_laudos:
    print(f"   ✅ {tab[0]}")

print()

# Conta clínicas
cursor_novo.execute("SELECT COUNT(*) FROM clinicas")
total_clinicas = cursor_novo.fetchone()[0]
print(f"🏥 Total de clínicas no banco novo: {total_clinicas}")

if total_clinicas > 0:
    print("\n   Algumas clínicas:")
    cursor_novo.execute("SELECT id, nome FROM clinicas LIMIT 10")
    clinicas = cursor_novo.fetchall()
    for c in clinicas:
        print(f"      ID {c[0]}: {c[1]}")

conn_novo.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 PRÓXIMO PASSO:")
print("   1. Recarregue o sistema (aperte R)")
print("   2. Os laudos agora serão salvos no banco")
print("   3. As clínicas estarão disponíveis")
print("   4. A busca de laudos vai funcionar!\n")

print("⚠️  IMPORTANTE:")
print("   Laudos ANTIGOS (só PDF) não aparecerão na busca.")
print("   Apenas laudos NOVOS (a partir de agora) serão registrados.\n")
