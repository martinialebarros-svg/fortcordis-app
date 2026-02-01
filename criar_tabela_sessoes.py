import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" CRIAR TABELA sessoes_persistentes ".center(70))
print("="*70 + "\n")

try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Verifica se já existe
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='sessoes_persistentes'
    """)
    
    existe = cursor.fetchone()
    
    if existe:
        print("⚠️  Tabela já existe!\n")
        
        # Mostra quantos registros tem
        cursor.execute("SELECT COUNT(*) FROM sessoes_persistentes")
        qtd = cursor.fetchone()[0]
        print(f"📊 Registros existentes: {qtd}\n")
        
    else:
        print("📋 Criando tabela...\n")
        
        # Cria a tabela
        cursor.execute("""
            CREATE TABLE sessoes_persistentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expira_em TIMESTAMP NOT NULL,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        conn.commit()
        
        print("✅ Tabela criada com sucesso!\n")
    
    conn.close()
    
    print("="*70)
    print("✅ PRONTO!")
    print("="*70)
    
except Exception as e:
    print(f"❌ Erro: {e}\n")
    print("="*70)

print("\n🎯 PRÓXIMO PASSO:")
print("   1. A tabela está pronta")
print("   2. Limpe o navegador (cookies)")
print("   3. Acesse em aba anônima")
print("   4. Faça login SEM marcar checkbox")
print("   5. Teste se funciona normalmente\n")

print("="*70 + "\n")
