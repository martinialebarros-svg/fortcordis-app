"""
Script para diagnosticar por que as clínicas não migraram
Execute: python diagnosticar_migracao_clinicas.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" DIAGNÓSTICO: Clínicas ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica tabelas que existem
print("🔍 Tabelas relacionadas a clínicas:\n")
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE '%clinic%'
    ORDER BY name
""")
tabelas = cursor.fetchall()

for tab in tabelas:
    nome_tabela = tab[0]
    cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}")
    qtd = cursor.fetchone()[0]
    print(f"   📋 {nome_tabela}: {qtd} registro(s)")
    
    # Mostra estrutura
    cursor.execute(f"PRAGMA table_info({nome_tabela})")
    colunas = cursor.fetchall()
    print(f"      Colunas: {', '.join([c[1] for c in colunas])}")
    
    # Mostra alguns registros
    if qtd > 0:
        cursor.execute(f"SELECT * FROM {nome_tabela} LIMIT 3")
        registros = cursor.fetchall()
        print(f"\n      Primeiros registros:")
        for reg in registros:
            print(f"         {reg}")
    print()

conn.close()

print("="*70)
print("\n💡 Me envie TODO este resultado!")
