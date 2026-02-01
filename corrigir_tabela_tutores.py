"""
Script para corrigir a tabela tutores
Execute: python corrigir_tabela_tutores.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORRIGIR TABELA TUTORES ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 Verificando estrutura da tabela tutores...\n")

# Verifica se a coluna 'numero' existe
cursor.execute("PRAGMA table_info(tutores)")
colunas = cursor.fetchall()

print("📋 Colunas atuais:")
for col in colunas:
    print(f"   - {col[1]} ({col[2]})")

# Verifica se 'numero' existe
tem_numero = any(col[1] == 'numero' for col in colunas)

if tem_numero:
    print("\n✅ Coluna 'numero' já existe!")
else:
    print("\n❌ Coluna 'numero' NÃO existe. Adicionando...")
    
    try:
        cursor.execute("ALTER TABLE tutores ADD COLUMN numero TEXT")
        conn.commit()
        print("✅ Coluna 'numero' adicionada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")

conn.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70 + "\n")

print("🎯 Próximo passo:")
print("   Tente cadastrar o tutor novamente no sistema\n")
