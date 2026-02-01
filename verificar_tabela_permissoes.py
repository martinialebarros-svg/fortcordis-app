import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" ESTRUTURA DA TABELA permissoes ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica se a tabela existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permissoes'")
existe = cursor.fetchone()

if not existe:
    print("❌ Tabela 'permissoes' NÃO EXISTE!\n")
    
    # Verifica outras tabelas com nome parecido
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%permiss%'")
    similares = cursor.fetchall()
    
    if similares:
        print("📋 Tabelas parecidas encontradas:")
        for tab in similares:
            print(f"   • {tab[0]}")
    
    print("\n" + "="*70 + "\n")
    conn.close()
    exit()

# Mostra estrutura
cursor.execute("PRAGMA table_info(permissoes)")
colunas = cursor.fetchall()

print("📋 Colunas existentes:\n")

for col in colunas:
    print(f"   {col[1]:<30} {col[2]:<15}")

print("\n" + "="*70 + "\n")

# Mostra exemplos
cursor.execute("SELECT * FROM permissoes LIMIT 3")
permissoes = cursor.fetchall()

if permissoes:
    print("📄 Exemplos de registros:\n")
    for perm in permissoes:
        print(f"   Registro: {perm}")

conn.close()

print("\n" + "="*70 + "\n")
