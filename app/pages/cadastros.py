# app/pages/cadastros.py
"""Página Cadastros: clínicas parceiras, serviços e tabelas de preço."""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from app.components import tabela_tabular
from app.config import DB_PATH
from fortcordis_modules.database import garantir_tabelas_financeiro_extras, garantir_tabelas_preco
from modules.rbac import verificar_permissao


def render_cadastros():
    st.title("🏢 Cadastros")
    
    tab_c1, tab_c2 = st.tabs(["🏥 Clínicas Parceiras", "🛠️ Serviços"])
    
    with tab_c1:
        garantir_tabelas_financeiro_extras()
        st.subheader("Clínicas Parceiras")
        
        # ⚠️ PROTEÇÃO: Só quem pode criar vê o formulário
        if verificar_permissao("cadastros", "criar"):
            with st.expander("➕ Cadastrar Nova Clínica", expanded=True):
                st.markdown("**Informações da Clínica**")
                
                col_c1, col_c2 = st.columns(2)
                
                with col_c1:
                    novo_nome = st.text_input("Nome da Clínica *", key="novo_cli_nome", 
                        help="Digite EXATAMENTE como você preenche no campo 'Clínica' dos laudos")
                    novo_end = st.text_input("Endereço", key="novo_cli_end")
                    novo_cidade = st.text_input("Cidade", value="Fortaleza", key="novo_cli_cidade")
                
                with col_c2:
                    novo_tel = st.text_input("Telefone", key="novo_cli_tel", placeholder="(85) 3456-7890")
                    novo_whats = st.text_input("WhatsApp", key="novo_cli_whats", placeholder="(85) 98765-4321")
                    novo_cnpj = st.text_input("CNPJ", key="novo_cli_cnpj", placeholder="00.000.000/0001-00")
                
                st.markdown("**Responsável Técnico**")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    novo_resp = st.text_input("Veterinário Responsável", key="novo_cli_resp")
                with col_r2:
                    novo_crmv = st.text_input("CRMV", key="novo_cli_crmv", placeholder="CRMV-CE 12345")
                
                if st.button("✅ Cadastrar Clínica", type="primary"):
                    if not novo_nome:
                        st.error("❌ Preencha o nome da clínica")
                    else:
                        conn = sqlite3.connect(str(DB_PATH))
                        cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                INSERT INTO clinicas_parceiras (
                                    nome, endereco, cidade, telefone, whatsapp,
                                    cnpj, responsavel_veterinario, crmv_responsavel
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (novo_nome, novo_end, novo_cidade, novo_tel, 
                                novo_whats, novo_cnpj, novo_resp, novo_crmv))
                            conn.commit()
                            st.success(f"✅ Clínica '{novo_nome}' cadastrada com sucesso!")
                            st.balloons()
                        except sqlite3.IntegrityError:
                            st.error(f"❌ Clínica '{novo_nome}' já existe no sistema")
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar: {e}")
                        finally:
                            conn.close()
        else:
            # Usuário não tem permissão
            st.info("ℹ️ Você pode visualizar as clínicas, mas não pode cadastrar novas.")
            st.caption("Contate a recepção ou administrador para cadastrar clínicas.")
        
        st.markdown("---")
        st.markdown("### 📋 Clínicas Cadastradas")

        conn = sqlite3.connect(str(DB_PATH))
        try:
            clinicas = pd.read_sql_query("""
                SELECT 
                    id,
                    nome as 'Nome',
                    cidade as 'Cidade',
                    telefone as 'Telefone',
                    whatsapp as 'WhatsApp',
                    responsavel_veterinario as 'Responsável'
                FROM clinicas_parceiras
                WHERE (ativo = 1 OR ativo IS NULL)
                ORDER BY nome
            """, conn)
            
            tabela_tabular(
                clinicas,
                caption=f"Total: {len(clinicas)} clínica(s)" if not clinicas.empty else None,
                empty_message="Nenhuma clínica cadastrada.",
            )
            if not clinicas.empty:
                # ========== EDITAR/EXCLUIR ==========
                st.markdown("---")
                st.markdown("### ✏️ Editar ou Excluir Clínica")
                
                # Seleção de clínica
                opcoes_clinicas = dict(zip(clinicas['Nome'], clinicas['id']))
                clinica_sel = st.selectbox(
                    "Selecione uma clínica para editar/excluir",
                    options=list(opcoes_clinicas.keys()),
                    key="clinica_sel_edicao"
                )
                
                if clinica_sel:
                    clinica_id = opcoes_clinicas[clinica_sel]
                    
                    # Busca dados da clínica
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM clinicas_parceiras WHERE id = ?", (clinica_id,))
                    row = cursor.fetchone()
                    cols = [d[0] for d in cursor.description] if cursor.description else []
                    dados = dict(zip(cols, row)) if row and cols else {}
                    
                    # Tabelas de preço (para dropdown)
                    try:
                        cursor.execute("SELECT id, nome FROM tabelas_preco ORDER BY id")
                        tabelas_list = cursor.fetchall()
                        nome_by_id = {r[0]: r[1] for r in tabelas_list}
                    except Exception:
                        tabelas_list = []
                        nome_by_id = {1: "Clínicas Fortaleza"}
                    current_tabela = dados.get("tabela_preco_id") or 1
                    if current_tabela not in nome_by_id:
                        current_tabela = list(nome_by_id.keys())[0] if nome_by_id else 1
                    idx_tabela = list(nome_by_id.keys()).index(current_tabela) if nome_by_id else 0
                    
                    if dados:
                        col_edit, col_del = st.columns([4, 1])
                        
                        with col_edit:
                            with st.form(key=f"form_edit_{clinica_id}"):
                                st.markdown("**Editar Dados:**")
                                
                                col_e1, col_e2 = st.columns(2)
                                
                                with col_e1:
                                    edit_nome = st.text_input("Nome", value=dados.get("nome", ""), key=f"edit_nome_{clinica_id}")
                                    edit_end = st.text_input("Endereço", value=dados.get("endereco") or "", key=f"edit_end_{clinica_id}")
                                    edit_cidade = st.text_input("Cidade", value=dados.get("cidade") or "Fortaleza", key=f"edit_cidade_{clinica_id}")
                                
                                with col_e2:
                                    edit_tel = st.text_input("Telefone", value=dados.get("telefone") or "", key=f"edit_tel_{clinica_id}")
                                    edit_whats = st.text_input("WhatsApp", value=dados.get("whatsapp") or "", key=f"edit_whats_{clinica_id}")
                                    edit_cnpj = st.text_input("CNPJ", value=dados.get("cnpj") or "", key=f"edit_cnpj_{clinica_id}")
                                
                                col_r1, col_r2 = st.columns(2)
                                with col_r1:
                                    edit_resp = st.text_input("Veterinário Responsável", value=dados.get("responsavel_veterinario") or "", key=f"edit_resp_{clinica_id}")
                                with col_r2:
                                    edit_crmv = st.text_input("CRMV", value=dados.get("crmv_responsavel") or "", key=f"edit_crmv_{clinica_id}")
                                
                                if nome_by_id:
                                    edit_tabela_id = st.selectbox(
                                        "Tabela de preço",
                                        options=list(nome_by_id.keys()),
                                        format_func=lambda x: nome_by_id.get(x, str(x)),
                                        index=idx_tabela,
                                        key=f"edit_tabela_{clinica_id}",
                                        help="Usada ao marcar agendamento como realizado para gerar a OS com o valor correto."
                                    )
                                else:
                                    edit_tabela_id = current_tabela
                                edit_limite_desc = st.number_input(
                                    "Limite de desconto (%)",
                                    value=float(dados.get("limite_desconto_percentual") or 0),
                                    min_value=0.0,
                                    max_value=100.0,
                                    step=0.5,
                                    key=f"edit_limite_desc_{clinica_id}",
                                    help="Percentual máximo de desconto permitido para esta clínica."
                                )
                                edit_saldo_credito = st.number_input(
                                    "Saldo de crédito (R$)",
                                    value=float(dados.get("saldo_credito") or 0),
                                    min_value=0.0,
                                    step=1.0,
                                    format="%.2f",
                                    key=f"edit_saldo_credito_{clinica_id}",
                                    help="Crédito disponível da clínica (controle de créditos)."
                                )
                                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                                    try:
                                        if nome_by_id:
                                            cursor.execute("""
                                                UPDATE clinicas_parceiras 
                                                SET nome = ?, endereco = ?, cidade = ?, telefone = ?,
                                                    whatsapp = ?, cnpj = ?, responsavel_veterinario = ?,
                                                    crmv_responsavel = ?, tabela_preco_id = ?,
                                                    limite_desconto_percentual = ?, saldo_credito = ?
                                                WHERE id = ?
                                            """, (edit_nome, edit_end, edit_cidade, edit_tel, edit_whats,
                                                edit_cnpj, edit_resp, edit_crmv, edit_tabela_id, edit_limite_desc, edit_saldo_credito, clinica_id))
                                        else:
                                            cursor.execute("""
                                                UPDATE clinicas_parceiras 
                                                SET nome = ?, endereco = ?, cidade = ?, telefone = ?,
                                                    whatsapp = ?, cnpj = ?, responsavel_veterinario = ?,
                                                    crmv_responsavel = ?,
                                                    limite_desconto_percentual = ?, saldo_credito = ?
                                                WHERE id = ?
                                            """, (edit_nome, edit_end, edit_cidade, edit_tel, edit_whats,
                                                edit_cnpj, edit_resp, edit_crmv, edit_limite_desc, edit_saldo_credito, clinica_id))
                                        conn.commit()
                                        st.success(f"✅ Clínica '{edit_nome}' atualizada com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao atualizar: {e}")
                        
                        with col_del:
                            st.markdown("**Excluir:**")
                            if st.button("🗑️ Excluir Clínica", key=f"del_{clinica_id}", type="secondary"):
                                try:
                                    cursor.execute("UPDATE clinicas_parceiras SET ativo = 0 WHERE id = ?", (clinica_id,))
                                    conn.commit()
                                    st.success(f"✅ Clínica '{clinica_sel}' removida!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir: {e}")
            
            else:
                st.info("Nenhuma clínica cadastrada ainda")

        except (sqlite3.OperationalError, pd.errors.DatabaseError):
            st.info("Nenhuma clínica cadastrada ainda")
        finally:
            conn.close()
    
    with tab_c2:
        st.subheader("Serviços e Tabelas de Preço")
        st.caption("Valores por tabela (Clínicas Fortaleza, Região Metropolitana, Atendimento Domiciliar, Plantão). A pendência financeira é gerada ao marcar o agendamento como realizado.")
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            # Serviços com valor base
            servicos = pd.read_sql_query("""
                SELECT
                    nome as 'Serviço',
                    valor_base as 'Valor Base'
                FROM servicos
                WHERE (ativo = 1 OR ativo IS NULL)
                ORDER BY nome
            """, conn)
            
            if not servicos.empty:
                servicos_display = servicos.copy()
                servicos_display['Valor Base'] = servicos_display['Valor Base'].apply(lambda x: f"R$ {float(x):,.2f}")
                st.dataframe(servicos_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum serviço cadastrado ainda.")

            # Formulário para adicionar novo serviço
            if verificar_permissao("cadastros", "criar"):
                with st.expander("➕ Adicionar Novo Serviço", expanded=servicos.empty):
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        novo_serv_nome = st.text_input("Nome do Serviço *", key="novo_serv_nome",
                                                        placeholder="Ex: Holter 24h")
                    with col_s2:
                        novo_serv_valor = st.number_input("Valor Base (R$)", min_value=0.0, value=0.0,
                                                           step=10.0, format="%.2f", key="novo_serv_valor")
                    novo_serv_desc = st.text_input("Descrição", key="novo_serv_desc",
                                                    placeholder="Breve descrição do serviço")

                    if st.button("✅ Cadastrar Serviço", type="primary", key="btn_cadastrar_servico"):
                        if not novo_serv_nome.strip():
                            st.error("❌ Preencha o nome do serviço")
                        else:
                            try:
                                cursor_s = conn.cursor()
                                cursor_s.execute("PRAGMA table_info(servicos)")
                                colunas = [row[1].lower() for row in cursor_s.fetchall()]
                                cols = ["nome", "descricao", "valor_base", "ativo"]
                                vals = [novo_serv_nome.strip(), novo_serv_desc.strip(), novo_serv_valor, 1]
                                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                if "data_cadastro" in colunas:
                                    cols.append("data_cadastro")
                                    vals.append(agora)
                                elif "created_at" in colunas:
                                    cols.append("created_at")
                                    vals.append(agora)
                                    if "updated_at" in colunas:
                                        cols.append("updated_at")
                                        vals.append(agora)
                                ph = ", ".join("?" * len(cols))
                                cursor_s.execute(f"INSERT INTO servicos ({', '.join(cols)}) VALUES ({ph})", vals)
                                conn.commit()
                                st.success(f"✅ Serviço '{novo_serv_nome}' cadastrado!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"❌ Serviço '{novo_serv_nome}' já existe")
                            except Exception as e:
                                st.error(f"❌ Erro ao cadastrar: {e}")
            
            # Tabelas de preço (valores por serviço por tabela) — com edição direta
            st.markdown("---")
            st.markdown("### 📋 Valores por Tabela de Preço")
            try:
                garantir_tabelas_preco()
            except Exception:
                pass
            try:
                tabelas = pd.read_sql_query("SELECT id, nome, descricao FROM tabelas_preco WHERE (ativo = 1 OR ativo IS NULL) ORDER BY id", conn)
            except Exception:
                tabelas = pd.DataFrame()
            if not tabelas.empty:
                for _, tb in tabelas.iterrows():
                    with st.expander(f"💰 {tb['nome']}" + (f" — {tb['descricao']}" if pd.notna(tb.get('descricao')) and tb.get('descricao') else ""), expanded=(tb['id'] == 1)):
                        tb_id = int(tb['id'])
                        df_preco = pd.read_sql_query("""
                            SELECT s.nome as Serviço, sp.valor as valor, sp.servico_id, sp.tabela_preco_id
                            FROM servico_preco sp
                            JOIN servicos s ON s.id = sp.servico_id
                            WHERE sp.tabela_preco_id = ?
                            ORDER BY s.nome
                        """, conn, params=(tb_id,))
                        # Formulário para incluir ou criar serviço
                        with st.form(key=f"form_add_t{tb_id}", clear_on_submit=True):
                            col1, col2, col3 = st.columns([2, 1.5, 1])
                            with col1:
                                # Buscar serviços existentes (para incluir na tabela)
                                ids_na_tabela = df_preco['servico_id'].astype(int).tolist() if not df_preco.empty else []
                                if ids_na_tabela:
                                    placeholders = ",".join("?" * len(ids_na_tabela))
                                    df_resto = pd.read_sql_query(
                                        f"SELECT id, nome FROM servicos WHERE (ativo = 1 OR ativo IS NULL) AND id NOT IN ({placeholders}) ORDER BY nome",
                                        conn, params=ids_na_tabela
                                    )
                                else:
                                    df_resto = pd.read_sql_query(
                                        "SELECT id, nome FROM servicos WHERE (ativo = 1 OR ativo IS NULL) ORDER BY nome",
                                        conn
                                    )

                                # Sempre mostrar opção de criar novo + serviços disponíveis
                                opcoes = [("novo", "➕ Criar novo serviço...")]
                                if not df_resto.empty:
                                    opcoes += [(str(r['id']), r['nome']) for _, r in df_resto.iterrows()]
                                else:
                                    opcoes.append(("todos", "Todos os serviços já estão na tabela"))

                                servico_opcao = st.selectbox(
                                    "Serviço",
                                    options=[x[0] for x in opcoes],
                                    format_func=lambda x: next((n for i, n in opcoes if i == x), str(x)),
                                    key=f"opcao_t{tb_id}"
                                )

                                # Mostrar mensagem se todos serviços já estão na tabela
                                if servico_opcao == "todos":
                                    st.caption("Todos os serviços já estão incluídos nesta tabela")

                            with col2:
                                if servico_opcao == "novo":
                                    nome_servico = st.text_input(
                                        "Nome do novo serviço",
                                        key=f"nome_novo_t{tb_id}",
                                        placeholder="Ex: Holter 24h"
                                    )
                                else:
                                    nome_servico = None

                                valor_servico = st.number_input(
                                    "Valor (R$)",
                                    min_value=0.0,
                                    value=0.0,
                                    step=10.0,
                                    format="%.2f",
                                    key=f"valor_novo_t{tb_id}"
                                )
                            with col3:
                                st.write("")
                                botao_acao = st.form_submit_button(
                                    "Criar" if servico_opcao == "novo" else "Incluir",
                                    type="primary",
                                    disabled=(servico_opcao == "todos")
                                )

                            if botao_acao:
                                if servico_opcao == "novo":
                                    # Criar novo serviço
                                    if not nome_servico or not nome_servico.strip():
                                        st.error("Digite o nome do serviço")
                                    else:
                                        try:
                                            cur = conn.cursor()
                                            cur.execute("PRAGMA table_info(servicos)")
                                            colunas = [row[1].lower() for row in cur.fetchall()]
                                            cols = ["nome", "descricao", "valor_base", "ativo"]
                                            vals = [nome_servico.strip(), "", valor_servico, 1]
                                            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            if "data_cadastro" in colunas:
                                                cols.append("data_cadastro")
                                                vals.append(agora)
                                            elif "created_at" in colunas:
                                                cols.append("created_at")
                                                vals.append(agora)
                                                if "updated_at" in colunas:
                                                    cols.append("updated_at")
                                                    vals.append(agora)
                                            ph = ", ".join("?" * len(cols))
                                            cur.execute(f"INSERT INTO servicos ({', '.join(cols)}) VALUES ({ph})", vals)
                                            novo_id = cur.lastrowid
                                            cur.execute(
                                                "INSERT INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, ?, ?)",
                                                (novo_id, tb_id, valor_servico)
                                            )
                                            conn.commit()
                                            st.success(f"✅ '{nome_servico}' criado e adicionado!")
                                            st.rerun()
                                        except sqlite3.IntegrityError:
                                            st.error("Serviço já existe")
                                        except Exception as e:
                                            st.error(f"Erro: {e}")
                                elif servico_opcao == "todos":
                                    st.info("Todos os serviços já estão nesta tabela")
                                else:
                                    # Incluir serviço existente
                                    try:
                                        sid = int(servico_opcao)
                                        cur = conn.cursor()
                                        cur.execute(
                                            "INSERT INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, ?, ?)",
                                            (sid, tb_id, valor_servico)
                                        )
                                        conn.commit()
                                        st.success("Serviço incluído!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
                        # Apagar serviço desta tabela
                        if not df_preco.empty:
                            st.markdown("**🗑️ Remover serviço desta tabela**")
                            opcoes_del = [(int(r['servico_id']), r['Serviço']) for _, r in df_preco.iterrows()]
                            col_del1, col_del2 = st.columns([2, 1])
                            with col_del1:
                                servico_del_id = st.selectbox(
                                    "Serviço a remover",
                                    options=[x[0] for x in opcoes_del],
                                    format_func=lambda x: next(n for i, n in opcoes_del if i == x),
                                    key=f"del_servico_t{tb_id}"
                                )
                            with col_del2:
                                st.write("")
                                st.write("")
                                if st.button("Apagar", key=f"btn_apagar_t{tb_id}"):
                                    try:
                                        cursor_del = conn.cursor()
                                        cursor_del.execute(
                                            "DELETE FROM servico_preco WHERE servico_id = ? AND tabela_preco_id = ?",
                                            (servico_del_id, tb_id)
                                        )
                                        conn.commit()
                                        st.success("Serviço removido desta tabela.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao apagar: {e}")
                        st.markdown("---")
                        if not df_preco.empty:
                            with st.form(key=f"form_preco_tabela_{tb_id}"):
                                for _, row in df_preco.iterrows():
                                    servico_id, valor_atual = int(row['servico_id']), float(row['valor'])
                                    st.number_input(
                                        row['Serviço'],
                                        min_value=0.0,
                                        value=valor_atual,
                                        step=10.0,
                                        format="%.2f",
                                        key=f"preco_t{tb_id}_s{servico_id}",
                                        help="Valor em R$"
                                    )
                                if st.form_submit_button("💾 Salvar alterações nesta tabela"):
                                    cursor_preco = conn.cursor()
                                    atualizados = 0
                                    for _, row in df_preco.iterrows():
                                        servico_id = int(row['servico_id'])
                                        val = st.session_state.get(f"preco_t{tb_id}_s{servico_id}", row['valor'])
                                        try:
                                            v = float(val)
                                        except (TypeError, ValueError):
                                            v = float(row['valor'])
                                        cursor_preco.execute(
                                            "UPDATE servico_preco SET valor = ? WHERE servico_id = ? AND tabela_preco_id = ?",
                                            (v, servico_id, tb_id)
                                        )
                                        if cursor_preco.rowcount:
                                            atualizados += 1
                                    conn.commit()
                                    st.success(f"✅ {atualizados} valor(es) atualizado(s).")
                                    st.rerun()
                            resumo = df_preco[['Serviço', 'valor']].copy()
                            resumo['Valor (R$)'] = resumo['valor'].apply(lambda x: f"R$ {float(x):,.2f}")
                            st.dataframe(resumo[['Serviço', 'Valor (R$)']], use_container_width=True, hide_index=True)
                        else:
                            st.caption("Nenhum valor cadastrado para esta tabela. Use «Incluir serviço» acima.")
            else:
                st.info("Reinicie o app para criar as tabelas de preço (Clínicas Fortaleza, Região Metropolitana, Atendimento Domiciliar, Plantão).")
        except Exception as e:
            st.warning(f"⚠️ Erro ao carregar serviços: {e}")
        finally:
            conn.close()

