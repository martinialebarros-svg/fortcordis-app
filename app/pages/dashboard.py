# Tela: Dashboard - resumo do sistema
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from app.config import DB_PATH
from fortcordis_modules.database import listar_agendamentos


def render_dashboard():
    st.title("📊 Dashboard - Fort Cordis")
    st.markdown("### Resumo do Sistema")

    col1, col2, col3, col4 = st.columns(4)
    conn = sqlite3.connect(str(DB_PATH))

    with col1:
        hoje = datetime.now().strftime("%Y-%m-%d")
        try:
            agends_hoje = listar_agendamentos(data_inicio=hoje, data_fim=hoje)
            total = len([a for a in agends_hoje if (a.get("status") or "") != "Cancelado"])
        except Exception:
            total = 0
        st.metric("Agendamentos Hoje", total)

    with col2:
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            agends_amanha = listar_agendamentos(data_inicio=amanha, data_fim=amanha)
            total = len([a for a in agends_amanha if (a.get("status") or "") in ("Agendado", "") or a.get("status") is None])
        except Exception:
            total = 0
        st.metric("Pendentes Confirmação", total)

    with col3:
        try:
            a_receber = pd.read_sql_query(
                "SELECT SUM(valor_final) as total FROM financeiro WHERE status_pagamento = 'pendente'",
                conn
            )
            valor = a_receber['total'].iloc[0] if not a_receber.empty and a_receber['total'].iloc[0] else 0
        except Exception:
            valor = 0
        st.metric("Contas a Receber", f"R$ {valor:,.2f}")

    with col4:
        try:
            atrasados = pd.read_sql_query(
                "SELECT COUNT(*) as total FROM acompanhamentos WHERE status = 'atrasado'",
                conn
            )
            total = atrasados['total'].iloc[0] if not atrasados.empty else 0
        except Exception:
            total = 0
        st.metric("Retornos Atrasados", total)

    conn.close()

    st.markdown("---")
    st.success("✅ Sistema inicializado com sucesso!")
    st.info("""
    ### 🎯 Fluxo integrado:

    1. **Agendamentos:** Crie agendamentos; use **"📲 Confirmar amanhã"** para listar os de amanhã e abrir o link WhatsApp da clínica e confirmar 24h antes.
    2. **Laudos:** Em "🩺 Laudos e Exames" emita o laudo; a OS é criada automaticamente em Financeiro.
    3. **Financeiro:** Veja as OS em **"💳 Contas a Receber"**; quando receber o pagamento, use **"✅ Dar baixa"** para marcar como pago (data e forma) e unificar tudo no sistema.
    4. **Cadastros:** Mantenha clínicas com **WhatsApp** preenchido para o link de confirmação funcionar.
    """)
