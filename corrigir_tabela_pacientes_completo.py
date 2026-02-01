"""
Script para corrigir a tabela pacientes (mesmo problema da tutores)
Execute: python corrigir_tabela_pacientes_completo.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORREÇÃO COMPLETA DA TABELA PACIENTES ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 Verificando estrutura atual...\n")

# Verifica colunas atuais
cursor.execute("PRAGMA table_info(pacientes)")
colunas_atuais = {col[1]: col[2] for col in cursor.fetchall()}

print(f"📋 Colunas existentes atualmente: {len(colunas_atuais)}\n")

# TODAS as colunas que a tabela pacientes DEVE ter
colunas_completas = {
    'id': 'INTEGER',
    'tutor_id': 'INTEGER',
    'nome': 'TEXT',
    'especie': 'TEXT',
    'raca': 'TEXT',
    'sexo': 'TEXT',
    'castrado': 'INTEGER',
    'data_nascimento': 'DATE',
    'idade_anos': 'INTEGER',
    'idade_meses': 'INTEGER',
    'peso_kg': 'REAL',
    'cor_pelagem': 'TEXT',
    'microchip': 'TEXT',
    'numero_registro': 'TEXT',
    'foto_url': 'TEXT',
    'alergias': 'TEXT',
    'medicamentos_uso': 'TEXT',
    'doencas_previas': 'TEXT',
    'cirurgias_previas': 'TEXT',
    'vacinacao_em_dia': 'INTEGER',
    'vermifugacao_em_dia': 'INTEGER',
    'observacoes': 'TEXT',
    'ativo': 'INTEGER',
    'data_cadastro': 'TIMESTAMP',
    'data_obito': 'DATE',
    'criado_por': 'INTEGER'
}

print("🔧 Adicionando colunas faltantes...\n")

adicionadas = []
erros = []

for coluna, tipo in colunas_completas.items():
    if coluna not in colunas_atuais:
        try:
            tipo_base = tipo.split()[0]
            
            if 'INTEGER' in tipo and coluna in ['ativo', 'castrado', 'vacinacao_em_dia', 'vermifugacao_em_dia']:
                sql = f"ALTER TABLE pacientes ADD COLUMN {coluna} INTEGER DEFAULT 1"
            elif 'TIMESTAMP' in tipo:
                sql = f"ALTER TABLE pacientes ADD COLUMN {coluna} TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            else:
                sql = f"ALTER TABLE pacientes ADD COLUMN {coluna} {tipo_base}"
            
            cursor.execute(sql)
            conn.commit()
            print(f"   ✅ {coluna:<25} ({tipo_base})")
            adicionadas.append(coluna)
            
        except Exception as e:
            print(f"   ❌ {coluna:<25} ERRO: {e}")
            erros.append((coluna, str(e)))
    else:
        print(f"   ⏭️  {coluna:<25} (já existe)")

# Verifica novamente
cursor.execute("PRAGMA table_info(pacientes)")
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
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Tente cadastrar o paciente novamente")
print("   3. DEVE funcionar! 🎉\n")

print("="*70 + "\n")
