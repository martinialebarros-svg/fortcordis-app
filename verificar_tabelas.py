import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\Desktop\FortCordis_Novo\fortcordis.db")

print(f"Verificando: {DB_PATH}")
print(f"Existe? {DB_PATH.exists()}")

if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Lista todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = cursor.fetchall()
    
    print(f"\n✅ Total de tabelas: {len(tabelas)}")
    
    for tabela in tabelas:
        nome_tabela = tabela[0]
        print(f"\n📋 Tabela: {nome_tabela}")
        
        # Lista as colunas de cada tabela
        cursor.execute(f"PRAGMA table_info({nome_tabela})")
        colunas = cursor.fetchall()
        
        for col in colunas:
            print(f"   - {col[1]} ({col[2]})")
    
    conn.close()
else:
    print("❌ Banco não existe!")