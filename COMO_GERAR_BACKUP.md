# Como gerar o backup no PC

O backup é um arquivo `.db` que você envia no sistema online (Configurações > Importar dados) para restaurar clínicas, tutores, pacientes, laudos e clínicas parceiras.

---

## Passo a passo

### 1. Abrir o terminal no PC

- **Windows:** Tecla Win, digite `cmd` ou `PowerShell` e abra.
- Ou no VS Code / Cursor: menu **Terminal** > **Novo Terminal**.

### 2. Ir até a pasta do projeto

```powershell
cd C:\Users\marti\Desktop\FortCordis_Novo
```

(Use o caminho real da pasta onde está o `exportar_backup.py`.)

### 3. Rodar o script de backup

**Opção A – Usar o banco que o script acha sozinho**

O script procura o `fortcordis.db` nesta ordem:

1. Pasta do projeto (FortCordis_Novo)
2. `C:\Users\marti\FortCordis\data\fortcordis.db`
3. `C:\Users\marti\FortCordis\DB\fortcordis.db`

```powershell
python exportar_backup.py
```

**Opção B – Indicar o banco manualmente**

Se o seu banco está em outro lugar:

```powershell
python exportar_backup.py --banco "C:\caminho\completo\para\fortcordis.db"
```

Exemplo:

```powershell
python exportar_backup.py --banco "C:\Users\marti\Documents\FortCordis\fortcordis.db"
```

**Opção C – Escolher o nome do arquivo de saída**

```powershell
python exportar_backup.py --saida meu_backup.db
```

**Opção D – Banco e saída ao mesmo tempo**

```powershell
python exportar_backup.py --banco "C:\Users\marti\FortCordis\data\fortcordis.db" --saida backup_hoje.db
```

### 4. Conferir o resultado

- Se der certo, aparece algo como:
  - `Exportando de: C:\...\fortcordis.db`
  - Lista de tabelas e quantidades (clinicas, tutores, pacientes, laudos, clinicas_parceiras)
  - `OK: Exportadas XXX linhas para ...`
- O arquivo `.db` é criado na pasta do projeto com nome tipo:
  - `backup_fortcordis_20260201_1430.db` (data e hora)
  - Ou o nome que você passou em `--saida`.

### 5. Enviar no sistema online

1. Abra o app no Streamlit (navegador).
2. Vá em **Configurações do sistema** > aba **Importar dados**.
3. Marque **«Limpar laudos antes de importar»** (se quiser evitar repetidos).
4. Em **Enviar arquivo de backup (.db)**, escolha o arquivo que você gerou.
5. Clique em **Importar agora**.

---

## Se der erro

- **"Nenhum banco encontrado"**  
  Use `--banco` com o caminho completo do seu `fortcordis.db`.

- **"O banco está vazio"**  
  O arquivo `.db` que você está usando não tem dados nas tabelas de exportação. Confira o caminho com `--banco` ou use o banco onde você realmente usa o Fort Cordis no PC.

- **"python não é reconhecido"**  
  Instale o Python ou use `py exportar_backup.py` no lugar de `python exportar_backup.py`.

---

## Resumo rápido

```powershell
cd C:\Users\marti\Desktop\FortCordis_Novo
python exportar_backup.py
```

O arquivo `backup_fortcordis_AAAAMMDD_HHMM.db` aparecerá na pasta FortCordis_Novo. Envie esse arquivo em Configurações > Importar dados no sistema online.
