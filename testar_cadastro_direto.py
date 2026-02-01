import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\Desktop\FortCordis_Novo\fortcordis.db")

print(f"Conectando em: {DB_PATH}")
print(f"Existe? {DB_PATH.exists()}")

if not DB_PATH.exists():
    print("ERRO: Banco não existe!")
    exit()

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Lista tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = [t[0] for t in cursor.fetchall()]
print(f"\nTabelas: {tabelas}")

if 'clinicas_parceiras' not in tabelas:
    print("\n❌ ERRO: Tabela 'clinicas_parceiras' NÃO EXISTE!")
    print("Execute: python CRIAR_BANCO_FINAL.py")
    exit()

print("\n✅ Tabela existe! Testando inserção...")

try:
    cursor.execute("""
        INSERT INTO clinicas_parceiras (
            nome, endereco, cidade, telefone, whatsapp,
            cnpj, responsavel_veterinario, crmv_responsavel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Vetworld FINAL", "Av. Rui Barbosa, 550", "Fortaleza", 
          "(85) 3456-7890", "(85) 98765-4321", 
          "00.000.000/0001-00", "Veterinário Responsável", "CRMV-CE 12345"))
    
    conn.commit()
    print("✅ INSERÇÃO FUNCIONOU!")
    
    # Mostra o que foi inserido
    cursor.execute("SELECT * FROM clinicas_parceiras")
    for row in cursor.fetchall():
        print(f"  - {row}")
    
except Exception as e:
    print(f"❌ ERRO ao inserir: {e}")
    import traceback
    traceback.print_exc()

conn.close()