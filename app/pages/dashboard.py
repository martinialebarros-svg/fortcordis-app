# Tela: Dashboard - resumo do sistema
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from app.components import metricas_linha
from app.config import DB_PATH
from fortcordis_modules.database import listar_agendamentos


def render_dashboard():
    st.title("📊 Dashboard - Fort Cordis")
    st.markdown("### Resumo do Sistema")

    conn = sqlite3.connect(str(DB_PATH))

    hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        agends_hoje = listar_agendamentos(data_inicio=hoje, data_fim=hoje)
        total_hoje = len([a for a in agends_hoje if (a.get("status") or "") != "Cancelado"])
    except Exception:
        total_hoje = 0

    amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        agends_amanha = listar_agendamentos(data_inicio=amanha, data_fim=amanha)
        total_amanha = len([a for a in agends_amanha if (a.get("status") or "") in ("Agendado", "") or a.get("status") is None])
    except Exception:
        total_amanha = 0

    try:
        a_receber = pd.read_sql_query(
            "SELECT SUM(valor_final) as total FROM financeiro WHERE status_pagamento = 'pendente'",
            conn,
        )
        valor_receber = a_receber["total"].iloc[0] if not a_receber.empty and a_receber["total"].iloc[0] else 0
    except Exception:
        valor_receber = 0

    try:
        atrasados = pd.read_sql_query(
            "SELECT COUNT(*) as total FROM acompanhamentos WHERE status = 'atrasado'",
            conn,
        )
        total_atrasados = atrasados["total"].iloc[0] if not atrasados.empty else 0
    except Exception:
        total_atrasados = 0

    conn.close()

    metricas_linha([
        ("Agendamentos Hoje", total_hoje, None),
        ("Pendentes Confirmação", total_amanha, None),
        ("Contas a Receber", f"R$ {valor_receber:,.2f}", None),
        ("Retornos Atrasados", total_atrasados, None),
    ])

    st.markdown("---")
    st.success("✅ Sistema inicializado com sucesso!")
    st.info("""
    ### 🎯 Fluxo integrado:

    1. **Agendamentos:** Crie agendamentos; use **"📲 Confirmar amanhã"** para listar os de amanhã e abrir o link WhatsApp da clínica e confirmar 24h antes.
    2. **Laudos:** Em "🩺 Laudos e Exames" emita o laudo; a OS é criada automaticamente em Financeiro.
    3. **Financeiro:** Veja as OS em **"💳 Contas a Receber"**; quando receber o pagamento, use **"✅ Dar baixa"** para marcar como pago (data e forma) e unificar tudo no sistema.
    4. **Cadastros:** Mantenha clínicas com **WhatsApp** preenchido para o link de confirmação funcionar.
    """)
