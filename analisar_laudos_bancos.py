"""Analisa vários .db e mostra quais têm tabelas de laudos e quantos registros."""
import sqlite3
from pathlib import Path

BANCOS = [
    Path(r"c:\Users\marti\Desktop\FortCordis_BACKUP_25JAN2026\Clinica\fortcordis_master.db"),
    Path(r"c:\Users\marti\Desktop\FortCordis_BACKUP_25JAN2026\DB\fortcordis.db"),
    Path(r"c:\FortCordis_Novo\fortcordis.db"),
    Path(r"c:\Users\marti\FortCordis\DB\fortcordis.db"),
    Path(r"c:\Users\marti\FortCordis\DB\fortcordis_master.db"),
]

TABELAS_LAUDOS = ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial")

def analisar(banco: Path):
    if not banco.exists():
        return None, "Arquivo nao existe", []
    try:
        conn = sqlite3.connect(str(banco))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tabelas_lista = [r[0] for r in cur.fetchall()]
        tabelas = set(tabelas_lista)
        resultado = {}
        total_laudos = 0
        for t in TABELAS_LAUDOS:
            if t in tabelas:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                n = cur.fetchone()[0]
                resultado[t] = n
                total_laudos += n
            else:
                resultado[t] = None
        conn.close()
        return resultado, total_laudos, tabelas_lista
    except Exception as e:
        return None, str(e), []


def main():
    print("=" * 70)
    print("ANALISE DE BANCOS - TABELAS DE LAUDOS")
    print("=" * 70)
    for banco in BANCOS:
        print(f"\n[DB] {banco}")
        res, total, tabelas_lista = analisar(banco)
        if res is None and not tabelas_lista:
            print(f"   ERRO: {total}")
            continue
        if isinstance(total, str):
            print(f"   ERRO: {total}")
            continue
        for tabela in TABELAS_LAUDOS:
            v = res.get(tabela)
            if v is None:
                print(f"   - {tabela}: (tabela nao existe)")
            else:
                print(f"   - {tabela}: {v} registro(s)")
        print(f"   >>> TOTAL LAUDOS: {total}")
        if tabelas_lista:
            print(f"   Tabelas no banco: {', '.join(tabelas_lista)}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
