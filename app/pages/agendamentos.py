# Tela: Agendamentos
import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

from app.config import DB_PATH
from fortcordis_modules.database import (
    criar_agendamento,
    listar_agendamentos,
    atualizar_agendamento,
    deletar_agendamento,
    criar_os_ao_marcar_realizado,
)
from fortcordis_modules.integrations import (
    whatsapp_link,
    mensagem_confirmacao_agendamento,
    exportar_agendamento_ics,
)


def _cadastrar_clinica_rapido_agendamentos(nome, endereco=None, telefone=None):
    """Cadastra nova clínica em clinicas_parceiras (mesma tabela de Cadastros). Retorna (clinica_id, None) ou (None, msg_erro)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clinicas_parceiras (nome, endereco, telefone, cidade)
            VALUES (?, ?, ?, 'Fortaleza')
        """, (nome or "", endereco or "", telefone or ""))
        clinica_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return clinica_id, None
    except sqlite3.IntegrityError:
        return None, "Clínica com este nome já existe."
    except Exception as e:
        return None, str(e)


def render_agendamentos():
    st.title("📅 Gestão de Agendamentos")

    tab_novo, tab_lista, tab_calendario, tab_confirmar = st.tabs([
        "➕ Novo Agendamento",
        "📋 Lista de Agendamentos",
        "📅 Calendário",
        "📲 Confirmar amanhã (24h)"
    ])

    with tab_novo:
        st.subheader("Criar Novo Agendamento")
        col1, col2 = st.columns(2)
        with col1:
            data_agend = st.date_input("Data", value=date.today(), key="novo_agend_data")
            hora_agend = st.time_input("Horário", value=datetime.now().time(), key="novo_agend_hora")
            paciente_agend = st.text_input("Paciente", key="novo_agend_paciente")
            tutor_agend = st.text_input("Tutor", key="novo_agend_tutor")
        with col2:
            telefone_agend = st.text_input("Telefone/WhatsApp", key="novo_agend_telefone")
            servico_agend = st.selectbox(
                "Serviço",
                ["Ecocardiograma", "Consulta Cardiológica", "Retorno", "Eletrocardiograma", "Raio-X", "Pressão Arterial", "Outro"],
                key="novo_agend_servico"
            )
            try:
                conn_temp = sqlite3.connect(str(DB_PATH))
                cursor_temp = conn_temp.cursor()
                try:
                    cursor_temp.execute(
                        "SELECT nome FROM clinicas_parceiras WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome"
                    )
                except sqlite3.OperationalError:
                    cursor_temp.execute("SELECT nome FROM clinicas_parceiras ORDER BY nome")
                lista_clinicas = [row[0] for row in cursor_temp.fetchall()]
                conn_temp.close()
                # Opção "Cadastrar nova clínica" no topo; "Digitar manualmente" no final (igual Laudos)
                opcoes_clinica = ["➕ Cadastrar Nova Clínica"] + (lista_clinicas or []) + ["📝 Digitar manualmente"]
                clinica_agend_sel = st.selectbox(
                    "Clínica",
                    options=opcoes_clinica,
                    key="novo_agend_clinica_sel",
                    help="Clínicas cadastradas em Cadastros > Clínicas Parceiras. Use a primeira opção para cadastrar uma nova."
                )
                if clinica_agend_sel == "➕ Cadastrar Nova Clínica":
                    st.info("💡 Cadastrando nova clínica no sistema...")
                    with st.expander("📝 Dados da Nova Clínica", expanded=True):
                        nova_clinica_nome = st.text_input("Nome da Clínica *", key="nova_clinica_nome_agend")
                        nova_clinica_end = st.text_input("Endereço", key="nova_clinica_end_agend")
                        nova_clinica_tel = st.text_input("Telefone", key="nova_clinica_tel_agend")
                        if st.button("✅ Cadastrar Clínica", key="btn_cadastrar_clinica_agend", type="primary"):
                            if nova_clinica_nome:
                                clinica_id, msg = _cadastrar_clinica_rapido_agendamentos(
                                    nova_clinica_nome, nova_clinica_end, nova_clinica_tel
                                )
                                if clinica_id:
                                    st.success(f"✅ Clínica '{nova_clinica_nome}' cadastrada!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                            else:
                                st.error("Nome da clínica é obrigatório.")
                    clinica_agend = None
                elif clinica_agend_sel == "📝 Digitar manualmente":
                    clinica_agend = st.text_input("Digite o nome da clínica", key="novo_agend_clinica_manual")
                else:
                    clinica_agend = clinica_agend_sel
            except Exception:
                clinica_agend = st.text_input(
                    "Clínica (erro ao carregar cadastro)",
                    key="novo_agend_clinica",
                    help="Cadastre clínicas em Cadastros > Clínicas Parceiras para ver o dropdown."
                )
        observacoes_agend = st.text_area("Observações", key="novo_agend_obs", height=100)
        if st.button("✅ Criar Agendamento", type="primary", use_container_width=True):
            if not paciente_agend:
                st.error("O nome do paciente é obrigatório!")
            elif clinica_agend is None or (isinstance(clinica_agend, str) and not clinica_agend.strip()):
                st.error("Selecione uma clínica ou cadastre uma nova antes de criar o agendamento.")
            else:
                try:
                    agend_id = criar_agendamento(
                        data=str(data_agend),
                        hora=str(hora_agend.strftime("%H:%M")),
                        paciente=paciente_agend,
                        tutor=tutor_agend,
                        telefone=telefone_agend,
                        servico=servico_agend,
                        clinica=clinica_agend,
                        observacoes=observacoes_agend,
                        criado_por_id=st.session_state.get("usuario_id"),
                        criado_por_nome=st.session_state.get("usuario_nome", "")
                    )
                    st.success(f"✅ Agendamento #{agend_id} criado com sucesso!")
                    st.balloons()
                    for key in ['novo_agend_paciente', 'novo_agend_tutor', 'novo_agend_telefone', 'novo_agend_clinica', 'novo_agend_obs']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar agendamento: {e}")

    with tab_lista:
        st.subheader("Lista de Agendamentos")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            filtro_data_ini = st.date_input("Data Início", value=date.today(), key="filtro_data_ini")
        with col_f2:
            filtro_data_fim = st.date_input("Data Fim", value=date.today() + timedelta(days=7), key="filtro_data_fim")
        with col_f3:
            filtro_status = st.selectbox(
                "Status",
                ["Todos", "Agendado", "Confirmado", "Realizado", "Cancelado"],
                key="filtro_status"
            )
        with col_f4:
            filtro_clinica = st.text_input("Clínica", key="filtro_clinica")
        agendamentos = listar_agendamentos(
            data_inicio=str(filtro_data_ini) if filtro_data_ini else None,
            data_fim=str(filtro_data_fim) if filtro_data_fim else None,
            status=filtro_status if filtro_status != "Todos" else None,
            clinica=filtro_clinica if filtro_clinica else None
        )
        if not agendamentos:
            st.info("📭 Nenhum agendamento encontrado com os filtros selecionados.")
        else:
            st.write(f"**Total: {len(agendamentos)} agendamento(s)**")
            for agend in agendamentos:
                with st.expander(f"🗓️ {agend['data']} às {agend['hora']} - {agend['paciente']} ({agend['status']})"):
                    col_a1, col_a2 = st.columns([3, 1])
                    with col_a1:
                        st.write(f"**Paciente:** {agend['paciente']}")
                        st.write(f"**Tutor:** {agend['tutor']}")
                        st.write(f"**Telefone:** {agend['telefone']}")
                        st.write(f"**Serviço:** {agend['servico']}")
                        st.write(f"**Clínica:** {agend['clinica']}")
                        if agend.get('observacoes'):
                            st.write(f"**Observações:** {agend['observacoes']}")
                        criado_por = agend.get("criado_por_nome") or agend.get("criado_por_id")
                        criado_em = agend.get("criado_em")
                        if criado_por or criado_em:
                            criado_txt = f"Criado por **{criado_por or '—'}**"
                            if criado_em:
                                try:
                                    dt = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
                                    criado_txt += f" em {dt.strftime('%d/%m/%Y %H:%M')}"
                                except Exception:
                                    criado_txt += f" em {criado_em}"
                            st.caption(criado_txt)
                        if agend.get("confirmado_em"):
                            conf_por = agend.get("confirmado_por_nome") or agend.get("confirmado_por_id") or "—"
                            try:
                                dt = datetime.fromisoformat(agend["confirmado_em"].replace("Z", "+00:00"))
                                conf_em = dt.strftime("%d/%m/%Y %H:%M")
                            except Exception:
                                conf_em = agend["confirmado_em"]
                            st.caption(f"Confirmado por **{conf_por}** em {conf_em}")
                    with col_a2:
                        status_badge = {"Agendado": "🟢", "Confirmado": "📲", "Realizado": "✅", "Cancelado": "❌"}
                        st.write(f"**Status:** {status_badge.get(agend['status'], '⚪')} {agend['status']}")
                    titulo_ics = f"{agend.get('servico', 'Atendimento')} - {agend.get('paciente', '')} ({agend.get('clinica', '')})"
                    desc_ics = f"Paciente: {agend.get('paciente', '')} | Tutor: {agend.get('tutor', '')} | Clínica: {agend.get('clinica', '')}"
                    ics_content = exportar_agendamento_ics(
                        agend.get("data", ""), agend.get("hora", "09:00"), titulo_ics, desc_ics, duracao_minutos=60
                    )
                    st.download_button(
                        "📅 Exportar .ics (Google Agenda)",
                        data=ics_content.encode("utf-8"),
                        file_name=f"agendamento_{agend.get('id', '')}_{agend.get('data', '')}.ics",
                        mime="text/calendar",
                        key=f"ics_agend_{agend['id']}"
                    )
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    with col_btn1:
                        if agend['status'] == 'Agendado':
                            if st.button("📲 Marcar como confirmado", key=f"confirmado_{agend['id']}"):
                                now = datetime.now().isoformat(timespec="seconds")
                                atualizar_agendamento(
                                    agend['id'], status='Confirmado',
                                    confirmado_em=now,
                                    confirmado_por_id=st.session_state.get("usuario_id"),
                                    confirmado_por_nome=st.session_state.get("usuario_nome", "")
                                )
                                st.success("Agendamento marcado como confirmado!")
                                st.rerun()
                    with col_btn2:
                        if agend['status'] in ('Agendado', 'Confirmado'):
                            if st.button("✅ Marcar Realizado", key=f"realizado_{agend['id']}"):
                                numero_os, erro_os = criar_os_ao_marcar_realizado(agend['id'])
                                if erro_os:
                                    st.warning(f"Agendamento marcado como realizado. Pendência financeira não criada: {erro_os}")
                                elif numero_os:
                                    st.success(f"Agendamento marcado como realizado! OS {numero_os} criada em Contas a Receber.")
                                else:
                                    st.success("Agendamento marcado como realizado!")
                                atualizar_agendamento(agend['id'], status='Realizado')
                                st.rerun()
                    with col_btn3:
                        if agend['status'] in ('Agendado', 'Confirmado'):
                            if st.button("❌ Cancelar", key=f"cancelar_{agend['id']}"):
                                atualizar_agendamento(agend['id'], status='Cancelado')
                                st.warning("Agendamento cancelado!")
                                st.rerun()
                    with col_btn4:
                        if st.button("🗑️ Excluir", key=f"excluir_{agend['id']}"):
                            deletar_agendamento(agend['id'])
                            st.success("Agendamento excluído!")
                            st.rerun()

    with tab_calendario:
        st.subheader("📅 Visão de Calendário")
        col_mes1, col_mes2 = st.columns([3, 1])
        with col_mes1:
            mes_sel = st.date_input("Selecione o mês", value=date.today(), key="calendario_mes")
        primeiro_dia = date(mes_sel.year, mes_sel.month, 1)
        if mes_sel.month == 12:
            ultimo_dia = date(mes_sel.year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(mes_sel.year, mes_sel.month + 1, 1) - timedelta(days=1)
        agendamentos_mes = listar_agendamentos(data_inicio=str(primeiro_dia), data_fim=str(ultimo_dia))
        agendamentos_por_dia = {}
        for agend in agendamentos_mes:
            data = agend['data']
            if data not in agendamentos_por_dia:
                agendamentos_por_dia[data] = []
            agendamentos_por_dia[data].append(agend)
        st.markdown("### Resumo do Mês")
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        total_mes = len(agendamentos_mes)
        agendados = len([a for a in agendamentos_mes if a['status'] == 'Agendado'])
        realizados = len([a for a in agendamentos_mes if a['status'] == 'Realizado'])
        cancelados = len([a for a in agendamentos_mes if a['status'] == 'Cancelado'])
        col_stat1.metric("Total", total_mes)
        col_stat2.metric("Agendados", agendados, delta=None)
        col_stat3.metric("Realizados", realizados, delta=None)
        col_stat4.metric("Cancelados", cancelados, delta=None)
        st.markdown("---")
        st.markdown("### Agendamentos do Mês")
        if not agendamentos_por_dia:
            st.info("📭 Nenhum agendamento neste mês.")
        else:
            for data in sorted(agendamentos_por_dia.keys()):
                agends_dia = agendamentos_por_dia[data]
                try:
                    data_obj = datetime.strptime(data, "%Y-%m-%d")
                    data_fmt = data_obj.strftime("%d/%m/%Y - %A")
                except Exception:
                    data_fmt = data
                with st.expander(f"📅 {data_fmt} - {len(agends_dia)} agendamento(s)"):
                    for agend in agends_dia:
                        status_icon = {"Agendado": "🟢", "Confirmado": "📲", "Realizado": "✅", "Cancelado": "❌"}
                        st.write(f"{status_icon.get(agend['status'], '⚪')} **{agend['hora']}** - {agend['paciente']} ({agend['servico']})")

    with tab_confirmar:
        st.subheader("📲 Confirmar agendamentos de amanhã (24h antes)")
        st.caption("Lista de agendamentos para amanhã. Use o link WhatsApp da clínica para confirmar com a parceira.")
        amanha_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        agends_amanha = listar_agendamentos(data_inicio=amanha_str, data_fim=amanha_str, status=None)
        agends_amanha = [a for a in agends_amanha if (a.get("status") or "") in ("Agendado", "") or a.get("status") is None]
        if not agends_amanha:
            st.info("📭 Nenhum agendamento para amanhã que precise de confirmação.")
        else:
            conn_cli = sqlite3.connect(str(DB_PATH))
            cur_cli = conn_cli.cursor()
            cur_cli.execute("SELECT nome, whatsapp, telefone FROM clinicas_parceiras WHERE (ativo = 1 OR ativo IS NULL)")
            clinicas_whatsapp = {row[0]: (row[1] or row[2] or "") for row in cur_cli.fetchall()}
            conn_cli.close()
            for agend in agends_amanha:
                clinica_nome = (agend.get("clinica") or "").strip()
                whatsapp_clinica = (clinicas_whatsapp.get(clinica_nome) or "").strip() if clinica_nome else ""
                msg = mensagem_confirmacao_agendamento(
                    agend.get("data", amanha_str),
                    agend.get("hora", ""),
                    agend.get("paciente", ""),
                    clinica_nome or "Clínica"
                )
                link_wa = whatsapp_link(whatsapp_clinica, msg) if whatsapp_clinica else ""
                with st.expander(f"🟢 {agend.get('hora', '')} – {agend.get('paciente', '')} | {clinica_nome or 'Sem clínica'}"):
                    st.write(f"**Paciente:** {agend.get('paciente', '')}")
                    st.write(f"**Tutor:** {agend.get('tutor', '')}")
                    st.write(f"**Telefone/WhatsApp (tutor):** {agend.get('telefone', '')}")
                    st.write(f"**Serviço:** {agend.get('servico', '')}")
                    st.write(f"**Clínica:** {clinica_nome or '—'}")
                    if link_wa:
                        st.markdown(f"[📲 Abrir WhatsApp (clínica) e enviar confirmação]({link_wa})")
                    else:
                        st.caption("Clínica sem WhatsApp cadastrado. Cadastre em Cadastros > Clínicas Parceiras para gerar o link.")
