# Tela: Dashboard - resumo do sistema
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

from app.components import metricas_linha
from app.config import DB_PATH
from fortcordis_modules.database import listar_agendamentos


def _card_open(title: str, subtitle: str = ""):
    st.markdown('<div class="fc-card">', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard():
    st.title("🏥 Painel da Clínica")
    st.caption("Visão diária operacional: agenda, laudos e financeiro.")

    filtro_periodo = st.session_state.get("ui_filtro_periodo_global", st.session_state.get("filtro_periodo_global", "Hoje"))
    status_selecionados = st.session_state.get(
        "ui_filtro_status_global",
        st.session_state.get("filtro_status_global", ["Agendado", "Confirmado", "Realizado"]),
    )

    conn = sqlite3.connect(str(DB_PATH))
    hoje = datetime.now().strftime("%Y-%m-%d")

    try:
        agenda = listar_agendamentos(data_inicio=hoje, data_fim=hoje)
    except Exception:
        agenda = []

    agenda_validos = [
        a for a in agenda
        if (a.get("status") or "Agendado") in status_selecionados and (a.get("status") or "") != "Cancelado"
    ]

    try:
        laudos_pendentes = pd.read_sql_query(
            """
            SELECT COUNT(*) AS total
            FROM laudos_arquivos
            WHERE COALESCE(pdf_nome, '') = ''
            """,
            conn,
        )["total"].iloc[0]
    except Exception:
        laudos_pendentes = 0

    try:
        valor_receber = pd.read_sql_query(
            "SELECT COALESCE(SUM(valor_final),0) AS total FROM financeiro WHERE status_pagamento = 'pendente'",
            conn,
        )["total"].iloc[0]
    except Exception:
        valor_receber = 0

    try:
        proximos = pd.read_sql_query(
            """
            SELECT data_agendamento, hora_agendamento, nome_animal, tutor_nome, clinica_nome, status
            FROM agendamentos
            WHERE data_agendamento >= date('now')
            ORDER BY data_agendamento, hora_agendamento
            LIMIT 8
            """,
            conn,
        )
    except Exception:
        proximos = pd.DataFrame()

    conn.close()

    _card_open("Indicadores principais", f"Período selecionado: {filtro_periodo}")
    metricas_linha([
        ("Atendimentos do dia", len(agenda_validos), None),
        ("Pendências de laudo", int(laudos_pendentes or 0), None),
        ("Pagamentos pendentes", f"R$ {float(valor_receber or 0):,.2f}", None),
    ])
    _card_close()

    _card_open("Próximos agendamentos", "Fila rápida para secretária/apoio")
    if proximos.empty:
        st.info("Nenhum agendamento futuro encontrado.")
    else:
        proximos = proximos.rename(columns={
            "data_agendamento": "Data",
            "hora_agendamento": "Hora",
            "nome_animal": "Paciente",
            "tutor_nome": "Tutor",
            "clinica_nome": "Clínica",
            "status": "Status",
        })
        if status_selecionados:
            proximos = proximos[proximos["Status"].fillna("Agendado").isin(status_selecionados)]
        st.dataframe(proximos, use_container_width=True, hide_index=True)
    _card_close()

    _card_open("Fluxo recomendado", "Use este trilho para reduzir retrabalho")
    st.markdown(
        """
        1. **Cadastro** → confirmar paciente/tutor/clínica e reaproveitar dados anteriores.
        2. **Exame** → preencher medidas e validar valores fora da curva.
        3. **Interpretação** → usar templates de frases por achado.
        4. **Laudo** → revisar e gerar PDF final.
        5. **Cobrança/OS** → conferir pendências e baixar pagamento.
        """
    )
    _card_close()
