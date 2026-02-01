# ============================================================================
# VERSÃO FINAL DO DROPDOWN DE CLÍNICAS (BUSCA DE clinicas_parceiras)
# ============================================================================
#
# SUBSTITUA as funções no código dos laudos por estas versões
#
# ============================================================================

def buscar_clinicas_cadastradas_laudos():
    """
    Busca clínicas da tabela clinicas_parceiras (menu Cadastros)
    Esta é a tabela CORRETA usada pelo sistema
    """
    DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # IMPORTANTE: Busca de clinicas_parceiras (não de clinicas!)
        cursor.execute("""
            SELECT 
                id, 
                nome, 
                COALESCE(endereco, '') || 
                    CASE WHEN bairro IS NOT NULL THEN ', ' || bairro ELSE '' END || 
                    CASE WHEN cidade IS NOT NULL THEN ', ' || cidade ELSE '' END as endereco_completo,
                COALESCE(telefone, whatsapp) as telefone
            FROM clinicas_parceiras
            WHERE ativo = 1
            ORDER BY nome
        """)
        
        clinicas = cursor.fetchall()
        conn.close()
        
        return clinicas
    except Exception as e:
        st.error(f"Erro ao buscar clínicas: {e}")
        return []

def cadastrar_clinica_rapido_laudos(nome, endereco=None, telefone=None):
    """
    Cadastra nova clínica na tabela clinicas_parceiras
    """
    DB_PATH = Path.home() / "FortCordis" / "data" / "fortcordis.db"
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # IMPORTANTE: Insere em clinicas_parceiras (não em clinicas!)
        cursor.execute("""
            INSERT INTO clinicas_parceiras (
                nome, endereco, cidade, telefone, ativo
            ) VALUES (?, ?, 'Fortaleza', ?, 1)
        """, (nome, endereco, telefone))
        
        clinica_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return clinica_id, "success"
    except Exception as e:
        return None, str(e)

# ============================================================================
# CÓDIGO DO DROPDOWN (versão limpa e funcional)
# ============================================================================

        # ====================================================================
        # SELEÇÃO DE CLÍNICA
        # ====================================================================
        
        st.markdown("#### 🏥 Clínica Solicitante")
        
        clinicas_cadastradas = buscar_clinicas_cadastradas_laudos()
        
        if not clinicas_cadastradas:
            st.warning("⚠️ Nenhuma clínica cadastrada!")
            st.info("💡 Cadastre clínicas em: Menu → Cadastros → Clínicas Parceiras")
            clinica = None
            clinica_id = None
        
        else:
            # Cria dropdown
            clinicas_dict = {}
            
            for cli in clinicas_cadastradas:
                # cli = (id, nome, endereco_completo, telefone)
                endereco = cli[2] if cli[2] else "Sem endereço"
                telefone = cli[3] if cli[3] else "Sem telefone"
                
                # Formato exibido no dropdown
                display = f"{cli[1]} ({endereco} | {telefone})"
                
                clinicas_dict[display] = {
                    'id': cli[0],
                    'nome': cli[1]
                }
            
            # Adiciona opção de cadastrar nova
            clinicas_dict["➕ Cadastrar Nova Clínica"] = {'id': None, 'nome': None}
            
            # Dropdown principal
            clinica_sel = st.selectbox(
                "Selecione a Clínica *",
                options=list(clinicas_dict.keys()),
                key="dropdown_clinica_laudo",
                help="Clínicas do menu Cadastros"
            )
            
            # Processa seleção
            if clinica_sel == "➕ Cadastrar Nova Clínica":
                st.info("💡 Cadastrando nova clínica...")
                
                with st.expander("📝 Dados da Nova Clínica", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nova_nome = st.text_input("Nome da Clínica *", key="nova_cli_nome")
                        nova_end = st.text_input("Endereço", key="nova_cli_end")
                    
                    with col2:
                        nova_tel = st.text_input("Telefone", key="nova_cli_tel")
                    
                    if st.button("✅ Cadastrar Clínica", key="btn_cad_cli", type="primary"):
                        if nova_nome:
                            cli_id, msg = cadastrar_clinica_rapido_laudos(
                                nova_nome, nova_end, nova_tel
                            )
                            
                            if cli_id:
                                st.success(f"✅ Clínica '{nova_nome}' cadastrada!")
                                st.info("💡 Selecione ela no dropdown acima")
                                st.balloons()
                                import time
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f"❌ Erro: {msg}")
                        else:
                            st.error("❌ Nome obrigatório")
                
                clinica = None
                clinica_id = None
            
            else:
                # Clínica válida selecionada
                clinica_id = clinicas_dict[clinica_sel]['id']
                clinica = clinicas_dict[clinica_sel]['nome']
                
                st.success(f"✅ Clínica: **{clinica}**")

# ============================================================================
# CHECKLIST DE IMPLEMENTAÇÃO
# ============================================================================

"""
CHECKLIST FINAL:

1. ✅ Execute: python migrar_clinicas_para_parceiras.py
2. ✅ Substitua as funções buscar_clinicas_cadastradas_laudos() e 
      cadastrar_clinica_rapido_laudos() pelas versões acima
3. ✅ Substitua o código do dropdown pelo código acima
4. ✅ Recarregue o sistema (R)
5. ✅ Vá em Cadastros → Clínicas Parceiras
6. ✅ Confirme que as 46 clínicas aparecem
7. ✅ Vá em Laudos e Exames
8. ✅ Veja o dropdown com TODAS as clínicas
9. ✅ Funciona! 🎉

IMPORTANTE:
- As funções DEVEM buscar de clinicas_parceiras
- As funções DEVEM inserir em clinicas_parceiras
- O menu Cadastros já usa clinicas_parceiras (correto)
- Depois da migração, tudo ficará unificado
"""
