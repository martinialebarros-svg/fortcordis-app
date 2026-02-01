"""
Importa laudos da pasta local (JSON/PDF/imagens) para o banco fortcordis.db.
Assim os exames aparecem em Buscar exames no sistema online apos importar o backup.

Uso (na pasta do projeto):
  python importar_pasta_laudos_para_banco.py
  python importar_pasta_laudos_para_banco.py --pasta "C:\\Users\\marti\\FortCordis\\Laudos"

O banco usado e o fortcordis.db na mesma pasta do script (FortCordis_Novo).
Depois execute exportar_backup.py e importe o .db em Configuracoes > Importar dados no sistema online.
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PASTA_PROJETO = Path(__file__).resolve().parent
DB_PATH = PASTA_PROJETO / "fortcordis.db"
PASTA_LAUDOS_PADRAO = Path.home() / "FortCordis" / "Laudos"


def criar_tabelas(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS laudos_arquivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_exame TEXT NOT NULL,
            nome_animal TEXT,
            nome_tutor TEXT,
            nome_clinica TEXT,
            tipo_exame TEXT DEFAULT 'ecocardiograma',
            nome_base TEXT UNIQUE,
            conteudo_json BLOB,
            conteudo_pdf BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS laudos_arquivos_imagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            laudo_arquivo_id INTEGER NOT NULL,
            ordem INTEGER DEFAULT 0,
            nome_arquivo TEXT,
            conteudo BLOB,
            FOREIGN KEY(laudo_arquivo_id) REFERENCES laudos_arquivos(id)
        )
    """)


def inferir_tipo_exame(obj):
    """Inferir tipo por medidas presentes no JSON."""
    medidas = obj.get("medidas") or {}
    if isinstance(medidas, dict):
        if "pressao_sistolica" in medidas or "pressao_diastolica" in medidas:
            return "pressao_arterial"
        if "ritmo" in medidas or "frequencia_cardiaca" in medidas:
            return "eletrocardiograma"
    return "ecocardiograma"


def importar_pasta(pasta: Path):
    if not pasta.exists():
        return False, f"Pasta nao encontrada: {pasta}"
    arquivos_json = sorted(pasta.glob("*.json"))
    if not arquivos_json:
        return False, f"Nenhum arquivo .json na pasta: {pasta}"

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    criar_tabelas(cur)
    conn.commit()

    inseridos = 0
    erros = []
    for p in arquivos_json:
        try:
            texto = p.read_text(encoding="utf-8")
            obj = json.loads(texto)
            pac = obj.get("paciente") or {}
            if isinstance(pac, dict):
                data_exame = (pac.get("data_exame") or "")[:10]
                nome_animal = (pac.get("nome") or "").strip()
                nome_tutor = (pac.get("tutor") or "").strip()
                nome_clinica = (pac.get("clinica") or "").strip()
            else:
                data_exame = nome_animal = nome_tutor = nome_clinica = ""
            if not data_exame:
                data_exame = p.stem[:10] if len(p.stem) >= 10 else datetime.now().strftime("%Y-%m-%d")
            tipo_exame = inferir_tipo_exame(obj)
            nome_base = p.stem

            conteudo_json = p.read_bytes()
            pdf_path = pasta / (p.stem + ".pdf")
            conteudo_pdf = pdf_path.read_bytes() if pdf_path.exists() else None

            cur.execute("SELECT id FROM laudos_arquivos WHERE nome_base=?", (nome_base,))
            row_ant = cur.fetchone()
            if row_ant:
                cur.execute("DELETE FROM laudos_arquivos_imagens WHERE laudo_arquivo_id=?", (row_ant[0],))
            cur.execute(
                """INSERT OR REPLACE INTO laudos_arquivos
                   (data_exame, nome_animal, nome_tutor, nome_clinica, tipo_exame, nome_base, conteudo_json, conteudo_pdf, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data_exame,
                    nome_animal,
                    nome_tutor,
                    nome_clinica,
                    tipo_exame,
                    nome_base,
                    conteudo_json,
                    conteudo_pdf,
                    datetime.now().isoformat(),
                ),
            )
            laudo_id = cur.lastrowid
            if laudo_id == 0:
                cur.execute("SELECT id FROM laudos_arquivos WHERE nome_base=?", (nome_base,))
                r = cur.fetchone()
                laudo_id = r[0] if r else None
            if laudo_id:
                cur.execute("DELETE FROM laudos_arquivos_imagens WHERE laudo_arquivo_id=?", (laudo_id,))
                img_ordem = 0
                for img_path in sorted(pasta.glob(f"{p.stem}__IMG_*.*")):
                    try:
                        img_bytes = img_path.read_bytes()
                        cur.execute(
                            "INSERT INTO laudos_arquivos_imagens (laudo_arquivo_id, ordem, nome_arquivo, conteudo) VALUES (?, ?, ?, ?)",
                            (laudo_id, img_ordem, img_path.name, img_bytes),
                        )
                        img_ordem += 1
                    except Exception as e:
                        erros.append(f"{img_path.name}: {e}")
            inseridos += 1
        except Exception as e:
            erros.append(f"{p.name}: {e}")

    conn.commit()
    conn.close()

    msg = f"Importados {inseridos} exame(s) para {DB_PATH}."
    if erros:
        msg += f" Erros: {'; '.join(erros[:5])}" + ("..." if len(erros) > 5 else "")
    return True, msg


def main():
    pasta = PASTA_LAUDOS_PADRAO
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--pasta" and i + 1 < len(sys.argv):
            pasta = Path(sys.argv[i + 1])
            i += 2
            continue
        i += 1

    print("Banco:", DB_PATH)
    print("Pasta de laudos:", pasta)
    ok, msg = importar_pasta(pasta)
    if ok:
        print("OK:", msg)
    else:
        print("ERRO:", msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
