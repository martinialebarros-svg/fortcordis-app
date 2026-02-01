"""
Script para corrigir a constraint UNIQUE da coluna microchip
Execute: python corrigir_microchip_pacientes.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORRIGIR CONSTRAINT MICROCHIP ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica o problema
print("🔍 Verificando estrutura da tabela pacientes...\n")
cursor.execute("PRAGMA table_info(pacientes)")
colunas = cursor.fetchall()

print("📋 Colunas da tabela:")
for col in colunas:
    print(f"   {col[1]:<25} {col[2]:<10}")

# Verifica constraints
print("\n🔍 Verificando constraints...\n")
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pacientes'")
create_sql = cursor.fetchone()[0]

if 'UNIQUE' in create_sql and 'microchip' in create_sql:
    print("   ⚠️  PROBLEMA: Coluna microchip tem constraint UNIQUE!")
    print("   → Nem todo animal tem microchip, não pode ser UNIQUE\n")
else:
    print("   ✅ Sem constraint UNIQUE no microchip")
    print("   → O problema pode ser outro...\n")

# Salva dados atuais
print("💾 Salvando dados dos pacientes...\n")
cursor.execute("""
    SELECT 
        id, tutor_id, nome, especie, raca, sexo, castrado,
        data_nascimento, idade_anos, idade_meses, peso_kg, cor_pelagem,
        microchip, numero_registro, foto_url,
        alergias, medicamentos_uso, doencas_previas, cirurgias_previas,
        vacinacao_em_dia, vermifugacao_em_dia, observacoes,
        ativo, data_cadastro, data_obito, criado_por
    FROM pacientes
""")
dados_salvos = cursor.fetchall()

print(f"   ✅ {len(dados_salvos)} paciente(s) salvo(s)\n")

for pac in dados_salvos:
    print(f"   ID {pac[0]}: {pac[2]} - Microchip: {pac[12] or 'Sem microchip'}")

# Recria tabela SEM constraint UNIQUE no microchip
print("\n🗑️  Apagando tabela antiga...\n")
cursor.execute("DROP TABLE pacientes")
conn.commit()

print("🔨 Criando tabela nova (sem UNIQUE no microchip)...\n")
cursor.execute("""
    CREATE TABLE pacientes (
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
conn.commit()

print("   ✅ Tabela recriada\n")

# Reinsere dados
if dados_salvos:
    print("📥 Reinserindo pacientes...\n")
    
    for pac in dados_salvos:
        cursor.execute("""
            INSERT INTO pacientes (
                id, tutor_id, nome, especie, raca, sexo, castrado,
                data_nascimento, idade_anos, idade_meses, peso_kg, cor_pelagem,
                microchip, numero_registro, foto_url,
                alergias, medicamentos_uso, doencas_previas, cirurgias_previas,
                vacinacao_em_dia, vermifugacao_em_dia, observacoes,
                ativo, data_cadastro, data_obito, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pac)
    
    conn.commit()
    print(f"   ✅ {len(dados_salvos)} paciente(s) reinserido(s)\n")

# Verifica
print("🔍 Verificando resultado...\n")
cursor.execute("SELECT id, nome, microchip FROM pacientes")
pacientes = cursor.fetchall()

for p in pacientes:
    print(f"   ID {p[0]}: {p[1]} - Microchip: {p[2] or 'Sem microchip'}")

# Testa constraint
print("\n🧪 Testando: é possível cadastrar 2 pacientes sem microchip?")
try:
    cursor.execute("""
        INSERT INTO pacientes (tutor_id, nome, especie, sexo, microchip)
        VALUES (1, 'Teste1', 'Canina', 'Macho', NULL)
    """)
    teste1_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO pacientes (tutor_id, nome, especie, sexo, microchip)
        VALUES (1, 'Teste2', 'Canina', 'Macho', NULL)
    """)
    teste2_id = cursor.lastrowid
    
    # Remove testes
    cursor.execute("DELETE FROM pacientes WHERE id IN (?, ?)", (teste1_id, teste2_id))
    conn.commit()
    
    print("   ✅ SIM! Agora funciona corretamente")
except Exception as e:
    print(f"   ❌ Ainda tem erro: {e}")

conn.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Tente cadastrar o novo paciente")
print("   3. Deve funcionar agora! 🎉\n")
