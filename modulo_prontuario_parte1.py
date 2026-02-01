# ============================================================================
# MÓDULO: PRONTUÁRIO ELETRÔNICO - PARTE 1
# ============================================================================
#
# 📍 ONDE ADICIONAR: No menu principal, adicione uma nova opção "📋 Prontuário"
#
# Modifique o menu_principal para incluir:
# menu_principal = st.sidebar.radio(
#     "Navegação",
#     [
#         "🏠 Dashboard",
#         "📅 Agendamentos",
#         "📋 Prontuário",  # ← NOVA OPÇÃO
#         "🩺 Laudos e Exames",
#         "💊 Prescrições",
#         "💰 Financeiro",
#         "🏢 Cadastros",
#         "⚙️ Configurações"
#     ]
# )
#
# ============================================================================

# ============================================================================
# TELA: PRONTUÁRIO
# ============================================================================

elif menu_principal == "📋 Prontuário":
    st.title("📋 Prontuário Eletrônico")
    
    # Verifica permissão
    if not verificar_permissao("prontuario", "ver"):
        st.error("❌ Você não tem permissão para acessar o prontuário")
        st.stop()
    
    # Abas do prontuário
    tab_busca, tab_tutores, tab_pacientes, tab_consultas = st.tabs([
        "🔍 Busca Rápida",
        "👨‍👩‍👧 Tutores",
        "🐕 Pacientes",
        "🩺 Consultas"
    ])
    
    # ========================================================================
    # ABA 1: BUSCA RÁPIDA
    # ========================================================================
    
    with tab_busca:
        st.subheader("🔍 Busca Rápida de Pacientes")
        
        col_busca1, col_busca2 = st.columns([3, 1])
        
        with col_busca1:
            termo_busca = st.text_input(
                "Digite o nome do paciente ou tutor:",
                placeholder="Ex: Thor, Maria Silva...",
                key="busca_paciente"
            )
        
        with col_busca2:
            tipo_busca = st.selectbox(
                "Buscar por:",
                ["Paciente", "Tutor"],
                key="tipo_busca"
            )
        
        if termo_busca:
            DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
            conn_pront = sqlite3.connect(str(DB_PATH_AUTH))
            
            if tipo_busca == "Paciente":
                query = """
                    SELECT 
                        p.id,
                        p.nome as paciente,
                        p.especie,
                        p.raca,
                        p.idade_anos,
                        t.nome as tutor,
                        t.telefone,
                        p.ativo
                    FROM pacientes p
                    JOIN tutores t ON p.tutor_id = t.id
                    WHERE p.nome LIKE ? AND p.ativo = 1
                    ORDER BY p.nome
                """
                resultados = pd.read_sql_query(query, conn_pront, params=(f"%{termo_busca}%",))
            else:
                query = """
                    SELECT 
                        p.id,
                        p.nome as paciente,
                        p.especie,
                        p.raca,
                        p.idade_anos,
                        t.nome as tutor,
                        t.telefone,
                        p.ativo
                    FROM pacientes p
                    JOIN tutores t ON p.tutor_id = t.id
                    WHERE t.nome LIKE ? AND p.ativo = 1
                    ORDER BY t.nome, p.nome
                """
                resultados = pd.read_sql_query(query, conn_pront, params=(f"%{termo_busca}%",))
            
            conn_pront.close()
            
            if not resultados.empty:
                st.success(f"✅ Encontrados {len(resultados)} resultado(s)")
                
                # Exibe resultados
                for _, row in resultados.iterrows():
                    with st.expander(f"🐾 {row['paciente']} ({row['especie']}) - Tutor: {row['tutor']}"):
                        col_info1, col_info2, col_info3 = st.columns(3)
                        
                        with col_info1:
                            st.write(f"**Paciente:** {row['paciente']}")
                            st.write(f"**Espécie:** {row['especie']}")
                            st.write(f"**Raça:** {row['raca'] or 'Não informada'}")
                        
                        with col_info2:
                            st.write(f"**Tutor:** {row['tutor']}")
                            st.write(f"**Telefone:** {row['telefone'] or 'Não informado'}")
                        
                        with col_info3:
                            idade = f"{row['idade_anos']} ano(s)" if row['idade_anos'] else "Não informada"
                            st.write(f"**Idade:** {idade}")
                        
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        
                        with col_btn1:
                            if st.button("📋 Ver Prontuário", key=f"ver_pront_{row['id']}"):
                                st.info("Em desenvolvimento...")
                        
                        with col_btn2:
                            if st.button("🩺 Nova Consulta", key=f"nova_cons_{row['id']}"):
                                st.session_state['paciente_consulta_id'] = row['id']
                                st.info("Vá para a aba 'Consultas'")
                        
                        with col_btn3:
                            if st.button("✏️ Editar", key=f"editar_pac_{row['id']}"):
                                st.info("Em desenvolvimento...")
            else:
                st.warning(f"⚠️ Nenhum resultado encontrado para '{termo_busca}'")
    
    # ========================================================================
    # ABA 2: TUTORES
    # ========================================================================
    
    with tab_tutores:
        st.subheader("👨‍👩‍👧 Cadastro de Tutores")
        
        # Verifica permissão para criar
        if verificar_permissao("prontuario", "criar"):
            with st.expander("➕ Cadastrar Novo Tutor", expanded=False):
                st.markdown("**Dados Pessoais:**")
                
                col_t1, col_t2 = st.columns(2)
                
                with col_t1:
                    tutor_nome = st.text_input("Nome Completo *", key="tutor_nome")
                    tutor_cpf = st.text_input("CPF", key="tutor_cpf", placeholder="000.000.000-00")
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
                    if not tutor_nome or not tutor_cel:
                        st.error("❌ Preencha nome e celular (obrigatórios)")
                    else:
                        DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
                        conn_tutor = sqlite3.connect(str(DB_PATH_AUTH))
                        cursor_tutor = conn_tutor.cursor()
                        
                        try:
                            usuario = obter_usuario_logado()
                            
                            cursor_tutor.execute("""
                                INSERT INTO tutores (
                                    nome, cpf, rg, telefone, celular, email,
                                    endereco, numero, complemento, bairro, cidade, cep,
                                    observacoes, criado_por
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                tutor_nome, tutor_cpf, tutor_rg, tutor_tel, tutor_cel, tutor_email,
                                tutor_end, tutor_num, tutor_comp, tutor_bairro, tutor_cidade, tutor_cep,
                                tutor_obs, usuario["id"]
                            ))
                            
                            conn_tutor.commit()
                            st.success(f"✅ Tutor '{tutor_nome}' cadastrado com sucesso!")
                            st.balloons()
                            
                        except sqlite3.IntegrityError:
                            st.error(f"❌ CPF '{tutor_cpf}' já cadastrado")
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar: {e}")
                        finally:
                            conn_tutor.close()
        else:
            st.info("ℹ️ Você não tem permissão para cadastrar tutores")
        
        # Lista de tutores
        st.markdown("---")
        st.markdown("### 📋 Tutores Cadastrados")
        
        DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
        conn_list = sqlite3.connect(str(DB_PATH_AUTH))
        
        try:
            tutores_df = pd.read_sql_query("""
                SELECT 
                    t.id,
                    t.nome as 'Nome',
                    t.cpf as 'CPF',
                    t.celular as 'Celular',
                    t.cidade as 'Cidade',
                    COUNT(p.id) as 'Qtd Pacientes'
                FROM tutores t
                LEFT JOIN pacientes p ON t.id = p.tutor_id AND p.ativo = 1
                WHERE t.ativo = 1
                GROUP BY t.id
                ORDER BY t.nome
            """, conn_list)
            
            if not tutores_df.empty:
                st.dataframe(tutores_df.drop('id', axis=1), use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(tutores_df)} tutor(es)")
            else:
                st.info("Nenhum tutor cadastrado ainda")
        
        except Exception as e:
            st.error(f"Erro ao carregar tutores: {e}")
        finally:
            conn_list.close()
    
    # ========================================================================
    # ABA 3: PACIENTES
    # ========================================================================
    
    with tab_pacientes:
        st.subheader("🐕 Cadastro de Pacientes")
        
        # Verifica permissão para criar
        if verificar_permissao("prontuario", "criar"):
            with st.expander("➕ Cadastrar Novo Paciente", expanded=False):
                
                # Primeiro: Selecionar tutor
                DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
                conn_pac = sqlite3.connect(str(DB_PATH_AUTH))
                
                tutores_opcoes = pd.read_sql_query(
                    "SELECT id, nome FROM tutores WHERE ativo = 1 ORDER BY nome",
                    conn_pac
                )
                
                if tutores_opcoes.empty:
                    st.warning("⚠️ Cadastre um tutor primeiro!")
                    conn_pac.close()
                else:
                    tutores_dict = dict(zip(tutores_opcoes['nome'], tutores_opcoes['id']))
                    
                    pac_tutor = st.selectbox(
                        "Tutor Responsável *",
                        options=list(tutores_dict.keys()),
                        key="pac_tutor"
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
                    
                    if st.button("✅ Cadastrar Paciente", type="primary", key="btn_cadastrar_paciente"):
                        if not pac_nome or not pac_especie or not pac_sexo:
                            st.error("❌ Preencha nome, espécie e sexo (obrigatórios)")
                        else:
                            try:
                                usuario = obter_usuario_logado()
                                tutor_id = tutores_dict[pac_tutor]
                                
                                cursor_pac = conn_pac.cursor()
                                cursor_pac.execute("""
                                    INSERT INTO pacientes (
                                        tutor_id, nome, especie, raca, sexo, castrado,
                                        idade_anos, idade_meses, peso_kg, cor_pelagem, microchip,
                                        alergias, medicamentos_uso, doencas_previas,
                                        vacinacao_em_dia, vermifugacao_em_dia, observacoes,
                                        criado_por
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    tutor_id, pac_nome, pac_especie, pac_raca, pac_sexo, int(pac_castrado),
                                    pac_idade_anos, pac_idade_meses, pac_peso, pac_cor, pac_microchip,
                                    pac_alergias, pac_medicamentos, pac_doencas,
                                    int(pac_vac), int(pac_verm), pac_obs,
                                    usuario["id"]
                                ))
                                
                                conn_pac.commit()
                                st.success(f"✅ Paciente '{pac_nome}' cadastrado com sucesso!")
                                st.balloons()
                                
                            except Exception as e:
                                st.error(f"❌ Erro ao cadastrar: {e}")
                            finally:
                                conn_pac.close()
        else:
            st.info("ℹ️ Você não tem permissão para cadastrar pacientes")
        
        # Lista de pacientes
        st.markdown("---")
        st.markdown("### 📋 Pacientes Cadastrados")
        
        DB_PATH_AUTH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
        conn_list_pac = sqlite3.connect(str(DB_PATH_AUTH))
        
        try:
            pacientes_df = pd.read_sql_query("""
                SELECT 
                    p.id,
                    p.nome as 'Paciente',
                    p.especie as 'Espécie',
                    p.raca as 'Raça',
                    p.idade_anos || ' ano(s)' as 'Idade',
                    t.nome as 'Tutor',
                    t.celular as 'Contato'
                FROM pacientes p
                JOIN tutores t ON p.tutor_id = t.id
                WHERE p.ativo = 1
                ORDER BY p.nome
            """, conn_list_pac)
            
            if not pacientes_df.empty:
                st.dataframe(pacientes_df.drop('id', axis=1), use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(pacientes_df)} paciente(s)")
            else:
                st.info("Nenhum paciente cadastrado ainda")
        
        except Exception as e:
            st.error(f"Erro ao carregar pacientes: {e}")
        finally:
            conn_list_pac.close()
    
    # ========================================================================
    # ABA 4: CONSULTAS (Em desenvolvimento)
    # ========================================================================
    
    with tab_consultas:
        st.subheader("🩺 Consultas e Atendimentos")
        st.info("🚧 Esta seção será implementada na próxima fase")
        st.caption("Aqui você poderá registrar consultas, exames físicos, diagnósticos e condutas")
