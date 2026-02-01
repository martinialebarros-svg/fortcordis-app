# 🏥 FORT CORDIS - GUIA DE IMPLEMENTAÇÃO
## Sistema Integrado de Gestão Clínica e Financeira

---

## 📋 VISÃO GERAL

Este documento descreve como integrar os novos módulos de gestão clínica e financeira ao seu sistema existente de laudos Fort Cordis, mantendo todas as funcionalidades atuais intactas.

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
FortCordis/
├── fortcordis_app.py                      # Arquivo principal (seu código atual + integrações)
├── fortcordis_modules/
│   ├── __init__.py
│   ├── database.py                        # Banco de dados e funções core
│   ├── documentos.py                      # Geração de PDFs (receitas, atestados, GTA)
│   ├── agendamentos.py                    # Interface de agendamentos
│   ├── financeiro.py                      # Interface financeira
│   └── prescricoes.py                     # Interface de prescrições
├── fortcordis.db                          # Banco SQLite
├── Laudos/                                # Pasta de laudos (já existe)
├── Prescricoes/                           # Nova pasta para prescrições
├── Documentos/                            # Nova pasta para atestados/GTA
├── logo.png                               # Logo (já existe)
├── temp_watermark_faded.png              # Marca d'água (já existe)
└── tabela_referencia.csv                 # Tabelas de ref (já existem)
```

---

## 🛠️ PASSO 1: PREPARAR O AMBIENTE

### 1.1 Instalar Dependências Adicionais

```bash
pip install pandas --break-system-packages
pip install fpdf2 --break-system-packages
```

### 1.2 Criar Pastas Necessárias

```python
from pathlib import Path

# Adicione essas linhas no início do seu código principal
PASTA_PRESCRICOES = Path.home() / "FortCordis" / "Prescricoes"
PASTA_DOCUMENTOS = Path.home() / "FortCordis" / "Documentos"
PASTA_PRESCRICOES.mkdir(parents=True, exist_ok=True)
PASTA_DOCUMENTOS.mkdir(parents=True, exist_ok=True)
```

---

## 🔧 PASSO 2: INTEGRAÇÃO NO CÓDIGO PRINCIPAL

### 2.1 Imports Adicionais (adicione no topo do arquivo)

```python
# Seus imports existentes +
import sys
sys.path.append(str(Path(__file__).parent / "fortcordis_modules"))

from database import (
    inicializar_banco, 
    gerar_numero_os, 
    calcular_valor_final,
    registrar_cobranca_automatica,
    DB_PATH
)
from documentos import (
    gerar_receituario_pdf,
    gerar_atestado_saude_pdf,
    gerar_gta_pdf,
    calcular_posologia,
    formatar_posologia
)
```

### 2.2 Menu Principal Expandido

Substitua seu menu principal atual por:

```python
st.sidebar.title("🏥 Fort Cordis")
st.sidebar.markdown("### Sistema Integrado")

# NOVO MENU PRINCIPAL
menu_principal = st.sidebar.radio(
    "Navegação",
    [
        "🏠 Dashboard",
        "📅 Agendamentos", 
        "🩺 Laudos e Exames",  # <- Sua tela atual de laudos
        "💊 Prescrições",
        "💰 Financeiro",
        "🏢 Cadastros",
        "⚙️ Configurações"
    ]
)
```

### 2.3 Integração da Geração de PDF com Financeiro

**LOCALIZAÇÃO**: Encontre a função `criar_pdf()` no seu código (aproximadamente linha 4700-5040)

**MODIFICAÇÃO**: Após gerar o PDF, adicione registro financeiro automático:

```python
if st.button("🧾 Gerar PDF"):
    pdf_bytes = criar_pdf()
    st.session_state["pdf_bytes"] = pdf_bytes

    # ... seu código de arquivamento existente ...

    # ===== NOVO: REGISTRO FINANCEIRO AUTOMÁTICO =====
    try:
        # Identifica a clínica do laudo
        clinica_nome = st.session_state.get("clinica", "")
        
        if clinica_nome:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Busca ID da clínica
            cursor.execute("SELECT id FROM clinicas_parceiras WHERE nome = ?", (clinica_nome,))
            resultado = cursor.fetchone()
            
            if resultado:
                clinica_id = resultado[0]
                
                # Identifica serviços realizados (baseado no tipo de laudo)
                # Assumindo que você sempre faz ecocardiograma
                cursor.execute("SELECT id FROM servicos WHERE nome = 'Ecocardiograma'")
                servico = cursor.fetchone()
                
                if servico:
                    servico_id = servico[0]
                    
                    # Calcula valor
                    vb, vd, vf = calcular_valor_final(servico_id, clinica_id)
                    
                    # Gera OS
                    numero_os = gerar_numero_os()
                    data_comp = datetime.now().strftime("%Y-%m-%d")
                    
                    cursor.execute("""
                        INSERT INTO financeiro (
                            clinica_id, numero_os, descricao,
                            valor_bruto, valor_desconto, valor_final,
                            status_pagamento, data_competencia
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
                    """, (clinica_id, numero_os, 
                          f"Ecocardiograma - {nome_animal}",
                          vb, vd, vf, data_comp))
                    
                    conn.commit()
                    st.success(f"✅ PDF gerado! OS {numero_os} criada automaticamente.")
            
            conn.close()
    except Exception as e:
        st.warning(f"PDF gerado, mas erro ao criar OS: {e}")
```

---

## 📊 PASSO 3: ESTRUTURA DO BANCO DE DADOS

O banco SQLite é criado automaticamente em `~/FortCordis/fortcordis.db` com as seguintes tabelas:

### Tabelas Principais

1. **clinicas_parceiras**: Cadastro de clínicas
2. **servicos**: Catálogo de serviços (Ecocardiograma, ECG, etc)
3. **parcerias_descontos**: Descontos negociados por clínica
4. **agendamentos**: Controle de agenda
5. **agendamento_servicos**: Relação N:N entre agendamentos e serviços
6. **financeiro**: Cobranças e recebimentos
7. **medicamentos**: Banco de medicamentos
8. **prescricoes**: Histórico de prescrições
9. **prescricoes_templates**: Templates de receitas prontas
10. **acompanhamentos**: Controle de retornos

---

## 💡 PASSO 4: FUNCIONALIDADES IMPLEMENTADAS

### 4.1 Dashboard (🏠)
- Métricas: Agendamentos hoje, Pendentes confirmação, Contas a receber, Retornos atrasados
- Lista de próximos agendamentos
- Últimas cobranças

### 4.2 Agendamentos (📅)

**Novo Agendamento**
- Seleciona clínica parceira
- Informa dados do paciente e tutor
- Seleciona serviços solicitados
- Registra secretária responsável

**Lista de Agendamentos**
- Filtros por data e status
- Ações rápidas: Confirmar, Concluir

**Confirmações**
- Lista agendamentos próximas 24h pendentes de confirmação
- Links WhatsApp automáticos para envio de lembretes

### 4.3 Laudos e Exames (🩺)
**Mantém 100% do seu código atual de laudos**

### 4.4 Prescrições (💊)

**Nova Prescrição**
- Cadastro de paciente
- Busca inteligente de medicamentos
- Cálculo automático de posologia (mg/kg → ml)
- Templates de prescrição prontas
- Geração de PDF de receituário

**Banco de Medicamentos**
- Cadastro com: nome, concentração, dose padrão (mg/kg)
- Cálculo automático: Ex: Animal 10kg + Furosemida 2mg/kg = 20mg total

**Templates de Prescrição**
- Salva prescrições frequentes
- Reutilização rápida

### 4.5 Financeiro (💰)

**Ordem de Serviço Automática**
- Gerada automaticamente ao clicar "Gerar PDF" do laudo
- Aplica descontos da clínica parceira
- Status: Pendente → Pago

**Motor de Descontos**
```python
# Exemplo de cálculo:
# Ecocardiograma = R$ 300,00 (valor tabela)
# Clínica X tem 20% de desconto
# Valor final = R$ 240,00

calcular_valor_final(servico_id=1, clinica_id=5)
# Retorna: (valor_base=300.00, desconto=60.00, valor_final=240.00)
```

**Dashboard Financeiro**
- Contas a receber por clínica
- Filtros por período
- Status de pagamento
- Relatórios mensais

### 4.6 Cadastros (🏢)

**Clínicas Parceiras**
- Nome, endereço, CNPJ
- Responsável veterinário + CRMV
- Configuração de descontos

**Serviços**
- Nome, descrição, valor base
- Duração estimada

**Descontos Negociados**
- Por clínica + serviço específico
- Tipo: Percentual ou Valor Fixo
- Vigência com data início/fim

---

## 🔄 PASSO 5: FLUXO DE TRABALHO INTEGRADO

### Cenário Completo: Do Agendamento ao Pagamento

```
1. AGENDAMENTO
   └─> Clínica X liga → Secretária cadastra no sistema
       ├─> Paciente: Rex
       ├─> Serviços: Ecocardiograma + ECG
       └─> Data: Amanhã 10h

2. CONFIRMAÇÃO (24h ANTES)
   └─> Sistema lista agendamento
       └─> Secretária clica no link WhatsApp automático
           └─> Envia: "Olá [Tutor], lembrete do agendamento..."

3. ATENDIMENTO
   └─> Dr. comparece na Clínica X
       ├─> Realiza exame
       ├─> Importa XML do Vivid
       └─> Edita laudo no sistema

4. GERAÇÃO DO LAUDO
   └─> Clica "Gerar PDF"
       ├─> PDF salvo em ~/FortCordis/Laudos/
       └─> OS automática criada:
           ├─> Eco: R$ 300 - 20% = R$ 240
           ├─> ECG: R$ 150 - 20% = R$ 120
           └─> Total OS-2026-00123: R$ 360 (Status: Pendente)

5. PRESCRIÇÃO (se necessário)
   └─> Aba "Prescrições"
       ├─> Busca "Furosemida 10mg/ml"
       ├─> Peso Rex: 25kg
       ├─> Dose padrão: 2mg/kg
       ├─> Sistema calcula: 5ml
       └─> Gera PDF da receita

6. COBRANÇA
   └─> Secretária acessa "Financeiro"
       ├─> Filtra "Clínica X"
       ├─> Vê OS-2026-00123: R$ 360 (Pendente)
       ├─> Liga para clínica
       └─> Registra pagamento (PIX/Boleto/etc)

7. ACOMPANHAMENTO
   └─> Sistema registra: Rex fez eco em 25/01/2026
       └─> Próxima avaliação: 6 meses (25/07/2026)
           └─> 30 dias antes, aparece em "Retornos Próximos"
```

---

## 🎯 PASSO 6: DADOS INICIAIS (SEED)

### Cadastrar Serviços Padrão

Execute uma vez no seu sistema:

```python
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / "FortCordis" / "fortcordis.db"
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

servicos_padrao = [
    ("Ecocardiograma", "Exame ecocardiográfico completo", 300.00, 60),
    ("Eletrocardiograma", "ECG de repouso", 150.00, 30),
    ("Pressão Arterial", "Aferição de PA sistêmica", 80.00, 15),
    ("Consulta Cardiológica", "Avaliação clínica cardiológica", 250.00, 45),
    ("Holter 24h", "Monitoramento cardíaco contínuo", 500.00, 30),
    ("MAPA 24h", "Monitoramento ambulatorial de PA", 450.00, 30)
]

for nome, desc, valor, duracao in servicos_padrao:
    cursor.execute("""
        INSERT OR IGNORE INTO servicos (nome, descricao, valor_base, duracao_minutos)
        VALUES (?, ?, ?, ?)
    """, (nome, desc, valor, duracao))

conn.commit()
conn.close()
print("✅ Serviços cadastrados!")
```

### Cadastrar Medicamentos Comuns

```python
medicamentos_padrao = [
    ("Furosemida 10mg/ml", "Furosemida", "10mg/ml", "mg/ml", "Solução injetável", 2.0, 1.0, 4.0, "BID (12/12h)", "VO/IM/IV"),
    ("Pimobendan 1.25mg", "Pimobendan", "1.25mg", "mg", "Comprimido", 0.25, 0.2, 0.3, "BID (12/12h)", "VO"),
    ("Enalapril 10mg", "Enalapril", "10mg", "mg", "Comprimido", 0.5, 0.25, 1.0, "SID/BID", "VO"),
    ("Espironolactona 25mg", "Espironolactona", "25mg", "mg", "Comprimido", 2.0, 1.0, 2.0, "SID/BID", "VO"),
    ("Sildenafil 20mg", "Sildenafil", "20mg", "mg", "Comprimido", 1.0, 0.5, 3.0, "TID (8/8h)", "VO")
]

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

for nome, princ, conc, unid, forma, dose_pad, dose_min, dose_max, freq, via in medicamentos_padrao:
    cursor.execute("""
        INSERT OR IGNORE INTO medicamentos (
            nome, principio_ativo, concentracao, unidade_concentracao,
            forma_farmaceutica, dose_padrao_mg_kg, dose_min_mg_kg, dose_max_mg_kg,
            frequencia_padrao, via_administracao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nome, princ, conc, unid, forma, dose_pad, dose_min, dose_max, freq, via))

conn.commit()
conn.close()
print("✅ Medicamentos cadastrados!")
```

---

## 📱 PASSO 7: ESTRUTURA DAS TELAS

### DASHBOARD (🏠)

```python
if menu_principal == "🏠 Dashboard":
    st.title("📊 Dashboard - Fort Cordis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Métricas principais
    # [código fornecido nos módulos]
```

### AGENDAMENTOS (📅)

```python
elif menu_principal == "📅 Agendamentos":
    # Três abas:
    # 1. Novo Agendamento
    # 2. Lista de Agendamentos  
    # 3. Confirmações (24h)
    
    # [código fornecido nos módulos]
```

### LAUDOS E EXAMES (🩺)

```python
elif menu_principal == "🩺 Laudos e Exames":
    # ==================================================
    # AQUI VAI TODO O SEU CÓDIGO ATUAL DE LAUDOS
    # NÃO MODIFICAR NADA - APENAS INDENTAR UM NÍVEL
    # ==================================================
    
    # Todo o código da linha ~150 até ~5100 do seu arquivo atual
    # vai aqui, mantendo exatamente como está
```

### PRESCRIÇÕES (💊)

```python
elif menu_principal == "💊 Prescrições":
    st.title("💊 Sistema de Prescrições")
    
    tab_p1, tab_p2, tab_p3 = st.tabs([
        "✍️ Nova Prescrição",
        "💊 Banco de Medicamentos", 
        "📋 Templates"
    ])
    
    with tab_p1:
        # Interface de prescrição
        # [código detalhado a seguir]
```

### FINANCEIRO (💰)

```python
elif menu_principal == "💰 Financeiro":
    st.title("💰 Gestão Financeira")
    
    tab_f1, tab_f2, tab_f3 = st.tabs([
        "📊 Dashboard",
        "💳 Contas a Receber",
        "📈 Relatórios"
    ])
    
    # [código detalhado a seguir]
```

---

## 🔐 PASSO 8: CÓDIGO DETALHADO DAS NOVAS TELAS

### 8.1 Tela de Prescrições Completa

```python
elif menu_principal == "💊 Prescrições":
    st.title("💊 Sistema de Prescrições")
    
    tab_p1, tab_p2, tab_p3 = st.tabs([
        "✍️ Nova Prescrição",
        "💊 Banco de Medicamentos",
        "📋 Templates"
    ])
    
    with tab_p1:
        st.subheader("Nova Prescrição")
        
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            presc_paciente = st.text_input("Nome do Paciente *", key="presc_pac")
            presc_tutor = st.text_input("Nome do Tutor *", key="presc_tut")
            presc_especie = st.selectbox("Espécie", ["Canina", "Felina"], key="presc_esp")
        
        with col_p2:
            presc_peso = st.number_input("Peso (kg)", min_value=0.1, value=10.0, step=0.1, key="presc_peso")
            presc_medico = st.text_input("Médico Veterinário", value="Dr. [Nome]", key="presc_med")
            presc_crmv = st.text_input("CRMV", value="CRMV-CE XXXXX", key="presc_crmv")
        
        st.markdown("---")
        st.markdown("### 💊 Medicamentos")
        
        # Busca de medicamentos
        conn = sqlite3.connect(str(DB_PATH))
        medicamentos_df = pd.read_sql_query(
            "SELECT id, nome, concentracao, dose_padrao_mg_kg FROM medicamentos WHERE ativo = 1",
            conn
        )
        conn.close()
        
        if not medicamentos_df.empty:
            # Sistema de adição de medicamentos
            if 'lista_medicamentos_presc' not in st.session_state:
                st.session_state.lista_medicamentos_presc = []
            
            col_add1, col_add2, col_add3 = st.columns([3, 1, 1])
            
            with col_add1:
                med_selecionado = st.selectbox(
                    "Selecione o medicamento",
                    options=medicamentos_df['id'].tolist(),
                    format_func=lambda x: f"{medicamentos_df[medicamentos_df['id']==x]['nome'].iloc[0]} ({medicamentos_df[medicamentos_df['id']==x]['concentracao'].iloc[0]})",
                    key="med_sel"
                )
            
            with col_add2:
                if st.button("➕ Adicionar"):
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT nome, concentracao, dose_padrao_mg_kg, frequencia_padrao, via_administracao
                        FROM medicamentos WHERE id = ?
                    """, (med_selecionado,))
                    med_info = cursor.fetchone()
                    conn.close()
                    
                    if med_info:
                        nome, conc, dose, freq, via = med_info
                        
                        # Calcula volume
                        try:
                            conc_num = float(conc.lower().replace('mg/ml', '').replace('mg', '').strip())
                            if 'ml' in conc.lower():
                                volume_ml = calcular_posologia(presc_peso, dose, conc_num)
                                texto_med = f"{nome} ({conc}) - {volume_ml} ml - {freq} - {via}"
                            else:
                                dose_total = presc_peso * dose
                                texto_med = f"{nome} ({conc}) - {dose_total:.1f} mg - {freq} - {via}"
                        except:
                            texto_med = f"{nome} ({conc}) - {freq} - {via}"
                        
                        st.session_state.lista_medicamentos_presc.append(texto_med)
                        st.rerun()
            
            with col_add3:
                if st.button("🗑️ Limpar"):
                    st.session_state.lista_medicamentos_presc = []
                    st.rerun()
            
            # Lista de medicamentos adicionados
            if st.session_state.lista_medicamentos_presc:
                st.markdown("**Medicamentos na Prescrição:**")
                for idx, med in enumerate(st.session_state.lista_medicamentos_presc, 1):
                    col_m1, col_m2 = st.columns([10, 1])
                    with col_m1:
                        st.text(f"{idx}. {med}")
                    with col_m2:
                        if st.button("❌", key=f"rem_{idx}"):
                            st.session_state.lista_medicamentos_presc.pop(idx-1)
                            st.rerun()
        
        # Texto adicional
        st.markdown("### 📝 Orientações Adicionais")
        texto_adicional = st.text_area(
            "Instruções complementares",
            placeholder="Ex: Administrar após as refeições. Retorno em 30 dias...",
            height=100,
            key="presc_obs"
        )
        
        # Botão gerar
        if st.button("📄 Gerar Receituário"):
            if not presc_paciente or not presc_tutor:
                st.error("Preencha os dados do paciente e tutor")
            elif not st.session_state.lista_medicamentos_presc:
                st.error("Adicione pelo menos um medicamento")
            else:
                # Monta texto completo da prescrição
                texto_prescricao = "\n\n".join(st.session_state.lista_medicamentos_presc)
                if texto_adicional:
                    texto_prescricao += f"\n\n{texto_adicional}"
                
                # Gera PDF
                pdf_bytes = gerar_receituario_pdf(
                    paciente_nome=presc_paciente,
                    tutor_nome=presc_tutor,
                    especie=presc_especie,
                    peso_kg=presc_peso,
                    prescricao_texto=texto_prescricao,
                    medico=presc_medico,
                    crmv=presc_crmv,
                    logo_path="logo.png"
                )
                
                # Salva no banco
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                
                nome_arquivo = f"RX_{presc_paciente}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                caminho_completo = PASTA_PRESCRICOES / nome_arquivo
                
                with open(caminho_completo, 'wb') as f:
                    f.write(pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.encode('latin-1'))
                
                cursor.execute("""
                    INSERT INTO prescricoes (
                        paciente_nome, tutor_nome, especie, peso_kg,
                        data_prescricao, texto_prescricao,
                        medico_veterinario, crmv, caminho_pdf
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (presc_paciente, presc_tutor, presc_especie, presc_peso,
                      datetime.now().strftime("%Y-%m-%d"), texto_prescricao,
                      presc_medico, presc_crmv, str(caminho_completo)))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Receituário gerado: {nome_arquivo}")
                
                # Download
                st.download_button(
                    "⬇️ Baixar Receituário",
                    data=pdf_bytes,
                    file_name=nome_arquivo,
                    mime="application/pdf"
                )
                
                # Limpa lista
                st.session_state.lista_medicamentos_presc = []
    
    with tab_p2:
        st.subheader("💊 Banco de Medicamentos")
        
        # Formulário de cadastro
        with st.expander("➕ Cadastrar Novo Medicamento"):
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                novo_med_nome = st.text_input("Nome Comercial *")
                novo_med_princ = st.text_input("Princípio Ativo")
                novo_med_conc = st.text_input("Concentração (ex: 10mg/ml)")
                novo_med_forma = st.selectbox("Forma Farmacêutica", 
                    ["Comprimido", "Solução injetável", "Solução oral", "Suspensão", "Cápsula"])
            
            with col_m2:
                novo_med_dose_pad = st.number_input("Dose Padrão (mg/kg)", min_value=0.0, step=0.1)
                novo_med_dose_min = st.number_input("Dose Mínima (mg/kg)", min_value=0.0, step=0.1)
                novo_med_dose_max = st.number_input("Dose Máxima (mg/kg)", min_value=0.0, step=0.1)
                novo_med_freq = st.text_input("Frequência Padrão (ex: BID, TID)")
            
            novo_med_via = st.text_input("Via de Administração (ex: VO, IM, IV)")
            novo_med_obs = st.text_area("Observações")
            
            if st.button("✅ Cadastrar Medicamento"):
                if novo_med_nome:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO medicamentos (
                            nome, principio_ativo, concentracao, forma_farmaceutica,
                            dose_padrao_mg_kg, dose_min_mg_kg, dose_max_mg_kg,
                            frequencia_padrao, via_administracao, observacoes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (novo_med_nome, novo_med_princ, novo_med_conc, novo_med_forma,
                          novo_med_dose_pad, novo_med_dose_min, novo_med_dose_max,
                          novo_med_freq, novo_med_via, novo_med_obs))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Medicamento '{novo_med_nome}' cadastrado!")
                    st.rerun()
        
        # Lista de medicamentos
        st.markdown("### Lista de Medicamentos")
        conn = sqlite3.connect(str(DB_PATH))
        meds_lista = pd.read_sql_query("""
            SELECT 
                nome as Nome,
                concentracao as Concentração,
                dose_padrao_mg_kg as 'Dose Padrão (mg/kg)',
                frequencia_padrao as Frequência,
                via_administracao as Via
            FROM medicamentos 
            WHERE ativo = 1
            ORDER BY nome
        """, conn)
        conn.close()
        
        if not meds_lista.empty:
            st.dataframe(meds_lista, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum medicamento cadastrado")
    
    with tab_p3:
        st.subheader("📋 Templates de Prescrição")
        
        # Cadastro de template
        with st.expander("➕ Novo Template"):
            nome_template = st.text_input("Nome do Template")
            indicacao_template = st.text_input("Indicação (ex: ICC Grau B1)")
            texto_template = st.text_area("Texto da Prescrição", height=200)
            
            if st.button("✅ Salvar Template"):
                if nome_template and texto_template:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO prescricoes_templates (nome_template, indicacao, texto_prescricao)
                        VALUES (?, ?, ?)
                    """, (nome_template, indicacao_template, texto_template))
                    conn.commit()
                    conn.close()
                    st.success("✅ Template salvo!")
                    st.rerun()
        
        # Lista templates
        conn = sqlite3.connect(str(DB_PATH))
        templates_df = pd.read_sql_query("""
            SELECT id, nome_template as Nome, indicacao as Indicação
            FROM prescricoes_templates WHERE ativo = 1
        """, conn)
        conn.close()
        
        if not templates_df.empty:
            st.dataframe(templates_df, use_container_width=True, hide_index=True)
```

### 8.2 Tela Financeira Completa

```python
elif menu_principal == "💰 Financeiro":
    st.title("💰 Gestão Financeira")
    
    tab_f1, tab_f2, tab_f3, tab_f4 = st.tabs([
        "📊 Dashboard",
        "💳 Contas a Receber",
        "📈 Relatórios",
        "📄 Ordem de Serviço Manual"
    ])
    
    with tab_f1:
        st.subheader("Resumo Financeiro")
        
        conn = sqlite3.connect(str(DB_PATH))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pendentes = pd.read_sql_query("""
                SELECT SUM(valor_final) as total 
                FROM financeiro 
                WHERE status_pagamento = 'pendente'
            """, conn)
            valor_pend = pendentes['total'].iloc[0] if pendentes['total'].iloc[0] else 0
            st.metric("A Receber", f"R$ {valor_pend:,.2f}")
        
        with col2:
            mes_atual = datetime.now().strftime("%Y-%m")
            recebido_mes = pd.read_sql_query(f"""
                SELECT SUM(valor_final) as total 
                FROM financeiro 
                WHERE status_pagamento = 'pago'
                AND data_pagamento LIKE '{mes_atual}%'
            """, conn)
            valor_rec = recebido_mes['total'].iloc[0] if recebido_mes['total'].iloc[0] else 0
            st.metric("Recebido (Mês)", f"R$ {valor_rec:,.2f}")
        
        with col3:
            total_os = pd.read_sql_query("SELECT COUNT(*) as total FROM financeiro", conn)
            st.metric("Total de OS", total_os['total'].iloc[0])
        
        conn.close()
        
        st.markdown("---")
        
        # Gráfico por clínica
        st.subheader("📊 Faturamento por Clínica (Últimos 3 Meses)")
        
        conn = sqlite3.connect(str(DB_PATH))
        tres_meses_atras = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        fat_clinicas = pd.read_sql_query(f"""
            SELECT 
                c.nome as Clínica,
                COUNT(f.id) as 'Qtd OS',
                SUM(f.valor_final) as 'Total'
            FROM financeiro f
            LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
            WHERE f.data_competencia >= '{tres_meses_atras}'
            GROUP BY c.nome
            ORDER BY SUM(f.valor_final) DESC
        """, conn)
        conn.close()
        
        if not fat_clinicas.empty:
            fat_clinicas['Total'] = fat_clinicas['Total'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(fat_clinicas, use_container_width=True, hide_index=True)
    
    with tab_f2:
        st.subheader("💳 Contas a Receber")
        
        col_fr1, col_fr2 = st.columns(2)
        with col_fr1:
            filtro_clinica_fin = st.selectbox("Filtrar por Clínica", ["Todas"] + list(
                pd.read_sql_query("SELECT nome FROM clinicas_parceiras WHERE ativo = 1", 
                                 sqlite3.connect(str(DB_PATH)))['nome']
            ))
        
        with col_fr2:
            filtro_status_fin = st.multiselect(
                "Status", 
                ['pendente', 'pago', 'cancelado'],
                default=['pendente']
            )
        
        conn = sqlite3.connect(str(DB_PATH))
        
        query = """
            SELECT 
                f.id as ID,
                f.numero_os as 'OS',
                c.nome as 'Clínica',
                f.descricao as 'Descrição',
                f.valor_bruto as 'Valor Bruto',
                f.valor_desconto as 'Desconto',
                f.valor_final as 'Valor Final',
                f.status_pagamento as 'Status',
                f.data_competencia as 'Data'
            FROM financeiro f
            LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
            WHERE 1=1
        """
        
        if filtro_clinica_fin != "Todas":
            query += f" AND c.nome = '{filtro_clinica_fin}'"
        
        if filtro_status_fin:
            status_str = "','".join(filtro_status_fin)
            query += f" AND f.status_pagamento IN ('{status_str}')"
        
        query += " ORDER BY f.data_competencia DESC"
        
        contas_df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not contas_df.empty:
            # Formata valores
            contas_df['Valor Bruto'] = contas_df['Valor Bruto'].apply(lambda x: f"R$ {x:,.2f}")
            contas_df['Desconto'] = contas_df['Desconto'].apply(lambda x: f"R$ {x:,.2f}")
            contas_df['Valor Final'] = contas_df['Valor Final'].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(contas_df, use_container_width=True, hide_index=True)
            
            # Registrar pagamento
            st.markdown("### 💰 Registrar Pagamento")
            col_pg1, col_pg2, col_pg3 = st.columns(3)
            
            with col_pg1:
                os_pagar = st.number_input("ID da OS", min_value=1, step=1)
            with col_pg2:
                forma_pag = st.selectbox("Forma de Pagamento", 
                    ["PIX", "Transferência", "Boleto", "Dinheiro", "Cartão"])
            with col_pg3:
                data_pag = st.date_input("Data do Pagamento", value=datetime.now())
            
            if st.button("✅ Confirmar Pagamento"):
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE financeiro
                    SET status_pagamento = 'pago',
                        forma_pagamento = ?,
                        data_pagamento = ?
                    WHERE id = ?
                """, (forma_pag, data_pag.strftime("%Y-%m-%d"), os_pagar))
                conn.commit()
                conn.close()
                st.success(f"✅ Pagamento da OS #{os_pagar} registrado!")
                st.rerun()
        else:
            st.info("Nenhuma conta encontrada")
    
    with tab_f3:
        st.subheader("📈 Relatórios")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            rel_data_inicio = st.date_input("Período - Início", 
                value=datetime.now().replace(day=1))
        with col_r2:
            rel_data_fim = st.date_input("Período - Fim", value=datetime.now())
        
        if st.button("🔍 Gerar Relatório"):
            conn = sqlite3.connect(str(DB_PATH))
            
            relatorio = pd.read_sql_query(f"""
                SELECT 
                    c.nome as Clínica,
                    COUNT(f.id) as 'Qtd OS',
                    SUM(CASE WHEN f.status_pagamento = 'pendente' THEN f.valor_final ELSE 0 END) as 'Pendente',
                    SUM(CASE WHEN f.status_pagamento = 'pago' THEN f.valor_final ELSE 0 END) as 'Pago',
                    SUM(f.valor_final) as 'Total'
                FROM financeiro f
                LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                WHERE date(f.data_competencia) BETWEEN '{rel_data_inicio}' AND '{rel_data_fim}'
                GROUP BY c.nome
                ORDER BY SUM(f.valor_final) DESC
            """, conn)
            conn.close()
            
            if not relatorio.empty:
                relatorio['Pendente'] = relatorio['Pendente'].apply(lambda x: f"R$ {x:,.2f}")
                relatorio['Pago'] = relatorio['Pago'].apply(lambda x: f"R$ {x:,.2f}")
                relatorio['Total'] = relatorio['Total'].apply(lambda x: f"R$ {x:,.2f}")
                
                st.dataframe(relatorio, use_container_width=True, hide_index=True)
                
                # Totalizador
                conn = sqlite3.connect(str(DB_PATH))
                totais = pd.read_sql_query(f"""
                    SELECT 
                        SUM(CASE WHEN status_pagamento = 'pendente' THEN valor_final ELSE 0 END) as pend,
                        SUM(CASE WHEN status_pagamento = 'pago' THEN valor_final ELSE 0 END) as pago,
                        SUM(valor_final) as total
                    FROM financeiro
                    WHERE date(data_competencia) BETWEEN '{rel_data_inicio}' AND '{rel_data_fim}'
                """, conn)
                conn.close()
                
                st.markdown("---")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    st.metric("Total Pendente", f"R$ {totais['pend'].iloc[0]:,.2f}")
                with col_t2:
                    st.metric("Total Pago", f"R$ {totais['pago'].iloc[0]:,.2f}")
                with col_t3:
                    st.metric("TOTAL GERAL", f"R$ {totais['total'].iloc[0]:,.2f}")
            else:
                st.info("Nenhum dado no período selecionado")
    
    with tab_f4:
        st.subheader("📄 Criar Ordem de Serviço Manual")
        st.info("💡 Use quando precisar criar uma OS sem vínculo com agendamento")
        
        # [Similar ao cadastro de agendamento, mas direto para financeiro]
```

---

## 🏢 PASSO 9: TELA DE CADASTROS

```python
elif menu_principal == "🏢 Cadastros":
    st.title("🏢 Cadastros")
    
    tab_c1, tab_c2, tab_c3 = st.tabs([
        "🏥 Clínicas Parceiras",
        "🛠️ Serviços",
        "🎁 Descontos Negociados"
    ])
    
    with tab_c1:
        st.subheader("Clínicas Parceiras")
        
        with st.expander("➕ Nova Clínica"):
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                nova_cli_nome = st.text_input("Nome da Clínica *")
                nova_cli_end = st.text_input("Endereço")
                nova_cli_bairro = st.text_input("Bairro")
                nova_cli_cidade = st.text_input("Cidade", value="Fortaleza")
                nova_cli_tel = st.text_input("Telefone")
            
            with col_c2:
                nova_cli_whats = st.text_input("WhatsApp")
                nova_cli_email = st.text_input("Email")
                nova_cli_cnpj = st.text_input("CNPJ")
                nova_cli_resp = st.text_input("Responsável Veterinário")
                nova_cli_crmv = st.text_input("CRMV do Responsável")
            
            nova_cli_obs = st.text_area("Observações")
            
            if st.button("✅ Cadastrar Clínica"):
                if nova_cli_nome:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO clinicas_parceiras (
                            nome, endereco, bairro, cidade, telefone, whatsapp,
                            email, cnpj, responsavel_veterinario, crmv_responsavel, observacoes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (nova_cli_nome, nova_cli_end, nova_cli_bairro, nova_cli_cidade,
                          nova_cli_tel, nova_cli_whats, nova_cli_email, nova_cli_cnpj,
                          nova_cli_resp, nova_cli_crmv, nova_cli_obs))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Clínica '{nova_cli_nome}' cadastrada!")
                    st.rerun()
        
        # Lista clínicas
        conn = sqlite3.connect(str(DB_PATH))
        clinicas_lista = pd.read_sql_query("""
            SELECT 
                id as ID,
                nome as Nome,
                cidade as Cidade,
                telefone as Telefone,
                whatsapp as WhatsApp,
                responsavel_veterinario as Responsável
            FROM clinicas_parceiras
            WHERE ativo = 1
            ORDER BY nome
        """, conn)
        conn.close()
        
        if not clinicas_lista.empty:
            st.dataframe(clinicas_lista, use_container_width=True, hide_index=True)
    
    with tab_c2:
        st.subheader("Serviços Oferecidos")
        
        # [Similar ao cadastro de clínicas]
        
    with tab_c3:
        st.subheader("Descontos Negociados")
        
        st.info("💡 Configure descontos especiais para clínicas parceiras")
        
        with st.expander("➕ Novo Desconto"):
            conn = sqlite3.connect(str(DB_PATH))
            clinicas_df = pd.read_sql_query("SELECT id, nome FROM clinicas_parceiras WHERE ativo = 1", conn)
            servicos_df = pd.read_sql_query("SELECT id, nome FROM servicos WHERE ativo = 1", conn)
            conn.close()
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                desc_clinica = st.selectbox(
                    "Clínica *",
                    options=clinicas_df['id'].tolist(),
                    format_func=lambda x: clinicas_df[clinicas_df['id']==x]['nome'].iloc[0]
                )
                
                desc_servico = st.selectbox(
                    "Serviço (deixe vazio para desconto geral)",
                    options=[None] + servicos_df['id'].tolist(),
                    format_func=lambda x: "Todos os serviços" if x is None else servicos_df[servicos_df['id']==x]['nome'].iloc[0]
                )
            
            with col_d2:
                desc_tipo = st.radio("Tipo de Desconto", ['percentual', 'valor_fixo'])
                desc_valor = st.number_input(
                    "Valor do Desconto" + (" (%)" if desc_tipo == 'percentual' else " (R$)"),
                    min_value=0.0,
                    step=0.1 if desc_tipo == 'percentual' else 1.0
                )
            
            desc_obs = st.text_area("Observações do Acordo")
            
            if st.button("✅ Cadastrar Desconto"):
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO parcerias_descontos (
                        clinica_id, servico_id, tipo_desconto, valor_desconto, observacoes
                    ) VALUES (?, ?, ?, ?, ?)
                """, (desc_clinica, desc_servico, desc_tipo, desc_valor, desc_obs))
                conn.commit()
                conn.close()
                st.success("✅ Desconto cadastrado!")
                st.rerun()
        
        # Lista descontos
        conn = sqlite3.connect(str(DB_PATH))
        descontos_lista = pd.read_sql_query("""
            SELECT 
                c.nome as Clínica,
                COALESCE(s.nome, 'TODOS') as Serviço,
                pd.tipo_desconto as Tipo,
                pd.valor_desconto as Valor,
                pd.observacoes as Observações
            FROM parcerias_descontos pd
            LEFT JOIN clinicas_parceiras c ON pd.clinica_id = c.id
            LEFT JOIN servicos s ON pd.servico_id = s.id
            WHERE pd.ativo = 1
            ORDER BY c.nome, s.nome
        """, conn)
        conn.close()
        
        if not descontos_lista.empty:
            st.dataframe(descontos_lista, use_container_width=True, hide_index=True)
```

---

## ⚙️ PASSO 10: TELA DE CONFIGURAÇÕES

```python
elif menu_principal == "⚙️ Configurações":
    st.title("⚙️ Configurações do Sistema")
    
    tab_conf1, tab_conf2, tab_conf3 = st.tabs([
        "👨‍⚕️ Dados Profissionais",
        "📊 Valores de Referência",  # <- Sua tela atual
        "📝 Frases Personalizadas"   # <- Sua tela atual
    ])
    
    with tab_conf1:
        st.subheader("Dados Profissionais")
        
        # Armazena em session_state ou arquivo config
        medico_nome = st.text_input(
            "Nome do Médico Veterinário",
            value=st.session_state.get("config_medico", "Dr. [Nome]")
        )
        
        medico_crmv = st.text_input(
            "CRMV",
            value=st.session_state.get("config_crmv", "CRMV-CE XXXXX")
        )
        
        if st.button("💾 Salvar Configurações"):
            st.session_state["config_medico"] = medico_nome
            st.session_state["config_crmv"] = medico_crmv
            st.success("✅ Configurações salvas!")
    
    with tab_conf2:
        # ==== SEU CÓDIGO ATUAL DE VALORES DE REFERÊNCIA ====
        # Mova todo o código da aba de "Valores de Referência" para cá
        pass
    
    with tab_conf3:
        # ==== SEU CÓDIGO ATUAL DE FRASES PERSONALIZADAS ====
        # Mova todo o código da aba de "Frases" para cá
        pass
```

---

## 🚀 PASSO 11: INICIALIZAÇÃO DO SISTEMA

No início do arquivo principal, adicione:

```python
from fortcordis_modules.database import inicializar_banco, DB_PATH
from fortcordis_modules.documentos import *

# Inicializa banco
inicializar_banco()

# Cria pastas
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
PASTA_PRESCRICOES = Path.home() / "FortCordis" / "Prescricoes"
PASTA_DOCUMENTOS = Path.home() / "FortCordis" / "Documentos"

for pasta in [PASTA_LAUDOS, PASTA_PRESCRICOES, PASTA_DOCUMENTOS]:
    pasta.mkdir(parents=True, exist_ok=True)
```

---

## 📌 PASSO 12: PONTOS DE INTEGRAÇÃO CRÍTICOS

### 12.1 Ao Gerar PDF do Laudo

**LOCALIZAÇÃO**: Função que gera PDF (linha ~5046)

**ADICIONAR**: Logo após salvar o PDF

```python
# Seu código existente de salvar PDF...

# NOVO: Cria OS automaticamente
try:
    clinica_nome = st.session_state.get("clinica", "")
    if clinica_nome:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clinicas_parceiras WHERE nome = ?", (clinica_nome,))
        res = cursor.fetchone()
        
        if res:
            clinica_id = res[0]
            cursor.execute("SELECT id FROM servicos WHERE nome = 'Ecocardiograma'")
            serv = cursor.fetchone()
            
            if serv:
                vb, vd, vf = calcular_valor_final(serv[0], clinica_id)
                numero_os = gerar_numero_os()
                
                cursor.execute("""
                    INSERT INTO financeiro (
                        clinica_id, numero_os, descricao, valor_bruto, 
                        valor_desconto, valor_final, data_competencia, status_pagamento
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
                """, (clinica_id, numero_os, f"Eco - {nome_animal}", 
                      vb, vd, vf, datetime.now().strftime("%Y-%m-%d")))
                
                conn.commit()
                st.info(f"💰 OS {numero_os} criada: R$ {vf:.2f}")
        
        conn.close()
except Exception as e:
    pass  # Não quebra o fluxo se der erro
```

### 12.2 Sincronização de Cadastro

Quando o usuário preenche dados no laudo, esses dados devem estar disponíveis nas outras telas. Mantenha usando `st.session_state` que já funciona.

---

## 🎨 PASSO 13: MELHORIAS VISUAIS

### CSS Personalizado

Adicione no início do arquivo principal:

```python
st.markdown("""
    <style>
    .stApp {
        background-color: #f5f7fa;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)
```

---

## ✅ PASSO 14: CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Criar pasta `fortcordis_modules/`
- [ ] Copiar `database.py` para a pasta
- [ ] Copiar `documentos.py` para a pasta
- [ ] Criar `__init__.py` vazio na pasta
- [ ] Adicionar imports no arquivo principal
- [ ] Modificar menu principal
- [ ] Integrar geração de OS no botão "Gerar PDF"
- [ ] Testar criação de agendamento
- [ ] Testar geração de laudo + OS automática
- [ ] Cadastrar serviços padrão
- [ ] Cadastrar pelo menos uma clínica parceira
- [ ] Configurar desconto para uma clínica
- [ ] Testar prescrição com cálculo automático
- [ ] Validar relatórios financeiros

---

## 🐛 TROUBLESHOOTING

### Erro: "No module named 'fortcordis_modules'"

**Solução**: Verifique que a pasta está no mesmo diretório do arquivo principal e contém `__init__.py`

### Erro: "table already exists"

**Solução**: Normal. O sistema verifica e cria apenas tabelas inexistentes.

### OS não sendo criada automaticamente

**Solução**: 
1. Verifique que a clínica está cadastrada com o mesmo nome usado no laudo
2. Verifique que existe o serviço "Ecocardiograma" cadastrado

### Cálculo de posologia incorreto

**Solução**: Certifique-se que a concentração está no formato correto: "10mg/ml" (não "10 mg/ml" ou "10mg / ml")

---

## 📊 EXEMPLO DE FLUXO COMPLETO

```
SEGUNDA 09:00
├─> Secretária: Cadastra agendamento
    └─> Clínica Vet Center - Rex - Eco + ECG - Terça 14h

TERÇA 10:00  
├─> Sistema: Lista "Pendentes Confirmação"
    └─> Secretária: Clica link WhatsApp → Confirma

TERÇA 14:00
├─> Dr.: Atende na Vet Center
    ├─> Examina Rex
    ├─> Importa XML do Vivid
    ├─> Edita laudo
    ├─> Gera PDF
    └─> Sistema: Cria OS-2026-00001 automática
        ├─> Eco: R$ 300 - 15% = R$ 255
        └─> ECG: R$ 150 - 15% = R$ 127,50
        └─> TOTAL: R$ 382,50 (Pendente)

TERÇA 15:00
├─> Dr.: Prescreve medicação
    └─> Furosemida 10mg/ml
        ├─> Peso Rex: 25kg
        ├─> Dose: 2mg/kg
        └─> Sistema calcula: 5ml BID

QUARTA 10:00
├─> Secretária: Acessa "Financeiro"
    ├─> Filtra "Vet Center"
    ├─> Vê OS-2026-00001: R$ 382,50
    ├─> Liga para clínica
    └─> Registra pagamento PIX

SÁBADO
├─> Sistema: Cria acompanhamento automático
    └─> Rex - Último eco: 25/01/2026
        └─> Próximo eco: 25/07/2026 (6 meses)
```

---

## 🎓 DICAS PROFISSIONAIS

### 1. Backup Automático

Adicione no dashboard:

```python
if st.button("💾 Fazer Backup do Banco"):
    import shutil
    backup_path = Path.home() / "FortCordis" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_PATH, backup_path)
    st.success(f"✅ Backup salvo: {backup_path}")
```

### 2. Exportação de Relatórios

```python
# Em Financeiro > Relatórios
if st.button("📥 Exportar para Excel"):
    relatorio.to_excel("relatorio_financeiro.xlsx", index=False)
    st.success("✅ Exportado!")
```

### 3. Notificações de Retorno

Configure no dashboard:

```python
# Alerta de retornos atrasados
atrasados = pd.read_sql_query("""
    SELECT paciente_nome, tutor_whatsapp, proxima_avaliacao
    FROM acompanhamentos WHERE status = 'atrasado' AND lembrete_enviado = 0
""", conn)

if not atrasados.empty:
    st.warning(f"⚠️ {len(atrasados)} retornos atrasados!")
```

---

## 📞 SUPORTE E MANUTENÇÃO

### Logs do Sistema

Adicione logging para debug:

```python
import logging

logging.basicConfig(
    filename=Path.home() / 'FortCordis' / 'app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Use em pontos críticos:
logging.info(f"OS {numero_os} criada para clínica {clinica_id}")
```

---

## 🏆 FUNCIONALIDADES AVANÇADAS (FUTURAS)

1. **API WhatsApp Business** para envio automático de lembretes
2. **OCR** para digitalizar exames físicos
3. **Dashboard com gráficos** usando Plotly
4. **Exportação NFSe** automática
5. **Integração com agenda Google Calendar**

---

## ✨ CONCLUSÃO

Este sistema transforma seu aplicativo de laudos em uma solução completa de gestão veterinária, mantendo 100% das funcionalidades existentes e adicionando:

✅ Gestão de agendamentos com confirmações automáticas
✅ Módulo financeiro com OS automáticas e descontos inteligentes
✅ Sistema de prescrições com cálculo automático de posologia
✅ Controle de retornos e acompanhamento
✅ Geração de documentos (receitas, atestados, GTA)
✅ Dashboard executivo com métricas em tempo real

**Próximo passo**: Implemente seção por seção, testando cada funcionalidade antes de passar para a próxima.
