"""
Script para RECRIAR a tabela consultas sem constraints problemáticas
ATENÇÃO: Este script APAGA e RECRIA a tabela consultas
Execute: python recriar_tabela_consultas.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" RECRIAR TABELA CONSULTAS ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica se há dados na tabela
cursor.execute("SELECT COUNT(*) FROM consultas")
qtd_registros = cursor.fetchone()[0]

if qtd_registros > 0:
    print(f"⚠️  ATENÇÃO: Existem {qtd_registros} registro(s) na tabela consultas")
    print("   Esses registros serão PERDIDOS se você continuar!")
    resposta = input("\n   Deseja continuar? (digite SIM para confirmar): ")
    
    if resposta.upper() != "SIM":
        print("\n❌ Operação cancelada pelo usuário")
        conn.close()
        exit()

print("\n🗑️  Apagando tabela antiga...\n")
cursor.execute("DROP TABLE IF EXISTS consultas")
conn.commit()
print("   ✅ Tabela antiga removida\n")

print("🔨 Criando tabela nova (sem constraints problemáticas)...\n")

cursor.execute("""
    CREATE TABLE consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL,
        tutor_id INTEGER NOT NULL,
        data_consulta DATE NOT NULL,
        hora_consulta TIME,
        tipo_atendimento TEXT,
        motivo_consulta TEXT,
        anamnese TEXT,
        historico_atual TEXT,
        alimentacao TEXT,
        ambiente TEXT,
        comportamento TEXT,
        peso_kg REAL,
        temperatura_c REAL,
        frequencia_cardiaca INTEGER,
        frequencia_respiratoria INTEGER,
        tpc TEXT,
        mucosas TEXT,
        hidratacao TEXT,
        linfonodos TEXT,
        auscultacao_cardiaca TEXT,
        auscultacao_respiratoria TEXT,
        palpacao_abdominal TEXT,
        exame_fisico_geral TEXT,
        diagnostico_presuntivo TEXT,
        diagnostico_diferencial TEXT,
        diagnostico_definitivo TEXT,
        conduta_terapeutica TEXT,
        prescricao_id INTEGER,
        exames_solicitados TEXT,
        procedimentos_realizados TEXT,
        orientacoes TEXT,
        prognostico TEXT,
        data_retorno DATE,
        observacoes TEXT,
        veterinario_id INTEGER NOT NULL,
        status TEXT DEFAULT 'finalizado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_modificacao TIMESTAMP,
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (tutor_id) REFERENCES tutores(id),
        FOREIGN KEY (veterinario_id) REFERENCES usuarios(id)
    )
""")

conn.commit()
print("   ✅ Tabela criada com sucesso!\n")

# Verifica a estrutura
cursor.execute("PRAGMA table_info(consultas)")
colunas = cursor.fetchall()

print("📋 Estrutura da tabela (total de colunas: {}):".format(len(colunas)))
for col in colunas:
    null_str = "NOT NULL" if col[3] == 1 else "NULL"
    default_str = f" DEFAULT {col[4]}" if col[4] else ""
    print(f"   • {col[1]:<30} {col[2]:<10} {null_str:<10}{default_str}")

conn.close()

print("\n" + "="*70)
print("✅ TABELA CONSULTAS RECRIADA COM SUCESSO!")
print("="*70)

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Tente registrar a consulta novamente")
print("   3. Deve funcionar perfeitamente agora! 🎉\n")

print("="*70 + "\n")
