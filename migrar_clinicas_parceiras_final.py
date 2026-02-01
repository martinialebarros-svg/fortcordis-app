"""
Script para migrar clínicas de clinicas_parceiras → clinicas
COM todos os dados (endereço, telefone, etc)
Execute: python migrar_clinicas_parceiras_final.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" MIGRAÇÃO: clinicas_parceiras → clinicas ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# ============================================================================
# ETAPA 1: Buscar clínicas de clinicas_parceiras
# ============================================================================

print("📋 ETAPA 1: Buscando clínicas em 'clinicas_parceiras'\n")
print("-" * 70 + "\n")

cursor.execute("""
    SELECT 
        id, nome, endereco, bairro, cidade, estado, 
        telefone, whatsapp, email, cnpj, 
        inscricao_estadual, responsavel_veterinario, crmv_responsavel,
        observacoes
    FROM clinicas_parceiras
    WHERE ativo = 1
""")

clinicas_parceiras = cursor.fetchall()

print(f"✅ Encontradas {len(clinicas_parceiras)} clínica(s):\n")

for cp in clinicas_parceiras:
    print(f"   📌 {cp[1]}")
    print(f"      Endereço: {cp[2]}, {cp[3]} - {cp[4]}/{cp[5]}")
    print(f"      Telefone: {cp[6]}")
    print(f"      WhatsApp: {cp[7]}")
    print()

print("="*70 + "\n")

# ============================================================================
# ETAPA 2: Migrar para clinicas
# ============================================================================

print("📋 ETAPA 2: Migrando para 'clinicas'\n")
print("-" * 70 + "\n")

migradas = 0
atualizadas = 0
duplicadas = 0

for cp in clinicas_parceiras:
    nome = cp[1]
    endereco_completo = f"{cp[2]}, {cp[3]}, {cp[4]}/{cp[5]}"
    telefone = cp[6]
    whatsapp = cp[7]
    email = cp[8]
    cnpj = cp[9]
    responsavel = cp[11]  # responsavel_veterinario
    
    # Verifica se já existe em clinicas
    cursor.execute("""
        SELECT id, endereco, telefone 
        FROM clinicas 
        WHERE UPPER(TRIM(nome)) = UPPER(TRIM(?))
    """, (nome,))
    
    existe = cursor.fetchone()
    
    if existe:
        clinica_id = existe[0]
        endereco_atual = existe[1]
        telefone_atual = existe[2]
        
        # Se já tem dados, pula
        if endereco_atual and telefone_atual:
            print(f"   ⏭️  '{nome}' → Já existe COM dados completos")
            duplicadas += 1
        else:
            # Atualiza com os dados
            print(f"   🔄 '{nome}' → Atualizando dados...")
            
            cursor.execute("""
                UPDATE clinicas
                SET 
                    endereco = ?,
                    telefone = ?,
                    email = ?,
                    cnpj = ?,
                    responsavel = ?
                WHERE id = ?
            """, (endereco_completo, telefone, email, cnpj, responsavel, clinica_id))
            
            atualizadas += 1
            print(f"      ✅ Dados atualizados!")
    else:
        # Insere nova
        print(f"   ➕ '{nome}' → Inserindo como nova clínica...")
        
        cursor.execute("""
            INSERT INTO clinicas (
                nome, endereco, telefone, email, cnpj, responsavel, ativo
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (nome, endereco_completo, telefone, email, cnpj, responsavel))
        
        migradas += 1
        print(f"      ✅ Inserida com sucesso!")

conn.commit()

print(f"\n📊 Resultado:")
print(f"   ✅ Novas inseridas: {migradas}")
print(f"   🔄 Atualizadas: {atualizadas}")
print(f"   ⏭️  Já completas: {duplicadas}")

print("\n" + "="*70 + "\n")

# ============================================================================
# ETAPA 3: Verificar resultado
# ============================================================================

print("📋 ETAPA 3: Verificando clínicas em 'clinicas'\n")
print("-" * 70 + "\n")

cursor.execute("""
    SELECT COUNT(*) 
    FROM clinicas 
    WHERE ativo = 1
""")
total = cursor.fetchone()[0]

print(f"🏥 Total de clínicas ativas: {total}\n")

# Mostra as que têm dados completos
cursor.execute("""
    SELECT nome, endereco, telefone
    FROM clinicas
    WHERE ativo = 1
    AND endereco IS NOT NULL 
    AND telefone IS NOT NULL
    ORDER BY nome
""")

completas = cursor.fetchall()

print(f"✅ Clínicas COM dados completos: {len(completas)}\n")

if completas:
    print("   Clínicas com dados:")
    for i, c in enumerate(completas):
        print(f"      {i+1}. {c[0]}")
        print(f"         • {c[1]}")
        print(f"         • {c[2]}")
        print()

# Mostra as que ainda precisam de dados
cursor.execute("""
    SELECT nome
    FROM clinicas
    WHERE ativo = 1
    AND (endereco IS NULL OR telefone IS NULL)
    ORDER BY nome
""")

incompletas = cursor.fetchall()

if incompletas:
    print(f"⚠️  Clínicas SEM dados: {len(incompletas)}")
    print("\n   Primeiras 10 que precisam de complementação:")
    for i, c in enumerate(incompletas[:10]):
        print(f"      {i+1}. {c[0]}")

conn.close()

print("\n" + "="*70)
print("✅ MIGRAÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 PRÓXIMOS PASSOS:\n")
print("1. ✅ Recarregue o sistema (aperte R)")
print("2. ✅ Vá em 'Laudos e Exames'")
print("3. ✅ O dropdown vai mostrar as 3 clínicas com dados!")
print("4. 💡 Complete dados das outras pelo menu 'Cadastros'")

print("\n="*70 + "\n")
