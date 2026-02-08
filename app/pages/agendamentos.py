# Tela: Agendamentos
import html as _html_mod
import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

from app.config import DB_PATH, formatar_data_br
from app.services.pacientes import buscar_pacientes_por_termo_livre
from app.db import db_upsert_tutor, db_upsert_paciente
from app.laudos_banco import listar_animais_tutores_de_laudos
from fortcordis_modules.database import (
    criar_agendamento,
    listar_agendamentos,
    atualizar_agendamento,
    deletar_agendamento,
    criar_os_ao_marcar_realizado,
    inserir_financeiro,
)
from fortcordis_modules.integrations import (
    whatsapp_link,
    mensagem_confirmacao_agendamento,
    exportar_agendamento_ics,
)


def _cadastrar_clinica_rapido_agendamentos(nome, endereco=None, telefone=None, tabela_preco_id=None):
    """Cadastra nova clínica em clinicas_parceiras (mesma tabela de Cadastros). Retorna (clinica_id, None) ou (None, msg_erro)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clinicas_parceiras (nome, endereco, telefone, cidade, tabela_preco_id)
            VALUES (?, ?, ?, 'Fortaleza', ?)
        """, (nome or "", endereco or "", telefone or "", tabela_preco_id))
        clinica_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return clinica_id, None
    except sqlite3.IntegrityError:
        return None, "Clínica com este nome já existe."
    except Exception as e:
        return None, str(e)


def _buscar_servicos_disponiveis_agend(conn):
    """Busca todos os serviços ativos disponíveis."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nome, valor_base
        FROM servicos
        WHERE ativo = 1 OR ativo IS NULL
        ORDER BY nome
    """)
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _criar_os_servico_extra(agendamento_id, servico_nome, valor_final):
    """Cria uma OS extra para um serviço adicional."""
    from fortcordis_modules.database import (
        buscar_agendamento_por_id,
        garantir_colunas_financeiro,
        gerar_numero_os,
    )
    garantir_colunas_financeiro()
    agend = buscar_agendamento_por_id(agendamento_id)
    if not agend:
        return None, "Agendamento não encontrado."
    clinica_nome = (agend.get("clinica") or "").strip()
    if not clinica_nome:
        return None, "Agendamento sem clínica informada."

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        # Garantir que a coluna exista
        cursor.execute("PRAGMA table_info(clinicas_parceiras)")
        cols = [r[1] for r in cursor.fetchall()]
        if "tabela_preco_id" not in cols:
            cursor.execute("ALTER TABLE clinicas_parceiras ADD COLUMN tabela_preco_id INTEGER")

        # Verificar ou cadastrar clínica
        cursor.execute(
            "SELECT id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL) LIMIT 1",
            (clinica_nome,),
        )
        row_cli = cursor.fetchone()
        if not row_cli:
            cursor.execute(
                "INSERT INTO clinicas_parceiras (nome, cidade, tabela_preco_id) VALUES (?, 'Fortaleza', 1)",
                (clinica_nome,)
            )
            clinica_id = cursor.lastrowid
        else:
            clinica_id = row_cli[0]

        data_atend = agend.get("data") or agend.get("data_agendamento")
        data_comp = str(data_atend)[:10] if data_atend else datetime.now().strftime("%Y-%m-%d")
        descricao = f"{servico_nome} - {agend.get('paciente', '')}"

        # Verificar duplicata
        cursor.execute("""
            SELECT numero_os FROM financeiro
            WHERE clinica_id = ? AND data_competencia = ? AND descricao = ?
            LIMIT 1
        """, (clinica_id, data_comp, descricao))
        if cursor.fetchone():
            conn.close()
            return None, "already_exists"

        numero_os = gerar_numero_os()
        inserir_financeiro(
            cursor,
            clinica_id=clinica_id,
            numero_os=numero_os,
            descricao=descricao,
            valor_bruto=valor_final,
            valor_desconto=0,
            valor_final=valor_final,
            data_competencia=data_comp,
            agendamento_id=agendamento_id,
        )
        conn.commit()
        conn.close()
        return numero_os, None
    except Exception as e:
        conn.rollback()
        conn.close()
        return None, str(e)


def _criar_os_unica_com_servicos(agendamento_id, servicos_selecionados, servicos_db, tabela_preco_id):
    """Cria uma única OS com o serviço original do agendamento + serviços extras."""
    from fortcordis_modules.database import (
        buscar_agendamento_por_id,
        garantir_colunas_financeiro,
        gerar_numero_os,
    )
    garantir_colunas_financeiro()
    agend = buscar_agendamento_por_id(agendamento_id)
    if not agend:
        return None, "Agendamento não encontrado."
    clinica_nome = (agend.get("clinica") or "").strip()
    if not clinica_nome:
        return None, "Clínica não informada."

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        # Garantir que a coluna exista
        cursor.execute("PRAGMA table_info(clinicas_parceiras)")
        cols = [r[1] for r in cursor.fetchall()]
        if "tabela_preco_id" not in cols:
            cursor.execute("ALTER TABLE clinicas_parceiras ADD COLUMN tabela_preco_id INTEGER")

        # Verificar ou cadastrar clínica
        cursor.execute(
            "SELECT id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL) LIMIT 1",
            (clinica_nome,),
        )
        row_cli = cursor.fetchone()
        if not row_cli:
            cursor.execute(
                "INSERT INTO clinicas_parceiras (nome, cidade, tabela_preco_id) VALUES (?, 'Fortaleza', 1)",
                (clinica_nome,)
            )
            clinica_id = cursor.lastrowid
        else:
            clinica_id = row_cli[0]

        data_atend = agend.get("data") or agend.get("data_agendamento")
        data_comp = str(data_atend)[:10] if data_atend else datetime.now().strftime("%Y-%m-%d")

        # Coletar todos os serviços (original + extras)
        todos_servicos = []
        servicos_formatados = []
        total = 0

        # 1. Adicionar serviço original do agendamento
        servico_original = (agend.get("servico") or "").strip()
        if servico_original:
            # Buscar o serviço no banco
            cursor.execute("SELECT id, valor_base FROM servicos WHERE (ativo = 1 OR ativo IS NULL) AND (nome = ? OR nome LIKE ?) LIMIT 1", (servico_original, f"%{servico_original}%"))
            row_serv = cursor.fetchone()
            if row_serv:
                servico_id, valor_base = row_serv[0], float(row_serv[1] or 0)
                # Buscar valor da tabela de preços
                cursor.execute("SELECT valor FROM servico_preco WHERE servico_id = ? AND tabela_preco_id = ?", (servico_id, tabela_preco_id))
                row_preco = cursor.fetchone()
                valor = float(row_preco[0]) if row_preco else valor_base
                todos_servicos.append((servico_original, valor))

        # 2. Adicionar serviços extras selecionados
        for opt in servicos_selecionados:
            nome_servico = opt.split(" (R$")[0]
            if nome_servico in servicos_db:
                servico_info = servicos_db[nome_servico]
                # Buscar valor da tabela de preços
                cursor.execute("SELECT valor FROM servico_preco WHERE servico_id = ? AND tabela_preco_id = ?", (servico_info["id"], tabela_preco_id))
                row_preco = cursor.fetchone()
                valor = float(row_preco[0]) if row_preco else servico_info["valor_base"]
                todos_servicos.append((nome_servico, valor))

        # Formatar para descrição
        for nome, valor in todos_servicos:
            servicos_formatados.append(f"{nome} (R$ {valor:,.2f})")
            total += valor

        if not servicos_formatados:
            conn.close()
            return None, "Nenhum serviço válido selecionado."

        descricao = f"{agend.get('paciente', '')}: " + " | ".join(servicos_formatados)

        # Verificar se já existe OS para esta descrição
        cursor.execute("""
            SELECT numero_os FROM financeiro
            WHERE clinica_id = ? AND data_competencia = ? AND descricao = ?
            LIMIT 1
        """, (clinica_id, data_comp, descricao))
        if cursor.fetchone():
            conn.close()
            return None, "already_exists"

        numero_os = gerar_numero_os()
        inserir_financeiro(
            cursor,
            clinica_id=clinica_id,
            numero_os=numero_os,
            descricao=descricao,
            valor_bruto=total,
            valor_desconto=0,
            valor_final=total,
            data_competencia=data_comp,
            agendamento_id=agendamento_id,
        )
        conn.commit()
        conn.close()
        return numero_os, None
    except Exception as e:
        conn.rollback()
        conn.close()
        return None, str(e)


def render_agendamentos():
    st.title("📅 Gestão de Agendamentos")

    # Inicializa states para modal de serviços extras (com .get() para evitar KeyError)
    st.session_state.setdefault("modal_servicos_realizado_open", False)
    st.session_state.setdefault("servicos_extras_selecionados", [])
    st.session_state.setdefault("agendamento_id_pendente_realizado", None)

    tab_novo, tab_lista, tab_calendario, tab_confirmar = st.tabs([
        "➕ Novo Agendamento",
        "📋 Lista de Agendamentos",
        "📅 Calendário",
        "📲 Confirmar amanhã (24h)"
    ])

    # ========== MODAL DE SERVIÇOS EXTRAS ==========
    if st.session_state.get("modal_servicos_realizado_open", False):
        agend_id = st.session_state.get("agendamento_id_pendente_realizado")
        agend = None
        clinica_nome = ""
        clinica_id = None
        tabela_preco_id = 1
        servicos_disponiveis = []

        # Buscar dados do agendamento
        if agend_id:
            from fortcordis_modules.database import buscar_agendamento_por_id
            agend = buscar_agendamento_por_id(agend_id)
            clinica_nome = (agend.get("clinica") or "").strip()

            if clinica_nome:
                try:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, tabela_preco_id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL) LIMIT 1",
                        (clinica_nome,)
                    )
                    row_cli = cursor.fetchone()
                    if row_cli:
                        clinica_id, tabela_preco_id = row_cli[0], row_cli[1] or 1
                    servicos_disponiveis = _buscar_servicos_disponiveis_agend(conn)
                    conn.close()
                except Exception as e:
                    st.error(f"Erro ao carregar serviços: {e}")

        with st.form("modal_servicos_realizado"):
            st.subheader("📋 Adicionar Serviços Extras à OS")
            st.info(f"Agendamento #{agend_id} - Clínica: **{clinica_nome}**")

            if servicos_disponiveis:
                st.caption(f"Tabela de preços ID: {tabela_preco_id}")

                # Criar opções para multiselect
                opcoes_servicos = {
                    f"{s['nome']} (R$ {s['valor_base']:,.2f})": s
                    for s in servicos_disponiveis
                }

                servicos_selecionados = st.multiselect(
                    "Selecione serviços adicionais para incluir na OS:",
                    options=list(opcoes_servicos.keys()),
                    key="ms_servicos_realizado"
                )

                # Mostrar preview dos valores
                if servicos_selecionados:
                    st.markdown("**Preview dos valores:**")
                    total = 0
                    for opt in servicos_selecionados:
                        s = opcoes_servicos[opt]
                        total += s["valor_base"]
                        st.text(f"  • {s['nome']}: R$ {s['valor_base']:,.2f}")
                    st.markdown(f"**Total: R$ {total:,.2f}**")
            else:
                st.warning("Nenhum serviço disponível.")
                servicos_selecionados = []

            col1, col2 = st.columns(2)
            with col1:
                submit_confirmar = st.form_submit_button("✅ Confirmar", type="primary")
            with col2:
                submit_cancelar = st.form_submit_button("❌ Cancelar")

            if submit_confirmar:
                st.session_state["servicos_extras_selecionados"] = servicos_selecionados
                st.session_state["modal_servicos_realizado_open"] = False
                st.rerun()

            if submit_cancelar:
                st.session_state["modal_servicos_realizado_open"] = False
                st.session_state["agendamento_id_pendente_realizado"] = None
                st.session_state["servicos_extras_selecionados"] = []
                st.rerun()

    # ========== FIM MODAL ==========

    with tab_novo:
        st.subheader("Criar Novo Agendamento")

        # Vincular a paciente já cadastrado ou com exame no sistema (evita duplicar ao remarcar)
        with st.expander("🔗 Vincular a paciente já cadastrado ou com exame no sistema", expanded=False):
            st.caption("Busque por nome do animal ou do tutor para preencher Paciente, Tutor e Telefone com um cadastro existente ou com um animal que já tenha laudo.")
            busca_vinculo = st.text_input("Buscar (animal ou tutor)", key="agend_vinculo_busca", placeholder="Ex.: Bolota ou Francisco")
            lista_vinculo = []
            if busca_vinculo and str(busca_vinculo).strip():
                cadastro = buscar_pacientes_por_termo_livre(termo=busca_vinculo.strip(), limite=15)
                laudos = listar_animais_tutores_de_laudos(termo=busca_vinculo.strip(), limite=15)
                cadastro_keys = {(c["paciente"].strip().lower(), c["tutor"].strip().lower()) for c in cadastro}
                for c in cadastro:
                    lista_vinculo.append({
                        "id": c.get("id"),
                        "paciente": c["paciente"],
                        "tutor": c["tutor"],
                        "telefone": c.get("telefone") or "",
                        "rotulo": f"{c['paciente']} — {c['tutor']} (cadastro)",
                    })
                for L in laudos:
                    pa, tu = (L.get("paciente") or "").strip(), (L.get("tutor") or "").strip()
                    if (pa.lower(), tu.lower()) not in cadastro_keys:
                        lista_vinculo.append({
                            "paciente": pa,
                            "tutor": tu,
                            "telefone": "",
                            "rotulo": f"{pa or '?'} — {tu or '?'} (exame no sistema)",
                        })
            if lista_vinculo:
                opcoes_rotulos = ["— Selecione para preencher —"] + [x["rotulo"] for x in lista_vinculo]
                sel_rotulo = st.selectbox(
                    "Selecione o paciente para preencher os campos abaixo",
                    options=opcoes_rotulos,
                    key="agend_vinculo_sel",
                )
                if sel_rotulo and sel_rotulo != "— Selecione para preencher —":
                    idx = opcoes_rotulos.index(sel_rotulo) - 1
                    if 0 <= idx < len(lista_vinculo):
                        rec = lista_vinculo[idx]
                        st.session_state["novo_agend_paciente"] = rec["paciente"]
                        st.session_state["novo_agend_tutor"] = rec["tutor"]
                        st.session_state["novo_agend_telefone"] = rec.get("telefone") or ""
                        st.session_state["novo_agend_paciente_id"] = rec.get("id")
                        st.success(f"Preenchido: **{rec['paciente']}** — **{rec['tutor']}**")
            elif busca_vinculo and str(busca_vinculo).strip():
                st.info("Nenhum paciente ou laudo encontrado com esse termo. Cadastre o paciente nos campos abaixo.")

        col1, col2 = st.columns(2)
        with col1:
            _default_data = date.today().strftime("%d/%m/%Y")
            data_str = st.text_input("Data", value=_default_data, placeholder="dd/mm/aaaa", key="novo_agend_data", help="Formato: dia/mês/ano (ex.: 04/02/2026)")
            try:
                data_agend = datetime.strptime(data_str.strip(), "%d/%m/%Y").date() if data_str and data_str.strip() else date.today()
            except ValueError:
                data_agend = date.today()
                if data_str and data_str.strip():
                    st.error("Data inválida. Use o formato dd/mm/aaaa (ex.: 04/02/2026).")
            hora_agend = st.time_input("Horário", value=datetime.now().time(), key="novo_agend_hora")
            paciente_agend = st.text_input("Paciente", key="novo_agend_paciente", help="Ou use o bloco acima para vincular a um paciente já cadastrado ou com exame.")
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
                # Botão "Cadastrar nova clínica" sempre visível no topo (fora do dropdown)
                with st.expander("➕ Cadastrar Nova Clínica", expanded=False):
                    st.caption("Não encontrou a clínica na lista? Cadastre aqui.")
                    nova_clinica_nome = st.text_input("Nome da Clínica *", key="nova_clinica_nome_agend")
                    nova_clinica_end = st.text_input("Endereço", key="nova_clinica_end_agend")
                    nova_clinica_tel = st.text_input("Telefone", key="nova_clinica_tel_agend")
                    # Seleção de tabela de preços
                    try:
                        cursor_temp.execute("SELECT id, nome FROM tabelas_preco ORDER BY id")
                        tabelas_list = cursor_temp.fetchall()
                        tabelas_opcoes = {f"ID {t[0]}: {t[1]}": t[0] for t in tabelas_list}
                        tabela_selecionada = st.selectbox(
                            "Tabela de Preços",
                            options=list(tabelas_opcoes.keys()),
                            index=0,
                            key="nova_clinica_tabela_preco",
                            help="Define os valores padrão para agendamentos nesta clínica"
                        )
                        nova_clinica_tabela_id = tabelas_opcoes.get(tabela_selecionada, 1)
                    except Exception:
                        nova_clinica_tabela_id = 1
                    if st.button("✅ Cadastrar Clínica", key="btn_cadastrar_clinica_agend", type="primary"):
                        if nova_clinica_nome:
                            clinica_id, msg = _cadastrar_clinica_rapido_agendamentos(
                                nova_clinica_nome, nova_clinica_end, nova_clinica_tel, nova_clinica_tabela_id
                            )
                            if clinica_id:
                                st.success(f"✅ Clínica '{nova_clinica_nome}' cadastrada!")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                        else:
                            st.error("Nome da clínica é obrigatório.")
                conn_temp.close()
                # Dropdown: só clínicas cadastradas + digitar manualmente
                opcoes_clinica = (lista_clinicas or []) + ["📝 Digitar manualmente"]
                clinica_agend_sel = st.selectbox(
                    "Clínica",
                    options=opcoes_clinica,
                    key="novo_agend_clinica_sel",
                    help="Clínicas cadastradas. Use o bloco acima para cadastrar uma nova."
                )
                if clinica_agend_sel == "📝 Digitar manualmente":
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
                    # Resolver paciente_id: da seleção vinculada, busca por nome, ou auto-cadastro
                    paciente_id = st.session_state.get("novo_agend_paciente_id")
                    if not paciente_id:
                        # Tentar encontrar paciente cadastrado pelo nome
                        resultados = buscar_pacientes_por_termo_livre(termo=paciente_agend.strip(), limite=5)
                        for r in resultados:
                            if r["paciente"].strip().lower() == paciente_agend.strip().lower():
                                paciente_id = r["id"]
                                break
                    if not paciente_id:
                        # Auto-cadastrar tutor e paciente para não bloquear o agendamento
                        tutor_nome = tutor_agend.strip() if tutor_agend and tutor_agend.strip() else paciente_agend.strip()
                        tutor_id = db_upsert_tutor(nome=tutor_nome, telefone=telefone_agend or None)
                        if tutor_id:
                            paciente_id = db_upsert_paciente(tutor_id=tutor_id, nome=paciente_agend.strip())
                    if not paciente_id:
                        st.error("Não foi possível vincular ou cadastrar o paciente. Verifique os dados informados.")
                        st.stop()
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
                        criado_por_nome=st.session_state.get("usuario_nome", ""),
                        paciente_id=paciente_id,
                    )
                    st.success(f"✅ Agendamento #{agend_id} criado com sucesso!")
                    st.balloons()
                    for key in ['novo_agend_paciente', 'novo_agend_tutor', 'novo_agend_telefone', 'novo_agend_clinica', 'novo_agend_obs', 'novo_agend_data', 'novo_agend_paciente_id']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar agendamento: {e}")

    with tab_lista:
        st.subheader("Lista de Agendamentos")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            _ini_default = date.today().strftime("%d/%m/%Y")
            filtro_ini_str = st.text_input("Data Início", value=_ini_default, placeholder="dd/mm/aaaa", key="filtro_data_ini")
            try:
                filtro_data_ini = datetime.strptime(filtro_ini_str.strip(), "%d/%m/%Y").date() if filtro_ini_str and filtro_ini_str.strip() else date.today()
            except ValueError:
                filtro_data_ini = date.today()
        with col_f2:
            _fim_default = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
            filtro_fim_str = st.text_input("Data Fim", value=_fim_default, placeholder="dd/mm/aaaa", key="filtro_data_fim")
            try:
                filtro_data_fim = datetime.strptime(filtro_fim_str.strip(), "%d/%m/%Y").date() if filtro_fim_str and filtro_fim_str.strip() else date.today() + timedelta(days=7)
            except ValueError:
                filtro_data_fim = date.today() + timedelta(days=7)
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
                with st.expander(f"🗓️ {formatar_data_br(agend.get('data', ''))} às {agend['hora']} - {agend['paciente']} ({agend['status']})"):
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
                            with st.form(f"form_realizado_{agend['id']}"):
                                col_b1, col_b2 = st.columns([1, 2])
                                with col_b1:
                                    btn_realizado = st.form_submit_button("✅ Marcar Realizado", type="primary")
                                with col_b2:
                                    chk_servicos_extras = st.checkbox(
                                        "Adicionar mais serviços?",
                                        key=f"chk_servicos_extras_{agend['id']}"
                                    )

                                if btn_realizado:
                                    if chk_servicos_extras:
                                        # Abrir modal de seleção de serviços
                                        st.session_state["modal_servicos_realizado_open"] = True
                                        st.session_state["agendamento_id_pendente_realizado"] = agend['id']
                                        st.session_state["servicos_extras_selecionados"] = []
                                        st.rerun()
                                    else:
                                        # Criar OS normalmente (comportamento original)
                                        numero_os, erro_os = criar_os_ao_marcar_realizado(agend['id'])
                                        if erro_os == "already_exists" and numero_os:
                                            st.info(f"Agendamento marcado como realizado. OS {numero_os} já existia (laudo ou anterior); não foi criada duplicata.")
                                        elif erro_os:
                                            st.warning(f"Agendamento marcado como realizado. Pendência financeira não criada: {erro_os}")
                                        elif numero_os:
                                            st.success(f"Agendamento marcado como realizado! OS {numero_os} criada em Contas a Receber.")
                                        else:
                                            st.success("Agendamento marcado como realizado!")
                                        atualizar_agendamento(agend['id'], status='Realizado')
                                        st.rerun()

                            # Processar serviços extras após confirmar no modal
                            if st.session_state.get("agendamento_id_pendente_realizado") == agend['id']:
                                servicos_extras = st.session_state.get("servicos_extras_selecionados", [])
                                if servicos_extras:
                                    # Buscar dados dos serviços
                                    conn = sqlite3.connect(str(DB_PATH))
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT id, nome, valor_base FROM servicos WHERE ativo = 1 OR ativo IS NULL")
                                    servicos_db = {row[1]: {"id": row[0], "valor_base": row[2]} for row in cursor.fetchall()}
                                    cursor.execute("SELECT id, tabela_preco_id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL)", (agend.get("clinica"),))
                                    row_cli = cursor.fetchone()
                                    tabela_preco_id = row_cli[1] if row_cli else 1
                                    conn.close()

                                    # Criar uma única OS com todos os serviços
                                    numero_os, erro = _criar_os_unica_com_servicos(
                                        agend['id'], servicos_extras, servicos_db, tabela_preco_id
                                    )
                                    if erro == "already_exists":
                                        st.info("OS com esses serviços já existe.")
                                    elif erro:
                                        st.warning(f"Erro ao criar OS: {erro}")
                                    else:
                                        st.success(f"💰 OS {numero_os} criada com {len(servicos_extras)} serviço(s)!")

                                    # Limpar states e marcar como realizado
                                    st.session_state["agendamento_id_pendente_realizado"] = None
                                    st.session_state["servicos_extras_selecionados"] = []
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
        _esc = _html_mod.escape
        _MESES_PT = [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        _DIAS_SEM = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        _DIAS_SEM_FULL = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        _STATUS_COR = {
            "Agendado":   ("#e8f5e9", "#2e7d32", "#4caf50"),
            "Confirmado": ("#e3f2fd", "#1565c0", "#2196f3"),
            "Realizado":  ("#f3e5f5", "#6a1b9a", "#9c27b0"),
            "Cancelado":  ("#fbe9e7", "#c62828", "#f44336"),
        }
        _STATUS_ICON = {"Agendado": "🟢", "Confirmado": "📲", "Realizado": "✅", "Cancelado": "❌"}

        def _ev_html(agend, compact=True):
            bg, fg, brd = _STATUS_COR.get(agend.get("status", ""), ("#f5f5f5", "#333", "#999"))
            hora = _esc(agend.get("hora", ""))
            pac = _esc(agend.get("paciente", ""))
            srv = _esc(agend.get("servico", ""))
            cli = _esc(agend.get("clinica", ""))
            td = "text-decoration:line-through;" if agend.get("status") == "Cancelado" else ""
            if compact:
                return (
                    f'<div style="font-size:11px;padding:2px 4px;margin:1px 0;border-radius:3px;'
                    f'background:{bg};color:{fg};border-left:3px solid {brd};'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{td}"'
                    f' title="{hora} - {pac} ({srv})">'
                    f'<b>{hora}</b> {pac}</div>'
                )
            return (
                f'<div style="font-size:13px;padding:4px 8px;margin:2px 0;border-radius:4px;'
                f'background:{bg};color:{fg};border-left:4px solid {brd};{td}">'
                f'<b>{hora}</b> — {pac}'
                f'<br><span style="font-size:11px;opacity:0.8">{srv} | {cli}</span></div>'
            )

        # --- Estado de navegação ---
        if "cal_ref_date" not in st.session_state:
            st.session_state["cal_ref_date"] = date.today()

        modo_cal = st.radio("Exibição", ["Mês", "Semana", "Dia"], horizontal=True, key="cal_modo")

        c_prev, c_label, c_next, c_today = st.columns([1, 6, 1, 1])
        with c_prev:
            if st.button("◀", key="cal_prev", use_container_width=True):
                r = st.session_state["cal_ref_date"]
                if modo_cal == "Mês":
                    st.session_state["cal_ref_date"] = (r.replace(day=1) - timedelta(days=1)).replace(day=1)
                elif modo_cal == "Semana":
                    st.session_state["cal_ref_date"] = r - timedelta(days=7)
                else:
                    st.session_state["cal_ref_date"] = r - timedelta(days=1)
                st.rerun()
        with c_next:
            if st.button("▶", key="cal_next", use_container_width=True):
                r = st.session_state["cal_ref_date"]
                if modo_cal == "Mês":
                    if r.month == 12:
                        st.session_state["cal_ref_date"] = date(r.year + 1, 1, 1)
                    else:
                        st.session_state["cal_ref_date"] = date(r.year, r.month + 1, 1)
                elif modo_cal == "Semana":
                    st.session_state["cal_ref_date"] = r + timedelta(days=7)
                else:
                    st.session_state["cal_ref_date"] = r + timedelta(days=1)
                st.rerun()
        with c_today:
            if st.button("Hoje", key="cal_today", use_container_width=True):
                st.session_state["cal_ref_date"] = date.today()
                st.rerun()

        ref = st.session_state["cal_ref_date"]

        # --- Período e label ---
        if modo_cal == "Mês":
            label_periodo = f"{_MESES_PT[ref.month]} {ref.year}"
            primeiro_dia = date(ref.year, ref.month, 1)
            ultimo_dia = (date(ref.year + (ref.month // 12), ref.month % 12 + 1, 1) - timedelta(days=1))
            grid_start = primeiro_dia - timedelta(days=primeiro_dia.weekday())
            grid_end = ultimo_dia + timedelta(days=(6 - ultimo_dia.weekday()))
            data_ini_query, data_fim_query = grid_start, grid_end
        elif modo_cal == "Semana":
            seg = ref - timedelta(days=ref.weekday())
            dom = seg + timedelta(days=6)
            label_periodo = f"{seg.strftime('%d/%m')} — {dom.strftime('%d/%m/%Y')}"
            data_ini_query, data_fim_query = seg, dom
        else:
            label_periodo = f"{ref.strftime('%d/%m/%Y')} — {_DIAS_SEM_FULL[ref.weekday()]}"
            data_ini_query, data_fim_query = ref, ref

        with c_label:
            st.markdown(f"### {label_periodo}")

        # --- Buscar agendamentos do período ---
        agendamentos_periodo = listar_agendamentos(
            data_inicio=str(data_ini_query), data_fim=str(data_fim_query),
        )
        agend_por_dia = {}
        for a in agendamentos_periodo:
            agend_por_dia.setdefault(a["data"], []).append(a)
        for d in agend_por_dia:
            agend_por_dia[d].sort(key=lambda x: x.get("hora", ""))

        # --- Métricas resumo ---
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Total", len(agendamentos_periodo))
        mc2.metric("🟢 Agendados", sum(1 for a in agendamentos_periodo if a["status"] == "Agendado"))
        mc3.metric("📲 Confirmados", sum(1 for a in agendamentos_periodo if a["status"] == "Confirmado"))
        mc4.metric("✅ Realizados", sum(1 for a in agendamentos_periodo if a["status"] == "Realizado"))
        mc5.metric("❌ Cancelados", sum(1 for a in agendamentos_periodo if a["status"] == "Cancelado"))

        st.markdown("---")

        # ===================== VISÃO MÊS =====================
        if modo_cal == "Mês":
            today_str = date.today().isoformat()
            n_weeks = ((grid_end - grid_start).days + 1) // 7

            html_parts = [
                '<style>',
                '.fcal{width:100%;border-collapse:collapse;table-layout:fixed}',
                '.fcal th{background:#1a73e8;color:#fff;padding:6px 4px;text-align:center;font-size:13px}',
                '.fcal td{border:1px solid #dadce0;height:105px;vertical-align:top;padding:3px 4px;overflow:hidden}',
                '.fcal .td-today{background:#fff8e1}',
                '.fcal .td-other{background:#f8f9fa}',
                '.fcal .td-other .dn{color:#bbb}',
                '.fcal .dn{font-weight:700;font-size:14px;margin-bottom:2px;color:#333}',
                '.fcal .dn-today{background:#1a73e8;color:#fff;border-radius:50%;display:inline-block;width:24px;height:24px;text-align:center;line-height:24px}',
                '.fcal .more{font-size:10px;color:#1a73e8;font-weight:500;cursor:default}',
                '</style>',
                '<table class="fcal"><thead><tr>',
            ]
            for ds in _DIAS_SEM:
                html_parts.append(f'<th>{ds}</th>')
            html_parts.append('</tr></thead><tbody>')

            cur_day = grid_start
            for _ in range(n_weeks):
                html_parts.append('<tr>')
                for __ in range(7):
                    d_str = cur_day.isoformat()
                    is_today = d_str == today_str
                    is_other = cur_day.month != ref.month
                    cls_list = []
                    if is_today:
                        cls_list.append("td-today")
                    if is_other:
                        cls_list.append("td-other")
                    cls_attr = f' class="{" ".join(cls_list)}"' if cls_list else ""
                    html_parts.append(f'<td{cls_attr}>')
                    if is_today:
                        html_parts.append(f'<div class="dn"><span class="dn-today">{cur_day.day}</span></div>')
                    else:
                        html_parts.append(f'<div class="dn">{cur_day.day}</div>')
                    evts = agend_por_dia.get(d_str, [])
                    max_show = 3
                    for ev in evts[:max_show]:
                        html_parts.append(_ev_html(ev, compact=True))
                    if len(evts) > max_show:
                        html_parts.append(f'<div class="more">+{len(evts) - max_show} mais</div>')
                    html_parts.append('</td>')
                    cur_day += timedelta(days=1)
                html_parts.append('</tr>')
            html_parts.append('</tbody></table>')
            st.markdown("".join(html_parts), unsafe_allow_html=True)

            # Detalhe do dia selecionado
            st.markdown("---")
            dia_det = st.date_input(
                "Ver detalhes do dia",
                value=ref,
                key="cal_dia_detalhe",
            )
            dia_str = dia_det.isoformat()
            evts_det = agend_por_dia.get(dia_str, [])
            if evts_det:
                st.markdown(f"**{len(evts_det)} agendamento(s) em {dia_det.strftime('%d/%m/%Y')}:**")
                for a in evts_det:
                    ico = _STATUS_ICON.get(a["status"], "⚪")
                    st.write(
                        f'{ico} **{a["hora"]}** — {a["paciente"]} | {a["servico"]} | '
                        f'{a.get("clinica", "")} | Tutor: {a.get("tutor", "")}'
                    )
            else:
                st.caption(f"Nenhum agendamento em {dia_det.strftime('%d/%m/%Y')}.")

        # ===================== VISÃO SEMANA =====================
        elif modo_cal == "Semana":
            seg = ref - timedelta(days=ref.weekday())
            today_str = date.today().isoformat()
            html_parts = [
                '<style>',
                '.fweek{width:100%;border-collapse:collapse;table-layout:fixed}',
                '.fweek th{background:#1a73e8;color:#fff;padding:8px 4px;text-align:center;font-size:12px}',
                '.fweek th.wk-today{background:#ffd600;color:#333}',
                '.fweek td{border:1px solid #dadce0;vertical-align:top;padding:4px;height:420px;overflow-y:auto}',
                '.fweek td.wk-today{background:#fff8e1}',
                '.fweek .wk-empty{color:#bbb;text-align:center;padding-top:30px;font-size:11px}',
                '</style>',
                '<table class="fweek"><thead><tr>',
            ]
            for i in range(7):
                d = seg + timedelta(days=i)
                is_today = d.isoformat() == today_str
                cls = ' class="wk-today"' if is_today else ""
                html_parts.append(f'<th{cls}>{_DIAS_SEM[i]}<br><b>{d.day}</b>/{d.month:02d}</th>')
            html_parts.append('</tr></thead><tbody><tr>')
            for i in range(7):
                d = seg + timedelta(days=i)
                d_str = d.isoformat()
                is_today = d_str == today_str
                cls = ' class="wk-today"' if is_today else ""
                evts = agend_por_dia.get(d_str, [])
                html_parts.append(f'<td{cls}>')
                if not evts:
                    html_parts.append('<div class="wk-empty">—</div>')
                else:
                    for ev in evts:
                        html_parts.append(_ev_html(ev, compact=False))
                html_parts.append('</td>')
            html_parts.append('</tr></tbody></table>')
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        # ===================== VISÃO DIA =====================
        else:
            d_str = ref.isoformat()
            today_str = date.today().isoformat()
            evts_dia = agend_por_dia.get(d_str, [])

            # Agrupar por hora
            evts_por_hora = {}
            for ev in evts_dia:
                try:
                    h = int(ev.get("hora", "0").split(":")[0])
                except (ValueError, IndexError):
                    h = 0
                evts_por_hora.setdefault(h, []).append(ev)

            now_h = datetime.now().hour if d_str == today_str else -1

            html_parts = [
                '<style>',
                '.fday{width:100%;border-collapse:collapse}',
                '.fday td{border-bottom:1px solid #e8e8e8;padding:4px 8px;vertical-align:top}',
                '.fday .dh{width:60px;color:#70757a;font-size:12px;text-align:right;padding-right:12px;font-weight:500}',
                '.fday .ds{min-height:56px}',
                '.fday .ds-now{background:#fff8e1}',
                '.fday .ds-has{background:#f0f7ff}',
                '</style>',
                '<table class="fday">',
            ]
            for h in range(7, 21):
                evts_h = evts_por_hora.get(h, [])
                cls_list = []
                if h == now_h:
                    cls_list.append("ds-now")
                elif evts_h:
                    cls_list.append("ds-has")
                cls = f' class="ds {" ".join(cls_list)}"' if cls_list else ' class="ds"'
                html_parts.append(f'<tr><td class="dh">{h:02d}:00</td><td{cls}>')
                for ev in evts_h:
                    html_parts.append(_ev_html(ev, compact=False))
                html_parts.append('</td></tr>')
            html_parts.append('</table>')
            st.markdown("".join(html_parts), unsafe_allow_html=True)

            if not evts_dia:
                st.info("Nenhum agendamento neste dia.")

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
