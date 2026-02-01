# 🚀 Deploy online – Fort Cordis

Guia para colocar o Fort Cordis na internet (Streamlit Community Cloud) e, em seguida, integrar com Google Calendar.

---

## 1. Colocar o sistema online (Streamlit Community Cloud)

### 1.1 Pré-requisitos

- Conta no **GitHub** (github.com)
- Conta no **Streamlit Community Cloud** (share.streamlit.io) – login com GitHub
- Código do projeto em um **repositório GitHub** (público ou privado)

### 1.2 O que o deploy usa

- **requirements.txt** (já criado na raiz do projeto) – dependências Python
- **Entrypoint:** `fortcordis_app.py` – arquivo principal do app
- **Banco:** SQLite (`fortcordis.db`) criado na pasta do app no servidor

Importante: no Streamlit Community Cloud o disco é **efêmero**. O banco e arquivos (laudos, assinatura, etc.) são apagados em cada **redeploy**. Para produção com dados persistentes, depois você pode migrar para um banco em nuvem (ex.: PostgreSQL no Neon/Supabase) e armazenamento de arquivos (ex.: S3/GCS).

### 1.3 Passo a passo no Streamlit Community Cloud

1. **Subir o projeto no GitHub**
   - Crie um repositório (ex.: `fortcordis-app`)
   - Envie o código (incluindo `fortcordis_app.py`, `fortcordis_modules/`, `requirements.txt`, `.streamlit/`, `modules/`, arquivos CSV e PNG necessários).
   - Não inclua o arquivo `fortcordis.db` no repositório (adicione ao `.gitignore`).

2. **Acessar o Streamlit Community Cloud**
   - Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com GitHub.

3. **Criar o app**
   - Clique em **“Create app”**.
   - Escolha **“Yup, I have an app”**.
   - Preencha:
     - **Repository:** `seu-usuario/fortcordis-app` (ou o nome do seu repo).
     - **Branch:** `main` (ou a branch que você usa).
     - **Main file path:** `fortcordis_app.py`.
   - (Opcional) **App URL:** escolha um subdomínio, ex.: `fortcordis.streamlit.app`.

4. **Configurações avançadas (recomendado)**
   - Clique em **“Advanced settings”**.
   - **Python version:** 3.10 ou 3.12 (igual ao que você usa localmente).
   - **Secrets:** se no futuro você usar variáveis de ambiente (banco, API do Google, etc.), pode colocar em formato TOML, ex.:
     ```toml
     # .streamlit/secrets.toml (local – NÃO commitar)
     # No Community Cloud, colar o conteúdo em "Secrets"
     # FORTCORDIS_DATA_DIR = "/tmp/fortcordis"
     ```

5. **Deploy**
   - Clique em **“Deploy”**. O Streamlit vai instalar o `requirements.txt` e rodar `fortcordis_app.py`.
   - Aguarde alguns minutos. A URL do app aparecerá no painel.

### 1.4 Após o primeiro deploy

- O app chama `inicializar_banco()` na subida, então as **tabelas são criadas** na primeira execução.
- Para ter **serviços, medicamentos e dados iniciais**, use dentro do próprio app a funcionalidade de cadastros ou rode uma vez o fluxo que popula dados (se existir no app). Em ambiente efêmero, isso precisará ser refeito após cada redeploy, a menos que você migre para banco externo.
- **Login:** use o mesmo fluxo de autenticação que você já tem no app (usuários/senha no banco).

### 1.5 Arquivos que devem estar no repositório

- `fortcordis_app.py`
- `fortcordis_modules/` (database.py, documentos.py, integrations.py, etc.)
- `modules/` (auth.py, rbac.py, etc.)
- `requirements.txt`
- `.streamlit/config.toml`
- `logo.png`, `temp_watermark_faded.png` (se o app usar)
- `tabela_referencia.csv`, `tabela_referencia_caninos.csv`, `tabela_referencia_felinos.csv` (se o app usar)

No **.gitignore** inclua, por exemplo:

- `fortcordis.db`
- `__pycache__/`
- `.streamlit/secrets.toml`
- `*.pyc`

### 1.6 Restaurar dados após o deploy (clínicas, tutores, pacientes, laudos)

Depois do deploy o banco online fica vazio. Para puxar os dados que você já tinha no computador:

1. **No seu computador** (na pasta do projeto):
   ```bash
   python exportar_backup.py
   ```
   Isso gera um arquivo `backup_fortcordis_AAAAAMMDD_HHMM.db` na mesma pasta.  
   - Para outro nome: `python exportar_backup.py --saida meu_backup.db`  
   - **Dois bancos no projeto:** o script tenta, nesta ordem: (1) `fortcordis.db` na pasta do projeto (FortCordis_Novo), (2) `FortCordis/data/fortcordis.db`, (3) `FortCordis/DB/fortcordis.db`. Se o backup sair com 0 registros, seus dados podem estar no outro caminho. Nesse caso use:
   ```bash
   python exportar_backup.py --banco "C:\Users\SEU_USUARIO\FortCordis\data\fortcordis.db"
   ```
   O script mostra de qual arquivo está exportando e quantos registros tem cada tabela antes de gerar o backup.

2. **No sistema online** (Streamlit):
   - Faça login como **administrador**.
   - Vá em **Configurações** → aba **"Importar dados"**.
   - Envie o arquivo `.db` de backup e clique em **"Importar agora"**.

O sistema importa: clínicas, tutores, pacientes, laudos (ecocardiograma, eletrocardiograma, pressão arterial) e clínicas parceiras. Se importar de novo, clínicas e tutores não duplicam (são identificados pelo nome).

**Nota:** O script `exportar_backup.py` deve estar na pasta do projeto e o `fortcordis.db` local deve ser o que tinha os cadastros e laudos. Pode incluir `exportar_backup.py` no repositório para uso local.

### 1.7 Onde ficam os arquivos de laudo (JSON, PDF, imagens)?

- **No seu computador:** o sistema espera a pasta de laudos em **`FortCordis\Laudos`** na sua pasta de usuário (ex.: `C:\Users\SEU_USUARIO\FortCordis\Laudos`). Se você usa a pasta do projeto, pode ser **`FortCordis_Novo\Laudos`** (ex.: `C:\Users\marti\Desktop\FortCordis_Novo\Laudos`). Nessa pasta ficam os arquivos `.json`, `.pdf` e imagens (ex.: `*_IMG_01.jpg`) de cada exame. O backup `.db` **não** inclui esses arquivos — só os registros do banco (datas, paciente, clínica, conclusão, etc.).

- **No sistema online (Streamlit Cloud):** não existe pasta persistente para esses arquivos. Além disso, o **banco guarda o caminho do seu PC** para localizar cada PDF/JSON (ex.: `C:\Users\...\FortCordis_Novo\Laudos\2026-01-29_Jully_Larissa_PET_MIX.pdf`). Quando você importa o backup online, esses caminhos são copiados — mas no servidor Linux esse caminho não existe, então o app **não consegue achar os arquivos** mesmo que eles existissem lá. O disco do app é **efêmero**: qualquer pasta (ex.: `/home/appuser/FortCordis/Laudos`) é recriada vazia a cada deploy. Por isso:
  - **O que vai para o online:** apenas o que está no `.db` (clínicas, tutores, pacientes, laudos com data, tipo, conclusão, etc.). Em **Buscar exames** você vê a lista de exames importados (data, clínica, animal, tutor, tipo).
  - **O que fica só no seu PC:** os arquivos reais — JSON, PDF e imagens dos laudos — continuam na sua pasta local (ex.: `FortCordis_Novo\Laudos`). Para abrir ou enviar um PDF/JSON, use essa pasta no seu computador.

- **Se no futuro quiser os PDFs/JSON também online:** seria preciso usar armazenamento em nuvem (ex.: AWS S3, Google Cloud Storage, ou anexos em banco) e alterar o app para gravar e ler dali. Hoje o desenho é: **online = metadados (banco); arquivos = no seu PC.**

---

## 2. Integração com Google Calendar (próxima etapa)

Objetivo: sincronizar **agendamentos** do Fort Cordis com eventos do Google Calendar (e, se quiser, o contrário).

### 2.1 O que será necessário

1. **Conta Google / Google Cloud**
   - Projeto no [Google Cloud Console](https://console.cloud.google.com).
   - Ativar a **Google Calendar API** no projeto.

2. **Credenciais OAuth 2.0**
   - Tipo “Aplicativo de desktop” ou “Aplicativo da Web”.
   - Baixar o JSON de credenciais (client_id / client_secret).
   - No deploy, guardar client_id e client_secret em **Secrets** (Streamlit) ou variáveis de ambiente.

3. **Biblioteca Python**
   - `google-auth`, `google-auth-oauthlib`, `google-api-python-client` no `requirements.txt`.

4. **Fluxo no app**
   - Botão “Conectar Google Calendar” → abre fluxo OAuth no navegador → salva tokens (refresh_token) em secrets ou banco.
   - Ao **criar/editar agendamento** no Fort Cordis → criar/atualizar evento no Calendar (titulo, data/hora, descrição com nome do paciente/clínica).
   - Opcional: job ou botão “Sincronizar” para trazer eventos do Calendar para a lista de agendamentos (evitar duplicar: usar um id externo, ex.: `google_event_id` na tabela de agendamentos).

### 2.2 Onde encaixar no código

- **Módulo:** ex.: `fortcordis_modules/calendar_sync.py` (ou `integrations/google_calendar.py`).
- **Funções sugeridas:**
  - `get_calendar_credentials()` – carrega/refresh OAuth.
  - `criar_evento_calendar(agendamento)` – recebe um agendamento (dict) e chama Calendar API para criar evento.
  - `atualizar_evento_calendar(event_id, agendamento)` – atualiza evento existente.
  - `listar_eventos_calendar(data_inicio, data_fim)` – para sincronização inversa (Calendar → Fort Cordis).
- **UI:** em “Agendamentos”, botão “Sincronizar com Google Calendar” e/ou checkbox “Enviar para Google Calendar” ao salvar agendamento.
- **Banco:** coluna opcional na tabela de agendamentos, ex.: `google_event_id`, para saber qual evento do Calendar corresponde a cada agendamento.

### 2.3 Segurança em produção

- Nunca commitar credenciais (JSON de cliente, tokens). Usar sempre **Secrets** do Streamlit ou variáveis de ambiente.
- Em produção, preferir **service account** ou OAuth com refresh token guardado de forma segura (banco criptografado ou secrets).

Quando você quiser implementar de fato, podemos:
- Criar o módulo `calendar_sync.py` (ou dentro de `integrations`).
- Adicionar as chamadas em “novo agendamento” / “editar agendamento”.
- Incluir `google-auth`, `google-auth-oauthlib` e `google-api-python-client` no `requirements.txt` e documentar os secrets necessários.

---

## 3. Resumo

| Etapa | Ação |
|-------|------|
| **Agora** | Deploy no Streamlit Community Cloud (repo no GitHub + `requirements.txt` + `fortcordis_app.py`). |
| **Depois** | Integração Google Calendar: OAuth, Calendar API, sincronizar agendamentos ↔ eventos. |
| **Opcional** | Banco persistente (PostgreSQL) e armazenamento de arquivos (S3/GCS) para não perder dados em redeploys. |

Se quiser, o próximo passo pode ser: (1) revisar o `.gitignore` e a lista de arquivos do repo para o deploy, ou (2) esboçar o `calendar_sync.py` e onde chamar no `fortcordis_app.py`.
