"""
Script para adicionar TODAS as colunas que faltam na tabela tutores
Execute: python adicionar_colunas_tutores.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" ADICIONAR COLUNAS FALTANTES - TUTORES ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 Verificando estrutura da tabela tutores...\n")

# Verifica colunas atuais
cursor.execute("PRAGMA table_info(tutores)")
colunas_atuais = {col[1] for col in cursor.fetchall()}

print(f"📋 Colunas existentes: {len(colunas_atuais)}")
for col in sorted(colunas_atuais):
    print(f"   ✅ {col}")

print("\n" + "-"*70 + "\n")

# Lista de colunas que DEVEM existir
colunas_necessarias = {
    'numero': 'TEXT',
    'complemento': 'TEXT',
    'whatsapp': 'TEXT'
}

print("🔧 Adicionando colunas faltantes...\n")

adicionadas = 0
ja_existentes = 0

for coluna, tipo in colunas_necessarias.items():
    if coluna not in colunas_atuais:
        try:
            sql = f"ALTER TABLE tutores ADD COLUMN {coluna} {tipo}"
            cursor.execute(sql)
            conn.commit()
            print(f"   ✅ Adicionada: {coluna} ({tipo})")
            adicionadas += 1
        except Exception as e:
            print(f"   ❌ Erro ao adicionar {coluna}: {e}")
    else:
        print(f"   ⏭️  Já existe: {coluna}")
        ja_existentes += 1

conn.close()

print("\n" + "="*70)
print("✅ PROCESSO CONCLUÍDO!")
print("="*70)

print(f"\n📊 Resumo:")
print(f"   ✅ Colunas adicionadas: {adicionadas}")
print(f"   ⏭️  Já existiam: {ja_existentes}")
print(f"   📋 Total de colunas necessárias: {len(colunas_necessarias)}")

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Tente cadastrar o tutor novamente")
print("   3. Deve funcionar agora!\n")
