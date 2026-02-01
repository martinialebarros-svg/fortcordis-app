import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" PROCURANDO TABELAS DE RELAÇÃO ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Lista TODAS as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tabelas = cursor.fetchall()

print("📋 Todas as tabelas do banco:\n")
for tab in tabelas:
    print(f"   • {tab[0]}")

print("\n" + "="*70 + "\n")

# Procura tabelas que podem ter relação usuario-permissao
print("🔍 Procurando tabelas com 'usuario' E 'permiss':\n")

for tab in tabelas:
    nome = tab[0].lower()
    if 'usuario' in nome or 'user' in nome or 'permiss' in nome or 'role' in nome or 'acesso' in nome:
        print(f"   📌 {tab[0]}")
        
        # Mostra estrutura
        cursor.execute(f"PRAGMA table_info({tab[0]})")
        colunas = cursor.fetchall()
        
        print(f"      Colunas: {', '.join([c[1] for c in colunas])}")
        
        # Mostra exemplo
        cursor.execute(f"SELECT * FROM {tab[0]} LIMIT 1")
        exemplo = cursor.fetchone()
        if exemplo:
            print(f"      Exemplo: {exemplo}")
        
        print()

conn.close()

print("="*70 + "\n")
