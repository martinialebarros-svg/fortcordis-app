"""
Exporta backup do Fort Cordis para restaurar no sistema após deploy.
Gera um arquivo .db com: clinicas, tutores, pacientes, laudos_*, clinicas_parceiras.

Uso (na pasta do projeto):
  python exportar_backup.py
  python exportar_backup.py --saida meu_backup.db
  python exportar_backup.py --banco "C:\\Users\\marti\\FortCordis\\data\\fortcordis.db"

Se não usar --banco, o script tenta nesta ordem:
  1) fortcordis.db na pasta do projeto (FortCordis_Novo)
  2) FortCordis/data/fortcordis.db (pasta do usuário)
  3) FortCordis/DB/fortcordis.db (pasta antiga)

O arquivo gerado deve ser enviado para o sistema online (Configurações > Importar dados).
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PASTA = Path(__file__).resolve().parent

# Ordem de busca do banco de origem (evita confusão entre dois bancos)
CANDIDATOS_DB = [
    PASTA / "fortcordis.db",                           # Pasta do projeto
    Path.home() / "FortCordis" / "data" / "fortcordis.db",
    Path.home() / "FortCordis" / "DB" / "fortcordis.db",
]

TABELAS_EXPORTAR = [
    "clinicas",
    "tutores",
    "pacientes",
    "laudos_ecocardiograma",
    "laudos_eletrocardiograma",
    "laudos_pressao_arterial",
    "clinicas_parceiras",
]


def _contar_registros(cursor, tabelas):
    """Retorna dict tabela -> quantidade de linhas (só tabelas que existem)."""
    counts = {}
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    existentes = {r[0] for r in cursor.fetchall()}
    for t in tabelas:
        if t not in existentes:
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cursor.fetchone()[0]
    return counts


def exportar(db_origem: Path, saida: Path):
    if not db_origem.exists():
        return False, f"Banco não encontrado: {db_origem}"

    try:
        conn_origem = sqlite3.connect(str(db_origem))
        conn_origem.row_factory = sqlite3.Row
        cursor_origem = conn_origem.cursor()

        # Mostrar de qual banco está exportando e quantos registros
        contagens = _contar_registros(cursor_origem, TABELAS_EXPORTAR)
        total_preview = sum(contagens.values())
        print(f"Exportando de: {db_origem}")
        for t, n in contagens.items():
            print(f"  - {t}: {n} registro(s)")
        if total_preview == 0:
            conn_origem.close()
            return False, (
                f"O banco está vazio (0 registros nas tabelas de exportação). "
                f"Se seus dados estão em outro arquivo, use: python exportar_backup.py --banco \"C:\\caminho\\para\\fortcordis.db\""
            )

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
    # --banco caminho   → usar este arquivo .db como origem
    # --saida caminho   → arquivo de backup de saída
    db_origem = None
    saida = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--banco" and i + 1 < len(sys.argv):
            db_origem = Path(sys.argv[i + 1])
            i += 2
            continue
        if sys.argv[i] == "--saida" and i + 1 < len(sys.argv):
            saida = Path(sys.argv[i + 1])
            i += 2
            continue
        i += 1

    if db_origem is None:
        for candidato in CANDIDATOS_DB:
            if candidato.exists():
                db_origem = candidato
                break
        if db_origem is None:
            print("ERRO: Nenhum banco encontrado. Caminhos verificados:")
            for c in CANDIDATOS_DB:
                print(f"  - {c}")
            print('Use: python exportar_backup.py --banco "C:\\caminho\\para\\fortcordis.db"')
            sys.exit(1)

    if saida is None:
        data = datetime.now().strftime("%Y%m%d_%H%M")
        saida = PASTA / f"backup_fortcordis_{data}.db"

    ok, msg = exportar(db_origem, saida)
    if ok:
        print(f"OK: {msg}")
    else:
        print(f"ERRO: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
