import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" ESTRUTURA DA TABELA laudos_ecocardiograma ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Mostra estrutura da tabela
cursor.execute("PRAGMA table_info(laudos_ecocardiograma)")
colunas = cursor.fetchall()

print("📋 Colunas existentes:\n")

for col in colunas:
    print(f"   {col[1]:<30} {col[2]:<15}")

conn.close()

print("\n" + "="*70 + "\n")
