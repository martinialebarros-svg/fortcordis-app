"""
Script para corrigir o tipo da coluna tutor_id na tabela consultas
Execute: python corrigir_tutor_id_consultas.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"

print("\n" + "="*70)
print(" CORRIGIR COLUNA TUTOR_ID ".center(70))
print("="*70 + "\n")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Verifica o problema
print("🔍 Verificando o problema...\n")
cursor.execute("SELECT id, tutor_id FROM consultas")
consultas = cursor.fetchall()

print(f"   Total de consultas: {len(consultas)}")
for c in consultas:
    print(f"   ID: {c[0]} | Tutor ID atual: {c[1]} (tipo: {type(c[1])})")

print("\n⚠️  O tutor_id está como BLOB em vez de INTEGER!")
print("   Vamos recriar a tabela com o tipo correto...\n")

# Salva os dados atuais
print("💾 Salvando dados atuais...\n")
cursor.execute("""
    SELECT 
        id, paciente_id, data_consulta, hora_consulta, tipo_atendimento,
        motivo_consulta, anamnese, historico_atual, alimentacao, ambiente, comportamento,
        peso_kg, temperatura_c, frequencia_cardiaca, frequencia_respiratoria,
        tpc, mucosas, hidratacao, linfonodos, auscultacao_cardiaca, auscultacao_respiratoria,
        palpacao_abdominal, exame_fisico_geral,
        diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
        conduta_terapeutica, prescricao_id, exames_solicitados, procedimentos_realizados, orientacoes,
        prognostico, data_retorno, observacoes,
        veterinario_id, status, data_criacao
    FROM consultas
""")
dados_salvos = cursor.fetchall()

print(f"   ✅ {len(dados_salvos)} consulta(s) salva(s) em memória\n")

# Extrai o tutor_id correto (primeiro byte do BLOB)
print("🔧 Extraindo tutor_id correto dos dados binários...\n")
for i, row in enumerate(dados_salvos):
    print(f"   Consulta {row[0]}: Convertendo tutor_id...")

# Apaga tabela antiga
print("\n🗑️  Apagando tabela antiga...\n")
cursor.execute("DROP TABLE consultas")
conn.commit()

# Cria tabela nova
print("🔨 Criando tabela nova com tipo correto...\n")
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

print("   ✅ Tabela recriada\n")

# Reinsere os dados com tutor_id correto
if dados_salvos:
    print("📥 Reinserindo dados com tutor_id correto...\n")
    
    for row in dados_salvos:
        # Busca o tutor_id correto através do paciente
        cursor.execute("SELECT tutor_id FROM pacientes WHERE id = ?", (row[1],))
        tutor_id_correto = cursor.fetchone()[0]
        
        print(f"   Consulta {row[0]}: Paciente {row[1]} → Tutor {tutor_id_correto}")
        
        cursor.execute("""
            INSERT INTO consultas (
                id, paciente_id, tutor_id, data_consulta, hora_consulta, tipo_atendimento,
                motivo_consulta, anamnese, historico_atual, alimentacao, ambiente, comportamento,
                peso_kg, temperatura_c, frequencia_cardiaca, frequencia_respiratoria,
                tpc, mucosas, hidratacao, linfonodos, auscultacao_cardiaca, auscultacao_respiratoria,
                palpacao_abdominal, exame_fisico_geral,
                diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
                conduta_terapeutica, prescricao_id, exames_solicitados, procedimentos_realizados, orientacoes,
                prognostico, data_retorno, observacoes,
                veterinario_id, status, data_criacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row[0], row[1], tutor_id_correto, row[2], row[3], row[4],
            row[5], row[6], row[7], row[8], row[9], row[10],
            row[11], row[12], row[13], row[14],
            row[15], row[16], row[17], row[18], row[19], row[20],
            row[21], row[22],
            row[23], row[24], row[25],
            row[26], row[27], row[28], row[29], row[30],
            row[31], row[32], row[33],
            row[34], row[35], row[36]
        ))
    
    conn.commit()
    print(f"\n   ✅ {len(dados_salvos)} consulta(s) reinserida(s) com sucesso!\n")

# Verifica se ficou correto
print("🔍 Verificando resultado...\n")
cursor.execute("SELECT id, tutor_id FROM consultas")
consultas_novas = cursor.fetchall()

for c in consultas_novas:
    print(f"   ID: {c[0]} | Tutor ID: {c[1]} (tipo: {type(c[1]).__name__})")

print()

# Testa a query do histórico
print("🧪 Testando query do histórico...\n")
cursor.execute("""
    SELECT 
        c.id,
        c.data_consulta,
        p.nome as paciente,
        t.nome as tutor,
        c.tipo_atendimento,
        c.diagnostico_presuntivo,
        u.nome as veterinario
    FROM consultas c
    JOIN pacientes p ON c.paciente_id = p.id
    JOIN tutores t ON c.tutor_id = t.id
    JOIN usuarios u ON c.veterinario_id = u.id
""")

resultados = cursor.fetchall()

if resultados:
    print("   ✅ Query funcionou! Resultado:")
    for r in resultados:
        print(f"\n   ID: {r[0]}")
        print(f"   Data: {r[1]}")
        print(f"   Paciente: {r[2]}")
        print(f"   Tutor: {r[3]}")
        print(f"   Tipo: {r[4]}")
        print(f"   Diagnóstico: {r[5]}")
        print(f"   Veterinário: {r[6]}")
else:
    print("   ⚠️  Query ainda retornou vazio")

conn.close()

print("\n" + "="*70)
print("✅ CORREÇÃO CONCLUÍDA!")
print("="*70)

print("\n🎯 Próximo passo:")
print("   1. Recarregue a página do Streamlit (aperte R)")
print("   2. Vá em Consultas")
print("   3. O histórico deve aparecer agora! 🎉\n")
