"""Verifica fortcordis.db na pasta do projeto (FortCordis_Novo)."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "fortcordis.db"
TABELAS_LAUDOS = ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial")

print("Arquivo:", DB)
print("Existe:", DB.exists())
if not DB.exists():
    exit(1)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tabs = [r[0] for r in cur.fetchall()]
print("Tabelas no banco:", ", ".join(tabs))
print()
total = 0
for t in TABELAS_LAUDOS:
    if t in tabs:
        cur.execute("SELECT COUNT(*) FROM " + t)
        n = cur.fetchone()[0]
        total += n
        print(f"  {t}: {n} registros")
    else:
        print(f"  {t}: (nao existe)")
print(">>> TOTAL LAUDOS:", total)
conn.close()
