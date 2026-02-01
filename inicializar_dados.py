"""
Script de Inicialização - Fort Cordis
Popula o banco de dados com dados iniciais (serviços, medicamentos, etc)
Execute este script UMA VEZ após criar o banco
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / "FortCordis" / "fortcordis.db"

def popular_servicos():
    """Cadastra serviços padrão de cardiologia veterinária"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    servicos_padrao = [
        ("Ecocardiograma", "Exame ecocardiográfico completo com modo M, bidimensional e Doppler", 300.00, 60),
        ("Eletrocardiograma", "ECG de repouso com análise do ritmo cardíaco", 150.00, 30),
        ("Pressão Arterial", "Aferição de pressão arterial sistêmica pelo método Doppler", 80.00, 15),
        ("Consulta Cardiológica", "Avaliação clínica cardiológica completa com exame físico", 250.00, 45),
        ("Holter 24h", "Monitoramento cardíaco contínuo por 24 horas", 500.00, 30),
        ("MAPA 24h", "Monitoramento ambulatorial de pressão arterial por 24 horas", 450.00, 30),
        ("Radiografia Torácica", "Radiografia de tórax em 2 posições para avaliação cardiopulmonar", 120.00, 20),
        ("Pacote Eco + ECG", "Ecocardiograma + Eletrocardiograma", 400.00, 90),
        ("Pacote Avaliação Completa", "Consulta + Eco + ECG + PA", 650.00, 120),
        ("Retorno Cardiológico", "Consulta de retorno para reavaliação", 150.00, 30)
    ]
    
    for nome, desc, valor, duracao in servicos_padrao:
        cursor.execute("""
            INSERT OR IGNORE INTO servicos (nome, descricao, valor_base, duracao_minutos)
            VALUES (?, ?, ?, ?)
        """, (nome, desc, valor, duracao))
    
    conn.commit()
    conn.close()
    print("✅ Serviços cadastrados com sucesso!")

def popular_medicamentos():
    """Cadastra medicamentos comuns em cardiologia veterinária"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    medicamentos_padrao = [
        # (nome, princípio_ativo, concentração, unidade, forma, dose_padrão, dose_min, dose_max, frequência, via, observações)
        
        # Diuréticos
        ("Furosemida 10mg/ml", "Furosemida", "10mg/ml", "mg/ml", "Solução injetável", 
         2.0, 1.0, 4.0, "BID (12/12h)", "VO/IM/IV", "Administrar pela manhã e tarde. Monitorar eletrólitos."),
        
        ("Furosemida 40mg", "Furosemida", "40mg", "mg", "Comprimido", 
         2.0, 1.0, 4.0, "BID (12/12h)", "VO", "Pode ser dividido conforme necessário"),
        
        ("Espironolactona 25mg", "Espironolactona", "25mg", "mg", "Comprimido", 
         2.0, 1.0, 2.0, "SID/BID", "VO", "Diurético poupador de potássio"),
        
        # Inotrópicos
        ("Pimobendan 1.25mg", "Pimobendan", "1.25mg", "mg", "Comprimido mastigável", 
         0.25, 0.2, 0.3, "BID (12/12h)", "VO", "Administrar 1h antes das refeições"),
        
        ("Pimobendan 5mg", "Pimobendan", "5mg", "mg", "Comprimido mastigável", 
         0.25, 0.2, 0.3, "BID (12/12h)", "VO", "Administrar 1h antes das refeições"),
        
        ("Digoxina 0.25mg", "Digoxina", "0.25mg", "mg", "Comprimido", 
         0.005, 0.003, 0.01, "BID", "VO", "Monitorar níveis séricos. Margem terapêutica estreita."),
        
        # IECA (Inibidores da ECA)
        ("Enalapril 10mg", "Enalapril", "10mg", "mg", "Comprimido", 
         0.5, 0.25, 1.0, "SID/BID", "VO", "Pode causar hipotensão inicial"),
        
        ("Enalapril 20mg", "Enalapril", "20mg", "mg", "Comprimido", 
         0.5, 0.25, 1.0, "SID/BID", "VO", "Para animais de maior porte"),
        
        ("Benazepril 5mg", "Benazepril", "5mg", "mg", "Comprimido", 
         0.5, 0.25, 1.0, "SID", "VO", "Eliminação hepatobiliar - melhor para pacientes com doença renal"),
        
        # Vasodilatadores
        ("Sildenafil 20mg", "Sildenafil", "20mg", "mg", "Comprimido", 
         1.0, 0.5, 3.0, "TID (8/8h)", "VO", "Para hipertensão pulmonar"),
        
        ("Hidralazina 25mg", "Hidralazina", "25mg", "mg", "Comprimido", 
         1.0, 0.5, 2.0, "BID", "VO", "Vasodilatador arterial direto"),
        
        # Beta-bloqueadores
        ("Atenolol 25mg", "Atenolol", "25mg", "mg", "Comprimido", 
         0.25, 0.125, 1.0, "SID/BID", "VO", "Para taquiarritmias. Evitar em ICC descompensada."),
        
        ("Carvedilol 6.25mg", "Carvedilol", "6.25mg", "mg", "Comprimido", 
         0.2, 0.1, 0.5, "BID", "VO", "Beta-bloqueador não seletivo"),
        
        # Antiarrítmicos
        ("Diltiazem 30mg", "Diltiazem", "30mg", "mg", "Comprimido", 
         0.5, 0.25, 1.5, "TID", "VO", "Bloqueador de canal de cálcio. Para taquiarritmias supraventriculares."),
        
        ("Amiodarona 200mg", "Amiodarona", "200mg", "mg", "Comprimido", 
         10.0, 5.0, 15.0, "SID/BID", "VO", "Antiarrítmico de classe III. Monitorar função tireoidiana."),
        
        # Suplementos
        ("Taurina 500mg", "Taurina", "500mg", "mg", "Cápsula", 
         250.0, 250.0, 500.0, "BID", "VO", "Suplementação em cardiomiopatia dilatada felina"),
        
        ("L-Carnitina 500mg", "L-Carnitina", "500mg", "mg", "Cápsula", 
         50.0, 50.0, 100.0, "TID", "VO", "Suporte metabólico cardíaco"),
        
        # Anticoagulantes
        ("Clopidogrel 75mg", "Clopidogrel", "75mg", "mg", "Comprimido", 
         1.0, 0.5, 2.0, "SID", "VO", "Antiagregante plaquetário para prevenção de tromboembolismo"),
        
        ("Aspirina 100mg", "Ácido Acetilsalicílico", "100mg", "mg", "Comprimido", 
         0.5, 0.5, 10.0, "A cada 72h (Gatos) / SID (Cães)", "VO", "Dose e frequência variam entre espécies"),
    ]
    
    for med in medicamentos_padrao:
        nome, princ, conc, unid, forma, dose_pad, dose_min, dose_max, freq, via, obs = med
        cursor.execute("""
            INSERT OR IGNORE INTO medicamentos (
                nome, principio_ativo, concentracao, unidade_concentracao,
                forma_farmaceutica, dose_padrao_mg_kg, dose_min_mg_kg, dose_max_mg_kg,
                frequencia_padrao, via_administracao, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, princ, conc, unid, forma, dose_pad, dose_min, dose_max, freq, via, obs))
    
    conn.commit()
    conn.close()
    print("✅ Medicamentos cadastrados com sucesso!")

def popular_templates_prescricao():
    """Cadastra templates comuns de prescrição"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    templates = [
        (
            "ICC B1 - Protocolo Inicial",
            "Insuficiência Cardíaca Congestiva Classe B1 (ACVIM)",
            """Pimobendan 1.25mg - Administrar 1 comprimido a cada 12 horas, 1 hora antes das refeições

Enalapril 10mg - Administrar 1 comprimido a cada 12 horas

Furosemida 40mg - Administrar 1 comprimido a cada 12 horas pela manhã e tarde

Retorno em 15 dias para reavaliação e ajuste de doses conforme resposta clínica."""
        ),
        (
            "ICC B2 - Protocolo Avançado",
            "Insuficiência Cardíaca Congestiva Classe B2 (ACVIM)",
            """Pimobendan 5mg - Administrar 1 comprimido a cada 12 horas, 1 hora antes das refeições

Furosemida 40mg - Administrar 1,5 comprimido a cada 12 horas

Espironolactona 25mg - Administrar 1 comprimido a cada 12 horas

Enalapril 20mg - Administrar 1 comprimido a cada 12 horas

Sildenafil 20mg - Administrar 1 comprimido a cada 8 horas (se hipertensão pulmonar)

Monitorar diurese, apetite e frequência respiratória. Retorno em 7 dias."""
        ),
        (
            "Hipertensão Pulmonar",
            "Hipertensão Pulmonar",
            """Sildenafil 20mg - Administrar 1 comprimido a cada 8 horas

Pimobendan 5mg - Administrar 1 comprimido a cada 12 horas, 1 hora antes das refeições

Furosemida 40mg - Administrar conforme necessário para controle de edema

Repouso relativo. Evitar esforços físicos intensos. Retorno em 30 dias para reavaliação ecocardiográfica."""
        ),
        (
            "Cardiomiopatia Dilatada Felina",
            "Cardiomiopatia Dilatada em Felinos",
            """Pimobendan 1.25mg - Administrar 1/4 de comprimido a cada 12 horas

Taurina 500mg - Administrar 1 cápsula a cada 12 horas

Enalapril 2.5mg - Administrar 1 comprimido a cada 24 horas

Furosemida 40mg - Administrar 1/4 de comprimido a cada 12 horas (ajustar conforme necessário)

Alimentação: dieta com alta concentração de taurina. Retorno em 10 dias."""
        ),
        (
            "Taquiarritmia Supraventricular",
            "Taquicardia Supraventricular",
            """Diltiazem 30mg - Administrar 1 comprimido a cada 8 horas

Atenolol 25mg - Administrar 1/2 comprimido a cada 12 horas (se necessário)

Monitorar frequência cardíaca em repouso. Evitar estresse. Retorno em 15 dias para novo ECG."""
        )
    ]
    
    for nome, indicacao, texto in templates:
        cursor.execute("""
            INSERT OR IGNORE INTO prescricoes_templates (nome_template, indicacao, texto_prescricao)
            VALUES (?, ?, ?)
        """, (nome, indicacao, texto))
    
    conn.commit()
    conn.close()
    print("✅ Templates de prescrição cadastrados com sucesso!")

def popular_clinicas_exemplo():
    """Cadastra algumas clínicas exemplo (OPCIONAL - você pode pular ou adaptar)"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    clinicas_exemplo = [
        ("Clínica Veterinária Centro", "Av. Santos Dumont, 1234", "Aldeota", "Fortaleza",
         "(85) 3456-7890", "(85) 98765-4321", "contato@vetcentro.com.br", "12.345.678/0001-90",
         "Dr. João Silva", "CRMV-CE 12345", "Parceria desde 2020. Desconto de 15% em todos os serviços."),
        
        ("Vet Care Pet Shop e Clínica", "Rua Barão de Studart, 567", "Meireles", "Fortaleza",
         "(85) 3234-5678", "(85) 99876-5432", "atendimento@vetcare.com", "23.456.789/0001-01",
         "Dra. Maria Santos", "CRMV-CE 23456", "Cliente regular. Pagamento via PIX."),
        
        ("Hospital Veterinário 24h", "Av. Washington Soares, 8900", "Edson Queiroz", "Fortaleza",
         "(85) 3333-4444", "(85) 98888-9999", "recepcao@hosp24h.vet", "34.567.890/0001-12",
         "Dr. Carlos Oliveira", "CRMV-CE 34567", "Parceria preferencial. Faturamento mensal.")
    ]
    
    for clinica in clinicas_exemplo:
        nome, end, bairro, cidade, tel, whats, email, cnpj, resp, crmv, obs = clinica
        cursor.execute("""
            INSERT OR IGNORE INTO clinicas_parceiras (
                nome, endereco, bairro, cidade, telefone, whatsapp,
                email, cnpj, responsavel_veterinario, crmv_responsavel, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, end, bairro, cidade, tel, whats, email, cnpj, resp, crmv, obs))
    
    conn.commit()
    conn.close()
    print("✅ Clínicas exemplo cadastradas com sucesso!")

def popular_descontos_exemplo():
    """Cadastra descontos para as clínicas exemplo"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Desconto de 15% para Clínica Centro em todos os serviços
    cursor.execute("""
        INSERT OR IGNORE INTO parcerias_descontos (clinica_id, servico_id, tipo_desconto, valor_desconto, observacoes)
        SELECT id, NULL, 'percentual', 15.0, 'Desconto geral de 15% em todos os serviços'
        FROM clinicas_parceiras WHERE nome = 'Clínica Veterinária Centro'
    """)
    
    # Desconto de 10% para Vet Care
    cursor.execute("""
        INSERT OR IGNORE INTO parcerias_descontos (clinica_id, servico_id, tipo_desconto, valor_desconto, observacoes)
        SELECT id, NULL, 'percentual', 10.0, 'Desconto de 10% em todos os serviços'
        FROM clinicas_parceiras WHERE nome = 'Vet Care Pet Shop e Clínica'
    """)
    
    # Desconto de 20% para Hospital 24h em pacotes
    cursor.execute("""
        INSERT OR IGNORE INTO parcerias_descontos (clinica_id, servico_id, tipo_desconto, valor_desconto, observacoes)
        SELECT c.id, s.id, 'percentual', 20.0, 'Desconto especial de 20% em pacotes'
        FROM clinicas_parceiras c, servicos s 
        WHERE c.nome = 'Hospital Veterinário 24h' AND s.nome LIKE 'Pacote%'
    """)
    
    conn.commit()
    conn.close()
    print("✅ Descontos exemplo cadastrados com sucesso!")

def main():
    """Executa todas as funções de população"""
    print("\n🏥 FORT CORDIS - Inicialização do Banco de Dados\n")
    print("=" * 60)
    
    # Verifica se o banco existe
    if not DB_PATH.exists():
        print("❌ Erro: Banco de dados não encontrado!")
        print(f"   Esperado em: {DB_PATH}")
        print("   Execute primeiro o sistema principal para criar o banco.")
        return
    
    print(f"📁 Banco de dados encontrado: {DB_PATH}\n")
    
    try:
        print("1️⃣ Populando serviços...")
        popular_servicos()
        
        print("\n2️⃣ Populando medicamentos...")
        popular_medicamentos()
        
        print("\n3️⃣ Populando templates de prescrição...")
        popular_templates_prescricao()
        
        # OPCIONAL: Descomentar para adicionar dados exemplo
        resposta = input("\n❓ Deseja adicionar clínicas e descontos exemplo? (s/n): ")
        if resposta.lower() == 's':
            print("\n4️⃣ Populando clínicas exemplo...")
            popular_clinicas_exemplo()
            
            print("\n5️⃣ Populando descontos exemplo...")
            popular_descontos_exemplo()
        
        print("\n" + "=" * 60)
        print("✅ Inicialização concluída com sucesso!")
        print("\n📊 Resumo:")
        
        conn = sqlite3.connect(str(DB_PATH))
        
        servicos_count = conn.execute("SELECT COUNT(*) FROM servicos").fetchone()[0]
        print(f"   • Serviços cadastrados: {servicos_count}")
        
        meds_count = conn.execute("SELECT COUNT(*) FROM medicamentos").fetchone()[0]
        print(f"   • Medicamentos cadastrados: {meds_count}")
        
        templates_count = conn.execute("SELECT COUNT(*) FROM prescricoes_templates").fetchone()[0]
        print(f"   • Templates de prescrição: {templates_count}")
        
        clinicas_count = conn.execute("SELECT COUNT(*) FROM clinicas_parceiras").fetchone()[0]
        print(f"   • Clínicas parceiras: {clinicas_count}")
        
        descontos_count = conn.execute("SELECT COUNT(*) FROM parcerias_descontos").fetchone()[0]
        print(f"   • Descontos configurados: {descontos_count}")
        
        conn.close()
        
        print("\n🚀 O sistema está pronto para uso!")
        print("   Execute o arquivo principal do Streamlit para começar.")
        
    except Exception as e:
        print(f"\n❌ Erro durante a inicialização: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
