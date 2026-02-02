"""
Exporta o backup do Fort Cordis em VÁRIOS ARQUIVOS MENORES para evitar erro
ao carregar no sistema (arquivo único muito grande).

Gera uma pasta com:
  - parte_01_base.db          → clínicas, clínicas parceiras, tutores, pacientes
  - parte_02_laudos_01.db     → base + laudos (ecocardiograma, eletro, pressão) em lotes
  - parte_02_laudos_02.db     → ...
  - parte_03_arquivos_01.db   → laudos_arquivos (JSON/PDF) + imagens em lotes
  - parte_03_arquivos_02.db   → ...

Uso (na pasta do projeto):
  python exportar_backup_partes.py
  python exportar_backup_partes.py --banco "C:\\caminho\\para\\fortcordis.db"
  python exportar_backup_partes.py --pasta saida_backup --laudos 500 --arquivos 50

Importe no sistema na ordem: parte_01_base.db primeiro; depois parte_02_laudos_*.db;
por último parte_03_arquivos_*.db. Não marque "Limpar laudos" após a primeira parte.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PASTA = Path(__file__).resolve().parent

CANDIDATOS_DB = [
    PASTA / "fortcordis.db",
    Path.home() / "FortCordis" / "data" / "fortcordis.db",
    Path.home() / "FortCordis" / "DB" / "fortcordis.db",
]

TABELAS_BASE = ["clinicas", "clinicas_parceiras", "tutores", "pacientes"]
TABELAS_LAUDOS = ["laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"]
TABELA_LAUDOS_ARQUIVOS = "laudos_arquivos"
TABELA_LAUDOS_IMAGENS = "laudos_arquivos_imagens"

# Tamanho dos lotes (ajuste se ainda der erro de tamanho)
LAUDOS_POR_ARQUIVO = 500   # laudos (eco + eletro + pressão) por parte_02
ARQUIVOS_POR_PARTE = 50    # laudos_arquivos (JSON/PDF + imagens) por parte_03


def _contar_registros(cursor, tabelas):
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


def _copiar_tabela(cursor_origem, cursor_destino, tabela, tabelas_existentes, where=None, params=()):
    """Copia uma tabela do origem para o destino. Opcional: WHERE para limitar linhas."""
    if tabela not in tabelas_existentes:
        return 0
    cursor_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
    ddl_row = cursor_origem.fetchone()
    if not ddl_row or not ddl_row[0]:
        return 0
    cursor_destino.execute(f"DROP TABLE IF EXISTS {tabela}")
    cursor_destino.execute(ddl_row[0])
    sel = f"SELECT * FROM {tabela}"
    if where:
        sel += " " + where
    cursor_origem.execute(sel, params)
    rows = cursor_origem.fetchall()
    if not rows:
        return 0
    cursor_origem.execute(f"PRAGMA table_info({tabela})")
    colunas = [c[1] for c in cursor_origem.fetchall()]
    placeholders = ", ".join(["?" for _ in colunas])
    cols_str = ", ".join(colunas)
    for row in rows:
        cursor_destino.execute(
            f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders})",
            list(row),
        )
    return len(rows)


def _exportar_base(conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo):
    """Exporta apenas as tabelas base para parte_01_base.db"""
    arquivo = pasta_saida / f"{prefixo}parte_01_base.db"
    conn_dest = sqlite3.connect(str(arquivo))
    cur_dest = conn_dest.cursor()
    total = 0
    for tabela in TABELAS_BASE:
        n = _copiar_tabela(cursor_origem, cur_dest, tabela, tabelas_existentes)
        total += n
    conn_dest.commit()
    conn_dest.close()
    return arquivo, total


def _exportar_laudos_em_partes(conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo, laudos_por_arquivo):
    """Exporta base + laudos em vários arquivos (cada um com base + um lote de laudos)."""
    arquivos_criados = []
    for tabela in TABELAS_LAUDOS:
        if tabela not in tabelas_existentes:
            continue
        cursor_origem.execute(f"SELECT COUNT(*) FROM {tabela}")
        total = cursor_origem.fetchone()[0]
        if total == 0:
            continue
        offset = 0
        idx = 1
        while offset < total:
            arquivo = pasta_saida / f"{prefixo}parte_02_laudos_{tabela.replace('laudos_', '')}_{idx:02d}.db"
            conn_dest = sqlite3.connect(str(arquivo))
            cur_dest = conn_dest.cursor()
            # 1) Copiar base (para o importador montar map_clinica, map_tutor, map_paciente)
            for t in TABELAS_BASE:
                _copiar_tabela(cursor_origem, cur_dest, t, tabelas_existentes)
            # 2) Copiar lote desta tabela de laudos
            cursor_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
            ddl = cursor_origem.fetchone()
            if ddl and ddl[0]:
                cur_dest.execute(f"DROP TABLE IF EXISTS {tabela}")
                cur_dest.execute(ddl[0])
                cursor_origem.execute(f"PRAGMA table_info({tabela})")
                colunas = [c[1] for c in cursor_origem.fetchall()]
                cols_str = ", ".join(colunas)
                placeholders = ", ".join(["?" for _ in colunas])
                cursor_origem.execute(
                    f"SELECT * FROM {tabela} LIMIT ? OFFSET ?",
                    (laudos_por_arquivo, offset),
                )
                rows = cursor_origem.fetchall()
                for row in rows:
                    cur_dest.execute(
                        f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders})",
                        list(row),
                    )
            conn_dest.commit()
            conn_dest.close()
            arquivos_criados.append((arquivo, len(rows) if rows else 0))
            offset += laudos_por_arquivo
            idx += 1
    return arquivos_criados


def _exportar_laudos_arquivos_em_partes(conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo, arquivos_por_parte):
    """Exporta laudos_arquivos + laudos_arquivos_imagens em vários arquivos (cada um com um lote)."""
    if TABELA_LAUDOS_ARQUIVOS not in tabelas_existentes:
        return []
    cursor_origem.execute(f"SELECT COUNT(*) FROM {TABELA_LAUDOS_ARQUIVOS}")
    total = cursor_origem.fetchone()[0]
    if total == 0:
        return []
    arquivos_criados = []
    offset = 0
    idx = 1
    while offset < total:
        arquivo = pasta_saida / f"{prefixo}parte_03_arquivos_{idx:02d}.db"
        conn_dest = sqlite3.connect(str(arquivo))
        cur_dest = conn_dest.cursor()

        # Buscar IDs dos laudos_arquivos deste lote
        cursor_origem.execute(
            f"SELECT id FROM {TABELA_LAUDOS_ARQUIVOS} ORDER BY id LIMIT ? OFFSET ?",
            (arquivos_por_parte, offset),
        )
        ids_lote = [r[0] for r in cursor_origem.fetchall()]
        if not ids_lote:
            conn_dest.close()
            break

        # DDL laudos_arquivos
        cursor_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (TABELA_LAUDOS_ARQUIVOS,))
        ddl_arq = cursor_origem.fetchone()
        if ddl_arq and ddl_arq[0]:
            cur_dest.execute(f"DROP TABLE IF EXISTS {TABELA_LAUDOS_ARQUIVOS}")
            cur_dest.execute(ddl_arq[0])
        cursor_origem.execute(f"PRAGMA table_info({TABELA_LAUDOS_ARQUIVOS})")
        colunas_arq = [c[1] for c in cursor_origem.fetchall()]
        cols_str = ", ".join(colunas_arq)
        placeholders = ", ".join(["?" for _ in colunas_arq])
        cursor_origem.execute(
            f"SELECT * FROM {TABELA_LAUDOS_ARQUIVOS} WHERE id IN ({','.join('?'*len(ids_lote))})",
            ids_lote,
        )
        for row in cursor_origem.fetchall():
            cur_dest.execute(f"INSERT INTO {TABELA_LAUDOS_ARQUIVOS} ({cols_str}) VALUES ({placeholders})", list(row))
        n_arq = len(ids_lote)

        # laudos_arquivos_imagens cujo laudo_arquivo_id está neste lote
        n_img = 0
        if TABELA_LAUDOS_IMAGENS in tabelas_existentes:
            cursor_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (TABELA_LAUDOS_IMAGENS,))
            ddl_img = cursor_origem.fetchone()
            if ddl_img and ddl_img[0]:
                cur_dest.execute(f"DROP TABLE IF EXISTS {TABELA_LAUDOS_IMAGENS}")
                cur_dest.execute(ddl_img[0])
                cursor_origem.execute(f"PRAGMA table_info({TABELA_LAUDOS_IMAGENS})")
                colunas_img = [c[1] for c in cursor_origem.fetchall()]
                cols_img_str = ", ".join(colunas_img)
                ph_img = ", ".join(["?" for _ in colunas_img])
                cursor_origem.execute(
                    f"SELECT * FROM {TABELA_LAUDOS_IMAGENS} WHERE laudo_arquivo_id IN ({','.join('?'*len(ids_lote))})",
                    ids_lote,
                )
                for row in cursor_origem.fetchall():
                    cur_dest.execute(
                        f"INSERT INTO {TABELA_LAUDOS_IMAGENS} ({cols_img_str}) VALUES ({ph_img})",
                        list(row),
                    )
                    n_img += 1

        conn_dest.commit()
        conn_dest.close()
        arquivos_criados.append((arquivo, n_arq, n_img))
        offset += arquivos_por_parte
        idx += 1
    return arquivos_criados


def exportar_em_partes(db_origem: Path, pasta_saida: Path, laudos_por_arquivo: int, arquivos_por_parte: int):
    if not db_origem.exists():
        return False, f"Banco não encontrado: {db_origem}"

    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    prefixo = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}_"

    try:
        conn_origem = sqlite3.connect(str(db_origem))
        conn_origem.row_factory = sqlite3.Row
        cursor_origem = conn_origem.cursor()

        cursor_origem.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tabelas_existentes = {r[0] for r in cursor_origem.fetchall()}

        contagens = _contar_registros(cursor_origem, TABELAS_BASE + TABELAS_LAUDOS + [TABELA_LAUDOS_ARQUIVOS])
        total_preview = sum(contagens.values())
        if total_preview == 0:
            conn_origem.close()
            return False, "O banco está vazio nas tabelas de exportação."

        print(f"Exportando em partes de: {db_origem}")
        print(f"Pasta de saída: {pasta_saida}")
        for t, n in contagens.items():
            print(f"  - {t}: {n} registro(s)")

        # Parte 1: base
        arq1, n1 = _exportar_base(conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo)
        print(f"  Criado: {arq1.name} ({n1} registros base)")

        # Parte 2: laudos em lotes
        lista_2 = _exportar_laudos_em_partes(
            conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo, laudos_por_arquivo
        )
        for arq, n in lista_2:
            print(f"  Criado: {arq.name} ({n} laudos)")

        # Parte 3: laudos_arquivos + imagens em lotes
        lista_3 = _exportar_laudos_arquivos_em_partes(
            conn_origem, cursor_origem, pasta_saida, tabelas_existentes, prefixo, arquivos_por_parte
        )
        for arq, n_arq, n_img in lista_3:
            print(f"  Criado: {arq.name} ({n_arq} exames, {n_img} imagens)")

        conn_origem.close()

        total_arquivos = 1 + len(lista_2) + len(lista_3)
        return True, (
            f"Exportacao concluida: {total_arquivos} arquivo(s) em {pasta_saida}. "
            f"Importe na ordem: parte_01_base.db, depois parte_02_laudos_*.db, por ultimo parte_03_arquivos_*.db"
        )
    except Exception as e:
        return False, str(e)


def main():
    db_origem = None
    pasta_saida = PASTA / "backup_partes"
    laudos_por_arquivo = LAUDOS_POR_ARQUIVO
    arquivos_por_parte = ARQUIVOS_POR_PARTE
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--banco" and i + 1 < len(sys.argv):
            db_origem = Path(sys.argv[i + 1])
            i += 2
            continue
        if sys.argv[i] == "--pasta" and i + 1 < len(sys.argv):
            pasta_saida = Path(sys.argv[i + 1])
            i += 2
            continue
        if sys.argv[i] == "--laudos" and i + 1 < len(sys.argv):
            laudos_por_arquivo = max(1, int(sys.argv[i + 1]))
            i += 2
            continue
        if sys.argv[i] == "--arquivos" and i + 1 < len(sys.argv):
            arquivos_por_parte = max(1, int(sys.argv[i + 1]))
            i += 2
            continue
        i += 1

    if db_origem is None:
        for candidato in CANDIDATOS_DB:
            if candidato.exists():
                db_origem = candidato
                break
        if db_origem is None:
            print("ERRO: Nenhum banco encontrado.")
            print('Use: python exportar_backup_partes.py --banco "C:\\caminho\\para\\fortcordis.db"')
            sys.exit(1)

    ok, msg = exportar_em_partes(db_origem, pasta_saida, laudos_por_arquivo, arquivos_por_parte)
    if ok:
        print(f"\nOK: {msg}")
        print("\nPróximo passo: em Configurações > Importar dados, envie os arquivos NA ORDEM acima.")
    else:
        print(f"ERRO: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
