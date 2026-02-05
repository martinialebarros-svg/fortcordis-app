# app/pages/prescricoes.py
"""Página Prescrições: nova prescrição, buscar paciente, medicamentos, templates, histórico."""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from app.config import DB_PATH, formatar_data_br
from app.services import buscar_pacientes
from modules.rbac import verificar_permissao


def render_prescricoes():
    st.title("💊 Sistema de Prescrições")

    # Verificação de permissão
    if not verificar_permissao("prescricoes", "ver"):
        st.error("❌ Acesso Negado")
        st.warning("⚠️ Você não tem permissão para acessar o módulo de prescrições")
        st.info("💡 Contate o administrador se precisar de acesso")
        st.stop()

    # Tabs do módulo
    tab_nova, tab_pacientes, tab_medicamentos, tab_templates, tab_historico = st.tabs([
        "✍️ Nova Prescrição",
        "🔍 Buscar Paciente",
        "💊 Banco de Medicamentos",
        "📋 Templates",
        "📜 Histórico"
    ])

    # ========================================================================
    # TAB 1: NOVA PRESCRIÇÃO
    # ========================================================================
    with tab_nova:
        st.subheader("✍️ Nova Prescrição")

        # Verifica se há dados do paciente carregados do XML/laudo
        dados_xml_disponiveis = any([
            st.session_state.get("cad_paciente"),
            st.session_state.get("cad_tutor"),
            st.session_state.get("presc_paciente_selecionado")
        ])

        if dados_xml_disponiveis:
            st.success("📋 Dados do paciente carregados automaticamente!")

        # Dados do paciente - pega valores da sessão se disponíveis
        st.markdown("### 🐾 Dados do Paciente")

        # Valores default da sessão (XML ou seleção manual)
        paciente_default = st.session_state.get("presc_paciente_selecionado", {})
        nome_paciente_default = paciente_default.get("nome") or st.session_state.get("cad_paciente", "")
        tutor_default = paciente_default.get("tutor") or st.session_state.get("cad_tutor", "")
        especie_default = paciente_default.get("especie") or st.session_state.get("cad_especie", "Canino")
        raca_default = paciente_default.get("raca") or st.session_state.get("cad_raca", "")
        idade_default = paciente_default.get("idade") or st.session_state.get("cad_idade", "")

        # Pega peso da sessão
        try:
            peso_default = float(st.session_state.get("cad_peso", 10.0))
        except (ValueError, TypeError):
            peso_default = 10.0

        col_pac1, col_pac2, col_pac3 = st.columns(3)

        with col_pac1:
            presc_paciente = st.text_input("Nome do Paciente *", value=nome_paciente_default,
                                           key="presc_paciente", placeholder="Ex: Thor")
            especie_opcoes = ["Canino", "Felino"]
            especie_idx = 0
            if especie_default:
                especie_norm = "Canino" if "can" in especie_default.lower() else "Felino" if "fel" in especie_default.lower() else "Canino"
                especie_idx = especie_opcoes.index(especie_norm) if especie_norm in especie_opcoes else 0
            presc_especie = st.selectbox("Espécie *", especie_opcoes, index=especie_idx, key="presc_especie")

        with col_pac2:
            presc_tutor = st.text_input("Nome do Tutor *", value=tutor_default,
                                        key="presc_tutor", placeholder="Ex: Maria Silva")
            presc_raca = st.text_input("Raça", value=raca_default,
                                       key="presc_raca", placeholder="Ex: Golden Retriever")

        with col_pac3:
            presc_peso = st.number_input("Peso (kg) *", min_value=0.1, max_value=200.0,
                                         value=peso_default, step=0.1, key="presc_peso",
                                         help="Peso necessário para cálculo de doses")
            presc_idade = st.text_input("Idade", value=idade_default,
                                        key="presc_idade", placeholder="Ex: 5 anos")

        st.divider()

        # Seção de medicamentos
        st.markdown("### 💊 Medicamentos")

        # Inicializa lista de medicamentos na sessão
        if "presc_medicamentos_lista" not in st.session_state:
            st.session_state.presc_medicamentos_lista = []

        # Buscar medicamentos do banco
        conn_med = sqlite3.connect(str(DB_PATH))
        try:
            medicamentos_df = pd.read_sql_query("""
                SELECT id, nome, apresentacao,
                       concentracao_valor, concentracao_unidade,
                       dose_padrao_mgkg, dose_min_mgkg, dose_max_mgkg,
                       frequencia_padrao, via, observacoes
                FROM medicamentos
                WHERE ativo = 1
                ORDER BY nome
            """, conn_med)
            medicamentos_disponiveis = medicamentos_df['nome'].tolist()
        except Exception as e:
            medicamentos_df = pd.DataFrame()
            medicamentos_disponiveis = []
        conn_med.close()

        # Carregar templates
        conn_temp = sqlite3.connect(str(DB_PATH))
        try:
            templates_df = pd.read_sql_query("""
                SELECT id, nome, texto_template
                FROM prescricoes_templates
                ORDER BY nome
            """, conn_temp)
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            templates_df = pd.DataFrame()
        conn_temp.close()

        # Opção de usar template
        col_template, col_manual = st.columns([1, 1])

        with col_template:
            if not templates_df.empty:
                template_selecionado = st.selectbox(
                    "📋 Usar Template Pronto",
                    options=["-- Selecione um template --"] + templates_df['nome'].tolist(),
                    key="presc_template_select"
                )

                if template_selecionado != "-- Selecione um template --":
                    template_info = templates_df[templates_df['nome'] == template_selecionado].iloc[0]

                    if st.button("📥 Aplicar Template", key="btn_aplicar_template"):
                        st.session_state.presc_texto_manual = template_info['texto_template']
                        st.success("✅ Template aplicado! Ajuste conforme necessário.")
                        st.rerun()

        with col_manual:
            st.markdown("**Ou adicione medicamentos individualmente:**")

        # Adicionar medicamento individual
        with st.expander("➕ Adicionar Medicamento", expanded=True):
            col_med1, col_med2 = st.columns([2, 1])

            with col_med1:
                if medicamentos_disponiveis:
                    med_selecionado = st.selectbox(
                        "Selecione o Medicamento",
                        options=["-- Selecione --"] + medicamentos_disponiveis,
                        key="presc_med_select"
                    )
                else:
                    med_selecionado = "-- Selecione --"
                    st.warning("⚠️ Nenhum medicamento cadastrado. Cadastre no 'Banco de Medicamentos'.")

            with col_med2:
                dose_personalizada = st.checkbox("Dose personalizada", key="presc_dose_custom")

            # Se selecionou um medicamento
            if med_selecionado != "-- Selecione --" and not medicamentos_df.empty:
                med_info = medicamentos_df[medicamentos_df['nome'] == med_selecionado].iloc[0]

                col_info1, col_info2, col_info3 = st.columns(3)

                with col_info1:
                    conc_display = f"{med_info['concentracao_valor']} {med_info['concentracao_unidade']}" if med_info['concentracao_valor'] else "-"
                    st.markdown(f"**Concentração:** {conc_display}")
                    st.markdown(f"**Forma:** {med_info['apresentacao'] or '-'}")

                with col_info2:
                    st.markdown(f"**Via:** {med_info['via'] or '-'}")
                    st.markdown(f"**Frequência:** {med_info['frequencia_padrao'] or '-'}")

                with col_info3:
                    dose_range = f"{med_info['dose_min_mgkg']} - {med_info['dose_max_mgkg']} mg/kg"
                    st.markdown(f"**Dose (mg/kg):** {dose_range}")
                    st.markdown(f"**Padrão:** {med_info['dose_padrao_mgkg']} mg/kg")

                # Cálculo automático de dose
                if presc_peso and presc_peso > 0:
                    if dose_personalizada:
                        dose_usar = st.number_input(
                            "Dose (mg/kg)",
                            min_value=0.01,
                            max_value=100.0,
                            value=float(med_info['dose_padrao_mgkg'] or 1.0),
                            step=0.01,
                            key="presc_dose_input"
                        )
                    else:
                        dose_usar = float(med_info['dose_padrao_mgkg'] or 1.0)

                    # Cálculo da dose total
                    dose_total_mg = presc_peso * dose_usar

                    # Tenta calcular volume se for solução (mg/ml)
                    volume_calculado = None
                    conc_unidade = str(med_info['concentracao_unidade'] or '').lower()

                    if 'mg/ml' in conc_unidade and med_info['concentracao_valor']:
                        try:
                            conc_num = float(med_info['concentracao_valor'])
                            volume_calculado = dose_total_mg / conc_num
                        except (ValueError, TypeError, ZeroDivisionError):
                            pass

                    st.success(f"""
                    **📊 Cálculo para {presc_peso} kg:**
                    - Dose total: **{dose_total_mg:.2f} mg**
                    {f"- Volume: **{volume_calculado:.2f} ml**" if volume_calculado else ""}
                    - Frequência: {med_info['frequencia_padrao'] or '-'}
                    """)

                    # Frequência editável
                    frequencia_usar = st.text_input(
                        "Frequência/Posologia",
                        value=med_info['frequencia_padrao'] or '',
                        key="presc_freq_input"
                    )

                    observacao_med = st.text_input(
                        "Observação adicional",
                        placeholder="Ex: Administrar com alimento",
                        key="presc_obs_med"
                    )

                    if st.button("➕ Adicionar à Prescrição", type="primary", key="btn_add_med"):
                        # Monta texto do medicamento
                        via_med = med_info['via'] or 'VO'
                        if volume_calculado:
                            texto_med = f"{med_info['nome']} - {volume_calculado:.2f} ml ({dose_total_mg:.1f} mg) - {frequencia_usar} - {via_med}"
                        else:
                            texto_med = f"{med_info['nome']} - {dose_total_mg:.1f} mg - {frequencia_usar} - {via_med}"

                        if observacao_med:
                            texto_med += f"\n   → {observacao_med}"

                        st.session_state.presc_medicamentos_lista.append(texto_med)
                        st.success(f"✅ {med_info['nome']} adicionado!")
                        st.rerun()

                # Observações do medicamento
                if med_info['observacoes']:
                    st.info(f"💡 **Obs:** {med_info['observacoes']}")

        st.divider()

        # Área de texto da prescrição
        st.markdown("### 📝 Texto da Prescrição")

        # Junta medicamentos adicionados
        texto_meds_adicionados = "\n\n".join(st.session_state.presc_medicamentos_lista) if st.session_state.presc_medicamentos_lista else ""

        # Usa texto do template se existir
        valor_inicial_texto = st.session_state.get("presc_texto_manual", texto_meds_adicionados)

        presc_texto = st.text_area(
            "Prescrição completa (edite conforme necessário)",
            value=valor_inicial_texto,
            height=300,
            key="presc_texto_final",
            help="Você pode editar livremente o texto da prescrição"
        )

        # Botão para limpar medicamentos
        col_limpar, col_espacador = st.columns([1, 3])
        with col_limpar:
            if st.button("🗑️ Limpar Medicamentos", key="btn_limpar_meds"):
                st.session_state.presc_medicamentos_lista = []
                if "presc_texto_manual" in st.session_state:
                    del st.session_state.presc_texto_manual
                st.rerun()

        st.divider()

        # Dados do veterinário
        st.markdown("### 👨‍⚕️ Veterinário Responsável")
        col_vet1, col_vet2 = st.columns(2)

        with col_vet1:
            presc_medico = st.text_input(
                "Nome do Veterinário *",
                value=st.session_state.get("usuario_nome", ""),
                key="presc_medico"
            )

        with col_vet2:
            presc_crmv = st.text_input(
                "CRMV *",
                placeholder="CRMV-CE 12345",
                key="presc_crmv"
            )

        st.divider()

        # Gerar PDF
        st.markdown("### 📄 Gerar Receituário")

        # Validação
        campos_ok = all([presc_paciente, presc_tutor, presc_peso, presc_texto, presc_medico, presc_crmv])

        if not campos_ok:
            st.warning("⚠️ Preencha todos os campos obrigatórios (*) para gerar o PDF")

        col_gerar, col_download = st.columns([1, 1])

        with col_gerar:
            if st.button("📄 Gerar PDF do Receituário", type="primary", disabled=not campos_ok, key="btn_gerar_receita"):
                try:
                    # Gera PDF usando a função do módulo documentos
                    pdf_bytes = gerar_receituario_pdf(
                        paciente_nome=presc_paciente,
                        tutor_nome=presc_tutor,
                        especie=presc_especie,
                        peso_kg=presc_peso,
                        prescricao_texto=presc_texto,
                        medico=presc_medico,
                        crmv=presc_crmv,
                        logo_path=None  # Pode adicionar caminho do logo
                    )

                    st.session_state.presc_pdf_bytes = pdf_bytes

                    # Salva no banco de dados
                    conn_salvar = sqlite3.connect(str(DB_PATH))
                    cursor_salvar = conn_salvar.cursor()

                    # Cria pasta para prescrições se não existir
                    PASTA_PRESCRICOES = Path.home() / "FortCordis" / "Prescricoes"
                    PASTA_PRESCRICOES.mkdir(parents=True, exist_ok=True)

                    # Nome do arquivo
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nome_arquivo = f"Receita_{presc_paciente.replace(' ', '_')}_{timestamp}.pdf"
                    caminho_pdf = PASTA_PRESCRICOES / nome_arquivo

                    # Salva o PDF
                    with open(caminho_pdf, 'wb') as f:
                        f.write(pdf_bytes)

                    # Registra no banco
                    now = datetime.now().isoformat()
                    cursor_salvar.execute("""
                        INSERT INTO prescricoes (
                            paciente_nome, tutor_nome, especie, peso_kg,
                            data_prescricao, texto_prescricao, medico_veterinario,
                            crmv, caminho_pdf, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        presc_paciente, presc_tutor, presc_especie, presc_peso,
                        datetime.now().strftime("%Y-%m-%d"), presc_texto,
                        presc_medico, presc_crmv, str(caminho_pdf), now, now
                    ))

                    conn_salvar.commit()
                    conn_salvar.close()

                    st.success(f"✅ Receituário gerado e salvo!")
                    st.info(f"📁 Arquivo: {caminho_pdf}")

                except Exception as e:
                    st.error(f"❌ Erro ao gerar PDF: {e}")

        with col_download:
            if "presc_pdf_bytes" in st.session_state:
                st.download_button(
                    "⬇️ Baixar Receituário PDF",
                    data=st.session_state.presc_pdf_bytes,
                    file_name=f"Receita_{presc_paciente}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="btn_download_receita"
                )

    # ========================================================================
    # TAB 2: BUSCAR PACIENTE (CONTINUIDADE DE ATENDIMENTO)
    # ========================================================================
    with tab_pacientes:
        st.subheader("🔍 Buscar Paciente / Continuar Atendimento")
        st.info("💡 Busque um paciente pelo nome ou tutor para carregar seus dados e laudos anteriores")

        # Filtros de busca
        col_busca_pac, col_busca_tut = st.columns(2)

        with col_busca_pac:
            busca_nome_pac = st.text_input("🐾 Nome do Paciente", placeholder="Ex: Pipoca", key="busca_pac_nome")

        with col_busca_tut:
            busca_nome_tut = st.text_input("👤 Nome do Tutor", placeholder="Ex: Maria", key="busca_pac_tutor")

        if busca_nome_pac or busca_nome_tut:
            try:
                pacientes_encontrados = buscar_pacientes(
                    nome=busca_nome_pac or None,
                    tutor=busca_nome_tut or None,
                    limite=20,
                )
            except Exception as e:
                pacientes_encontrados = pd.DataFrame()
                st.warning(f"Erro na busca: {e}")

            if not pacientes_encontrados.empty:
                st.markdown(f"**{len(pacientes_encontrados)} pacientes encontrados**")

                for idx, pac in pacientes_encontrados.iterrows():
                    with st.expander(f"🐾 {pac['paciente']} ({pac['especie'] or 'N/I'}) - Tutor: {pac['tutor'] or 'N/I'}", expanded=False):
                        col_info, col_acoes = st.columns([3, 1])

                        with col_info:
                            st.markdown(f"**Paciente:** {pac['paciente']}")
                            st.markdown(f"**Espécie:** {pac['especie'] or 'Não informada'}")
                            st.markdown(f"**Raça:** {pac['raca'] or 'Não informada'}")
                            st.markdown(f"**Sexo:** {pac['sexo'] or 'Não informado'}")
                            st.markdown(f"**Tutor:** {pac['tutor'] or 'Não informado'}")
                            if pac['telefone']:
                                st.markdown(f"**Telefone:** {pac['telefone']}")

                        with col_acoes:
                            if st.button("📋 Selecionar", key=f"sel_pac_{pac['id']}", type="primary"):
                                # Carrega dados do paciente na sessão
                                st.session_state.presc_paciente_selecionado = {
                                    "id": pac['id'],
                                    "nome": pac['paciente'],
                                    "especie": pac['especie'],
                                    "raca": pac['raca'],
                                    "sexo": pac['sexo'],
                                    "tutor": pac['tutor'],
                                    "telefone": pac['telefone']
                                }
                                st.success(f"✅ Paciente {pac['paciente']} selecionado! Vá para 'Nova Prescrição'.")

                        # Busca laudos anteriores deste paciente
                        st.divider()
                        st.markdown("**📊 Laudos Anteriores:**")

                        conn_laudos = sqlite3.connect(str(DB_PATH))
                        try:
                            # Busca nos arquivos JSON salvos na pasta Laudos
                            PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
                            laudos_encontrados = []

                            if PASTA_LAUDOS.exists():
                                # Só considera laudos do MESMO paciente e MESMO tutor (evita laudos de outros animais)
                                # O JSON dos laudos usa estrutura: { "paciente": { "nome", "tutor", "clinica", "data_exame" } } (igual à busca em Laudos e Exames)
                                pac_nome_norm = _norm_key(str(pac.get("paciente", "")))
                                pac_tutor_norm = _norm_key(str(pac.get("tutor", "")))
                                for arquivo_json in PASTA_LAUDOS.glob("*.json"):
                                    try:
                                        with open(arquivo_json, 'r', encoding='utf-8') as f:
                                            dados_laudo = json.load(f)
                                            # Ler do mesmo formato que "Buscar exames arquivados" (paciente.nome, paciente.tutor)
                                            obj_pac = dados_laudo.get("paciente", {}) if isinstance(dados_laudo.get("paciente"), dict) else {}
                                            nome_laudo = (obj_pac.get("nome") or dados_laudo.get("nome_animal") or "")
                                            tutor_laudo = (obj_pac.get("tutor") or dados_laudo.get("tutor") or "")
                                            nome_laudo_norm = _norm_key(str(nome_laudo))
                                            tutor_laudo_norm = _norm_key(str(tutor_laudo))

                                            # Match exato por nome do animal E tutor (evita Pip vs Pipoca, outro tutor etc.)
                                            if pac_nome_norm and pac_tutor_norm and nome_laudo_norm == pac_nome_norm and tutor_laudo_norm == pac_tutor_norm:
                                                laudos_encontrados.append({
                                                    "arquivo": arquivo_json.name,
                                                    "caminho": str(arquivo_json),
                                                    "data": obj_pac.get("data_exame") or dados_laudo.get("data", "N/I"),
                                                    "tipo": dados_laudo.get("tipo_exame", "Ecocardiograma"),
                                                    "clinica": obj_pac.get("clinica") or dados_laudo.get("clinica", "N/I"),
                                                    "dados": dados_laudo
                                                })
                                    except Exception:
                                        continue

                            if laudos_encontrados:
                                pac_id = pac.get('id', id(pac))
                                for idx_laudo, laudo in enumerate(sorted(laudos_encontrados, key=lambda x: x['data'], reverse=True)[:5]):
                                    col_l1, col_l2 = st.columns([3, 1])
                                    with col_l1:
                                        st.caption(f"📅 {laudo['data']} | {laudo['tipo']} | {laudo['clinica']}")
                                    with col_l2:
                                        # Keys únicas por paciente + índice para evitar duplicata no Streamlit
                                        key_dl = f"dl_laudo_{pac_id}_{idx_laudo}_{laudo['arquivo']}"
                                        key_load = f"load_laudo_{pac_id}_{idx_laudo}_{laudo['arquivo']}"
                                        # Verifica se existe PDF
                                        pdf_path = Path(laudo['caminho'].replace('.json', '.pdf'))
                                        if pdf_path.exists():
                                            with open(pdf_path, 'rb') as f:
                                                st.download_button(
                                                    "📄 PDF",
                                                    data=f.read(),
                                                    file_name=pdf_path.name,
                                                    mime="application/pdf",
                                                    key=key_dl
                                                )

                                        if st.button("📂 Carregar", key=key_load):
                                            # Carrega dados do laudo na sessão para usar (mesmo formato: paciente.nome, paciente.tutor, etc.)
                                            dados = laudo['dados']
                                            obj_pac = dados.get("paciente", {}) if isinstance(dados.get("paciente"), dict) else {}
                                            st.session_state.presc_paciente_selecionado = {
                                                "id": pac['id'],
                                                "nome": obj_pac.get("nome") or dados.get("nome_animal", pac['paciente']),
                                                "especie": obj_pac.get("especie") or dados.get("especie", pac['especie']),
                                                "raca": obj_pac.get("raca") or dados.get("raca", pac['raca']),
                                                "sexo": pac['sexo'],
                                                "tutor": obj_pac.get("tutor") or dados.get("tutor", pac['tutor']),
                                                "telefone": pac['telefone'],
                                                "peso": obj_pac.get("peso") or dados.get("peso"),
                                                "idade": obj_pac.get("idade") or dados.get("idade"),
                                                "laudo_anterior": laudo
                                            }
                                            # Atualiza peso na sessão
                                            peso_laudo = obj_pac.get("peso") or dados.get("peso")
                                            if peso_laudo:
                                                try:
                                                    st.session_state.cad_peso = float(str(peso_laudo).replace(",", "."))
                                                except Exception:
                                                    pass
                                            st.success(f"✅ Laudo de {laudo['data']} carregado!")
                                            st.rerun()
                            else:
                                st.caption("Nenhum laudo encontrado para este paciente")
                        except Exception as e:
                            st.caption(f"Erro ao buscar laudos: {e}")
                        conn_laudos.close()
            else:
                st.info("Nenhum paciente encontrado. Tente outro termo de busca.")

        # Limpar seleção
        if st.session_state.get("presc_paciente_selecionado"):
            st.divider()
            pac_sel = st.session_state.presc_paciente_selecionado
            st.success(f"**Paciente selecionado:** {pac_sel.get('nome')} - Tutor: {pac_sel.get('tutor')}")

            if pac_sel.get("laudo_anterior"):
                laudo_ant = pac_sel["laudo_anterior"]
                st.info(f"📊 Laudo carregado: {laudo_ant.get('tipo')} de {laudo_ant.get('data')}")

            if st.button("🗑️ Limpar Seleção", key="limpar_pac_sel"):
                del st.session_state.presc_paciente_selecionado
                st.rerun()

    # ========================================================================
    # TAB 3: BANCO DE MEDICAMENTOS
    # ========================================================================
    with tab_medicamentos:
        st.subheader("💊 Banco de Medicamentos")
        st.caption("94 medicamentos cardiológicos cadastrados (Fonte: MSD Vet Manual, CEG, CardioRush)")

        # Buscar medicamentos com categoria
        conn_med2 = sqlite3.connect(str(DB_PATH))
        try:
            meds_todos = pd.read_sql_query("""
                SELECT id, nome, apresentacao,
                       concentracao_valor, concentracao_unidade,
                       dose_padrao_mgkg, dose_min_mgkg, dose_max_mgkg,
                       frequencia_padrao, via, observacoes, categoria, ativo
                FROM medicamentos
                ORDER BY categoria, nome
            """, conn_med2)

            # Busca categorias disponíveis
            categorias = pd.read_sql_query(
                "SELECT DISTINCT categoria FROM medicamentos WHERE categoria IS NOT NULL ORDER BY categoria",
                conn_med2
            )['categoria'].tolist()
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            meds_todos = pd.DataFrame()
            categorias = []
        conn_med2.close()

        # Filtros
        col_busca, col_cat, col_status = st.columns([2, 1, 1])

        with col_busca:
            busca_med = st.text_input("🔍 Buscar medicamento", placeholder="Digite o nome", key="busca_med_banco")

        with col_cat:
            filtro_categoria = st.selectbox("Categoria", ["Todas"] + categorias, key="filtro_categoria")

        with col_status:
            filtro_ativo = st.selectbox("Status", ["Ativos", "Todos", "Inativos"], key="filtro_med_status")

        # Aplica filtros
        if not meds_todos.empty:
            meds_filtrados = meds_todos.copy()

            if busca_med:
                meds_filtrados = meds_filtrados[
                    meds_filtrados['nome'].str.contains(busca_med, case=False, na=False)
                ]

            if filtro_categoria != "Todas":
                meds_filtrados = meds_filtrados[meds_filtrados['categoria'] == filtro_categoria]

            if filtro_ativo == "Ativos":
                meds_filtrados = meds_filtrados[meds_filtrados['ativo'] == 1]
            elif filtro_ativo == "Inativos":
                meds_filtrados = meds_filtrados[meds_filtrados['ativo'] == 0]

            st.markdown(f"**{len(meds_filtrados)} medicamentos encontrados**")

            # Exibe por categoria com expansores
            if filtro_categoria == "Todas" and not busca_med:
                for cat in meds_filtrados['categoria'].unique():
                    meds_cat = meds_filtrados[meds_filtrados['categoria'] == cat]
                    with st.expander(f"📦 {cat} ({len(meds_cat)})", expanded=False):
                        for idx, med in meds_cat.iterrows():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                conc = f"{med['concentracao_valor']} {med['concentracao_unidade']}" if med['concentracao_valor'] else "-"
                                st.markdown(f"**{med['nome']}** ({conc})")
                                st.caption(f"{med['apresentacao']} | {med['via']} | {med['frequencia_padrao']}")
                                if med['observacoes']:
                                    st.caption(f"💡 {med['observacoes'][:100]}...")
                            with col2:
                                st.metric("Dose", f"{med['dose_padrao_mgkg']} mg/kg")
                            with col3:
                                if verificar_permissao("prescricoes", "editar"):
                                    if st.button("✏️", key=f"edit_med_{med['id']}", help="Editar"):
                                        st.session_state.med_editando_id = med['id']
                                        st.rerun()
                            st.divider()
            else:
                # Exibe lista simples quando filtrado
                for idx, med in meds_filtrados.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 1, 0.5, 0.5])
                    with col1:
                        conc = f"{med['concentracao_valor']} {med['concentracao_unidade']}" if med['concentracao_valor'] else "-"
                        status_icon = "✅" if med['ativo'] == 1 else "❌"
                        st.markdown(f"{status_icon} **{med['nome']}** ({conc})")
                        st.caption(f"{med['categoria']} | {med['apresentacao']} | {med['via']} | {med['frequencia_padrao']}")
                    with col2:
                        st.metric("Dose", f"{med['dose_padrao_mgkg']} mg/kg", label_visibility="collapsed")
                    with col3:
                        if verificar_permissao("prescricoes", "editar"):
                            if st.button("✏️", key=f"edit_med_{med['id']}", help="Editar"):
                                st.session_state.med_editando_id = med['id']
                                st.rerun()
                    with col4:
                        if verificar_permissao("prescricoes", "deletar"):
                            if med['ativo'] == 1:
                                if st.button("🗑️", key=f"del_med_{med['id']}", help="Desativar"):
                                    conn_del = sqlite3.connect(str(DB_PATH))
                                    conn_del.execute("UPDATE medicamentos SET ativo = 0, updated_at = ? WHERE id = ?",
                                                    (datetime.now().isoformat(), med['id']))
                                    conn_del.commit()
                                    conn_del.close()
                                    st.rerun()
                            else:
                                if st.button("♻️", key=f"reativar_med_{med['id']}", help="Reativar"):
                                    conn_reat = sqlite3.connect(str(DB_PATH))
                                    conn_reat.execute("UPDATE medicamentos SET ativo = 1, updated_at = ? WHERE id = ?",
                                                     (datetime.now().isoformat(), med['id']))
                                    conn_reat.commit()
                                    conn_reat.close()
                                    st.rerun()
        else:
            st.info("Nenhum medicamento cadastrado ainda.")

        # Modal de edição
        if "med_editando_id" in st.session_state and st.session_state.med_editando_id:
            st.divider()
            st.subheader("✏️ Editar Medicamento")

            conn_edit = sqlite3.connect(str(DB_PATH))
            med_edit = pd.read_sql_query(
                "SELECT * FROM medicamentos WHERE id = ?",
                conn_edit, params=(st.session_state.med_editando_id,)
            ).iloc[0]
            conn_edit.close()

            col_e1, col_e2, col_e3 = st.columns(3)

            with col_e1:
                edit_nome = st.text_input("Nome *", value=med_edit['nome'], key="edit_med_nome")
                edit_conc_valor = st.number_input("Concentração", value=float(med_edit['concentracao_valor'] or 0),
                                                   step=0.1, key="edit_med_conc_valor")
                edit_conc_unidade = st.selectbox("Unidade", ["mg", "mg/ml", "mcg", "UI", "%"],
                    index=["mg", "mg/ml", "mcg", "UI", "%"].index(med_edit['concentracao_unidade']) if med_edit['concentracao_unidade'] in ["mg", "mg/ml", "mcg", "UI", "%"] else 0,
                    key="edit_med_conc_unidade")

            with col_e2:
                edit_forma = st.text_input("Forma farmacêutica", value=med_edit['apresentacao'] or '', key="edit_med_forma")
                edit_via = st.text_input("Via", value=med_edit['via'] or '', key="edit_med_via")
                edit_freq = st.text_input("Frequência", value=med_edit['frequencia_padrao'] or '', key="edit_med_freq")

            with col_e3:
                edit_dose = st.number_input("Dose padrão (mg/kg)", value=float(med_edit['dose_padrao_mgkg'] or 0),
                                            step=0.01, key="edit_med_dose")
                edit_dose_min = st.number_input("Dose mín (mg/kg)", value=float(med_edit['dose_min_mgkg'] or 0),
                                                step=0.01, key="edit_med_dose_min")
                edit_dose_max = st.number_input("Dose máx (mg/kg)", value=float(med_edit['dose_max_mgkg'] or 0),
                                                step=0.01, key="edit_med_dose_max")

            edit_categoria = st.selectbox("Categoria", categorias,
                index=categorias.index(med_edit['categoria']) if med_edit['categoria'] in categorias else 0,
                key="edit_med_categoria")
            edit_obs = st.text_area("Observações", value=med_edit['observacoes'] or '', key="edit_med_obs")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_edit_med"):
                    conn_save = sqlite3.connect(str(DB_PATH))
                    conn_save.execute("""
                        UPDATE medicamentos SET
                            nome = ?, nome_key = ?, apresentacao = ?, concentracao_valor = ?,
                            concentracao_unidade = ?, dose_padrao_mgkg = ?, dose_min_mgkg = ?,
                            dose_max_mgkg = ?, frequencia_padrao = ?, via = ?, observacoes = ?,
                            categoria = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        edit_nome, edit_nome.lower().strip(), edit_forma, edit_conc_valor,
                        edit_conc_unidade, edit_dose, edit_dose_min, edit_dose_max,
                        edit_freq, edit_via, edit_obs, edit_categoria,
                        datetime.now().isoformat(), st.session_state.med_editando_id
                    ))
                    conn_save.commit()
                    conn_save.close()
                    del st.session_state.med_editando_id
                    st.success("✅ Medicamento atualizado!")
                    st.rerun()

            with col_btn2:
                if st.button("❌ Cancelar", key="btn_cancelar_edit_med"):
                    del st.session_state.med_editando_id
                    st.rerun()

        # Formulário para novo medicamento
        if verificar_permissao("prescricoes", "criar"):
            st.divider()
            with st.expander("➕ Cadastrar Novo Medicamento", expanded=False):
                st.markdown("**Dados do Medicamento**")

                col_m1, col_m2, col_m3 = st.columns(3)

                with col_m1:
                    novo_med_nome = st.text_input("Nome comercial *", key="novo_med_nome",
                                                  placeholder="Ex: Furosemida 40mg")
                    novo_med_conc_valor = st.number_input("Concentração (valor) *", min_value=0.01,
                                                          value=10.0, step=0.1, key="novo_med_conc_valor")
                    novo_med_conc_unidade = st.selectbox("Unidade", ["mg", "mg/ml", "mcg", "UI"],
                                                          key="novo_med_conc_unidade")

                with col_m2:
                    novo_med_forma = st.selectbox("Forma farmacêutica", [
                        "Comprimido", "Comprimido mastigável", "Cápsula",
                        "Solução oral", "Solução injetável", "Suspensão", "Pomada", "Outro"
                    ], key="novo_med_forma")
                    novo_med_via = st.selectbox("Via de administração", [
                        "VO", "IM", "IV", "SC", "VO/IM/IV", "IV/IM", "Tópica", "IT", "CRI"
                    ], key="novo_med_via")
                    novo_med_freq = st.text_input("Frequência padrão", key="novo_med_freq",
                                                  placeholder="Ex: BID (12/12h)")

                with col_m3:
                    novo_med_dose = st.number_input("Dose padrão (mg/kg)", min_value=0.001,
                                                    value=1.0, step=0.01, key="novo_med_dose")
                    novo_med_dose_min = st.number_input("Dose mínima (mg/kg)", min_value=0.001,
                                                        value=0.5, step=0.01, key="novo_med_dose_min")
                    novo_med_dose_max = st.number_input("Dose máxima (mg/kg)", min_value=0.001,
                                                        value=2.0, step=0.01, key="novo_med_dose_max")

                novo_med_categoria = st.selectbox("Categoria", categorias if categorias else ["Outro"], key="novo_med_categoria")
                novo_med_obs = st.text_area("Observações", key="novo_med_obs",
                                            placeholder="Ex: Monitorar eletrólitos. Evitar em pacientes desidratados.")

                if st.button("✅ Cadastrar Medicamento", type="primary", key="btn_cadastrar_med"):
                    if novo_med_nome:
                        try:
                            now = datetime.now().isoformat()
                            nome_key = novo_med_nome.lower().strip()

                            conn_novo = sqlite3.connect(str(DB_PATH))
                            cursor_novo = conn_novo.cursor()

                            cursor_novo.execute("""
                                INSERT INTO medicamentos (
                                    nome, nome_key, apresentacao, concentracao_valor, concentracao_unidade,
                                    dose_padrao_mgkg, dose_min_mgkg, dose_max_mgkg,
                                    frequencia_padrao, via, observacoes, categoria, ativo, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                            """, (
                                novo_med_nome, nome_key, novo_med_forma,
                                novo_med_conc_valor, novo_med_conc_unidade,
                                novo_med_dose, novo_med_dose_min, novo_med_dose_max,
                                novo_med_freq, novo_med_via, novo_med_obs, novo_med_categoria,
                                now, now
                            ))

                            conn_novo.commit()
                            conn_novo.close()

                            st.success(f"✅ Medicamento '{novo_med_nome}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar: {e}")
                    else:
                        st.error("❌ Preencha o nome do medicamento")

    # ========================================================================
    # TAB 3: TEMPLATES DE PRESCRIÇÃO
    # ========================================================================
    with tab_templates:
        st.subheader("📋 Templates de Prescrição")

        # Buscar templates
        conn_temp2 = sqlite3.connect(str(DB_PATH))
        try:
            templates_todos = pd.read_sql_query("""
                SELECT id, nome, texto_template
                FROM prescricoes_templates
                ORDER BY nome
            """, conn_temp2)
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            templates_todos = pd.DataFrame()
        conn_temp2.close()

        if not templates_todos.empty:
            st.markdown(f"**{len(templates_todos)} templates disponíveis**")

            for idx, template in templates_todos.iterrows():
                with st.expander(f"📋 {template['nome']}", expanded=False):
                    st.markdown("**Prescrição:**")
                    st.text(template['texto_template'])

                    # Botão para usar este template
                    if st.button(f"📥 Usar este Template", key=f"btn_usar_template_{template['id']}"):
                        st.session_state.presc_texto_manual = template['texto_template']
                        st.success("✅ Template carregado! Vá para 'Nova Prescrição' para usar.")
        else:
            st.info("Nenhum template cadastrado ainda.")

        # Formulário para novo template
        if verificar_permissao("prescricoes", "criar"):
            st.divider()
            with st.expander("➕ Criar Novo Template", expanded=False):
                novo_temp_nome = st.text_input("Nome do Template *", key="novo_temp_nome",
                                               placeholder="Ex: ICC B1 - Protocolo Inicial")
                novo_temp_texto = st.text_area("Texto da Prescrição *", key="novo_temp_texto",
                                               height=200,
                                               placeholder="Digite o texto completo da prescrição...")

                if st.button("✅ Salvar Template", type="primary", key="btn_salvar_template"):
                    if novo_temp_nome and novo_temp_texto:
                        try:
                            from datetime import datetime
                            now = datetime.now().isoformat()

                            conn_temp_novo = sqlite3.connect(str(DB_PATH))
                            cursor_temp = conn_temp_novo.cursor()

                            cursor_temp.execute("""
                                INSERT INTO prescricoes_templates (nome, texto_template, created_at, updated_at)
                                VALUES (?, ?, ?, ?)
                            """, (novo_temp_nome, novo_temp_texto, now, now))

                            conn_temp_novo.commit()
                            conn_temp_novo.close()

                            st.success(f"✅ Template '{novo_temp_nome}' salvo com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar: {e}")
                    else:
                        st.error("❌ Preencha todos os campos obrigatórios")

    # ========================================================================
    # TAB 4: HISTÓRICO DE PRESCRIÇÕES
    # ========================================================================
    with tab_historico:
        st.subheader("📜 Histórico de Prescrições")

        # Filtros
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

        with col_filtro1:
            filtro_paciente = st.text_input("🔍 Buscar por paciente", key="hist_filtro_paciente")

        with col_filtro2:
            filtro_tutor = st.text_input("🔍 Buscar por tutor", key="hist_filtro_tutor")

        with col_filtro3:
            filtro_data = st.date_input("📅 A partir de", value=datetime.now() - timedelta(days=30),
                                        key="hist_filtro_data")

        # Buscar prescrições
        conn_hist = sqlite3.connect(str(DB_PATH))
        try:
            query_hist = """
                SELECT id, paciente_nome, tutor_nome, especie, peso_kg,
                       data_prescricao, medico_veterinario, crmv, caminho_pdf
                FROM prescricoes
                WHERE data_prescricao >= ?
            """
            params_hist = [filtro_data.strftime("%Y-%m-%d")]

            if filtro_paciente:
                query_hist += " AND UPPER(paciente_nome) LIKE UPPER(?)"
                params_hist.append(f"%{filtro_paciente}%")

            if filtro_tutor:
                query_hist += " AND UPPER(tutor_nome) LIKE UPPER(?)"
                params_hist.append(f"%{filtro_tutor}%")

            query_hist += " ORDER BY data_prescricao DESC, id DESC LIMIT 50"

            historico_df = pd.read_sql_query(query_hist, conn_hist, params=params_hist)
        except Exception as e:
            historico_df = pd.DataFrame()
            st.warning(f"Erro ao buscar histórico: {e}")
        conn_hist.close()

        if not historico_df.empty:
            st.markdown(f"**{len(historico_df)} prescrições encontradas**")

            for idx, presc in historico_df.iterrows():
                with st.expander(f"📄 {presc['paciente_nome']} - {formatar_data_br(presc['data_prescricao'])}", expanded=False):
                    col_h1, col_h2 = st.columns(2)

                    with col_h1:
                        st.markdown(f"**Paciente:** {presc['paciente_nome']}")
                        st.markdown(f"**Tutor:** {presc['tutor_nome']}")
                        st.markdown(f"**Espécie:** {presc['especie']}")
                        st.markdown(f"**Peso:** {presc['peso_kg']} kg")

                    with col_h2:
                        st.markdown(f"**Data:** {formatar_data_br(presc['data_prescricao'])}")
                        st.markdown(f"**Veterinário:** {presc['medico_veterinario']}")
                        st.markdown(f"**CRMV:** {presc['crmv']}")

                    # Botão para baixar PDF se existir
                    if presc['caminho_pdf'] and Path(presc['caminho_pdf']).exists():
                        with open(presc['caminho_pdf'], 'rb') as f:
                            pdf_data = f.read()
                        st.download_button(
                            "⬇️ Baixar PDF",
                            data=pdf_data,
                            file_name=f"Receita_{presc['paciente_nome']}_{presc['data_prescricao']}.pdf",
                            mime="application/pdf",
                            key=f"btn_download_hist_{presc['id']}"
                        )
                    else:
                        st.warning("📁 Arquivo PDF não encontrado")
        else:
            st.info("Nenhuma prescrição encontrada para os filtros selecionados.")


# ============================================================================
# TELA: FINANCEIRO
# ============================================================================

