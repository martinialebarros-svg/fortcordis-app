# 🏥 FORT CORDIS - Sistema Completo de Gestão Veterinária

Sistema integrado para gestão de laudos cardiológicos, agendamentos, prescrições e financeiro para médicos veterinários cardiologistas.

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Instalação](#instalação)
3. [Estrutura de Arquivos](#estrutura-de-arquivos)
4. [Primeiro Uso](#primeiro-uso)
5. [Funcionalidades](#funcionalidades)
6. [Fluxo de Trabalho](#fluxo-de-trabalho)
7. [Suporte](#suporte)

---

## 🎯 VISÃO GERAL

O Fort Cordis é um sistema completo que integra:

- ✅ **Sistema de Laudos** (seu sistema atual mantido intacto)
- ✅ **Gestão de Agendamentos** com confirmações automáticas
- ✅ **Módulo Financeiro** com OS automáticas e descontos
- ✅ **Sistema de Prescrições** com cálculo automático de posologia
- ✅ **Controle de Retornos** para acompanhamento de pacientes
- ✅ **Geração de Documentos** (receitas, atestados, GTA, termos)

---

## 🛠️ INSTALAÇÃO

### Pré-requisitos

- Python 3.8 ou superior
- Sistema operacional: Windows, Mac ou Linux

### Passo 1: Instalar Dependências

```bash
# Dependências do sistema original
pip install streamlit pandas pillow beautifulsoup4 fpdf2 --break-system-packages

# Se já tinha instalado, pule este passo
```

### Passo 2: Estrutura de Pastas

Organize seus arquivos assim:

```
FortCordis/
├── fortcordis_app.py                    # Seu arquivo principal (modificado)
├── fortcordis_modules/
│   ├── __init__.py                      # Arquivo vazio
│   ├── database.py                      # Módulo de banco de dados
│   └── documentos.py                    # Módulo de geração de PDFs
├── inicializar_dados.py                 # Script de inicialização
├── logo.png                             # Sua logo
├── temp_watermark_faded.png            # Marca d'água
├── tabela_referencia.csv               # Tabelas de referência
└── tabela_referencia_felinos.csv
```

### Passo 3: Criar Arquivo __init__.py

```bash
# No terminal, na pasta do projeto:
mkdir fortcordis_modules
touch fortcordis_modules/__init__.py
```

Ou no Windows:
```cmd
mkdir fortcordis_modules
type nul > fortcordis_modules\__init__.py
```

### Passo 4: Copiar Módulos

1. Copie o arquivo `database.py` para dentro de `fortcordis_modules/`
2. Copie o arquivo `documentos.py` para dentro de `fortcordis_modules/`

---

## 📁 ESTRUTURA DE ARQUIVOS

Após a instalação, esta é a estrutura que será criada automaticamente:

```
~/FortCordis/                           # Pasta principal no seu Home
├── fortcordis.db                       # Banco de dados SQLite
├── Laudos/                             # PDFs e JSONs dos laudos
│   ├── 2026-01-25_Rex_Silva.pdf
│   └── 2026-01-25_Rex_Silva.json
├── Prescricoes/                        # PDFs de receituários
│   └── RX_Rex_20260125_143052.pdf
├── Documentos/                         # Atestados, GTA, termos
│   ├── Atestado_Rex_20260125.pdf
│   └── GTA_Rex_20260125.pdf
└── frases_personalizadas.json         # Seu arquivo atual
```

---

## 🚀 PRIMEIRO USO

### 1. Executar pela Primeira Vez

```bash
streamlit run fortcordis_app.py
```

O sistema irá:
- Criar o banco de dados automaticamente
- Criar todas as tabelas necessárias
- Criar as pastas de arquivos

### 2. Popular Dados Iniciais

Em outro terminal, execute:

```bash
python inicializar_dados.py
```

Este script irá:
- Cadastrar 10 serviços padrão (Ecocardiograma, ECG, etc)
- Cadastrar 20+ medicamentos comuns
- Criar templates de prescrição
- (Opcional) Criar clínicas e descontos exemplo

**IMPORTANTE**: Execute este script apenas UMA VEZ!

### 3. Primeiro Cadastro

No sistema, vá em **"🏢 Cadastros"** e:

1. Cadastre sua primeira clínica parceira
2. Configure um desconto (se aplicável)
3. Ajuste valores dos serviços se necessário

### 4. Configurar Dados Profissionais

Vá em **"⚙️ Configurações"** > **"Dados Profissionais"**:

- Nome completo
- CRMV

Estes dados aparecerão nos PDFs gerados.

---

## 💡 FUNCIONALIDADES

### 🏠 Dashboard

**O que faz:**
- Mostra métricas do dia: agendamentos, pendências, valores
- Lista próximos agendamentos
- Exibe últimas cobranças

**Quando usar:**
- Ao iniciar o dia
- Para visão geral rápida

---

### 📅 Agendamentos

#### ➕ Novo Agendamento

**O que faz:**
- Registra agendamento de consulta/exame
- Vincula à clínica parceira
- Seleciona serviços solicitados

**Como usar:**
1. Secretária recebe ligação da clínica
2. Seleciona clínica no menu
3. Preenche dados do paciente e tutor
4. Marca serviços (Eco, ECG, etc)
5. Clica "Criar Agendamento"

#### 📋 Lista de Agendamentos

**O que faz:**
- Lista todos os agendamentos
- Filtra por data e status
- Permite confirmar ou concluir

**Ações disponíveis:**
- ✅ **Confirmar**: Muda status para "confirmado"
- 🏁 **Concluir**: Muda para "concluído" + gera OS automática

#### 🔔 Confirmações

**O que faz:**
- Lista agendamentos das próximas 24h
- Gera links WhatsApp automáticos

**Como usar:**
1. Acesse a aba um dia antes
2. Clique no link do WhatsApp
3. Envia mensagem de lembrete
4. Após confirmação, marque como confirmado

---

### 🩺 Laudos e Exames

**TODO O SEU SISTEMA ATUAL MANTIDO 100% INALTERADO**

**NOVIDADE:** Ao clicar em "Gerar PDF":
- PDF é criado normalmente
- OS financeira é gerada automaticamente
- Desconto da clínica aplicado

Exemplo:
```
Laudo gerado: Rex - Clínica Centro
→ OS-2026-00001 criada
   Ecocardiograma: R$ 300,00
   Desconto 15%: -R$ 45,00
   TOTAL: R$ 255,00 (Pendente)
```

---

### 💊 Prescrições

#### ✍️ Nova Prescrição

**O que faz:**
- Busca medicamentos no banco
- Calcula posologia automaticamente
- Gera PDF de receituário

**Como usar:**

1. Preencha dados do paciente
2. Informe o peso (kg)
3. Busque medicamento: "Furosemida 10mg/ml"
4. Clique "Adicionar"
   - Sistema calcula automaticamente: 25kg × 2mg/kg ÷ 10mg/ml = 5ml
5. Adicione quantos medicamentos necessário
6. Escreva orientações adicionais
7. Clique "Gerar Receituário"

**Exemplo de saída:**

```
Paciente: Rex | Tutor: João Silva | Peso: 25kg

Rx

Furosemida 10mg/ml - 5ml - BID (12/12h) - VO
Enalapril 10mg - 12,5mg (0,5mg/kg) - BID - VO
Pimobendan 1.25mg - 6,25mg (0,25mg/kg) - BID - VO

Administrar após as refeições.
Retorno em 15 dias.

Dr. [Nome]
CRMV-CE XXXXX
```

#### 💊 Banco de Medicamentos

**O que faz:**
- Cadastra novos medicamentos
- Define doses padrão (mg/kg)
- Armazena frequências e vias

**Quando usar:**
- Cadastrar medicamento que não está no banco
- Atualizar concentrações

#### 📋 Templates

**O que faz:**
- Salva prescrições frequentes
- Reutiliza com um clique

**Exemplo:**
- Template: "ICC B1"
- Conteúdo: Pimobendan + Enalapril + Furosemida
- Basta selecionar o template e ajustar doses

---

### 💰 Financeiro

#### 📊 Dashboard

**O que faz:**
- Total a receber
- Recebido no mês
- Faturamento por clínica

#### 💳 Contas a Receber

**O que faz:**
- Lista todas as OS
- Filtra por clínica e status
- Registra pagamentos

**Como usar:**

1. Secretária liga para clínica para cobrar
2. Acessa "Financeiro" > "Contas a Receber"
3. Filtra pela clínica
4. Vê pendências:
   ```
   OS-2026-00001 | Clínica Centro | R$ 255,00 | Pendente
   OS-2026-00002 | Vet Care | R$ 360,00 | Pendente
   ```
5. Após receber:
   - Informa ID da OS
   - Seleciona forma de pagamento
   - Clica "Confirmar Pagamento"

#### 📈 Relatórios

**O que faz:**
- Gera relatório por período
- Totaliza por clínica
- Separa pago vs pendente

**Como usar:**
1. Seleciona período (ex: mês atual)
2. Clica "Gerar Relatório"
3. Visualiza breakdown por clínica

---

### 🏢 Cadastros

#### 🏥 Clínicas Parceiras

**O que faz:**
- Cadastra clínicas que você atende
- Guarda dados completos (CNPJ, responsável, etc)

**Dados importantes:**
- Nome (deve ser EXATO ao usado nos laudos)
- WhatsApp (para confirmações)
- CNPJ (para NF)

#### 🛠️ Serviços

**O que faz:**
- Define catálogo de serviços
- Valores base (antes dos descontos)

**Já cadastrados:**
- Ecocardiograma: R$ 300
- ECG: R$ 150
- Pressão Arterial: R$ 80
- Etc.

#### 🎁 Descontos Negociados

**O que faz:**
- Configura descontos por clínica
- Pode ser geral ou por serviço

**Tipos:**
- **Percentual**: Ex: 15% de desconto
- **Valor Fixo**: Ex: R$ 50 de desconto

**Exemplos:**

```
Clínica Centro:
└─> Desconto geral: 15% em tudo

Vet Care:
└─> Eco: 10%
└─> ECG: 15%

Hospital 24h:
└─> Pacotes: 20%
└─> Demais: 10%
```

**Como criar:**

1. Seleciona clínica
2. Seleciona serviço (ou deixa vazio para "todos")
3. Tipo: percentual ou valor fixo
4. Valor: 15 (se percentual = 15%)
5. Salva

---

## 🔄 FLUXO DE TRABALHO

### Cenário Completo: Atendimento do Rex

#### Segunda-feira 09:00 - Agendamento

**Secretária:**
1. Recebe ligação da "Clínica Centro"
2. Acessa: "📅 Agendamentos" > "Novo Agendamento"
3. Preenche:
   - Clínica: Clínica Centro
   - Paciente: Rex
   - Tutor: João Silva (85) 99999-9999
   - Data: Terça, 25/01
   - Hora: 14:00
   - Serviços: Ecocardiograma + ECG
4. Clica "Criar Agendamento"

**Sistema:**
- Agendamento #123 criado ✅

---

#### Segunda-feira 14:00 - Confirmação

**Secretária:**
1. Acessa: "📅 Agendamentos" > "Confirmações"
2. Vê Rex na lista de amanhã
3. Clica no link WhatsApp automático
4. Envia: _"Olá João, lembrete do Rex para amanhã às 14h na Clínica Centro"_
5. Tutor confirma
6. Secretária clica "Confirmar Agendamento"

**Sistema:**
- Status alterado para "Confirmado" ✅

---

#### Terça-feira 14:00 - Atendimento

**Dr.:**
1. Chega na Clínica Centro
2. Realiza exames no Rex
3. Acessa: "🩺 Laudos e Exames"
4. Importa XML do Vivid
5. Edita laudo
6. Carrega imagens
7. Clica "Gerar PDF"

**Sistema:**
- PDF salvo: `2026-01-25_Rex_Silva.pdf` ✅
- OS criada automaticamente:
  ```
  OS-2026-00001
  Clínica: Centro (15% desconto)
  ├─ Eco: R$ 300 - 15% = R$ 255
  └─ ECG: R$ 150 - 15% = R$ 127,50
  TOTAL: R$ 382,50 (Pendente)
  ```

---

#### Terça-feira 15:00 - Prescrição

**Dr.:**
1. Acessa: "💊 Prescrições" > "Nova Prescrição"
2. Preenche:
   - Paciente: Rex
   - Tutor: João Silva
   - Peso: 25kg
3. Busca "Furosemida 10mg/ml" → Adiciona
   - Sistema calcula: 5ml BID
4. Busca "Enalapril 10mg" → Adiciona
   - Sistema calcula: 12,5mg BID
5. Escreve: "Administrar após refeições"
6. Clica "Gerar Receituário"

**Sistema:**
- PDF salvo: `RX_Rex_20260125_150234.pdf` ✅
- WhatsApp do tutor pode enviar o PDF

---

#### Quarta-feira 10:00 - Cobrança

**Secretária:**
1. Acessa: "💰 Financeiro" > "Contas a Receber"
2. Filtra: "Clínica Centro"
3. Vê:
   ```
   OS-2026-00001 | R$ 382,50 | Pendente | 25/01/2026
   ```
4. Liga para clínica: "Bom dia! Segue o valor dos atendimentos..."
5. Clínica: "OK, vou fazer o PIX agora"
6. Secretária:
   - ID: 1
   - Forma: PIX
   - Data: 26/01/2026
   - Clica "Confirmar Pagamento"

**Sistema:**
- Status: Pendente → Pago ✅
- Dashboard atualizado

---

#### 6 meses depois - Retorno

**Sistema (automático):**
- Cria acompanhamento:
  ```
  Rex - Último eco: 25/01/2026
  Próximo: 25/07/2026 (6 meses)
  ```

**30 dias antes (25/06/2026):**
- Dashboard exibe: "1 retorno próximo"
- Secretária entra em contato com tutor

---

## 📊 RELATÓRIOS E ANÁLISES

### Relatório Mensal

1. Acesse: "💰 Financeiro" > "Relatórios"
2. Período: 01/01/2026 a 31/01/2026
3. Clica "Gerar"

**Resultado:**

```
┌──────────────────────┬────────┬────────────┬────────────┬────────────┐
│ Clínica              │ Qtd OS │ Pendente   │ Pago       │ Total      │
├──────────────────────┼────────┼────────────┼────────────┼────────────┤
│ Clínica Centro       │   12   │ R$ 850,00  │ R$ 3.200   │ R$ 4.050   │
│ Vet Care             │    8   │ R$ 0,00    │ R$ 2.100   │ R$ 2.100   │
│ Hospital 24h         │   15   │ R$ 1.500   │ R$ 5.800   │ R$ 7.300   │
├──────────────────────┼────────┼────────────┼────────────┼────────────┤
│ TOTAL                │   35   │ R$ 2.350   │ R$ 11.100  │ R$ 13.450  │
└──────────────────────┴────────┴────────────┴────────────┴────────────┘
```

---

## 🔧 MANUTENÇÃO

### Backup do Banco

**Manualmente:**
1. Dashboard > Botão "Backup"
2. Arquivo salvo em: `~/FortCordis/backup_YYYYMMDD_HHMMSS.db`

**Automaticamente (recomendado):**
Configure backup semanal no seu sistema operacional

**Windows:**
```batch
@echo off
xcopy "%USERPROFILE%\FortCordis\fortcordis.db" "%USERPROFILE%\FortCordis\Backups\fortcordis_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db" /Y
```

**Linux/Mac:**
```bash
#!/bin/bash
cp ~/FortCordis/fortcordis.db ~/FortCordis/Backups/fortcordis_$(date +%Y%m%d).db
```

---

### Logs do Sistema

Erros são registrados em: `~/FortCordis/app.log`

Para visualizar:
```bash
tail -f ~/FortCordis/app.log
```

---

## ❓ PERGUNTAS FREQUENTES

### OS não está sendo criada automaticamente

**Causas:**
1. Nome da clínica no laudo diferente do cadastro
2. Serviço "Ecocardiograma" não cadastrado

**Solução:**
1. Verifique nomes exatos em "Cadastros" > "Clínicas"
2. Certifique-se que executou `inicializar_dados.py`

---

### Cálculo de posologia incorreto

**Causa:**
- Formato da concentração incorreto

**Solução:**
- Use formato exato: `10mg/ml` (não `10 mg/ml` ou `10mg / ml`)

---

### Como alterar valor de um serviço?

1. Vá em "Cadastros" > "Serviços"
2. (Feature futura: edição inline)
3. Por ora, use SQL direto no banco:
```sql
UPDATE servicos SET valor_base = 350.00 WHERE nome = 'Ecocardiograma';
```

---

### Como excluir um agendamento?

1. "Agendamentos" > "Lista"
2. Marque como "Cancelado" (usa dropdown de ações)

---

### Esqueci de gerar OS ao fazer laudo

**Solução:**
1. Vá em "Financeiro" > "Ordem de Serviço Manual"
2. Preencha manualmente

---

## 📞 SUPORTE

### Problemas Comuns

**Erro: ModuleNotFoundError: No module named 'fortcordis_modules'**
- Verifique que a pasta `fortcordis_modules/` está no mesmo local do arquivo principal
- Certifique-se que existe o arquivo `__init__.py` dentro dela

**Erro: no such table: clinicas_parceiras**
- O banco não foi inicializado
- Execute o sistema uma vez para criar as tabelas

**PDF não abre / está corrompido**
- Verifique versão do fpdf2: `pip show fpdf2`
- Deve ser 2.7.0 ou superior

---

## 🚀 PRÓXIMOS PASSOS

Após dominar o sistema básico, considere:

1. **Integração WhatsApp API Business** para envio automático
2. **Dashboard com gráficos** (Plotly)
3. **App mobile** para visualização de agendamentos
4. **OCR** para digitalizar exames em papel
5. **Integração com sistemas contábeis**

---

## 📜 LICENÇA

Sistema proprietário desenvolvido para Fort Cordis Cardiologia Veterinária.

---

## 👨‍💻 CRÉDITOS

Desenvolvido para otimizar o fluxo de trabalho da cardiologia veterinária volante em Fortaleza-CE.

**Versão:** 2.0  
**Data:** Janeiro 2026
