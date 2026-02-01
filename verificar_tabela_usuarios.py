import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" ESTRUTURA DA TABELA usuarios ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(usuarios)")
colunas = cursor.fetchall()

print("📋 Colunas existentes:\n")

for col in colunas:
    print(f"   {col[1]:<30} {col[2]:<15}")

print("\n" + "="*70 + "\n")

# Mostra um usuário de exemplo
cursor.execute("SELECT * FROM usuarios LIMIT 1")
usuario = cursor.fetchone()

if usuario:
    print("📄 Exemplo de registro:\n")
    for i, col in enumerate(colunas):
        print(f"   {col[1]:<30} {usuario[i]}")

conn.close()

print("\n" + "="*70 + "\n")
