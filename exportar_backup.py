"""
Exporta backup do Fort Cordis para restaurar no sistema após deploy.
Gera um arquivo .db com: clinicas, tutores, pacientes, laudos_*, clinicas_parceiras.

Uso (na pasta do projeto):
  python exportar_backup.py
  python exportar_backup.py --saida meu_backup.db

O arquivo gerado deve ser enviado para o sistema online (Configurações > Importar dados).
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Banco local (mesma pasta do script)
PASTA = Path(__file__).resolve().parent
DB_ORIGEM = PASTA / "fortcordis.db"

TABELAS_EXPORTAR = [
    "clinicas",
    "tutores",
    "pacientes",
    "laudos_ecocardiograma",
    "laudos_eletrocardiograma",
    "laudos_pressao_arterial",
    "clinicas_parceiras",
]


def exportar(saida: Path):
    if not DB_ORIGEM.exists():
        return False, f"Banco não encontrado: {DB_ORIGEM}"

    try:
        conn_origem = sqlite3.connect(str(DB_ORIGEM))
        conn_origem.row_factory = sqlite3.Row
        cursor_origem = conn_origem.cursor()

        # Lista tabelas que existem no banco origem
        cursor_origem.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tabelas_existentes = {r[0] for r in cursor_origem.fetchall()}

        conn_destino = sqlite3.connect(str(saida))
        cursor_destino = conn_destino.cursor()

        total_linhas = 0
        for tabela in TABELAS_EXPORTAR:
            if tabela not in tabelas_existentes:
                continue
            cursor_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
            ddl_row = cursor_origem.fetchone()
            if not ddl_row or not ddl_row[0]:
                continue
            cursor_destino.execute(f"DROP TABLE IF EXISTS {tabela}")
            cursor_destino.execute(ddl_row[0])
            cursor_origem.execute(f"SELECT * FROM {tabela}")
            rows = cursor_origem.fetchall()
            if not rows:
                continue
            cursor_origem.execute(f"PRAGMA table_info({tabela})")
            colunas = [c[1] for c in cursor_origem.fetchall()]
            placeholders = ", ".join(["?" for _ in colunas])
            cols_str = ", ".join(colunas)
            for row in rows:
                cursor_destino.execute(
                    f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders})",
                    list(row),
                )
            total_linhas += len(rows)

        conn_destino.commit()
        conn_destino.close()
        conn_origem.close()

        return True, f"Exportadas {total_linhas} linhas para {saida}"

    except Exception as e:
        return False, str(e)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--saida" and len(sys.argv) > 2:
        saida = Path(sys.argv[2])
    else:
        data = datetime.now().strftime("%Y%m%d_%H%M")
        saida = PASTA / f"backup_fortcordis_{data}.db"

    ok, msg = exportar(saida)
    if ok:
        print(f"OK: {msg}")
    else:
        print(f"ERRO: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
