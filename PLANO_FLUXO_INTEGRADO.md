# Plano: Fluxo Integrado Fort Cordis

Este documento descreve o fluxo de trabalho atual e as implementações para unificar tudo no sistema, com integrações Google Agenda e WhatsApp.

---

## 1. Fluxo de trabalho (atual)

1. **Clínicas parceiras** entram em contato com secretárias e solicitam disponibilidade.
2. **Secretárias** marcam: horário, dia, clínica, tutor, pet, serviços. Registro hoje no **Google Agenda** (você visualiza).
3. **24h antes** do atendimento: secretárias confirmam com a clínica (geralmente **WhatsApp**).
4. **No dia**: você realiza os serviços.
5. **Em até 24h**: você emite o laudo e envia para a secretária, que encaminha à clínica.
6. **Durante a semana**: secretárias cobram clínicas que não pagaram no ato.
7. **Pagamento recebido**: baixa na planilha que as secretárias mantêm.

---

## 2. Objetivos do sistema integrado

- **Um só lugar**: agendamentos, laudos, financeiro e cobranças no Fort Cordis.
- **Integração Google Agenda**: sincronizar agendamentos (criar/ver eventos no Google Calendar).
- **Facilitar WhatsApp**: lista “Confirmar amanhã” com link para abrir conversa (número da clínica).
- **Laudo ↔ Agendamento ↔ OS**: vincular laudo ao agendamento e OS ao agendamento.
- **Dar baixa no pagamento**: no módulo Financeiro, marcar OS como paga (data e forma), substituindo a planilha.

---

## 3. Módulos e interligação

| Módulo        | Função no fluxo |
|---------------|------------------|
| **Agendamentos** | Registrar agendamentos; lista “Confirmar amanhã (24h)”; opção de enviar para Google Agenda. |
| **Laudos e Exames** | Emitir laudo; ao salvar, vincular a agendamento (data + clínica + paciente) e criar OS no Financeiro (já existe). |
| **Financeiro** | Ver OS (geradas pelo laudo); **dar baixa** (marcar pago, data, forma); filtrar por clínica; histórico. |
| **Cadastros** | Clínicas (nome, WhatsApp, etc.) e Serviços — usados em Agendamentos, Laudos e Financeiro. |

Fluxo de dados:

- **Agendamento** (clínica, data, paciente, serviço) → usado para “Confirmar amanhã” e, no futuro, Google Calendar.
- **Laudo** gerado → cria/atualiza **OS** no Financeiro e pode vincular ao **Agendamento** (por data/clínica/paciente).
- **Financeiro** → dar baixa na OS quando o pagamento for recebido (substitui planilha).

---

## 4. Implementações (resumo)

### 4.1 Já no sistema (aproveitado)

- Agendamentos: criar, listar, filtrar, marcar realizado/cancelado.
- Laudos: gerar PDF e salvar; criação automática de OS no Financeiro (Ecocardiograma + clínica parceira).
- Financeiro: tabela com `numero_os`, clínica, valor, `status_pagamento`, `data_pagamento`, `forma_pagamento`.
- Cadastros: clínicas (com WhatsApp) e serviços.

### 4.2 A fazer no sistema

1. **Financeiro – Dar baixa**
   - Na lista de OS: botão “Dar baixa” nas OS pendentes.
   - Ao dar baixa: marcar `status_pagamento = 'pago'`, preencher `data_pagamento` e `forma_pagamento` (ex.: PIX, dinheiro, transferência).

2. **Agendamentos – Confirmar amanhã (24h)**
   - Nova seção/aba: “Confirmar amanhã” com lista de agendamentos cuja data é amanhã.
   - Para cada item: mostrar clínica, tutor, paciente, horário e **link WhatsApp** (wa.me/55 + número da clínica, se cadastrado) para a secretária confirmar.

3. **Dashboard – Resumo do fluxo**
   - Cards: Agendamentos hoje; **Confirmar amanhã** (quantidade); Laudos recentes / pendentes; **Cobranças pendentes** (OS pendentes e valor total).

4. **Vínculos**
   - Laudo → Agendamento: ao salvar laudo, buscar agendamento por data + clínica + nome do paciente e guardar `agendamento_id` no laudo (ou em tabela de ligação), se existir.
   - Financeiro já tem `agendamento_id` opcional; quando a OS for criada a partir do laudo, podemos preencher `agendamento_id` se encontrarmos o agendamento.

### 4.3 Integrações externas (próximos passos)

- **Google Calendar**
   - Opção 1: “Enviar para Google Agenda” ao criar/editar agendamento (API Google Calendar) — exige conta de serviço ou OAuth e configuração de credenciais.
   - Opção 2: Exportar agenda (arquivo .ics ou link) para importar no Google — mais simples, sem API.
   - Recomendação: começar com exportação .ics; depois evoluir para API se quiser sincronização automática.

- **WhatsApp**
   - Hoje: apenas **link** “Abrir no WhatsApp” (wa.me/55XXXXXXXXX) usando o número da clínica cadastrada — não exige API.
   - Futuro: WhatsApp Business API para envio automático de lembretes (ex.: 24h antes) — exige conta Business API e aprovação Meta.

---

## 5. Ordem sugerida de implementação

1. **Financeiro: dar baixa** (marcar pago, data, forma) — elimina planilha de baixa.
2. **Agendamentos: “Confirmar amanhã”** + link WhatsApp — organiza o passo 24h antes.
3. **Dashboard: resumo** (confirmar amanhã, cobranças pendentes) — visão única do fluxo.
4. **Vínculo Laudo ↔ Agendamento** (e OS com agendamento quando possível).
5. **Google Agenda**: exportação .ics; depois API se desejar.
6. **WhatsApp**: manter link; depois avaliar API para lembretes automáticos.

---

## 6. Arquivos principais

- `fortcordis_app.py`: telas Agendamentos, Financeiro, Dashboard, Laudos.
- `fortcordis_modules/database.py`: funções de agendamentos, financeiro (incluindo atualizar OS para “pago”).
- `fortcordis_modules/integrations.py`: helpers para Google Calendar (export .ics, futura API) e WhatsApp (montar link wa.me).
- Cadastros: clínicas com campo **WhatsApp** preenchido para o link “Confirmar amanhã”.

Com isso, o processo fica unificado no sistema, com integrações progressivas (Google Agenda e WhatsApp) conforme a necessidade.
