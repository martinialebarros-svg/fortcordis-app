# Onde os laudos são salvos

**Atualizado em:** 02/2026

---

## 1. Resumo

Os laudos (PDF, JSON e imagens) passam a ser salvos em **dois lugares** quando você arquiva:

1. **Pasta local** (arquivos em disco)  
2. **Banco de dados** (tabelas `laudos_arquivos` e `laudos_arquivos_imagens`) — **um único lugar com tudo (JSON + PDF + imagens)**

O **banco** é o local único que concentra laudos e imagens e que pode persistir na nuvem se o banco for persistente (volume ou DB externo).

---

## 2. Pasta local (PASTA_LAUDOS)

- **Configuração:** `app/config.py` → `PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"`.
- **No seu PC:** por exemplo `C:\Users\<SeuUsuario>\FortCordis\Laudos` (Windows) ou `~/FortCordis/Laudos` (Linux/Mac).
- **No Streamlit Cloud:** a pasta fica no sistema de arquivos **efêmero** do container; arquivos são perdidos em redeploy ou reinício. Por isso o uso principal em produção é o banco.

**O que é salvo na pasta (quando o app escreve em disco):**

- `{nome_base}.pdf` — PDF do laudo  
- `{nome_base}.json` — Dados do laudo (incluindo referências às imagens)  
- `{nome_base}__IMG_01.jpg`, `{nome_base}__IMG_02.png`, … — Imagens do exame  

---

## 3. Banco de dados (um único lugar: laudos + imagens)

- **Tabelas:** `laudos_arquivos` e `laudos_arquivos_imagens` (criadas em `app/db.py` no `_db_init()`).
- **Quando é usado:** ao clicar em **Arquivar** (gerar PDF e arquivar) na página Laudos, o app chama `salvar_laudo_arquivo_no_banco()` e grava:
  - **laudos_arquivos:** `conteudo_json` (blob), `conteudo_pdf` (blob), além de `data_exame`, `nome_animal`, `nome_tutor`, `nome_clinica`, `tipo_exame`, `nome_base`.
  - **laudos_arquivos_imagens:** para cada imagem, um registro com `laudo_arquivo_id`, `ordem`, `nome_arquivo`, `conteudo` (blob).

Assim, **todos os laudos e imagens ficam no banco em um único lugar**.

- **Onde consultar no app:** **Laudos e Exames** → aba **Buscar exames** → seção **Exames da pasta (importados para o banco)**. Lá é possível baixar JSON/PDF e **Carregar JSON** para editar (dados + imagens vêm do banco).

---

## 4. Persistência na nuvem

- **Streamlit Cloud:** o SQLite (`fortcordis.db`) costuma ser efêmero, a menos que você use **persistent storage** (volume montado) ou um **banco externo**.
- Para laudos persistirem na nuvem:
  1. **Opção A:** Configurar **persistent storage** no Streamlit Cloud e apontar o app para um `fortcordis.db` nesse volume (o mesmo banco que já contém `laudos_arquivos` e `laudos_arquivos_imagens`).
  2. **Opção B:** Usar um **banco externo** (ex.: PostgreSQL em um serviço de nuvem) e alterar o app para usar esse banco em vez de SQLite (requer mudanças em `app/config.py` e na conexão em `app/db.py`).

Com isso, o “único lugar” dos laudos e imagens (o banco) fica em nuvem e persiste entre redeploys.

---

## 5. Tabelas antigas (apenas caminhos)

As tabelas **laudos_ecocardiograma**, **laudos_eletrocardiograma** e **laudos_pressao_arterial** continuam sendo preenchidas pelo `salvar_laudo_no_banco()` com **caminhos** de arquivo (`arquivo_json`, `arquivo_pdf`), não com o conteúdo. Em ambiente efêmero (ex.: Streamlit Cloud sem volume), esses caminhos podem deixar de ser válidos após reinício. O armazenamento completo e recomendado para “um lugar na nuvem” é **laudos_arquivos** + **laudos_arquivos_imagens**.

---

## 6. Resumo rápido

| O quê              | Onde (pasta)              | Onde (banco)                          |
|--------------------|---------------------------|----------------------------------------|
| PDF do laudo       | `PASTA_LAUDOS/{nome}.pdf` | `laudos_arquivos.conteudo_pdf`         |
| JSON do laudo      | `PASTA_LAUDOS/{nome}.json`| `laudos_arquivos.conteudo_json`        |
| Imagens do exame   | `PASTA_LAUDOS/{nome}__IMG_*` | `laudos_arquivos_imagens.conteudo`  |

**Recomendação:** usar o banco (`laudos_arquivos` + `laudos_arquivos_imagens`) como **único lugar** dos laudos e imagens e garantir que esse banco seja persistente na nuvem (volume ou DB externo) para não perder dados em redeploy.
