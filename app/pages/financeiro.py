# app/pages/financeiro.py
"""Página Gestão Financeira: contas a receber/pagar, movimentos de caixa, fluxo, demonstrativo, NFS-e, comissões, etc."""
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from app.config import DB_PATH, formatar_data_br
from app.services.financeiro import (
    clientes_em_debito,
    consumo_clinicas,
    creditos_clientes,
    demonstrativo_mensal,
    desempenho_colaboradores,
    fluxo_caixa_periodo,
    lucro_realizado,
)
from fortcordis_modules.database import (
    dar_baixa_conta_pagar,
    dar_baixa_os,
    excluir_os,
    excluir_os_em_lote,
    garantir_colunas_financeiro,
    garantir_tabelas_financeiro_extras,
    inserir_comissao,
    inserir_conciliacao_cartao,
    inserir_conta_pagar,
    inserir_devolucao,
    inserir_movimento_caixa_manual,
    inserir_nfse,
    listar_contas_a_pagar,
    listar_conciliacao_cartoes,
    listar_comissoes,
    listar_devolucoes_venda,
    listar_financeiro_pendentes,
    listar_movimentos_caixa,
    listar_nfse_por_clinica,
    listar_creditos_movimentos,
    registrar_credito_clinica,
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
    garantir_tabelas_financeiro_extras()

    tab_receber, tab_baixa, tab_pagar, tab_caixa, tab_fluxo, tab_debito, tab_creditos, tab_concil, tab_nfse, tab_comiss, tab_pacotes, tab_consumo, tab_devol, tab_limite, tab_desempenho, tab_integ = st.tabs([
        "💳 Contas a Receber",
        "✅ Dar baixa",
        "📤 Contas a Pagar",
        "📒 Movimentos Caixa",
        "📊 Fluxo e Demonstrativo",
        "⚠️ Clientes em Débito",
        "🎫 Créditos Clientes",
        "💳 Conciliação Cartões",
        "📄 NFS-e",
        "👥 Comissões",
        "📦 Pacotes/Kits",
        "📈 Análise Consumo",
        "↩️ Devoluções",
        "🔖 Limite Desconto",
        "🏆 Desempenho",
        "🔗 Integração",
    ])

    # ---- Contas a Receber ----
    with tab_receber:
        st.markdown("### Todas as OS (últimas 20)")
        conn = sqlite3.connect(str(DB_PATH))
        contas = None
        try:
            contas = pd.read_sql_query("""
                SELECT f.id, f.numero_os as 'Número OS', c.nome as 'Clínica', f.descricao as 'Descrição',
                    f.valor_final as 'Valor', f.status_pagamento as 'Status', f.data_competencia as 'Data',
                    f.data_pagamento as 'Data pagamento', f.forma_pagamento as 'Forma'
                FROM financeiro f
                LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                ORDER BY f.data_competencia DESC LIMIT 20
            """, conn)
            if not contas.empty:
                contas_display = contas.drop(columns=["id"], errors="ignore")
                contas_display["Valor"] = contas_display["Valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                for col in ["Data", "Data pagamento"]:
                    if col in contas_display.columns:
                        contas_display[col] = contas_display[col].apply(formatar_data_br)
                st.dataframe(contas_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma OS gerada ainda. Faça um laudo ou marque agendamento como realizado.")
        except Exception:
            st.info("Nenhuma OS gerada ainda.")
        conn.close()

        if contas is not None and not contas.empty and verificar_permissao("financeiro", "editar"):
            st.markdown("---")
            st.markdown("### 🗑️ Excluir ordem de serviço")
            opcoes_os = [(int(row["id"]), f"{row.get('Número OS', row['id'])} – {row.get('Clínica', '—')} – R$ {float(row.get('Valor', 0) or 0):,.2f}") for _, row in contas.iterrows()]
            ids_os = [x[0] for x in opcoes_os]
            labels_os = {x[0]: x[1] for x in opcoes_os}
            os_lote = st.multiselect("Selecione as OS a excluir", options=ids_os, format_func=lambda x: labels_os.get(x, str(x)), key="excluir_os_lote")
            if os_lote and st.button("🗑️ Excluir selecionadas", key="btn_excluir_lote", type="secondary"):
                n = excluir_os_em_lote(os_lote)
                if n > 0:
                    st.success(f"✅ {n} OS excluída(s).")
                    st.rerun()
            os_para_excluir = st.selectbox("Ou selecione uma OS", options=ids_os, format_func=lambda x: labels_os.get(x, str(x)), key="excluir_os_sel")
            if st.button("🗑️ Excluir OS", key="btn_excluir_os", type="secondary"):
                if excluir_os(os_para_excluir):
                    st.success("OS excluída.")
                    st.rerun()

    # ---- Dar baixa ----
    with tab_baixa:
        st.markdown("### Cobranças pendentes – dar baixa quando o pagamento for recebido")
        st.caption("Ao dar baixa, a entrada é registrada automaticamente em Movimentos de Caixa (integração financeira).")
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
                    st.write(f"**Data competência:** {formatar_data_br(p.get('data_competencia', ''))}")
                    with st.form(key=f"form_baixa_{p.get('id')}"):
                        data_pag = st.date_input("Data do pagamento", value=date.today(), key=f"data_pag_{p.get('id')}")
                        forma_pag = st.selectbox("Forma de pagamento", ["PIX", "Transferência", "Dinheiro", "Cartão (crédito)", "Cartão (débito)", "Outro"], key=f"forma_pag_{p.get('id')}")
                        if st.form_submit_button("✅ Dar baixa (marcar como pago)"):
                            if dar_baixa_os(p["id"], data_pagamento=data_pag.strftime("%Y-%m-%d"), forma_pagamento=forma_pag):
                                st.success("Baixa registrada! Entrada lançada no caixa.")
                                st.rerun()
                            else:
                                st.warning("Não foi possível dar baixa (talvez já esteja paga).")

    # ---- Contas a Pagar ----
    with tab_pagar:
        st.markdown("### Contas a Pagar")
        if verificar_permissao("financeiro", "criar"):
            with st.expander("➕ Lançar despesa"):
                with st.form("form_conta_pagar"):
                    desc = st.text_input("Descrição *")
                    valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
                    data_venc = st.date_input("Data vencimento")
                    cat = st.selectbox("Categoria", ["fornecedor", "folha", "insumo", "outro"])
                    fornecedor = st.text_input("Fornecedor")
                    obs = st.text_area("Observações")
                    if st.form_submit_button("Salvar"):
                        if desc:
                            pid = inserir_conta_pagar(desc, valor, data_venc.strftime("%Y-%m-%d"), categoria=cat, fornecedor_nome=fornecedor or None, observacoes=obs or None)
                            if pid:
                                st.success("Despesa lançada.")
                                st.rerun()
                            else:
                                st.error("Erro ao salvar.")
                        else:
                            st.error("Preencha a descrição.")
        pendentes_cp = listar_contas_a_pagar(status="pendente")
        if not pendentes_cp:
            st.info("Nenhuma conta a pagar pendente.")
        else:
            total_cp = sum(float(c.get("valor") or 0) for c in pendentes_cp)
            st.metric("Total a pagar (pendentes)", f"R$ {total_cp:,.2f}")
            for c in pendentes_cp:
                with st.expander(f"{c.get('descricao', '')} – R$ {float(c.get('valor', 0)):,.2f} – Venc: {formatar_data_br(c.get('data_vencimento'))}"):
                    st.write(f"Categoria: {c.get('categoria', '')} | Fornecedor: {c.get('fornecedor_nome', '') or '—'}")
                    with st.form(key=f"baixa_cp_{c.get('id')}"):
                        data_pag = st.date_input("Data pagamento", value=date.today(), key=f"data_cp_{c.get('id')}")
                        forma = st.selectbox("Forma", ["PIX", "Transferência", "Dinheiro", "Cartão", "Outro"], key=f"forma_cp_{c.get('id')}")
                        if st.form_submit_button("✅ Dar baixa"):
                            if dar_baixa_conta_pagar(c["id"], data_pagamento=data_pag.strftime("%Y-%m-%d"), forma_pagamento=forma):
                                st.success("Pago! Saída registrada no caixa.")
                                st.rerun()
        todas_cp = listar_contas_a_pagar()
        if todas_cp:
            df_cp = pd.DataFrame(todas_cp)
            df_cp["valor"] = df_cp["valor"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_cp[["descricao", "valor", "data_vencimento", "status", "categoria"]], use_container_width=True, hide_index=True)

    # ---- Movimentos de Caixa ----
    with tab_caixa:
        st.markdown("### Movimentos de Caixa")
        hoje = date.today()
        d1 = st.date_input("De", value=hoje - timedelta(days=30), key="caixa_de")
        d2 = st.date_input("Até", value=hoje, key="caixa_ate")
        movs = listar_movimentos_caixa(d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d"))
        if movs:
            df_m = pd.DataFrame(movs)
            df_m["valor"] = df_m.apply(lambda r: f"+ R$ {float(r['valor']):,.2f}" if r.get("tipo") == "entrada" else f"- R$ {float(r['valor']):,.2f}", axis=1)
            df_m["data_movimento"] = df_m["data_movimento"].apply(formatar_data_br)
            st.dataframe(df_m[["data_movimento", "tipo", "valor", "forma_pagamento", "descricao", "clinica_nome"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum movimento no período.")
        if verificar_permissao("financeiro", "criar"):
            with st.expander("➕ Lançamento manual (entrada/saída)"):
                with st.form("form_mov_manual"):
                    tipo_m = st.radio("Tipo", ["entrada", "saida"])
                    valor_m = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
                    data_m = st.date_input("Data", value=hoje)
                    forma_m = st.selectbox("Forma", ["PIX", "Transferência", "Dinheiro", "Cartão", "Outro"])
                    desc_m = st.text_input("Descrição")
                    if st.form_submit_button("Registrar"):
                        if inserir_movimento_caixa_manual(tipo_m, valor_m, data_m.strftime("%Y-%m-%d"), desc_m or None, forma_m):
                            st.success("Movimento registrado.")
                            st.rerun()

    # ---- Fluxo e Demonstrativo ----
    with tab_fluxo:
        st.markdown("### Fluxo de Caixa e Demonstrativo Financeiro Mensal")
        hoje = date.today()
        mes_s = st.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1, format_func=lambda x: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][x-1], key="dem_mes")
        ano_s = st.number_input("Ano", value=hoje.year, min_value=2020, max_value=2030, key="dem_ano")
        dem = demonstrativo_mensal(mes_s, ano_s)
        st.metric("Receitas (total)", f"R$ {dem['receitas_total']:,.2f}")
        st.metric("Despesas (total)", f"R$ {dem['despesas_total']:,.2f}")
        lucro = dem["lucro_realizado"]
        st.metric("Lucro Realizado", f"R$ {lucro:,.2f}")
        st.caption("Receitas = OS pagas + entradas em caixa no mês. Despesas = contas pagas + saídas em caixa.")
        st.markdown("---")
        d_ini = f"{ano_s}-{mes_s:02d}-01"
        import calendar
        ultimo = calendar.monthrange(ano_s, mes_s)[1]
        d_fim = f"{ano_s}-{mes_s:02d}-{ultimo}"
        fluxo = fluxo_caixa_periodo(d_ini, d_fim)
        st.markdown("**Fluxo de caixa no mês**")
        st.write(f"Entradas: R$ {fluxo['entradas']:,.2f} | Saídas: R$ {fluxo['saidas']:,.2f} | Saldo: R$ {fluxo['saldo']:,.2f}")

    # ---- Clientes em Débito ----
    with tab_debito:
        st.markdown("### Controle de Clientes em Débito")
        debitos = clientes_em_debito()
        if not debitos:
            st.success("Nenhuma clínica em débito.")
        else:
            for d in debitos:
                st.metric(f"{d['clinica_nome']}", f"R$ {d['total_pendente']:,.2f} ({d['qtd_os']} OS)")
                for os_item in d.get("os_list", [])[:5]:
                    st.caption(f"  {os_item.get('numero_os')} – R$ {os_item.get('valor', 0):,.2f} – {formatar_data_br(os_item.get('data_competencia'))}")
                if len(d.get("os_list", [])) > 5:
                    st.caption("  ...")

    # ---- Créditos de Clientes ----
    with tab_creditos:
        st.markdown("### Controle de Créditos de Clientes (clínicas)")
        creds = creditos_clientes()
        if not creds:
            st.info("Nenhuma clínica com saldo de crédito.")
        else:
            for c in creds:
                st.write(f"**{c.get('nome', '')}** – Crédito: R$ {float(c.get('saldo_credito', 0)):,.2f}")
        st.markdown("---")
        st.caption("Para adicionar crédito/debito ou ajuste: use Cadastros > Clínicas e o campo Saldo de crédito, ou registre movimentos de crédito (em desenvolvimento).")

    # ---- Conciliação Cartões ----
    with tab_concil:
        st.markdown("### Conciliação de Cartões")
        if verificar_permissao("financeiro", "criar"):
            with st.expander("➕ Registrar conciliação"):
                with st.form("form_concil"):
                    data_f = st.date_input("Data fechamento")
                    bandeira = st.text_input("Bandeira", placeholder="Visa, Master, etc.")
                    valor_b = st.number_input("Valor bruto (R$)", min_value=0.0, step=0.01, format="%.2f")
                    taxa = st.number_input("Taxa (%)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
                    obs_c = st.text_area("Observações")
                    if st.form_submit_button("Registrar"):
                        if valor_b > 0:
                            pid = inserir_conciliacao_cartao(data_f.strftime("%Y-%m-%d"), valor_b, bandeira or None, taxa, None, obs_c or None)
                            if pid:
                                st.success("Conciliação registrada. Entrada no caixa com valor líquido.")
                                st.rerun()
        lista_concil = listar_conciliacao_cartoes()
        if lista_concil:
            df_cc = pd.DataFrame(lista_concil)
            df_cc["valor_bruto"] = df_cc["valor_bruto"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_cc[["data_fechamento", "bandeira", "valor_bruto", "taxa_percentual", "valor_liquido"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma conciliação registrada.")

    # ---- NFS-e ----
    with tab_nfse:
        st.markdown("### Armazenamento de NFS-e (vinculado à clínica)")
        st.caption("Você gera a NFS-e externamente. Aqui apenas guardamos o vínculo com a clínica para quem o serviço foi prestado.")
        conn = sqlite3.connect(str(DB_PATH))
        clinicas_nfse = pd.read_sql_query("SELECT id, nome FROM clinicas_parceiras WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome", conn)
        conn.close()
        if clinicas_nfse.empty:
            st.warning("Cadastre clínicas em Cadastros > Clínicas Parceiras.")
        else:
            if verificar_permissao("financeiro", "criar"):
                with st.expander("➕ Registrar NFS-e"):
                    with st.form("form_nfse"):
                        opts_cli = clinicas_nfse["id"].tolist()
                        clinica_id_n = st.selectbox("Clínica", opts_cli, format_func=lambda x: clinicas_nfse.loc[clinicas_nfse["id"] == x, "nome"].iloc[0] if x in opts_cli else str(x))
                        numero_n = st.text_input("Número NFS-e")
                        data_em = st.date_input("Data emissão")
                        valor_n = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
                        desc_n = st.text_input("Descrição")
                        arq = st.file_uploader("Anexar arquivo (PDF/XML)", type=["pdf", "xml"])
                        if st.form_submit_button("Salvar"):
                            caminho = None
                            blob = arq.read() if arq else None
                            if arq:
                                caminho = arq.name
                            if inserir_nfse(int(clinica_id_n), numero_nfse=numero_n or None, arquivo_caminho=caminho, arquivo_blob=blob, data_emissao=data_em.strftime("%Y-%m-%d"), valor=valor_n, descricao=desc_n or None):
                                st.success("NFS-e registrada.")
                                st.rerun()
            lista_nfse = listar_nfse_por_clinica()
            if lista_nfse:
                df_n = pd.DataFrame(lista_nfse)
                df_n["valor"] = df_n["valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                st.dataframe(df_n[["clinica_nome", "numero_nfse", "data_emissao", "valor", "descricao"]], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma NFS-e cadastrada.")

    # ---- Comissões ----
    with tab_comiss:
        st.markdown("### Controle de Comissões")
        if verificar_permissao("financeiro", "criar"):
            with st.expander("➕ Lançar comissão"):
                conn = sqlite3.connect(str(DB_PATH))
                try:
                    usuarios = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome", conn)
                except Exception:
                    usuarios = pd.DataFrame()
                conn.close()
                opts_usu = usuarios["id"].tolist() if not usuarios.empty else []
                if opts_usu:
                    with st.form("form_comiss"):
                        colab_id = st.selectbox("Colaborador", opts_usu, format_func=lambda x: usuarios.loc[usuarios["id"] == x, "nome"].iloc[0] if x in opts_usu else str(x))
                        valor_co = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
                        per_ref = st.text_input("Período (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
                        tipo_co = st.selectbox("Tipo", ["percentual_os", "fixo", "outro"])
                        obs_co = st.text_input("Observações")
                        if st.form_submit_button("Salvar") and colab_id:
                            if inserir_comissao(int(colab_id), valor_co, per_ref, tipo_co, None, None, obs_co or None):
                                st.success("Comissão registrada.")
                                st.rerun()
                else:
                    st.caption("Cadastre usuários em Configurações para lançar comissões.")
        lista_com = listar_comissoes()
        if lista_com:
            df_com = pd.DataFrame(lista_com)
            df_com["valor"] = df_com["valor"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_com[["colaborador_nome", "valor", "periodo_ref", "tipo"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma comissão lançada.")

    # ---- Pacotes e Kits ----
    with tab_pacotes:
        st.markdown("### Controle de Pacotes e Kits")
        conn = sqlite3.connect(str(DB_PATH))
        try:
            pacotes = pd.read_sql_query("SELECT p.id, p.nome, p.valor_promocional, p.descricao FROM pacotes p WHERE (p.ativo = 1 OR p.ativo IS NULL) ORDER BY p.nome", conn)
            if not pacotes.empty:
                pacotes["valor_promocional"] = pacotes["valor_promocional"].apply(lambda x: f"R$ {float(x):,.2f}")
                st.dataframe(pacotes, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum pacote cadastrado. Os pacotes são configurados no banco (tabela pacotes / pacote_servicos).")
        except Exception:
            st.info("Tabela de pacotes não disponível.")
        finally:
            conn.close()

    # ---- Análise Consumo Clínicas ----
    with tab_consumo:
        st.markdown("### Análise de Consumo dos Clientes (clínicas)")
        hoje = date.today()
        c_d1 = st.date_input("De", value=hoje - timedelta(days=90), key="consumo_de")
        c_d2 = st.date_input("Até", value=hoje, key="consumo_ate")
        consumo = consumo_clinicas(c_d1.strftime("%Y-%m-%d"), c_d2.strftime("%Y-%m-%d"))
        if consumo:
            df_c = pd.DataFrame(consumo)
            df_c["total_faturado"] = df_c["total_faturado"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum faturamento no período.")

    # ---- Devoluções ----
    with tab_devol:
        st.markdown("### Devoluções de Venda")
        if verificar_permissao("financeiro", "criar"):
            with st.expander("➕ Registrar devolução"):
                conn = sqlite3.connect(str(DB_PATH))
                try:
                    os_list = pd.read_sql_query("SELECT f.id, f.numero_os, f.descricao, f.valor_final, c.nome FROM financeiro f LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id WHERE f.status_pagamento = 'pago' ORDER BY f.id DESC LIMIT 100", conn)
                except Exception:
                    os_list = pd.DataFrame()
                conn.close()
                opts_os = os_list["id"].tolist() if not os_list.empty else []
                if opts_os:
                    with st.form("form_devol"):
                        os_opt = st.selectbox("OS (paga)", opts_os, format_func=lambda x: f"{os_list.loc[os_list['id']==x, 'numero_os'].iloc[0]} – {os_list.loc[os_list['id']==x, 'nome'].iloc[0]} – R$ {float(os_list.loc[os_list['id']==x, 'valor_final'].iloc[0]):,.2f}" if x in opts_os else str(x))
                        valor_dev = st.number_input("Valor devolvido (R$)", min_value=0.01, step=0.01, format="%.2f")
                        data_dev = st.date_input("Data devolução", value=hoje)
                        motivo_dev = st.text_input("Motivo")
                        if st.form_submit_button("Registrar") and os_opt:
                            if inserir_devolucao(int(os_opt), valor_dev, data_dev.strftime("%Y-%m-%d"), motivo_dev or None):
                                st.success("Devolução registrada. Saída no caixa.")
                                st.rerun()
                else:
                    st.caption("Nenhuma OS paga para registrar devolução.")
        lista_dev = listar_devolucoes_venda()
        if lista_dev:
            df_d = pd.DataFrame(lista_dev)
            df_d["valor_devolvido"] = df_d["valor_devolvido"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_d[["numero_os", "clinica_nome", "valor_devolvido", "data_devolucao", "motivo"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma devolução registrada.")

    # ---- Limite de Desconto ----
    with tab_limite:
        st.markdown("### Limite de Desconto por Clínica")
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(clinicas_parceiras)")
            cols = [r[1] for r in cursor.fetchall()]
            if "limite_desconto_percentual" not in cols:
                st.info("Coluna limite_desconto_percentual será criada ao usar Gestão Financeira estendida.")
            else:
                lim_df = pd.read_sql_query("SELECT id, nome, COALESCE(limite_desconto_percentual, 0) as limite_desconto FROM clinicas_parceiras WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome", conn)
                if not lim_df.empty:
                    st.caption("Defina o percentual máximo de desconto permitido por clínica. Edite em Cadastros > Clínicas (campo Limite desconto %) ou aqui em breve.")
                    lim_df["limite_desconto"] = lim_df["limite_desconto"].apply(lambda x: f"{float(x):.1f}%")
                    st.dataframe(lim_df[["nome", "limite_desconto"]], use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma clínica cadastrada.")
        except Exception:
            st.info("Não foi possível carregar limites.")
        finally:
            conn.close()

    # ---- Desempenho Colaboradores ----
    with tab_desempenho:
        st.markdown("### Análise de Desempenho dos Colaboradores")
        hoje = date.today()
        des_d1 = st.date_input("De", value=hoje - timedelta(days=90), key="des_de")
        des_d2 = st.date_input("Até", value=hoje, key="des_ate")
        desemp = desempenho_colaboradores(des_d1.strftime("%Y-%m-%d"), des_d2.strftime("%Y-%m-%d"))
        if desemp:
            df_des = pd.DataFrame(desemp)
            df_des["valor_gerado"] = df_des["valor_gerado"].apply(lambda x: f"R$ {float(x):,.2f}")
            st.dataframe(df_des, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado de desempenho no período (agendamentos com criado_por preenchido).")

    # ---- Integração Financeira ----
    with tab_integ:
        st.markdown("### Integração Financeira")
        st.info("""
        **Já integrado:**
        - **Receitas:** Todas as entradas de receita são registradas automaticamente ao dar baixa nas OS (pagamentos de consultas, exames e procedimentos). Cada baixa gera entrada em Movimentos de Caixa.
        - **Despesas:** Ao dar baixa em Contas a Pagar, a saída é lançada no caixa.
        - **Relatórios:** Fluxo de caixa, demonstrativo mensal e lucro realizado usam os mesmos dados.

        **Evite erros:** Use sempre Dar baixa para marcar pagamentos; assim o caixa e os relatórios ficam consistentes.
        """)
