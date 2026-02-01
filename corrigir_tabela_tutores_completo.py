"""
Script DEFINITIVO para adicionar TODAS as colunas que podem faltar
Execute: python corrigir_tabela_tutores_completo.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORREÇÃO COMPLETA DA TABELA TUTORES ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 Verificando estrutura atual...\n")

# Verifica colunas atuais
cursor.execute("PRAGMA table_info(tutores)")
colunas_atuais = {col[1]: col[2] for col in cursor.fetchall()}

print(f"📋 Colunas existentes atualmente: {len(colunas_atuais)}\n")

# TODAS as colunas que a tabela tutores DEVE ter
colunas_completas = {
    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    'nome': 'TEXT NOT NULL',
    'cpf': 'TEXT',
    'rg': 'TEXT',
    'telefone': 'TEXT',
    'celular': 'TEXT',
    'whatsapp': 'TEXT',
    'email': 'TEXT',
    'endereco': 'TEXT',
    'numero': 'TEXT',  # ← Esta estava faltando
    'complemento': 'TEXT',  # ← Esta estava faltando
    'bairro': 'TEXT',
    'cidade': 'TEXT',
    'estado': 'TEXT',
    'cep': 'TEXT',
    'observacoes': 'TEXT',
    'ativo': 'INTEGER DEFAULT 1',
    'data_cadastro': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'criado_por': 'INTEGER'  # ← Esta estava faltando
}

print("🔧 Adicionando colunas faltantes...\n")

adicionadas = []
erros = []

for coluna, tipo in colunas_completas.items():
    if coluna not in colunas_atuais:
        try:
            # Para ALTER TABLE, usamos apenas o tipo base (sem DEFAULT, etc)
            tipo_base = tipo.split()[0]
            
            # Se for INTEGER com DEFAULT, adiciona o DEFAULT
            if 'INTEGER DEFAULT' in tipo:
                default_val = tipo.split('DEFAULT')[1].strip()
                sql = f"ALTER TABLE tutores ADD COLUMN {coluna} INTEGER DEFAULT {default_val}"
            elif 'TIMESTAMP DEFAULT' in tipo:
                sql = f"ALTER TABLE tutores ADD COLUMN {coluna} TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            else:
                sql = f"ALTER TABLE tutores ADD COLUMN {coluna} {tipo_base}"
            
            cursor.execute(sql)
            conn.commit()
            print(f"   ✅ {coluna:<20} ({tipo_base})")
            adicionadas.append(coluna)
            
        except Exception as e:
            print(f"   ❌ {coluna:<20} ERRO: {e}")
            erros.append((coluna, str(e)))
    else:
        print(f"   ⏭️  {coluna:<20} (já existe)")

# Verifica novamente
cursor.execute("PRAGMA table_info(tutores)")
colunas_final = {col[1] for col in cursor.fetchall()}

conn.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print(f"\n📊 Resumo:")
print(f"   ✅ Colunas adicionadas: {len(adicionadas)}")
if adicionadas:
    for col in adicionadas:
        print(f"      • {col}")

print(f"   ⏭️  Já existiam: {len(colunas_atuais)}")
print(f"   📋 Total de colunas agora: {len(colunas_final)}")

if erros:
    print(f"\n⚠️  Erros encontrados: {len(erros)}")
    for col, erro in erros:
        print(f"   • {col}: {erro}")

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R no navegador)")
print("   2. Tente cadastrar o tutor novamente")
print("   3. DEVE funcionar agora! 🎉\n")

print("="*70 + "\n")
