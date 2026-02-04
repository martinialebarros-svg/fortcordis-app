# app/pages/prontuario.py
"""Página Prontuário Eletrônico: busca, tutores, pacientes, laudos, consultas."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from app.config import DB_PATH
from app.db import _db_conn, _db_init
from app.components import tabela_tabular
from app.services import (
    listar_consultas_recentes,
    criar_consulta,
    listar_pacientes_com_tutor,
    listar_pacientes_tabela,
)
from modules.rbac import verificar_permissao


def render_prontuario():
    from datetime import datetime as _dt
    st.title("📋 Prontuário Eletrônico")

    # Verifica permissão
    if not verificar_permissao("prontuario", "ver"):
        st.error("❌ Você não tem permissão para acessar o prontuário")
        st.stop()

    # Prontuário usa o mesmo banco do app (DB_PATH) — obrigatório no deploy
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _db_init()  # Garante tabelas e colunas (ativo em tutores, etc.) antes das queries

    # Abas do prontuário
    tab_busca, tab_tutores, tab_pacientes, tab_laudos, tab_consultas = st.tabs([
        "🔍 Busca Rápida",
        "👨‍👩‍👧 Tutores",
        "🐕 Pacientes",
        "📊 Laudos",
        "🩺 Consultas"
    ])

    # ========================================================================
    # ABA 1: BUSCA RÁPIDA
    # ========================================================================

    with tab_busca:
        st.subheader("🔍 Busca Rápida de Pacientes")
        try:
            _c = _db_conn()
            n_tut = _c.execute("SELECT COUNT(*) FROM tutores").fetchone()[0]
            n_pac = _c.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
            st.caption(f"📁 Conectado ao banco principal com {n_tut} tutores e {n_pac} pacientes")
        except Exception:
            st.caption("📁 Conectado ao banco principal")

        col_busca1, col_busca2 = st.columns([3, 1])

        with col_busca1:
            termo_busca = st.text_input(
                "Digite o nome do paciente ou tutor:",
                placeholder="Ex: Pipoca, Maria Silva...",
                key="busca_paciente"
            )

        with col_busca2:
            tipo_busca = st.selectbox(
                "Buscar por:",
                ["Paciente", "Tutor"],
                key="tipo_busca"
            )

        if termo_busca:
            conn_pront = sqlite3.connect(str(DB_PATH))

            # Busca case-insensitive usando UPPER()
            termo_busca_upper = termo_busca.upper()

            if tipo_busca == "Paciente":
                query = """
                    SELECT
                        p.id,
                        p.nome as paciente,
                        p.especie,
                        p.raca,
                        p.sexo,
                        p.peso_kg,
                        p.nascimento,
                        t.nome as tutor,
                        t.telefone,
                        t.whatsapp,
                        p.microchip,
                        p.observacoes
                    FROM pacientes p
                    LEFT JOIN tutores t ON p.tutor_id = t.id
                    WHERE UPPER(p.nome) LIKE ? AND (p.ativo = 1 OR p.ativo IS NULL)
                    ORDER BY p.nome
                    LIMIT 50
                """
                resultados = pd.read_sql_query(query, conn_pront, params=(f"%{termo_busca_upper}%",))
            else:
                query = """
                    SELECT
                        p.id,
                        p.nome as paciente,
                        p.especie,
                        p.raca,
                        p.sexo,
                        p.peso_kg,
                        p.nascimento,
                        t.nome as tutor,
                        t.telefone,
                        t.whatsapp,
                        p.microchip,
                        p.observacoes
                    FROM pacientes p
                    LEFT JOIN tutores t ON p.tutor_id = t.id
                    WHERE UPPER(t.nome) LIKE ? AND (p.ativo = 1 OR p.ativo IS NULL)
                    ORDER BY t.nome, p.nome
                    LIMIT 50
                """
                resultados = pd.read_sql_query(query, conn_pront, params=(f"%{termo_busca_upper}%",))

            conn_pront.close()

            if not resultados.empty:
                st.success(f"✅ Encontrados {len(resultados)} resultado(s)")

                # Exibe resultados
                for _, row in resultados.iterrows():
                    tel_display = row['telefone'] or row['whatsapp'] or "Sem telefone"
                    especie_display = row['especie'] or "N/I"

                    with st.expander(
                        f"🐾 {row['paciente']} ({especie_display}) - "
                        f"Tutor: {row['tutor'] or 'N/I'}"
                    ):
                        col_info1, col_info2, col_info3 = st.columns(3)

                        with col_info1:
                            st.write(f"**Paciente:** {row['paciente']}")
                            st.write(f"**Espécie:** {especie_display}")
                            raca_display = row['raca'] if pd.notna(row['raca']) else 'SRD'
                            st.write(f"**Raça:** {raca_display}")
                            st.write(f"**Sexo:** {row['sexo'] or 'N/I'}")

                        with col_info2:
                            st.write(f"**Tutor:** {row['tutor'] or 'N/I'}")
                            st.write(f"**Telefone:** {tel_display}")
                            if row['whatsapp']:
                                st.write(f"**WhatsApp:** {row['whatsapp']}")

                        with col_info3:
                            if row['peso_kg']:
                                st.write(f"**Peso:** {row['peso_kg']} kg")
                            if row['microchip']:
                                st.write(f"**Microchip:** {row['microchip']}")
                            if row['nascimento']:
                                st.write(f"**Nascimento:** {row['nascimento']}")

                        if row['observacoes']:
                            st.info(f"📝 {row['observacoes']}")

                        # Busca laudos deste paciente
                        PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
                        laudos_pac = []
                        if PASTA_LAUDOS.exists():
                            for arq in PASTA_LAUDOS.glob("*.json"):
                                try:
                                    with open(arq, 'r', encoding='utf-8') as f:
                                        dados = json.load(f)
                                        if row['paciente'].lower() in dados.get('nome_animal', '').lower():
                                            laudos_pac.append({
                                                'data': dados.get('data', 'N/I'),
                                                'tipo': dados.get('tipo_exame', 'Eco'),
                                                'clinica': dados.get('clinica', 'N/I'),
                                                'arquivo': str(arq)
                                            })
                                except:
                                    continue

                        if laudos_pac:
                            st.markdown("**📊 Laudos encontrados:**")
                            for laudo in sorted(laudos_pac, key=lambda x: x['data'], reverse=True)[:3]:
                                st.caption(f"• {laudo['data']} - {laudo['tipo']} ({laudo['clinica']})")

                        col_btn1, col_btn2, col_btn3 = st.columns(3)

                        with col_btn1:
                            if st.button("📋 Abrir Prontuário", key=f"ver_pront_{row['id']}"):
                                st.session_state['prontuario_paciente_id'] = row['id']
                                st.session_state['prontuario_paciente_dados'] = row.to_dict()
                                st.info("💡 Vá para a aba 'Consultas' para ver/criar atendimentos")

                        with col_btn2:
                            if st.button("💊 Nova Prescrição", key=f"nova_presc_{row['id']}"):
                                # Carrega dados para prescrição
                                st.session_state.presc_paciente_selecionado = {
                                    "id": row['id'],
                                    "nome": row['paciente'],
                                    "especie": row['especie'],
                                    "raca": row['raca'],
                                    "sexo": row['sexo'],
                                    "tutor": row['tutor'],
                                    "telefone": row['telefone']
                                }
                                if row['peso_kg']:
                                    st.session_state.cad_peso = float(row['peso_kg'])
                                st.success("✅ Paciente carregado! Vá em 'Prescrições' no menu.")

                        with col_btn3:
                            if st.button("✏️ Editar Cadastro", key=f"editar_pac_{row['id']}"):
                                st.session_state['editar_paciente_id'] = row['id']
                                st.info("💡 Vá para a aba 'Pacientes' para editar")
            else:
                st.warning(f"⚠️ Nenhum resultado encontrado para '{termo_busca}'")

                # Mostra ajuda
                with st.expander("💡 Dicas de busca"):
                    st.write("**Como buscar:**")
                    st.write("• Por paciente: Digite parte do nome (ex: 'pip' acha 'Pipoca')")
                    st.write("• Por tutor: Selecione 'Tutor' e digite o nome")
                    st.write("• A busca não diferencia maiúsculas/minúsculas")

                    # Mostra quantos pacientes existem
                    conn_help = sqlite3.connect(str(DB_PATH))
                    try:
                        total_pac = pd.read_sql_query(
                            "SELECT COUNT(*) as total FROM pacientes WHERE ativo = 1 OR ativo IS NULL",
                            conn_help
                        )
                        total = total_pac['total'].iloc[0]

                        if total == 0:
                            st.info("📋 Ainda não há pacientes cadastrados")
                        else:
                            st.info(f"📋 Existem {total} paciente(s) cadastrado(s) no sistema")

                            # Lista alguns pacientes
                            alguns = pd.read_sql_query(
                                """SELECT p.nome, t.nome as tutor
                                   FROM pacientes p
                                   LEFT JOIN tutores t ON p.tutor_id = t.id
                                   WHERE p.ativo = 1 OR p.ativo IS NULL
                                   ORDER BY p.created_at DESC
                                   LIMIT 10""",
                                conn_help
                            )

                            if not alguns.empty:
                                st.write("**Últimos pacientes cadastrados:**")
                                for _, pac in alguns.iterrows():
                                    tutor_nome = pac['tutor'] if pac['tutor'] else 'N/I'
                                    st.write(f"• {pac['nome']} (Tutor: {tutor_nome})")
                    except Exception as e:
                        st.caption(f"Erro: {e}")
                    finally:
                        conn_help.close()
    
    # ========================================================================
    # ABA 2: TUTORES
    # ========================================================================
    
    with tab_tutores:
        st.subheader("👨‍👩‍👧 Cadastro de Tutores")
        
        # ====================================================================
        # FLUXO: Tutor recém-cadastrado → Cadastrar Animal
        # ====================================================================
        if "tutor_recem_cadastrado" in st.session_state:
            tutor_id = st.session_state["tutor_recem_cadastrado"]["id"]
            tutor_nome = st.session_state["tutor_recem_cadastrado"]["nome"]
            
            st.success(f"✅ Tutor '{tutor_nome}' cadastrado com sucesso!")
            
            st.markdown("---")
            st.info("💡 **Próximo passo:** Cadastre os animais deste tutor")
            
            col_acao1, col_acao2 = st.columns(2)
            
            with col_acao1:
                if st.button("🐕 Cadastrar Animal Agora", type="primary", key="btn_cadastrar_animal_agora"):
                    # Vai para aba de pacientes com tutor pré-selecionado
                    st.session_state["tutor_pre_selecionado"] = {
                        "id": tutor_id,
                        "nome": tutor_nome
                    }
                    del st.session_state["tutor_recem_cadastrado"]
                    st.rerun()
            
            with col_acao2:
                if st.button("✅ Concluir (cadastrar depois)", key="btn_concluir_tutor"):
                    del st.session_state["tutor_recem_cadastrado"]
                    st.rerun()
            
            st.markdown("---")
        
        # Verifica permissão para criar
        if verificar_permissao("prontuario", "criar"):
            with st.expander("➕ Cadastrar Novo Tutor", expanded=False):
                st.markdown("**Dados Pessoais:**")
                
                col_t1, col_t2 = st.columns(2)
                
                with col_t1:
                    tutor_nome = st.text_input("Nome Completo *", key="tutor_nome")
                    tutor_cpf = st.text_input("CPF *", key="tutor_cpf", 
                        placeholder="000.000.000-00",
                        help="CPF ajuda a identificar tutores com nomes parecidos")
                    tutor_rg = st.text_input("RG", key="tutor_rg")
                
                with col_t2:
                    tutor_tel = st.text_input("Telefone", key="tutor_tel", placeholder="(85) 3456-7890")
                    tutor_cel = st.text_input("Celular *", key="tutor_cel", placeholder="(85) 98765-4321")
                    tutor_email = st.text_input("Email", key="tutor_email")
                
                st.markdown("**Endereço:**")
                
                col_e1, col_e2, col_e3 = st.columns([3, 1, 1])
                
                with col_e1:
                    tutor_end = st.text_input("Endereço", key="tutor_end")
                
                with col_e2:
                    tutor_num = st.text_input("Número", key="tutor_num")
                
                with col_e3:
                    tutor_comp = st.text_input("Compl.", key="tutor_comp")
                
                col_e4, col_e5, col_e6 = st.columns(3)
                
                with col_e4:
                    tutor_bairro = st.text_input("Bairro", key="tutor_bairro")
                
                with col_e5:
                    tutor_cidade = st.text_input("Cidade", value="Fortaleza", key="tutor_cidade")
                
                with col_e6:
                    tutor_cep = st.text_input("CEP", key="tutor_cep", placeholder="60000-000")
                
                tutor_obs = st.text_area("Observações", key="tutor_obs", height=100)
                
                if st.button("✅ Cadastrar Tutor", type="primary", key="btn_cadastrar_tutor"):
                    telefone_tutor = (tutor_cel or tutor_tel or "").strip()
                    if not tutor_nome or not telefone_tutor:
                        st.error("❌ Preencha nome e celular/telefone (obrigatórios)")
                    else:
                        conn_tutor = sqlite3.connect(str(DB_PATH))
                        cursor_tutor = conn_tutor.cursor()
                        
                        try:
                            now = _dt.now().isoformat()
                            nome_key = _norm_key(tutor_nome) or ("tutor_" + now.replace(":", "").replace("-", "")[:14])
                            cursor_tutor.execute("""
                                INSERT INTO tutores (
                                    nome, nome_key, telefone, created_at
                                ) VALUES (?, ?, ?, ?)
                            """, (
                                tutor_nome.strip(), nome_key, telefone_tutor, now
                            ))
                            
                            tutor_id_novo = cursor_tutor.lastrowid
                            
                            conn_tutor.commit()
                            
                            # Salva info do tutor recém-cadastrado
                            st.session_state["tutor_recem_cadastrado"] = {
                                "id": tutor_id_novo,
                                "nome": tutor_nome
                            }
                            
                            st.rerun()
                            
                        except sqlite3.IntegrityError:
                            st.error("❌ Tutor com este nome já cadastrado no sistema")
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar: {e}")
                        finally:
                            conn_tutor.close()
        else:
            st.info("ℹ️ Você não tem permissão para cadastrar tutores")
        
        # Lista de tutores (mesmo banco dos cadastros/laudos: /DB/fortcordis.db)
        st.markdown("---")
        st.markdown("### 📋 Tutores Cadastrados")
        
        conn_list = sqlite3.connect(str(DB_PATH))
        
        try:
            tutores_df = pd.read_sql_query("""
                SELECT 
                    t.id,
                    t.nome as 'Nome',
                    t.telefone as 'Contato',
                    COUNT(p.id) as 'Qtd Pacientes'
                FROM tutores t
                LEFT JOIN pacientes p ON t.id = p.tutor_id AND (p.ativo = 1 OR p.ativo IS NULL)
                WHERE (t.ativo = 1 OR t.ativo IS NULL)
                GROUP BY t.id
                ORDER BY t.nome
            """, conn_list)
            
            if not tutores_df.empty:
                tutores_df["Contato"] = tutores_df["Contato"].fillna("Não informado")
            tabela_tabular(
                tutores_df,
                caption=f"Total: {len(tutores_df)} tutor(es)" if not tutores_df.empty else None,
                empty_message="Nenhum tutor cadastrado ainda",
            )
        
        except Exception as e:
            st.error(f"Erro ao carregar tutores: {e}")
        finally:
            conn_list.close()
    
    # ========================================================================
    # ABA 3: PACIENTES
    # ========================================================================
    
    with tab_pacientes:
        st.subheader("🐕 Cadastro de Pacientes")
        
        # ====================================================================
        # FLUXO: Tutor pré-selecionado (veio do cadastro de tutor)
        # ====================================================================
        tutor_pre_selecionado = st.session_state.get("tutor_pre_selecionado")
        
        if tutor_pre_selecionado:
            st.success(f"✅ Cadastrando animal para: **{tutor_pre_selecionado['nome']}**")
            
            if st.button("← Voltar (escolher outro tutor)", key="btn_voltar_tutor"):
                del st.session_state["tutor_pre_selecionado"]
                st.rerun()
            
            st.markdown("---")
        
        # Verifica permissão para criar
        if verificar_permissao("prontuario", "criar"):
            with st.expander("➕ Cadastrar Novo Paciente", expanded=True if tutor_pre_selecionado else False):
                
                # Buscar tutores (mesmo banco dos cadastros: /DB/fortcordis.db)
                conn_pac = sqlite3.connect(str(DB_PATH))
                
                tutores_opcoes = pd.read_sql_query(
                    "SELECT id, nome, telefone FROM tutores WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome",
                    conn_pac
                )
                
                if tutores_opcoes.empty:
                    st.warning("⚠️ Cadastre um tutor primeiro!")
                    conn_pac.close()
                else:
                    # Formata lista de tutores com telefone para facilitar identificação
                    tutores_display = []
                    tutores_dict = {}
                    
                    for _, t in tutores_opcoes.iterrows():
                        tel = t['telefone'] if pd.notna(t['telefone']) else "Sem tel"
                        display = f"{t['nome']} (Tel: {tel})"
                        tutores_display.append(display)
                        tutores_dict[display] = t['id']
                    
                    # Se tem tutor pré-selecionado, encontra ele na lista
                    if tutor_pre_selecionado:
                        # Encontra o display correto do tutor pré-selecionado
                        tutor_pre_display = None
                        for display, tid in tutores_dict.items():
                            if tid == tutor_pre_selecionado['id']:
                                tutor_pre_display = display
                                break
                        
                        index_tutor = tutores_display.index(tutor_pre_display) if tutor_pre_display else 0
                    else:
                        index_tutor = 0
                    
                    pac_tutor = st.selectbox(
                        "Tutor Responsável *",
                        options=tutores_display,
                        index=index_tutor,
                        key="pac_tutor",
                        help="Mostra: Nome (CPF | Telefone) para facilitar identificação"
                    )
                    
                    st.markdown("**Dados do Paciente:**")
                    
                    col_p1, col_p2, col_p3 = st.columns(3)
                    
                    with col_p1:
                        pac_nome = st.text_input("Nome do Animal *", key="pac_nome")
                        pac_especie = st.selectbox("Espécie *", ["Canina", "Felina"], key="pac_especie")
                    
                    with col_p2:
                        pac_raca = st.text_input("Raça", key="pac_raca", placeholder="Ex: SRD, Labrador...")
                        pac_sexo = st.selectbox("Sexo *", ["Macho", "Fêmea"], key="pac_sexo")
                    
                    with col_p3:
                        pac_castrado = st.checkbox("Castrado", key="pac_castrado")
                        pac_peso = st.number_input("Peso (kg)", min_value=0.0, step=0.1, key="pac_peso")
                    
                    col_i1, col_i2 = st.columns(2)
                    
                    with col_i1:
                        pac_idade_anos = st.number_input("Idade (anos)", min_value=0, max_value=30, key="pac_idade_anos")
                    
                    with col_i2:
                        pac_idade_meses = st.number_input("Meses adicionais", min_value=0, max_value=11, key="pac_idade_meses")
                    
                    pac_cor = st.text_input("Cor/Pelagem", key="pac_cor")
                    pac_microchip = st.text_input("Microchip", key="pac_microchip")
                    
                    st.markdown("**Histórico Médico:**")
                    
                    pac_alergias = st.text_area("Alergias conhecidas", key="pac_alergias", height=80)
                    pac_medicamentos = st.text_area("Medicamentos em uso", key="pac_medicamentos", height=80)
                    pac_doencas = st.text_area("Doenças prévias", key="pac_doencas", height=80)
                    
                    col_v1, col_v2 = st.columns(2)
                    
                    with col_v1:
                        pac_vac = st.checkbox("Vacinação em dia", value=True, key="pac_vac")
                    
                    with col_v2:
                        pac_verm = st.checkbox("Vermifugação em dia", value=True, key="pac_verm")
                    
                    pac_obs = st.text_area("Observações gerais", key="pac_obs", height=100)
                    
                    col_btn_pac1, col_btn_pac2 = st.columns(2)
                    
                    with col_btn_pac1:
                        if st.button("✅ Cadastrar Paciente", type="primary", key="btn_cadastrar_paciente"):
                            if not pac_nome or not pac_especie or not pac_sexo:
                                st.error("❌ Preencha nome, espécie e sexo (obrigatórios)")
                            else:
                                try:
                                    tutor_id = tutores_dict[pac_tutor]
                                    now = _dt.now().isoformat()
                                    nome_key = _norm_key(pac_nome) or ("pac_" + now.replace(":", "").replace("-", "")[:14])
                                    # Observações: idade, peso, alergias etc. em um único campo se existir
                                    obs_text = f"Idade: {pac_idade_anos}a {pac_idade_meses}m. Peso: {pac_peso}kg. "
                                    if pac_cor:
                                        obs_text += f"Cor: {pac_cor}. "
                                    if pac_alergias:
                                        obs_text += f"Alergias: {pac_alergias}. "
                                    if pac_medicamentos:
                                        obs_text += f"Meds: {pac_medicamentos}. "
                                    if pac_doencas:
                                        obs_text += f"Doenças: {pac_doencas}. "
                                    obs_text += pac_obs or ""
                                    
                                    cursor_pac = conn_pac.cursor()
                                    cursor_pac.execute("PRAGMA table_info(pacientes)")
                                    colunas = [c[1] for c in cursor_pac.fetchall()]
                                    
                                    if "peso_kg" in colunas and "microchip" in colunas and "observacoes" in colunas:
                                        cursor_pac.execute("""
                                            INSERT INTO pacientes (
                                                tutor_id, nome, nome_key, especie, raca, sexo, nascimento,
                                                peso_kg, microchip, observacoes, created_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            tutor_id, pac_nome.strip(), nome_key, pac_especie, pac_raca or "", pac_sexo,
                                            None, pac_peso or None, pac_microchip or None, obs_text.strip() or None, now
                                        ))
                                    else:
                                        cursor_pac.execute("""
                                            INSERT INTO pacientes (
                                                tutor_id, nome, nome_key, especie, raca, sexo, nascimento, created_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            tutor_id, pac_nome.strip(), nome_key, pac_especie, pac_raca or "", pac_sexo,
                                            None, now
                                        ))
                                    
                                    conn_pac.commit()
                                    st.success(f"✅ Paciente '{pac_nome}' cadastrado com sucesso!")
                                    st.balloons()
                                    
                                    # Limpa tutor pré-selecionado
                                    if "tutor_pre_selecionado" in st.session_state:
                                        del st.session_state["tutor_pre_selecionado"]
                                    
                                    import time
                                    time.sleep(2)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Erro ao cadastrar: {e}")
                                finally:
                                    conn_pac.close()
                    
                    with col_btn_pac2:
                        # Opção de cadastrar outro animal para o mesmo tutor
                        if tutor_pre_selecionado:
                            if st.button("🐕 Cadastrar Outro Animal (mesmo tutor)", key="btn_outro_animal"):
                                st.info("💡 Preencha os dados do próximo animal")
        else:
            st.info("ℹ️ Você não tem permissão para cadastrar pacientes")
        
        # Lista de pacientes (mesmo banco dos cadastros/laudos: /DB/fortcordis.db)
        st.markdown("---")
        st.markdown("### 📋 Pacientes Cadastrados")
        
        try:
            pacientes_df = listar_pacientes_tabela()
            if not pacientes_df.empty:
                pacientes_df["Raça"] = pacientes_df["Raça"].fillna("SRD")
                pacientes_df["Contato"] = pacientes_df["Contato"].fillna("Não informado")
            tabela_tabular(
                pacientes_df,
                caption=f"Total: {len(pacientes_df)} paciente(s)" if not pacientes_df.empty else None,
                empty_message="Nenhum paciente cadastrado ainda",
            )
        except Exception as e:
            st.error(f"Erro ao carregar pacientes: {e}")
    
    # ============================================================================
    # MÓDULO: CONSULTAS E ATENDIMENTOS - FASE 2
    # ============================================================================
    #
    # SUBSTITUA a aba "Consultas" pelo código abaixo
    # Procure por: with tab_consultas:
    #
    # ============================================================================

        with tab_consultas:
            st.subheader("🩺 Consultas e Atendimentos")
            
            # Verifica permissão
            if not verificar_permissao("prontuario", "criar"):
                st.warning("⚠️ Você não tem permissão para registrar consultas")
                st.stop()
            
            # ====================================================================
            # SELEÇÃO DE PACIENTE
            # ====================================================================
            
            st.markdown("### 1️⃣ Selecione o Paciente")
            
            try:
                pacientes_df = listar_pacientes_com_tutor()
            except Exception:
                pacientes_df = pd.DataFrame()
            
            if pacientes_df.empty:
                st.warning("⚠️ Nenhum paciente cadastrado. Cadastre um paciente primeiro!")
                st.stop()
            
            # Cria lista formatada de pacientes
            pacientes_opcoes = {}
            for _, pac in pacientes_df.iterrows():
                tel = pac['telefone'] if pd.notna(pac.get('telefone')) else "Sem tel"
                raca = (pac['raca'] or "SRD").title() if pd.notna(pac.get('raca')) else "SRD"
                display = f"{pac['paciente'].title()} ({pac['especie']}, {raca}) - Tutor: {pac['tutor'].title()} (Tel: {tel})"
                pacientes_opcoes[display] = pac['id']
            
            # Verifica se tem paciente pré-selecionado
            paciente_pre = st.session_state.get('paciente_consulta_id')
            index_pac = 0
            
            if paciente_pre:
                for idx, (display, pac_id) in enumerate(pacientes_opcoes.items()):
                    if pac_id == paciente_pre:
                        index_pac = idx
                        break
            
            paciente_selecionado_display = st.selectbox(
                "Paciente:",
                options=list(pacientes_opcoes.keys()),
                index=index_pac,
                key="consulta_paciente_select"
            )
            
            paciente_id = pacientes_opcoes[paciente_selecionado_display]
            
            # Busca dados completos do paciente
            paciente_dados = pacientes_df[pacientes_df['id'] == paciente_id].iloc[0]
            
            # Mostra resumo do paciente
            with st.expander("📋 Dados do Paciente", expanded=False):
                col_p1, col_p2, col_p3 = st.columns(3)
                
                with col_p1:
                    st.write(f"**Nome:** {paciente_dados['paciente'].title()}")
                    st.write(f"**Espécie:** {paciente_dados['especie']}")
                    raca_display = (paciente_dados['raca'] or "SRD").title() if pd.notna(paciente_dados.get('raca')) else "SRD"
                    st.write(f"**Raça:** {raca_display}")
                
                with col_p2:
                    st.write(f"**Tutor:** {paciente_dados['tutor'].title()}")
                    tel_display = paciente_dados.get('telefone') if pd.notna(paciente_dados.get('telefone')) else "Não informado"
                    st.write(f"**Contato:** {tel_display}")
                
                with col_p3:
                    nasc = paciente_dados.get('nascimento') if pd.notna(paciente_dados.get('nascimento')) else "Não informado"
                    st.write(f"**Nascimento:** {nasc}")
                    peso_val = paciente_dados.get('peso_kg')
                    peso = f"{peso_val:.1f} kg" if pd.notna(peso_val) and peso_val and float(peso_val) > 0 else "Não informado"
                    st.write(f"**Peso:** {peso}")
            
            st.markdown("---")
            
            # ====================================================================
            # FORMULÁRIO DE CONSULTA
            # ====================================================================
            
            st.markdown("### 2️⃣ Dados da Consulta")
            
            with st.form("form_nova_consulta"):
                
                # CABEÇALHO
                st.markdown("#### 📅 Informações Gerais")
                
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    data_consulta = st.date_input(
                        "Data da Consulta *",
                        value=_dt.now().date(),
                        key="cons_data"
                    )
                
                with col_info2:
                    hora_consulta = st.time_input(
                        "Hora",
                        value=_dt.now().time(),
                        key="cons_hora"
                    )
                
                with col_info3:
                    tipo_atendimento = st.selectbox(
                        "Tipo de Atendimento *",
                        ["Consulta", "Retorno", "Emergência", "Procedimento", "Vacinação"],
                        key="cons_tipo"
                    )
                
                motivo_consulta = st.text_area(
                    "Queixa Principal / Motivo da Consulta *",
                    placeholder="Ex: Tosse há 3 dias, vômitos, claudicação...",
                    height=100,
                    key="cons_motivo"
                )
                
                # ANAMNESE
                st.markdown("---")
                st.markdown("#### 📋 Anamnese")
                
                anamnese = st.text_area(
                    "Histórico Atual da Doença",
                    placeholder="História detalhada: início dos sintomas, evolução, tratamentos prévios...",
                    height=150,
                    key="cons_anamnese"
                )
                
                col_anam1, col_anam2 = st.columns(2)
                
                with col_anam1:
                    alimentacao = st.text_area(
                        "Alimentação",
                        placeholder="Tipo de ração, quantidade, frequência...",
                        height=80,
                        key="cons_alim"
                    )
                
                with col_anam2:
                    ambiente = st.text_area(
                        "Ambiente",
                        placeholder="Casa/apartamento, quintal, outros animais...",
                        height=80,
                        key="cons_amb"
                    )
                
                comportamento = st.text_area(
                    "Comportamento",
                    placeholder="Alterações comportamentais, atividade, sono...",
                    height=80,
                    key="cons_comport"
                )
                
                # EXAME FÍSICO
                st.markdown("---")
                st.markdown("#### 🩺 Exame Físico")
                
                col_ef1, col_ef2, col_ef3, col_ef4 = st.columns(4)
                
                with col_ef1:
                    peso_val = paciente_dados.get('peso_kg')
                    peso_atual = st.number_input(
                        "Peso (kg) *",
                        min_value=0.0,
                        value=float(peso_val) if pd.notna(peso_val) and peso_val and float(peso_val) > 0 else 0.0,
                        step=0.1,
                        key="cons_peso"
                    )
                
                with col_ef2:
                    temperatura = st.number_input(
                        "Temperatura (°C)",
                        min_value=35.0,
                        max_value=43.0,
                        value=38.5,
                        step=0.1,
                        key="cons_temp"
                    )
                
                with col_ef3:
                    fc = st.number_input(
                        "FC (bpm)",
                        min_value=0,
                        max_value=300,
                        value=100,
                        key="cons_fc"
                    )
                
                with col_ef4:
                    fr = st.number_input(
                        "FR (mpm)",
                        min_value=0,
                        max_value=150,
                        value=30,
                        key="cons_fr"
                    )
                
                col_ef5, col_ef6, col_ef7 = st.columns(3)
                
                with col_ef5:
                    tpc = st.selectbox(
                        "TPC",
                        ["< 2 segundos (normal)", "2-3 segundos", "> 3 segundos"],
                        key="cons_tpc"
                    )
                
                with col_ef6:
                    mucosas = st.selectbox(
                        "Mucosas",
                        ["Róseas", "Pálidas", "Ictéricas", "Hiperêmicas", "Cianóticas"],
                        key="cons_mucosas"
                    )
                
                with col_ef7:
                    hidratacao = st.selectbox(
                        "Hidratação",
                        ["Boa", "Leve desidratação (5%)", "Moderada (7-8%)", "Grave (>10%)"],
                        key="cons_hidrat"
                    )
                
                col_ef8, col_ef9 = st.columns(2)
                
                with col_ef8:
                    linfonodos = st.text_input(
                        "Linfonodos",
                        placeholder="Ex: Sem alterações, aumentados...",
                        key="cons_linf"
                    )
                
                with col_ef9:
                    auscultacao_card = st.text_input(
                        "Auscultação Cardíaca",
                        placeholder="Ex: Ritmo regular, sopro...",
                        key="cons_ausc_card"
                    )
                
                auscultacao_resp = st.text_input(
                    "Auscultação Respiratória",
                    placeholder="Ex: MV presente bilateralmente...",
                    key="cons_ausc_resp"
                )
                
                palpacao_abd = st.text_input(
                    "Palpação Abdominal",
                    placeholder="Ex: Sem alterações, dor em...",
                    key="cons_palp_abd"
                )
                
                exame_fisico_geral = st.text_area(
                    "Outros Achados do Exame Físico",
                    placeholder="Pele, pelos, olhos, ouvidos, boca, locomotor...",
                    height=100,
                    key="cons_ef_geral"
                )
                
                # AVALIAÇÃO E CONDUTA
                st.markdown("---")
                st.markdown("#### 💊 Avaliação e Conduta")
                
                diagnostico_presuntivo = st.text_area(
                    "Diagnóstico Presuntivo *",
                    placeholder="Hipótese diagnóstica principal",
                    height=80,
                    key="cons_diag_pres"
                )
                
                diagnostico_diferencial = st.text_area(
                    "Diagnósticos Diferenciais",
                    placeholder="Outras possibilidades diagnósticas",
                    height=80,
                    key="cons_diag_dif"
                )
                
                diagnostico_definitivo = st.text_area(
                    "Diagnóstico Definitivo",
                    placeholder="Após exames complementares (se aplicável)",
                    height=80,
                    key="cons_diag_def"
                )
                
                conduta = st.text_area(
                    "Conduta Terapêutica *",
                    placeholder="Tratamento prescrito, medicações, procedimentos...",
                    height=120,
                    key="cons_conduta"
                )
                
                exames_solicitados = st.text_area(
                    "Exames Complementares Solicitados",
                    placeholder="Hemograma, bioquímica, raio-X, ultrassom...",
                    height=80,
                    key="cons_exames"
                )
                
                procedimentos = st.text_area(
                    "Procedimentos Realizados",
                    placeholder="Coleta de sangue, aplicação de medicamento...",
                    height=80,
                    key="cons_proced"
                )
                
                orientacoes = st.text_area(
                    "Orientações ao Tutor *",
                    placeholder="Cuidados, administração de medicamentos, retorno...",
                    height=100,
                    key="cons_orient"
                )
                
                col_prog1, col_prog2 = st.columns(2)
                
                with col_prog1:
                    prognostico = st.selectbox(
                        "Prognóstico",
                        ["Bom", "Reservado", "Ruim", "A definir"],
                        key="cons_prog"
                    )
                
                with col_prog2:
                    data_retorno = st.date_input(
                        "Data de Retorno (se necessário)",
                        value=None,
                        key="cons_retorno"
                    )
                
                observacoes = st.text_area(
                    "Observações Gerais",
                    placeholder="Informações adicionais relevantes...",
                    height=80,
                    key="cons_obs"
                )
                
                # BOTÃO ENVIAR
                st.markdown("---")
                submitted = st.form_submit_button("✅ Registrar Consulta", type="primary")
                
                if submitted:
                    # Validações
                    if not motivo_consulta or not diagnostico_presuntivo or not conduta or not orientacoes:
                        st.error("❌ Preencha todos os campos obrigatórios (marcados com *)")
                    elif peso_atual <= 0:
                        st.error("❌ Informe o peso atual do paciente")
                    else:
                        usuario = st.session_state.get("usuario_id")
                        veterinario_id = usuario["id"] if isinstance(usuario, dict) else usuario
                        data_retorno_str = data_retorno.strftime("%Y-%m-%d") if data_retorno else ""
                        consulta_id, err = criar_consulta(
                            paciente_id=paciente_id,
                            tutor_id=int(paciente_dados["tutor_id"]),
                            veterinario_id=veterinario_id,
                            data_consulta=data_consulta.strftime("%Y-%m-%d"),
                            hora_consulta=hora_consulta.strftime("%H:%M"),
                            tipo_atendimento=tipo_atendimento,
                            motivo_consulta=motivo_consulta or "",
                            anamnese=anamnese or "",
                            historico_atual=anamnese or "",
                            alimentacao=alimentacao or "",
                            ambiente=ambiente or "",
                            comportamento=comportamento or "",
                            peso_kg=peso_atual,
                            temperatura_c=temperatura,
                            frequencia_cardiaca=fc,
                            frequencia_respiratoria=fr,
                            tpc=tpc or "",
                            mucosas=mucosas or "",
                            hidratacao=hidratacao or "",
                            linfonodos=linfonodos or "",
                            auscultacao_cardiaca=auscultacao_card or "",
                            auscultacao_respiratoria=auscultacao_resp or "",
                            palpacao_abdominal=palpacao_abd or "",
                            exame_fisico_geral=exame_fisico_geral or "",
                            diagnostico_presuntivo=diagnostico_presuntivo or "",
                            diagnostico_diferencial=diagnostico_diferencial or "",
                            diagnostico_definitivo=diagnostico_definitivo or "",
                            conduta_terapeutica=conduta or "",
                            exames_solicitados=exames_solicitados or "",
                            procedimentos_realizados=procedimentos or "",
                            orientacoes=orientacoes or "",
                            prognostico=prognostico or "",
                            data_retorno=data_retorno_str,
                            observacoes=observacoes or "",
                            atualizar_peso=True,
                        )
                        if err:
                            st.error(f"❌ Erro ao registrar consulta: {err}")
                        else:
                            st.success(f"✅ Consulta registrada com sucesso! (ID: {consulta_id})")
                            st.balloons()
                            if "paciente_consulta_id" in st.session_state:
                                del st.session_state["paciente_consulta_id"]
                            st.info("💡 A consulta foi salva no prontuário do paciente")
                            import time
                            time.sleep(2)
                            st.rerun()
            
            # ====================================================================
            # HISTÓRICO DE CONSULTAS
            # ====================================================================
            
            st.markdown("---")
            st.markdown("### 📋 Consultas Recentes")
            
            try:
                consultas_df = listar_consultas_recentes(limite=10)
                if not consultas_df.empty:
                    consultas_df["Paciente"] = consultas_df["Paciente"].str.title()
                    consultas_df["Tutor"] = consultas_df["Tutor"].str.title()
                tabela_tabular(
                    consultas_df,
                    caption=f"Mostrando as {len(consultas_df)} consultas mais recentes" if not consultas_df.empty else None,
                    empty_message="📋 Nenhuma consulta registrada ainda",
                )
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar histórico: {e}")

# ============================================================================
# TELA: LAUDOS E EXAMES (AQUI VIRÁ TODO O SEU CÓDIGO)
# ============================================================================

    # ============================================================================
    # FUNÇÕES DE GERENCIAMENTO DE LAUDOS NO BANCO
    # ============================================================================
    # (json e datetime já importados no topo do módulo)

    def salvar_laudo_no_banco(tipo_exame, dados_laudo, caminho_json, caminho_pdf):
        """Salva o laudo no banco de dados (usa o mesmo banco do app)"""
        _db = Path(__file__).resolve().parent / "fortcordis.db"
        try:
            conn = sqlite3.connect(str(_db))
            cursor = conn.cursor()
            
            tabelas = {
                "ecocardiograma": "laudos_ecocardiograma",
                "eletrocardiograma": "laudos_eletrocardiograma",
                "pressao_arterial": "laudos_pressao_arterial"
            }
            
            tabela = tabelas.get(tipo_exame.lower())
            
            if not tabela:
                return None, f"Tipo inválido: {tipo_exame}"
            
            # Dados comuns
            cursor.execute(f"""
                INSERT INTO {tabela} (
                    nome_paciente, especie, raca, idade, peso_kg,
                    data_exame, nome_clinica,
                    conclusao, observacoes,
                    arquivo_json, arquivo_pdf,
                    status, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                dados_laudo.get('nome_animal', ''),
                dados_laudo.get('especie', ''),
                dados_laudo.get('raca', ''),
                dados_laudo.get('idade', ''),
                float(dados_laudo.get('peso', 0)),
                dados_laudo.get('data', _dt.now().strftime('%Y-%m-%d')),
                dados_laudo.get('clinica', ''),
                dados_laudo.get('conclusao', ''),
                dados_laudo.get('observacoes', ''),
                str(caminho_json),
                str(caminho_pdf),
                'finalizado'
            ))
            
            laudo_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return laudo_id, None
            
        except Exception as e:
            return None, str(e)

    def buscar_laudos(tipo_exame=None, nome_paciente=None):
        """Busca laudos no banco (usa pasta do projeto - Streamlit Cloud)"""
        _db = Path(__file__).resolve().parent / "fortcordis.db"
        try:
            conn = sqlite3.connect(str(_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            tabelas = [
                "laudos_ecocardiograma",
                "laudos_eletrocardiograma", 
                "laudos_pressao_arterial"
            ]
            
            laudos = []
            
            for tabela in tabelas:
                query = f"""
                    SELECT 
                        id, tipo_exame, nome_paciente, especie, data_exame,
                        nome_clinica, arquivo_json, arquivo_pdf
                    FROM {tabela}
                    WHERE 1=1
                """
                params = []
                
                if nome_paciente:
                    query += " AND UPPER(nome_paciente) LIKE UPPER(?)"
                    params.append(f"%{nome_paciente}%")
                
                query += " ORDER BY data_exame DESC, id DESC"
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    laudos.append(dict(row))
            
            conn.close()
            
            laudos.sort(key=lambda x: x.get('data_exame', ''), reverse=True)
            
            return laudos, None
            
        except Exception as e:
            return [], str(e)

    def carregar_laudo_para_edicao(caminho_json):
        """Carrega JSON do laudo para editar"""
        try:
            json_path = Path(caminho_json)
            
            if not json_path.exists():
                return None, "Arquivo não encontrado"
            
            with open(json_path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            return dados, None
            
        except Exception as e:
            return None, str(e)

    def atualizar_laudo_editado(laudo_id, tipo_exame, caminho_json, dados_atualizados, novo_pdf_path=None):
        """Atualiza laudo após edição"""
        try:
            # Atualiza JSON
            with open(caminho_json, 'w', encoding='utf-8') as f:
                json.dump(dados_atualizados, f, ensure_ascii=False, indent=2)
            
            # Atualiza banco se necessário (usa DB_PATH do projeto para deploy)
            if novo_pdf_path:
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                
                tabelas = {
                    "ecocardiograma": "laudos_ecocardiograma",
                    "eletrocardiograma": "laudos_eletrocardiograma",
                    "pressao_arterial": "laudos_pressao_arterial"
                }
                
                tabela = tabelas.get(tipo_exame.lower())
                
                cursor.execute(f"""
                    UPDATE {tabela}
                    SET arquivo_pdf = ?, data_modificacao = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (str(novo_pdf_path), laudo_id))
                
                conn.commit()
                conn.close()
            
            return True, None
            
        except Exception as e:
            return False, str(e)

    # ============================================================================
    # FIM DAS FUNÇÕES DE GERENCIAMENTO
    # ============================================================================
