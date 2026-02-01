"""
Script para migrar clínicas antigas do sistema de laudos
e consolidar com o cadastro principal
Execute: python migrar_consolidar_clinicas.py
"""

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH_NOVO = Path.home() / "FortCordis" / "data" / "fortcordis.db"
DB_PATH_ANTIGO = Path.home() / "FortCordis" / "DB" / "fortcordis.db"

print("\n" + "="*70)
print(" MIGRAÇÃO E CONSOLIDAÇÃO DE CLÍNICAS ".center(70))
print("="*70 + "\n")

# ============================================================================
# ETAPA 1: IDENTIFICAR TODAS AS CLÍNICAS
# ============================================================================

print("📋 ETAPA 1: Identificando todas as clínicas\n")
print("-" * 70 + "\n")

conn_novo = sqlite3.connect(str(DB_PATH_NOVO))

# Banco NOVO - Tabela principal
print("🔍 Banco NOVO - Tabela 'clinicas':")
try:
    clinicas_novo_df = pd.read_sql_query("""
        SELECT id, nome, endereco, telefone, email, cnpj
        FROM clinicas
        ORDER BY nome
    """, conn_novo)
    print(f"   ✅ {len(clinicas_novo_df)} clínica(s) encontrada(s)")
    if not clinicas_novo_df.empty:
        print("\n   Primeiras 5:")
        for _, c in clinicas_novo_df.head().iterrows():
            end = c['endereco'] if pd.notna(c['endereco']) else "Sem endereço"
            print(f"      • {c['nome']} ({end})")
except Exception as e:
    print(f"   ⚠️  Erro: {e}")
    clinicas_novo_df = pd.DataFrame()

print()

# Banco NOVO - Tabela antiga (clinicas_parceiras)
print("🔍 Banco NOVO - Tabela 'clinicas_parceiras' (antiga):")
try:
    clinicas_parceiras_df = pd.read_sql_query("""
        SELECT id, nome
        FROM clinicas_parceiras
        ORDER BY nome
    """, conn_novo)
    print(f"   ✅ {len(clinicas_parceiras_df)} clínica(s) encontrada(s)")
    if not clinicas_parceiras_df.empty:
        print("\n   Todas as clínicas:")
        for _, c in clinicas_parceiras_df.iterrows():
            print(f"      • {c['nome']}")
except Exception as e:
    print(f"   ⚠️  Erro: {e}")
    clinicas_parceiras_df = pd.DataFrame()

print()

# Banco ANTIGO
print("🔍 Banco ANTIGO - Tabela 'clinicas':")
if DB_PATH_ANTIGO.exists():
    try:
        conn_antigo = sqlite3.connect(str(DB_PATH_ANTIGO))
        clinicas_antigo_df = pd.read_sql_query("""
            SELECT id, nome, endereco, telefone
            FROM clinicas
            ORDER BY nome
        """, conn_antigo)
        conn_antigo.close()
        print(f"   ✅ {len(clinicas_antigo_df)} clínica(s) encontrada(s)")
    except Exception as e:
        print(f"   ⚠️  Erro: {e}")
        clinicas_antigo_df = pd.DataFrame()
else:
    print("   ⚠️  Banco antigo não existe")
    clinicas_antigo_df = pd.DataFrame()

print("\n" + "="*70 + "\n")

# ============================================================================
# ETAPA 2: ANALISAR DUPLICATAS
# ============================================================================

print("📋 ETAPA 2: Analisando possíveis duplicatas\n")
print("-" * 70 + "\n")

# Cria conjunto de todos os nomes
todos_nomes = set()

if not clinicas_novo_df.empty:
    todos_nomes.update(clinicas_novo_df['nome'].str.upper().str.strip())

if not clinicas_parceiras_df.empty:
    todos_nomes.update(clinicas_parceiras_df['nome'].str.upper().str.strip())

if not clinicas_antigo_df.empty:
    todos_nomes.update(clinicas_antigo_df['nome'].str.upper().str.strip())

print(f"📊 Total de nomes únicos (case-insensitive): {len(todos_nomes)}\n")

# Identifica duplicatas
duplicatas = []

for nome in todos_nomes:
    contadores = {
        'novo': 0,
        'parceiras': 0,
        'antigo': 0
    }
    
    if not clinicas_novo_df.empty:
        contadores['novo'] = len(clinicas_novo_df[
            clinicas_novo_df['nome'].str.upper().str.strip() == nome
        ])
    
    if not clinicas_parceiras_df.empty:
        contadores['parceiras'] = len(clinicas_parceiras_df[
            clinicas_parceiras_df['nome'].str.upper().str.strip() == nome
        ])
    
    if not clinicas_antigo_df.empty:
        contadores['antigo'] = len(clinicas_antigo_df[
            clinicas_antigo_df['nome'].str.upper().str.strip() == nome
        ])
    
    total_ocorrencias = sum(contadores.values())
    
    if total_ocorrencias > 1 or contadores['parceiras'] > 0:
        duplicatas.append({
            'nome': nome,
            **contadores,
            'total': total_ocorrencias
        })

if duplicatas:
    print("⚠️  DUPLICATAS ENCONTRADAS:\n")
    for dup in duplicatas:
        print(f"   📌 {dup['nome'].title()}")
        print(f"      • Tabela 'clinicas': {dup['novo']}")
        print(f"      • Tabela 'clinicas_parceiras': {dup['parceiras']}")
        print(f"      • Banco antigo: {dup['antigo']}")
        print(f"      → Total: {dup['total']} ocorrência(s)\n")
else:
    print("✅ Nenhuma duplicata encontrada\n")

print("="*70 + "\n")

# ============================================================================
# ETAPA 3: MIGRAÇÃO
# ============================================================================

print("📋 ETAPA 3: Migrando clínicas de 'clinicas_parceiras' → 'clinicas'\n")
print("-" * 70 + "\n")

if clinicas_parceiras_df.empty:
    print("✅ Nenhuma clínica em 'clinicas_parceiras' para migrar\n")
else:
    print(f"📥 Migrando {len(clinicas_parceiras_df)} clínica(s)...\n")
    
    cursor_novo = conn_novo.cursor()
    
    migradas = 0
    duplicadas = 0
    
    for _, clinica in clinicas_parceiras_df.iterrows():
        nome = clinica['nome'].strip()
        
        # Verifica se já existe na tabela 'clinicas'
        cursor_novo.execute("""
            SELECT id FROM clinicas 
            WHERE UPPER(TRIM(nome)) = UPPER(TRIM(?))
        """, (nome,))
        
        if cursor_novo.fetchone():
            duplicadas += 1
            print(f"   ⏭️  '{nome}' → Já existe em 'clinicas'")
        else:
            try:
                cursor_novo.execute("""
                    INSERT INTO clinicas (nome, ativo)
                    VALUES (?, 1)
                """, (nome,))
                migradas += 1
                print(f"   ✅ '{nome}' → Migrada para 'clinicas'")
            except Exception as e:
                print(f"   ❌ '{nome}' → Erro: {e}")
    
    conn_novo.commit()
    
    print(f"\n📊 Resultado da migração:")
    print(f"   ✅ Migradas: {migradas}")
    print(f"   ⏭️  Duplicadas (ignoradas): {duplicadas}")
    print()

print("="*70 + "\n")

# ============================================================================
# ETAPA 4: RELATÓRIO FINAL
# ============================================================================

print("📋 ETAPA 4: Relatório Final\n")
print("-" * 70 + "\n")

# Conta clínicas finais
cursor_novo.execute("SELECT COUNT(*) FROM clinicas WHERE ativo = 1")
total_clinicas = cursor_novo.fetchone()[0]

print(f"🏥 Total de clínicas em 'clinicas': {total_clinicas}\n")

# Lista clínicas SEM dados completos
print("⚠️  Clínicas que PRECISAM de complementação de dados:\n")

cursor_novo.execute("""
    SELECT id, nome, endereco, telefone, email
    FROM clinicas
    WHERE ativo = 1
    AND (
        endereco IS NULL OR endereco = '' OR
        telefone IS NULL OR telefone = '' OR
        email IS NULL OR email = ''
    )
    ORDER BY nome
""")

clinicas_incompletas = cursor_novo.fetchall()

if clinicas_incompletas:
    print(f"   📋 {len(clinicas_incompletas)} clínica(s) sem dados completos:\n")
    
    for cli in clinicas_incompletas:
        print(f"   ID {cli[0]}: {cli[1]}")
        faltando = []
        if not cli[2]:
            faltando.append("Endereço")
        if not cli[3]:
            faltando.append("Telefone")
        if not cli[4]:
            faltando.append("Email")
        print(f"      → Faltam: {', '.join(faltando)}\n")
else:
    print("   ✅ Todas as clínicas têm dados completos!\n")

conn_novo.close()

print("="*70)
print("✅ MIGRAÇÃO E ANÁLISE CONCLUÍDAS!")
print("="*70)

print("\n🎯 PRÓXIMOS PASSOS:\n")
print("1. ✅ Clínicas migradas para a tabela principal")
print("2. ⚠️  Complete os dados faltantes pelo menu 'Cadastros'")
print("3. ✅ Recarregue o sistema (R)")
print("4. ✅ Vá em 'Cadastros → Clínicas'")
print("5. ✏️  Edite cada clínica e adicione:")
print("      • Endereço completo")
print("      • Telefone")
print("      • Email")
print("      • CNPJ (se tiver)")
print("6. ✅ Dropdown dos laudos terá TODAS as clínicas com dados completos!")

print("\n💡 DICA:")
print("   Você pode editar aos poucos, começando pelas clínicas mais usadas.\n")

print("="*70 + "\n")
