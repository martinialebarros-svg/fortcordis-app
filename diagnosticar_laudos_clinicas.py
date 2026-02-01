"""
Script para diagnosticar problemas com laudos e clínicas
Execute: python diagnosticar_laudos_clinicas.py
"""

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
DB_PATH_OLD = Path.home() / "FortCordis" / "DB" / "fortcordis.db"

print("\n" + "="*70)
print(" DIAGNÓSTICO: LAUDOS E CLÍNICAS ".center(70))
print("="*70 + "\n")

# ============================================================================
# PROBLEMA 1: LAUDOS NÃO APARECEM NA BUSCA
# ============================================================================

print("🔍 PROBLEMA 1: Laudos não aparecem na busca\n")
print("-" * 70 + "\n")

# Verifica em qual banco os laudos estão sendo salvos
print("📍 Verificando em qual banco os laudos são salvos...\n")

# Banco 1 (Novo - Autenticação)
print("🔍 Banco 1 (Autenticação): " + str(DB_PATH_AUTH))
if DB_PATH_AUTH.exists():
    conn1 = sqlite3.connect(str(DB_PATH_AUTH))
    cursor1 = conn1.cursor()
    
    # Verifica se tem tabela de laudos
    cursor1.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%laudo%'")
    tabelas_laudo = cursor1.fetchall()
    
    if tabelas_laudo:
        print(f"   ✅ Encontradas {len(tabelas_laudo)} tabela(s) de laudo:")
        for tab in tabelas_laudo:
            print(f"      • {tab[0]}")
            cursor1.execute(f"SELECT COUNT(*) FROM {tab[0]}")
            qtd = cursor1.fetchone()[0]
            print(f"        → {qtd} registro(s)")
    else:
        print("   ⚠️  Nenhuma tabela de laudo encontrada")
    
    conn1.close()
else:
    print("   ❌ Banco não existe")

print()

# Banco 2 (Antigo - Sistema original)
print("🔍 Banco 2 (Sistema Original): " + str(DB_PATH_OLD))
if DB_PATH_OLD.exists():
    conn2 = sqlite3.connect(str(DB_PATH_OLD))
    cursor2 = conn2.cursor()
    
    # Verifica se tem tabela de laudos
    cursor2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%laudo%'")
    tabelas_laudo2 = cursor2.fetchall()
    
    if tabelas_laudo2:
        print(f"   ✅ Encontradas {len(tabelas_laudo2)} tabela(s) de laudo:")
        for tab in tabelas_laudo2:
            print(f"      • {tab[0]}")
            cursor2.execute(f"SELECT COUNT(*) FROM {tab[0]}")
            qtd = cursor2.fetchone()[0]
            print(f"        → {qtd} registro(s)")
            
            # Mostra alguns registros
            if qtd > 0:
                print(f"\n      📋 Últimos registros em {tab[0]}:")
                try:
                    cursor2.execute(f"SELECT * FROM {tab[0]} ORDER BY id DESC LIMIT 3")
                    registros = cursor2.fetchall()
                    
                    # Pega nomes das colunas
                    cursor2.execute(f"PRAGMA table_info({tab[0]})")
                    colunas = [col[1] for col in cursor2.fetchall()]
                    
                    for reg in registros:
                        print(f"\n         ID: {reg[0]}")
                        # Mostra algumas colunas importantes
                        for i, col in enumerate(colunas[:10]):  # Primeiras 10 colunas
                            if reg[i]:
                                valor = str(reg[i])[:50]  # Limita tamanho
                                print(f"         {col}: {valor}")
                except Exception as e:
                    print(f"         Erro ao ler registros: {e}")
    else:
        print("   ⚠️  Nenhuma tabela de laudo encontrada")
    
    conn2.close()
else:
    print("   ❌ Banco não existe")

print("\n" + "="*70 + "\n")

# ============================================================================
# PROBLEMA 2: CLÍNICAS NÃO LINKADAS
# ============================================================================

print("🔍 PROBLEMA 2: Clínicas não aparecem nos laudos\n")
print("-" * 70 + "\n")

# Verifica onde as clínicas estão cadastradas
print("📍 Verificando onde as clínicas estão cadastradas...\n")

# Banco 1
print("🔍 Banco 1 (Autenticação): " + str(DB_PATH_AUTH))
if DB_PATH_AUTH.exists():
    conn1 = sqlite3.connect(str(DB_PATH_AUTH))
    cursor1 = conn1.cursor()
    
    cursor1.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%clinic%'")
    tabelas_clinic = cursor1.fetchall()
    
    if tabelas_clinic:
        print(f"   ✅ Encontradas {len(tabelas_clinic)} tabela(s) de clínica:")
        for tab in tabelas_clinic:
            print(f"      • {tab[0]}")
            cursor1.execute(f"SELECT COUNT(*) FROM {tab[0]}")
            qtd = cursor1.fetchone()[0]
            print(f"        → {qtd} registro(s)")
            
            if qtd > 0:
                cursor1.execute(f"SELECT id, nome FROM {tab[0]} LIMIT 5")
                clinicas = cursor1.fetchall()
                print("        Clínicas:")
                for c in clinicas:
                    print(f"          ID {c[0]}: {c[1]}")
    else:
        print("   ⚠️  Nenhuma tabela de clínica encontrada")
    
    conn1.close()
else:
    print("   ❌ Banco não existe")

print()

# Banco 2
print("🔍 Banco 2 (Sistema Original): " + str(DB_PATH_OLD))
if DB_PATH_OLD.exists():
    conn2 = sqlite3.connect(str(DB_PATH_OLD))
    cursor2 = conn2.cursor()
    
    cursor2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%clinic%'")
    tabelas_clinic2 = cursor2.fetchall()
    
    if tabelas_clinic2:
        print(f"   ✅ Encontradas {len(tabelas_clinic2)} tabela(s) de clínica:")
        for tab in tabelas_clinic2:
            print(f"      • {tab[0]}")
            cursor2.execute(f"SELECT COUNT(*) FROM {tab[0]}")
            qtd = cursor2.fetchone()[0]
            print(f"        → {qtd} registro(s)")
            
            if qtd > 0:
                cursor2.execute(f"SELECT id, nome FROM {tab[0]} LIMIT 5")
                clinicas = cursor2.fetchall()
                print("        Clínicas:")
                for c in clinicas:
                    print(f"          ID {c[0]}: {c[1]}")
    else:
        print("   ⚠️  Nenhuma tabela de clínica encontrada")
    
    conn2.close()
else:
    print("   ❌ Banco não existe")

print("\n" + "="*70 + "\n")

# ============================================================================
# ANÁLISE
# ============================================================================

print("📊 ANÁLISE E CONCLUSÃO\n")
print("-" * 70 + "\n")

print("💡 PROBLEMA 1 - Laudos não aparecem na busca:")
print("   • Laudos estão sendo salvos em: ?")
print("   • Busca está procurando em: ?")
print("   • Solução: Garantir que ambos usem o mesmo banco\n")

print("💡 PROBLEMA 2 - Clínicas não linkadas:")
print("   • Cadastros salvam clínicas em: ?")
print("   • Laudos buscam clínicas em: ?")
print("   • Solução: Garantir que ambos usem o mesmo banco\n")

print("🎯 PRÓXIMO PASSO:")
print("   Me envie TODO o resultado deste script!")
print("   Com essas informações, vou criar os scripts de correção.\n")
