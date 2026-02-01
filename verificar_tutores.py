import sqlite3
from pathlib import Path

print("\n" + "="*70)
print(" VERIFICAR TUTORES CADASTRADOS ".center(70))
print("="*70 + "\n")

DB_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
print(f"🔍 Verificando: {DB_AUTH}\n")

conn = sqlite3.connect(str(DB_AUTH))
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM tutores WHERE ativo = 1")
qtd = cursor.fetchone()[0]
print(f"✅ Total de tutores ativos: {qtd}\n")

if qtd > 0:
    cursor.execute("SELECT id, nome, cpf, celular FROM tutores WHERE ativo = 1")
    tutores = cursor.fetchall()
    print("📋 Lista completa:")
    for t in tutores:
        print(f"   ID: {t[0]}")
        print(f"   Nome: {t[1]}")
        print(f"   CPF: {t[2]}")
        print(f"   Celular: {t[3]}")
        print()

conn.close()

print("="*70 + "\n")