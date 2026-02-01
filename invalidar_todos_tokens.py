import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\marti\FortCordis\data\fortcordis.db")

print("\n" + "="*70)
print(" INVALIDAR TODOS OS TOKENS ".center(70))
print("="*70 + "\n")

try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Conta tokens ativos
    cursor.execute("SELECT COUNT(*) FROM sessoes_persistentes WHERE ativo = 1")
    qtd_ativos = cursor.fetchone()[0]
    
    print(f"📊 Tokens ativos antes: {qtd_ativos}\n")
    
    # Desativa TODOS
    cursor.execute("UPDATE sessoes_persistentes SET ativo = 0")
    
    conn.commit()
    
    # Verifica
    cursor.execute("SELECT COUNT(*) FROM sessoes_persistentes WHERE ativo = 1")
    qtd_depois = cursor.fetchone()[0]
    
    print(f"📊 Tokens ativos depois: {qtd_depois}\n")
    
    conn.close()
    
    print("="*70)
    print("✅ TODOS OS TOKENS FORAM INVALIDADOS!")
    print("="*70)
    
    print("\n🎯 PRÓXIMO PASSO:")
    print("   1. Feche o navegador completamente")
    print("   2. Limpe cookies e cache")
    print("   3. Abra em aba anônima")
    print("   4. Faça login sem marcar checkbox")
    print("   5. Teste se funciona\n")
    
except Exception as e:
    print(f"❌ Erro: {e}\n")

print("="*70 + "\n")
