"""
Script para adicionar TODAS as colunas que faltam na tabela consultas
Execute: python corrigir_tabela_consultas_completo.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORREÇÃO COMPLETA DA TABELA CONSULTAS ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 Verificando estrutura atual...\n")

# Verifica colunas atuais
cursor.execute("PRAGMA table_info(consultas)")
colunas_atuais = {col[1]: col[2] for col in cursor.fetchall()}

print(f"📋 Colunas existentes atualmente: {len(colunas_atuais)}\n")

# TODAS as colunas que a tabela consultas DEVE ter
colunas_completas = {
    'id': 'INTEGER',
    'paciente_id': 'INTEGER',
    'tutor_id': 'INTEGER',
    'data_consulta': 'DATE',
    'hora_consulta': 'TIME',
    'tipo_atendimento': 'TEXT',
    'motivo_consulta': 'TEXT',
    'anamnese': 'TEXT',
    'historico_atual': 'TEXT',
    'alimentacao': 'TEXT',
    'ambiente': 'TEXT',
    'comportamento': 'TEXT',
    'peso_kg': 'REAL',
    'temperatura_c': 'REAL',
    'frequencia_cardiaca': 'INTEGER',
    'frequencia_respiratoria': 'INTEGER',
    'tpc': 'TEXT',
    'mucosas': 'TEXT',
    'hidratacao': 'TEXT',
    'linfonodos': 'TEXT',
    'auscultacao_cardiaca': 'TEXT',
    'auscultacao_respiratoria': 'TEXT',
    'palpacao_abdominal': 'TEXT',
    'exame_fisico_geral': 'TEXT',
    'diagnostico_presuntivo': 'TEXT',
    'diagnostico_diferencial': 'TEXT',
    'diagnostico_definitivo': 'TEXT',
    'conduta_terapeutica': 'TEXT',
    'prescricao_id': 'INTEGER',
    'exames_solicitados': 'TEXT',
    'procedimentos_realizados': 'TEXT',
    'orientacoes': 'TEXT',
    'prognostico': 'TEXT',
    'data_retorno': 'DATE',
    'observacoes': 'TEXT',
    'veterinario_id': 'INTEGER',
    'status': 'TEXT',
    'data_criacao': 'TIMESTAMP',
    'data_modificacao': 'TIMESTAMP'
}

print("🔧 Adicionando colunas faltantes...\n")

adicionadas = []
erros = []

for coluna, tipo in colunas_completas.items():
    if coluna not in colunas_atuais:
        try:
            tipo_base = tipo.split()[0]
            
            if 'TIMESTAMP' in tipo and coluna == 'data_criacao':
                sql = f"ALTER TABLE consultas ADD COLUMN {coluna} TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            elif coluna == 'status':
                sql = f"ALTER TABLE consultas ADD COLUMN {coluna} TEXT DEFAULT 'finalizado'"
            else:
                sql = f"ALTER TABLE consultas ADD COLUMN {coluna} {tipo_base}"
            
            cursor.execute(sql)
            conn.commit()
            print(f"   ✅ {coluna:<30} ({tipo_base})")
            adicionadas.append(coluna)
            
        except Exception as e:
            print(f"   ❌ {coluna:<30} ERRO: {e}")
            erros.append((coluna, str(e)))
    else:
        tipo_atual = colunas_atuais[coluna]
        print(f"   ⏭️  {coluna:<30} (já existe: {tipo_atual})")

# Verifica novamente
cursor.execute("PRAGMA table_info(consultas)")
colunas_final = {col[1] for col in cursor.fetchall()}

conn.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print(f"\n📊 Resumo:")
print(f"   ✅ Colunas adicionadas: {len(adicionadas)}")
if adicionadas:
    print(f"\n   Colunas que foram adicionadas:")
    for col in adicionadas:
        print(f"      • {col}")

print(f"\n   ⏭️  Já existiam: {len(colunas_atuais)}")
print(f"   📋 Total de colunas agora: {len(colunas_final)}")
print(f"   🎯 Total esperado: {len(colunas_completas)}")

if len(colunas_final) == len(colunas_completas):
    print("\n   ✅ PERFEITO! Todas as colunas estão presentes!")
else:
    print(f"\n   ⚠️  Ainda faltam {len(colunas_completas) - len(colunas_final)} coluna(s)")

if erros:
    print(f"\n⚠️  Erros encontrados: {len(erros)}")
    for col, erro in erros:
        print(f"   • {col}: {erro}")

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Tente registrar a consulta novamente")
print("   3. DEVE funcionar! 🎉\n")

print("="*70 + "\n")
