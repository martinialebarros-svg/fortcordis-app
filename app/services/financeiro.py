# app/services/financeiro.py
"""Serviços de relatórios e análises financeiras: fluxo de caixa, demonstrativo, lucro realizado, etc."""
import calendar
import sqlite3
from datetime import datetime
from typing import Optional

from app.config import DB_PATH
from fortcordis_modules.database import (
    garantir_tabelas_financeiro_extras,
    get_conn,
    listar_contas_a_pagar,
    listar_financeiro_pendentes,
    listar_movimentos_caixa,
)


def fluxo_caixa_periodo(data_inicio: str, data_fim: str) -> dict:
    """
    Retorna fluxo de caixa no período: total entradas, total saídas, saldo.
    Baseado em movimentos_caixa.
    """
    garantir_tabelas_financeiro_extras()
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT tipo, SUM(valor) as total FROM movimentos_caixa
            WHERE date(data_movimento) >= date(?) AND date(data_movimento) <= date(?)
            GROUP BY tipo
        """, (data_inicio, data_fim))
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()
    entradas = sum(r[1] for r in rows if r[0] == "entrada")
    saidas = sum(r[1] for r in rows if r[0] == "saida")
    return {"entradas": entradas, "saidas": saidas, "saldo": entradas - saidas}


def demonstrativo_mensal(mes: int, ano: int) -> dict:
    """
    Demonstrativo financeiro mensal: receitas (OS pagas + entradas manuais), despesas (contas pagas + saídas),
    totais e lucro realizado do mês.
    """
    garantir_tabelas_financeiro_extras()
    data_inicio = f"{ano}-{mes:02d}-01"
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = f"{ano}-{mes:02d}-{ultimo_dia}"

    conn = get_conn()
    cursor = conn.cursor()

    # Receitas: financeiro pago no mês (data_pagamento) + entradas em movimentos_caixa no mês
    cursor.execute("""
        SELECT COALESCE(SUM(valor_final), 0) FROM financeiro
        WHERE status_pagamento = 'pago' AND date(data_pagamento) >= date(?) AND date(data_pagamento) <= date(?)
    """, (data_inicio, data_fim))
    receitas_os = (cursor.fetchone() or (0,))[0]

    cursor.execute("""
        SELECT COALESCE(SUM(valor), 0) FROM movimentos_caixa
        WHERE tipo = 'entrada' AND date(data_movimento) >= date(?) AND date(data_movimento) <= date(?)
    """, (data_inicio, data_fim))
    receitas_caixa = (cursor.fetchone() or (0,))[0]

    # Despesas: contas a pagar pagas no mês + saídas em movimentos_caixa no mês
    cursor.execute("""
        SELECT COALESCE(SUM(valor), 0) FROM contas_a_pagar
        WHERE status = 'pago' AND date(data_pagamento) >= date(?) AND date(data_pagamento) <= date(?)
    """, (data_inicio, data_fim))
    despesas_contas = (cursor.fetchone() or (0,))[0]

    cursor.execute("""
        SELECT COALESCE(SUM(valor), 0) FROM movimentos_caixa
        WHERE tipo = 'saida' AND date(data_movimento) >= date(?) AND date(data_movimento) <= date(?)
    """, (data_inicio, data_fim))
    despesas_caixa = (cursor.fetchone() or (0,))[0]

    conn.close()

    receitas = float(receitas_os or 0) + float(receitas_caixa or 0)
    despesas = float(despesas_contas or 0) + float(despesas_caixa or 0)
    lucro = receitas - despesas

    return {
        "mes": mes,
        "ano": ano,
        "receitas_os": float(receitas_os or 0),
        "receitas_caixa": float(receitas_caixa or 0),
        "receitas_total": receitas,
        "despesas_contas": float(despesas_contas or 0),
        "despesas_caixa": float(despesas_caixa or 0),
        "despesas_total": despesas,
        "lucro_realizado": lucro,
    }


def lucro_realizado(mes: Optional[int] = None, ano: Optional[int] = None) -> float:
    """
    Retorna o lucro realizado no mês/ano (receitas - despesas no período).
    Se mes/ano não informados, usa mês atual.
    """
    now = datetime.now()
    mes = mes or now.month
    ano = ano or now.year
    d = demonstrativo_mensal(mes, ano)
    return d["lucro_realizado"]


def clientes_em_debito() -> list:
    """
    Retorna lista de clínicas (clientes) em débito: OS pendentes com valor e data.
    Cada item: clinica_id, clinica_nome, total_pendente, qtd_os, lista de OS.
    """
    pendentes = listar_financeiro_pendentes()
    by_clinica = {}
    for p in pendentes:
        cid = p.get("clinica_id")
        cnome = p.get("clinica_nome") or "Clínica"
        if cid not in by_clinica:
            by_clinica[cid] = {"clinica_id": cid, "clinica_nome": cnome, "total_pendente": 0, "qtd_os": 0, "os_list": []}
        v = float(p.get("valor_final") or 0)
        by_clinica[cid]["total_pendente"] += v
        by_clinica[cid]["qtd_os"] += 1
        by_clinica[cid]["os_list"].append({"id": p.get("id"), "numero_os": p.get("numero_os"), "valor": v, "data_competencia": p.get("data_competencia")})
    return list(by_clinica.values())


def creditos_clientes() -> list:
    """
    Retorna lista de clínicas com saldo de crédito > 0 (controle de créditos de clientes).
    """
    garantir_tabelas_financeiro_extras()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(clinicas_parceiras)")
        cols = [r[1].lower() for r in cursor.fetchall()]
        if "saldo_credito" not in cols:
            conn.close()
            return []
        cursor.execute("""
            SELECT id, nome, COALESCE(saldo_credito, 0) as saldo_credito
            FROM clinicas_parceiras WHERE (ativo = 1 OR ativo IS NULL) AND COALESCE(saldo_credito, 0) > 0
            ORDER BY saldo_credito DESC
        """)
        rows = cursor.fetchall()
        out = [dict(r) for r in rows]
    except Exception:
        out = []
    conn.close()
    return out


def consumo_clinicas(data_inicio: str, data_fim: str) -> list:
    """
    Análise de consumo dos clientes (clínicas): por clínica, total faturado e quantidade de OS no período.
    Considera data_competencia da OS (data do serviço).
    """
    garantir_tabelas_financeiro_extras()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT f.clinica_id, c.nome as clinica_nome,
                   COUNT(f.id) as qtd_os,
                   SUM(f.valor_final) as total_faturado
            FROM financeiro f
            JOIN clinicas_parceiras c ON f.clinica_id = c.id
            WHERE date(f.data_competencia) >= date(?) AND date(f.data_competencia) <= date(?)
            GROUP BY f.clinica_id, c.nome
            ORDER BY total_faturado DESC
        """, (data_inicio, data_fim))
        rows = cursor.fetchall()
        out = [dict(r) for r in rows]
    except Exception:
        out = []
    conn.close()
    return out


def desempenho_colaboradores(data_inicio: str, data_fim: str) -> list:
    """
    Análise de desempenho dos colaboradores: por criado_por_id (agendamentos),
    quantidade de agendamentos realizados e valor total das OS geradas a partir deles.
    """
    garantir_tabelas_financeiro_extras()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(agendamentos)")
        cols = [r[1].lower() for r in cursor.fetchall()]
        if "criado_por_id" not in cols:
            conn.close()
            return []
        cursor.execute("PRAGMA table_info(agendamentos)")
        col_names = [r[1] for r in cursor.fetchall()]
        col_data = "data" if "data" in col_names else "data_agendamento"
        cursor.execute(f"""
            SELECT a.criado_por_id, a.criado_por_nome,
                   COUNT(DISTINCT a.id) as qtd_agendamentos,
                   COUNT(f.id) as qtd_os,
                   COALESCE(SUM(f.valor_final), 0) as valor_gerado
            FROM agendamentos a
            LEFT JOIN financeiro f ON f.agendamento_id = a.id
            WHERE date(a.{col_data}) >= date(?) AND date(a.{col_data}) <= date(?)
              AND (a.status = 'Realizado' OR f.id IS NOT NULL)
            GROUP BY a.criado_por_id, a.criado_por_nome
            HAVING a.criado_por_id IS NOT NULL
            ORDER BY valor_gerado DESC
        """, (data_inicio, data_fim))
        rows = cursor.fetchall()
        out = [dict(r) for r in rows]
    except Exception:
        out = []
    conn.close()
    return out
