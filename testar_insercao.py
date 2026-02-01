import sqlite3
from pathlib import Path

# Mesmo caminho que o código usa
DB_PATH = Path(__file__).parent / "fortcordis.db"

print(f"🔍 Tentando conectar em: {DB_PATH.absolute()}")
print(f"✅ Arquivo existe? {DB_PATH.exists()}")

if not DB_PATH.exists():
    print("❌ ERRO: Banco não existe!")
    exit()

# Tenta conectar e inserir
try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print("\n📋 Testando inserção...")
    
    cursor.execute("""
        INSERT INTO clinicas_parceiras (
            nome, endereco, cidade, telefone, whatsapp,
            cnpj, responsavel_veterinario, crmv_responsavel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Clínica Teste", "Rua Teste, 123", "Fortaleza", 
          "(85) 1234-5678", "(85) 98765-4321", 
          "00.000.000/0001-00", "Dr. Teste", "CRMV-CE 12345"))
    
    conn.commit()
    print("✅ INSERÇÃO FUNCIONOU!")
    
    # Lista as clínicas
    cursor.execute("SELECT id, nome FROM clinicas_parceiras")
    clinicas = cursor.fetchall()
    
    print(f"\n📊 Total de clínicas: {len(clinicas)}")
    for cli in clinicas:
        print(f"  - ID {cli[0]}: {cli[1]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()