# app/pages/financeiro.py
"""Página Gestão Financeira: contas a receber, dar baixa em pagamentos."""
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from app.config import DB_PATH
from fortcordis_modules.database import (
    dar_baixa_os,
    excluir_os,
    excluir_os_em_lote,
    garantir_colunas_financeiro,
    listar_financeiro_pendentes,
)
from modules.rbac import verificar_permissao


def render_financeiro():
    st.title("💰 Gestão Financeira")

    if not verificar_permissao("financeiro", "ver"):
        st.error("❌ Acesso Negado")
        st.warning("⚠️ Você não tem permissão para acessar o módulo financeiro")
        st.info("💡 Contate o administrador se precisar de acesso")
        st.stop()

    garantir_colunas_financeiro()

    tab_fin_lista, tab_fin_baixa = st.tabs(["💳 Contas a Receber", "✅ Dar baixa (pagamento recebido)"])

    with tab_fin_lista:
        st.markdown("### Todas as OS (últimas 20)")
        conn = sqlite3.connect(str(DB_PATH))
        contas = None
        try:
            contas = pd.read_sql_query("""
                SELECT 
                    f.id, f.numero_os as 'Número OS',
                    c.nome as 'Clínica',
                    f.descricao as 'Descrição',
                    f.valor_final as 'Valor',
                    f.status_pagamento as 'Status',
                    f.data_competencia as 'Data',
                    f.data_pagamento as 'Data pagamento',
                    f.forma_pagamento as 'Forma'
                FROM financeiro f
                LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                ORDER BY f.data_competencia DESC
                LIMIT 20
            """, conn)
            if not contas.empty:
                contas_display = contas.drop(columns=["id"], errors="ignore")
                contas_display["Valor"] = contas_display["Valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                st.dataframe(contas_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma OS gerada ainda. Faça um laudo para gerar a primeira!")
        except sqlite3.OperationalError:
            try:
                contas = pd.read_sql_query("""
                    SELECT f.id, f.id as 'Número OS', c.nome as 'Clínica', f.descricao as 'Descrição',
                           f.valor_final as 'Valor', f.status_pagamento as 'Status',
                           f.data_competencia as 'Data'
                    FROM financeiro f
                    LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                    ORDER BY f.id DESC LIMIT 20
                """, conn)
                if not contas.empty:
                    contas_display = contas.drop(columns=["id"], errors="ignore")
                    if "Valor" in contas_display.columns:
                        contas_display["Valor"] = contas_display["Valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                    st.dataframe(contas_display, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma OS gerada ainda. Faça um laudo para gerar a primeira!")
            except Exception:
                st.info("Nenhuma OS gerada ainda.")
        except Exception:
            st.info("Nenhuma OS gerada ainda.")
        conn.close()

        if contas is not None and not contas.empty:
            st.markdown("---")
            st.markdown("### 🗑️ Excluir ordem de serviço")
            st.caption("Use para remover OS de teste ou cobranças que não devem permanecer. A exclusão é definitiva.")
            opcoes_os = []
            for _, row in contas.iterrows():
                num_os = row.get("Número OS", row.get("id", ""))
                clinica = row.get("Clínica", "") or "—"
                valor = float(row.get("Valor", 0) or 0)
                opcoes_os.append((int(row["id"]), f"{num_os} – {clinica} – R$ {valor:,.2f}"))
            if opcoes_os:
                ids_os = [x[0] for x in opcoes_os]
                labels_os = {x[0]: x[1] for x in opcoes_os}

                st.markdown("**Excluir em lote**")
                os_lote = st.multiselect(
                    "Selecione as OS a excluir (pode escolher várias)",
                    options=ids_os,
                    format_func=lambda x: labels_os.get(x, str(x)),
                    key="excluir_os_lote"
                )
                if os_lote:
                    if st.button("🗑️ Excluir selecionadas", key="btn_excluir_lote", type="secondary"):
                        n = excluir_os_em_lote(os_lote)
                        if n > 0:
                            st.success(f"✅ {n} OS excluída(s).")
                            st.rerun()
                        else:
                            st.error("Não foi possível excluir.")

                st.markdown("**Excluir uma por uma**")
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    os_para_excluir = st.selectbox(
                        "Selecione a OS a excluir",
                        options=ids_os,
                        format_func=lambda x: labels_os.get(x, str(x)),
                        key="excluir_os_sel"
                    )
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Excluir OS", key="btn_excluir_os", type="secondary"):
                        if excluir_os(os_para_excluir):
                            st.success("OS excluída.")
                            st.rerun()
                        else:
                            st.error("Não foi possível excluir.")

    with tab_fin_baixa:
        st.markdown("### Cobranças pendentes – dar baixa quando o pagamento for recebido")
        st.caption("Marque como pago e informe a data e a forma de pagamento. Assim você unifica tudo no sistema e dispensa a planilha.")
        pendentes = listar_financeiro_pendentes()
        if not pendentes:
            st.success("✅ Nenhuma cobrança pendente.")
        else:
            total_pend = sum(float(p.get("valor_final") or 0) for p in pendentes)
            st.metric("Total a receber (pendentes)", f"R$ {total_pend:,.2f}")
            st.markdown("---")
            for p in pendentes:
                with st.expander(f"📄 {p.get('numero_os', '')} – {p.get('clinica_nome', 'Clínica')} – R$ {float(p.get('valor_final') or 0):,.2f}"):
                    st.write(f"**Descrição:** {p.get('descricao', '')}")
                    st.write(f"**Data competência:** {p.get('data_competencia', '')}")
                    with st.form(key=f"form_baixa_{p.get('id')}"):
                        data_pag = st.date_input("Data do pagamento", value=date.today(), key=f"data_pag_{p.get('id')}")
                        forma_pag = st.selectbox(
                            "Forma de pagamento",
                            ["PIX", "Transferência", "Dinheiro", "Cartão (crédito)", "Cartão (débito)", "Outro"],
                            key=f"forma_pag_{p.get('id')}"
                        )
                        if st.form_submit_button("✅ Dar baixa (marcar como pago)"):
                            ok = dar_baixa_os(
                                p["id"],
                                data_pagamento=data_pag.strftime("%Y-%m-%d"),
                                forma_pagamento=forma_pag
                            )
                            if ok:
                                st.success("Baixa registrada!")
                                st.rerun()
                            else:
                                st.warning("Não foi possível dar baixa (talvez já esteja paga).")
