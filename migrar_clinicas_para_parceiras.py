"""
Script para migrar clínicas na DIREÇÃO CORRETA:
clinicas (46 do sistema de laudos) → clinicas_parceiras (cadastro principal)

Execute: python migrar_clinicas_para_parceiras.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" MIGRAÇÃO CORRETA: clinicas → clinicas_parceiras ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# ============================================================================
# ETAPA 1: Analisar situação
# ============================================================================

print("📋 ETAPA 1: Analisando situação atual\n")
print("-" * 70 + "\n")

# Conta em cada tabela
cursor.execute("SELECT COUNT(*) FROM clinicas WHERE ativo = 1")
qtd_clinicas = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM clinicas_parceiras WHERE ativo = 1")
qtd_parceiras = cursor.fetchone()[0]

print(f"📊 Situação atual:")
print(f"   • Tabela 'clinicas': {qtd_clinicas} clínica(s)")
print(f"   • Tabela 'clinicas_parceiras': {qtd_parceiras} clínica(s)\n")

print("🎯 Objetivo:")
print("   Migrar as {qtd_clinicas} clínicas → clinicas_parceiras")
print("   Para ficarem visíveis no menu 'Cadastros'\n")

print("="*70 + "\n")

# ============================================================================
# ETAPA 2: Buscar clínicas que NÃO estão em clinicas_parceiras
# ============================================================================

print("📋 ETAPA 2: Identificando clínicas para migrar\n")
print("-" * 70 + "\n")

cursor.execute("""
    SELECT c.id, c.nome, c.endereco, c.telefone
    FROM clinicas c
    WHERE c.ativo = 1
    AND NOT EXISTS (
        SELECT 1 FROM clinicas_parceiras cp
        WHERE UPPER(TRIM(cp.nome)) = UPPER(TRIM(c.nome))
        AND cp.ativo = 1
    )
    ORDER BY c.nome
""")

clinicas_para_migrar = cursor.fetchall()

print(f"✅ Encontradas {len(clinicas_para_migrar)} clínica(s) para migrar\n")

if len(clinicas_para_migrar) > 10:
    print("   Primeiras 10:")
    for cli in clinicas_para_migrar[:10]:
        print(f"      • {cli[1]}")
    print(f"      ... e mais {len(clinicas_para_migrar) - 10}")
else:
    print("   Todas:")
    for cli in clinicas_para_migrar:
        print(f"      • {cli[1]}")

print()

# Mostra as que JÁ existem (duplicadas)
cursor.execute("""
    SELECT c.nome
    FROM clinicas c
    INNER JOIN clinicas_parceiras cp
        ON UPPER(TRIM(cp.nome)) = UPPER(TRIM(c.nome))
    WHERE c.ativo = 1 AND cp.ativo = 1
""")

duplicadas = cursor.fetchall()

if duplicadas:
    print(f"⏭️  {len(duplicadas)} clínica(s) JÁ existem em 'clinicas_parceiras':")
    for dup in duplicadas:
        print(f"      • {dup[0]}")
    print()

print("="*70 + "\n")

# ============================================================================
# ETAPA 3: Migração
# ============================================================================

print("📋 ETAPA 3: Migrando clínicas\n")
print("-" * 70 + "\n")

if not clinicas_para_migrar:
    print("✅ Nenhuma clínica para migrar! Todas já estão em 'clinicas_parceiras'\n")
else:
    migradas = 0
    erros = 0
    
    for cli in clinicas_para_migrar:
        nome = cli[1]
        endereco = cli[2] if cli[2] else None
        telefone = cli[3] if cli[3] else None
        
        print(f"   ➕ Migrando: {nome}")
        
        try:
            cursor.execute("""
                INSERT INTO clinicas_parceiras (
                    nome, endereco, cidade, telefone, ativo
                ) VALUES (?, ?, 'Fortaleza', ?, 1)
            """, (nome, endereco, telefone))
            
            migradas += 1
            print(f"      ✅ Migrada!\n")
            
        except Exception as e:
            erros += 1
            print(f"      ❌ Erro: {e}\n")
    
    conn.commit()
    
    print(f"📊 Resultado:")
    print(f"   ✅ Migradas com sucesso: {migradas}")
    if erros > 0:
        print(f"   ❌ Erros: {erros}")
    print()

print("="*70 + "\n")

# ============================================================================
# ETAPA 4: Relatório final
# ============================================================================

print("📋 ETAPA 4: Relatório Final\n")
print("-" * 70 + "\n")

# Conta clínicas finais em clinicas_parceiras
cursor.execute("SELECT COUNT(*) FROM clinicas_parceiras WHERE ativo = 1")
total_parceiras = cursor.fetchone()[0]

print(f"🏥 Total em 'clinicas_parceiras': {total_parceiras} clínica(s)\n")

# Lista clínicas SEM dados completos
cursor.execute("""
    SELECT nome, endereco, telefone, whatsapp
    FROM clinicas_parceiras
    WHERE ativo = 1
    AND (
        endereco IS NULL OR endereco = '' OR
        telefone IS NULL OR telefone = ''
    )
    ORDER BY nome
""")

sem_dados = cursor.fetchall()

if sem_dados:
    print(f"⚠️  {len(sem_dados)} clínica(s) sem dados completos:\n")
    
    if len(sem_dados) > 10:
        print("   Primeiras 10:")
        for cli in sem_dados[:10]:
            print(f"      • {cli[0]}")
            faltando = []
            if not cli[1]:
                faltando.append("Endereço")
            if not cli[2]:
                faltando.append("Telefone")
            if faltando:
                print(f"        → Faltam: {', '.join(faltando)}")
        print(f"\n   ... e mais {len(sem_dados) - 10}")
    else:
        for cli in sem_dados:
            print(f"      • {cli[0]}")
            faltando = []
            if not cli[1]:
                faltando.append("Endereço")
            if not cli[2]:
                faltando.append("Telefone")
            if faltando:
                print(f"        → Faltam: {', '.join(faltando)}")
    print()
else:
    print("✅ Todas as clínicas têm dados completos!\n")

conn.close()

print("="*70)
print("✅ MIGRAÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 PRÓXIMOS PASSOS:\n")
print("1. ✅ Clínicas migradas para 'clinicas_parceiras'")
print("2. ✅ Recarregue o sistema (aperte R)")
print("3. ✅ Vá em 'Cadastros → Clínicas Parceiras'")
print("4. ✅ Todas as clínicas estarão visíveis agora!")
print("5. ✏️  Edite as que não têm dados completos")
print("6. 📝 Complete: endereço, telefone, WhatsApp, etc")

print("\n💡 DICA:")
print("   Depois de editar no cadastro, o dropdown dos laudos")
print("   vai buscar de 'clinicas_parceiras' e mostrar os dados!\n")

print("="*70 + "\n")
