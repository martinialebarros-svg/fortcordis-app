# app/pages/configuracoes.py
"""Página Configurações: permissões, usuários, papéis, sistema, importar, assinatura, diagnóstico."""
import io
import os
import re
import sqlite3
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from app.config import DB_PATH
from app.db import _db_conn, _db_init
from app.laudos_banco import _criar_tabelas_laudos_se_nao_existirem
from app.utils import _norm_key
from modules.rbac import verificar_permissao, obter_permissoes_usuario

# Assinatura (mesmo caminho do app principal)
_PASTA_FORTCORDIS = Path.home() / "FortCordis"
ASSINATURA_PATH = str(_PASTA_FORTCORDIS / "assinatura.png")


def render_configuracoes():
    
    # Verifica se pode acessar configurações
    if not verificar_permissao("configuracoes", "ver"):
        st.error("❌ Acesso Negado")
        st.warning("⚠️ Apenas administradores podem acessar as configurações do sistema")
        st.info("💡 Se você precisa de acesso, contate o administrador")
        st.stop()
    
    st.title("⚙️ Configurações do Sistema")
    # Cria abas
    tab_permissoes, tab_usuarios, tab_papeis, tab_sistema, tab_importar, tab_assinatura, tab_diagnostico = st.tabs([
        "🔐 Minhas Permissões",
        "👥 Usuários do Sistema",
        "🎭 Papéis e Permissões",
        "⚙️ Configurações Gerais",
        "📥 Importar dados",
        "🖊️ Assinatura/Carimbo",
        "📊 Diagnóstico (memória/CPU)"
    ])

    #============================================================================
    # ABA 1: MINHAS PERMISSÕES - VERSÃO CORRIGIDA
    # ============================================================================
    with tab_permissoes:
        st.subheader("🔐 Suas Permissões no Sistema")
        
        # ✅ CORRIGIDO: Verifica autenticação
        if not st.session_state.get("autenticado"):
            st.error("Você não está logado")
            st.stop()
        
        # ✅ CORRIGIDO: Usa session_state diretamente
        usuario_id = st.session_state.get("usuario_id")
        usuario_nome = st.session_state.get("usuario_nome", "Usuário")
        usuario_email = st.session_state.get("usuario_email", "")
        
        if not usuario_id:
            st.error("Erro: dados do usuário não encontrados")
            st.stop()
        
        # Mostra dados do usuário
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"👤 **Usuário:** {usuario_nome}")
            st.info(f"**📧 Email:** {usuario_email}")
        
        with col2:
            # ✅ CORRIGIDO: Busca papéis do banco (usa DB_PATH do projeto para deploy)
            import sqlite3
            conn_temp = sqlite3.connect(str(DB_PATH))
            cursor_temp = conn_temp.cursor()
            
            cursor_temp.execute("""
                SELECT GROUP_CONCAT(p.nome, ', ') as papeis
                FROM usuario_papel up
                JOIN papeis p ON up.papel_id = p.id
                WHERE up.usuario_id = ?
            """, (usuario_id,))
            
            papeis_row = cursor_temp.fetchone()
            papeis = papeis_row[0] if papeis_row and papeis_row[0] else "Nenhum"
            conn_temp.close()
            
            st.info(f"**🎭 Papéis:** {papeis.title()}")
        
        st.markdown("---")
        
        # ✅ Admin tem tudo
        if usuario_id == 1:
            st.success("✅ Você é **Administrador** e tem acesso total ao sistema!")
            st.balloons()
        else:
            # Importa função de permissões
            from modules.rbac import obter_permissoes_usuario
            
            # Busca permissões
            permissoes = obter_permissoes_usuario(usuario_id)
            
            if not permissoes:
                st.warning("⚠️ Você não tem permissões específicas atribuídas")
                st.info("💡 Entre em contato com o administrador")
            else:
                st.success(f"✅ Você tem permissões em **{len(permissoes)} módulos**")
                
                # Mostra permissões por módulo
                st.markdown("### 📋 Permissões Detalhadas")
                
                # Organiza em colunas
                modulos = list(permissoes.keys())
                
                for i in range(0, len(modulos), 2):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if i < len(modulos):
                            modulo = modulos[i]
                            acoes = permissoes[modulo]
                            
                            with st.expander(f"📦 {modulo.replace('_', ' ').title()}", expanded=False):
                                if acoes:
                                    for acao in sorted(acoes):
                                        st.write(f"✅ {acao.replace('_', ' ').title()}")
                                else:
                                    st.caption("Sem permissões específicas")
                    
                    with col2:
                        if i + 1 < len(modulos):
                            modulo = modulos[i + 1]
                            acoes = permissoes[modulo]
                            
                            with st.expander(f"📦 {modulo.replace('_', ' ').title()}", expanded=False):
                                if acoes:
                                    for acao in sorted(acoes):
                                        st.write(f"✅ {acao.replace('_', ' ').title()}")
                                else:
                                    st.caption("Sem permissões específicas")

    # ============================================================================
    # ABA 2: USUÁRIOS DO SISTEMA (Só Admin)
    # ============================================================================
    with tab_usuarios:
        st.subheader("👥 Usuários do Sistema")
        
        # Verifica se é admin
        if not verificar_permissao("usuarios", "ver"):
            st.warning("⚠️ Apenas administradores podem visualizar esta seção")
            st.info("💡 Se você precisa de acesso, contate o administrador do sistema")
        else:
            import sqlite3
            
            conn = sqlite3.connect(str(DB_PATH))
            
            # Busca todos os usuários
            query = """
                SELECT 
                    u.id,
                    u.nome,
                    u.email,
                    u.ativo,
                    u.ultimo_acesso,
                    GROUP_CONCAT(p.nome, ', ') as papeis
                FROM usuarios u
                LEFT JOIN usuario_papel up ON u.id = up.usuario_id
                LEFT JOIN papeis p ON up.papel_id = p.id
                GROUP BY u.id
                ORDER BY u.nome
            """
            
            df_usuarios = pd.read_sql_query(query, conn)
            conn.close()
            
            # Mostra métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Usuários", len(df_usuarios))
            with col2:
                ativos = df_usuarios[df_usuarios['ativo'] == 1].shape[0]
                st.metric("Usuários Ativos", ativos)
            with col3:
                inativos = df_usuarios[df_usuarios['ativo'] == 0].shape[0]
                st.metric("Usuários Inativos", inativos)
            
            st.markdown("---")
            
            # Mostra tabela
            st.markdown("### 📋 Lista Completa")
            
            # Formata a tabela
            df_display = df_usuarios.copy()
            df_display['ativo'] = df_display['ativo'].map({1: '✅ Ativo', 0: '❌ Inativo'})
            df_display['ultimo_acesso'] = df_display['ultimo_acesso'].fillna('Nunca')
            
            # Renomeia colunas
            df_display.columns = ['ID', 'Nome', 'Email', 'Status', 'Último Acesso', 'Papéis']
            
            # Exibe tabela
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Mostra detalhes de cada usuário
            st.markdown("---")
            st.markdown("### 🔍 Detalhes dos Usuários")
            
            for _, row in df_usuarios.iterrows():
                with st.expander(f"👤 {row['nome']} ({row['email']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {row['id']}")
                        st.write(f"**Email:** {row['email']}")
                        st.write(f"**Status:** {'✅ Ativo' if row['ativo'] else '❌ Inativo'}")
                    
                    with col2:
                        st.write(f"**Papéis:** {row['papeis'] or 'Nenhum'}")
                        st.write(f"**Último acesso:** {row['ultimo_acesso'] or 'Nunca'}")
                    
                    # Busca permissões desse usuário
                    from modules.rbac import obter_permissoes_usuario
                    perms_user = obter_permissoes_usuario(row['id'])
                    
                    st.markdown("**Permissões:**")
                    if perms_user:
                        perms_resumo = []
                        for mod, acoes in perms_user.items():
                            if acoes:
                                perms_resumo.append(f"• {mod}: {len(acoes)} ações")
                        
                        if perms_resumo:
                            for p in perms_resumo:
                                st.caption(p)
                        else:
                            st.caption("Sem permissões específicas")
                    else:
                        st.caption("Sem permissões atribuídas")

            st.markdown("---")
            st.markdown("### 🔐 Gerenciar Permissões dos Usuários")
            st.caption("Apenas administradores podem modificar permissões")
            
            # Seleciona usuário para editar permissões
            st.markdown("#### 1️⃣ Selecione o Usuário")
            
            # Busca usuários novamente (usa DB_PATH do projeto para deploy)
            conn_perm = sqlite3.connect(str(DB_PATH))
            cursor_perm = conn_perm.cursor()
            
            cursor_perm.execute("""
                SELECT u.id, u.nome, u.email, GROUP_CONCAT(p.nome, ', ') as papeis
                FROM usuarios u
                LEFT JOIN usuario_papel up ON u.id = up.usuario_id
                LEFT JOIN papeis p ON up.papel_id = p.id
                GROUP BY u.id
                ORDER BY u.nome
            """)
            usuarios_list = cursor_perm.fetchall()
            
            # Cria dicionário de usuários
            usuarios_dict = {f"{u[1]} ({u[2]})": u[0] for u in usuarios_list}
            
            usuario_selecionado_str = st.selectbox(
                "Usuário para editar permissões:",
                options=list(usuarios_dict.keys()),
                key="usuario_edit_perm"
            )
            
            if usuario_selecionado_str:
                usuario_selecionado_id = usuarios_dict[usuario_selecionado_str]
                
                # Busca dados do usuário
                usuario_info = next((u for u in usuarios_list if u[0] == usuario_selecionado_id), None)
                
                if usuario_info:
                    st.markdown("#### 2️⃣ Papéis Atuais")
                    
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.info(f"**Nome:** {usuario_info[1]}")
                    with col_info2:
                        st.info(f"**Papéis:** {usuario_info[3] or 'Nenhum'}")
                    
                    st.markdown("---")
                    st.markdown("#### 3️⃣ Alterar Papel Principal")
                    st.caption("Mudar o papel altera automaticamente todas as permissões associadas")
                    
                    # Lista de papéis disponíveis
                    cursor_perm.execute("SELECT id, nome, descricao FROM papeis ORDER BY nome")
                    papeis_disponiveis = cursor_perm.fetchall()
                    
                    # Papel atual
                    cursor_perm.execute("""
                        SELECT p.id, p.nome 
                        FROM papeis p
                        JOIN usuario_papel up ON p.id = up.papel_id
                        WHERE up.usuario_id = ?
                        LIMIT 1
                    """, (usuario_selecionado_id,))
                    papel_atual = cursor_perm.fetchone()
                    
                    # Selectbox de papéis
                    papeis_opcoes = {f"{p[1].title()} - {p[2]}": p[0] for p in papeis_disponiveis}
                    
                    novo_papel_str = st.selectbox(
                        "Selecione o novo papel:",
                        options=list(papeis_opcoes.keys()),
                        index=list(papeis_opcoes.values()).index(papel_atual[0]) if papel_atual else 0,
                        key="novo_papel_select"
                    )
                    
                    novo_papel_id = papeis_opcoes[novo_papel_str]
                    
                    if st.button("🔄 Alterar Papel", type="primary", key="btn_alterar_papel"):
                        try:
                            # Remove papéis antigos
                            cursor_perm.execute(
                                "DELETE FROM usuario_papel WHERE usuario_id = ?",
                                (usuario_selecionado_id,)
                            )
                            
                            # Adiciona novo papel
                            cursor_perm.execute(
                                "INSERT INTO usuario_papel (usuario_id, papel_id) VALUES (?, ?)",
                                (usuario_selecionado_id, novo_papel_id)
                            )
                            
                            conn_perm.commit()
                            st.success(f"✅ Papel alterado com sucesso para: {novo_papel_str.split(' - ')[0]}")
                            st.balloons()
                            
                            # Recarrega a página após 2 segundos
                            import time
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao alterar papel: {e}")
                    
                    st.markdown("---")
                    st.markdown("#### 4️⃣ Permissões Específicas")
                    st.caption("Visualize as permissões que este usuário tem baseado no seu papel")
                    
                    # Busca permissões do usuário
                    from modules.rbac import obter_permissoes_usuario
                    permissoes_usuario = obter_permissoes_usuario(usuario_selecionado_id)
                    
                    if permissoes_usuario:
                        # Organiza em tabela
                        st.markdown("**Resumo de Permissões por Módulo:**")
                        
                        # Cria DataFrame para exibição
                        dados_tabela = []
                        for modulo, acoes in sorted(permissoes_usuario.items()):
                            dados_tabela.append({
                                "Módulo": modulo.replace("_", " ").title(),
                                "Ações Permitidas": ", ".join([a.replace("_", " ").title() for a in sorted(acoes)]) if acoes else "Nenhuma",
                                "Quantidade": len(acoes)
                            })
                        
                        df_perms = pd.DataFrame(dados_tabela)
                        st.dataframe(df_perms, use_container_width=True, hide_index=True)
                        
                        # Detalhes expandíveis
                        with st.expander("🔍 Ver Detalhes das Permissões"):
                            for modulo, acoes in sorted(permissoes_usuario.items()):
                                st.markdown(f"**📦 {modulo.replace('_', ' ').title()}**")
                                if acoes:
                                    for acao in sorted(acoes):
                                        st.write(f"  ✅ {acao.replace('_', ' ').title()}")
                                else:
                                    st.caption("  Sem permissões específicas")
                                st.markdown("")
                    else:
                        st.warning("⚠️ Este usuário não tem permissões atribuídas")
                    
                    st.markdown("---")
                    st.markdown("#### 5️⃣ Ações de Gerenciamento")
                    
                    col_acoes1, col_acoes2 = st.columns(2)
                    
                    with col_acoes1:
                        st.markdown("**Desativar Usuário:**")
                        st.caption("O usuário não poderá mais fazer login")
                        if st.button("🚫 Desativar Usuário", key="btn_desativar"):
                            try:
                                cursor_perm.execute(
                                    "UPDATE usuarios SET ativo = 0 WHERE id = ?",
                                    (usuario_selecionado_id,)
                                )
                                conn_perm.commit()
                                st.success("✅ Usuário desativado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro: {e}")
                    
                    with col_acoes2:
                        st.markdown("**Resetar Senha:**")
                        st.caption("Define senha padrão: Senha123")
                        if st.button("🔑 Resetar Senha", key="btn_reset_senha"):
                            try:
                                from modules.auth import hash_senha
                                nova_senha_hash = hash_senha("Senha123")
                                
                                cursor_perm.execute(
                                    "UPDATE usuarios SET senha_hash = ?, tentativas_login = 0, bloqueado_ate = NULL WHERE id = ?",
                                    (nova_senha_hash, usuario_selecionado_id)
                                )
                                conn_perm.commit()
                                st.success("✅ Senha resetada para: Senha123")
                                st.info("💡 Informe ao usuário que ele deve trocar a senha no próximo login")
                            except Exception as e:
                                st.error(f"❌ Erro: {e}")
            
            conn_perm.close()
            
            st.markdown("---")
            st.markdown("### ➕ Criar Novo Usuário")
            
            with st.expander("➕ Adicionar Novo Usuário ao Sistema"):
                st.markdown("**Dados do Novo Usuário:**")
                
                col_novo1, col_novo2 = st.columns(2)
                
                with col_novo1:
                    novo_user_nome = st.text_input("Nome Completo *", key="novo_user_nome")
                    novo_user_email = st.text_input("Email *", key="novo_user_email", 
                        help="Será usado para login")
                
                with col_novo2:
                    novo_user_senha = st.text_input("Senha *", type="password", key="novo_user_senha",
                        help="Mínimo 8 caracteres")
                    novo_user_senha2 = st.text_input("Confirmar Senha *", type="password", key="novo_user_senha2")
                
                # Seleção de papel
                novo_user_papel = st.selectbox(
                    "Papel do Usuário *",
                    options=["admin", "recepcao", "veterinario", "cardiologista", "financeiro"],
                    format_func=lambda x: {
                        "admin": "Administrador",
                        "recepcao": "Recepção",
                        "veterinario": "Veterinário",
                        "cardiologista": "Cardiologista",
                        "financeiro": "Financeiro"
                    }[x],
                    key="novo_user_papel"
                )
                
                if st.button("✅ Criar Usuário", type="primary", key="btn_criar_usuario"):
                    # Validações
                    erros = []
                    
                    if not novo_user_nome:
                        erros.append("Nome é obrigatório")
                    if not novo_user_email:
                        erros.append("Email é obrigatório")
                    if not novo_user_senha:
                        erros.append("Senha é obrigatória")
                    if len(novo_user_senha) < 8:
                        erros.append("Senha deve ter no mínimo 8 caracteres")
                    if novo_user_senha != novo_user_senha2:
                        erros.append("As senhas não coincidem")
                    
                    if erros:
                        for erro in erros:
                            st.error(f"❌ {erro}")
                    else:
                        # Cria usuário
                        from modules.auth import criar_usuario
                        
                        sucesso, mensagem, _, _ = criar_usuario(
                            nome=novo_user_nome,
                            email=novo_user_email,
                            senha=novo_user_senha,
                            papel=novo_user_papel,
                            criado_por=st.session_state.get("usuario_id")
                        )
                        
                        if sucesso:
                            st.success(mensagem)
                            st.balloons()
                            st.info(f"📧 Credenciais: {novo_user_email} / {novo_user_senha}")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(mensagem)


    # ============================================================================
    # CÓDIGO DA NOVA ABA "🎭 PAPÉIS E PERMISSÕES"
    # ============================================================================

    with tab_papeis:
        st.subheader("🎭 Gestão de Papéis e Permissões")
        st.caption("Crie papéis personalizados e defina permissões específicas")
        
        # Verifica se é admin
        if not verificar_permissao("usuarios", "alterar_permissoes"):
            st.warning("⚠️ Apenas administradores podem gerenciar papéis e permissões")
            st.stop()
        
        # ========================================================================
        # SEÇÃO 1: LISTA DE PAPÉIS EXISTENTES
        # ========================================================================
        
        st.markdown("### 📋 Papéis Cadastrados")
        
        conn_papeis = sqlite3.connect(str(DB_PATH))
        cursor_papeis = conn_papeis.cursor()
        
        # Busca todos os papéis
        cursor_papeis.execute("""
            SELECT p.id, p.nome, p.descricao, COUNT(up.usuario_id) as qtd_usuarios
            FROM papeis p
            LEFT JOIN usuario_papel up ON p.id = up.papel_id
            GROUP BY p.id
            ORDER BY p.nome
        """)
        papeis_list = cursor_papeis.fetchall()
        
        # Exibe em cards
        cols = st.columns(3)
        for idx, (papel_id, nome, descricao, qtd) in enumerate(papeis_list):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(f"**🎭 {nome.title()}**")
                    st.caption(descricao or "Sem descrição")
                    st.info(f"👥 {qtd} usuário(s)")
        
        st.markdown("---")
        
        # ========================================================================
        # SEÇÃO 2: CRIAR NOVO PAPEL
        # ========================================================================
        
        st.markdown("### ➕ Criar Novo Papel")
        
        with st.expander("➕ Adicionar Novo Papel Personalizado", expanded=False):
            st.markdown("**Dados do Novo Papel:**")
            
            col_papel1, col_papel2 = st.columns(2)
            
            with col_papel1:
                novo_papel_nome = st.text_input(
                    "Nome do Papel *", 
                    key="novo_papel_nome",
                    placeholder="Ex: atendente, gerente, estagiario",
                    help="Use letras minúsculas, sem espaços ou acentos"
                )
            
            with col_papel2:
                novo_papel_desc = st.text_input(
                    "Descrição *",
                    key="novo_papel_desc",
                    placeholder="Ex: Atendente - Recepção básica"
                )
            
            if st.button("✅ Criar Papel", key="btn_criar_papel", type="primary"):
                if not novo_papel_nome or not novo_papel_desc:
                    st.error("❌ Preencha nome e descrição")
                else:
                    # Valida nome
                    import re
                    if not re.match(r'^[a-z_]+$', novo_papel_nome):
                        st.error("❌ Nome deve conter apenas letras minúsculas e underscore (_)")
                    else:
                        try:
                            cursor_papeis.execute(
                                "INSERT INTO papeis (nome, descricao) VALUES (?, ?)",
                                (novo_papel_nome, novo_papel_desc)
                            )
                            conn_papeis.commit()
                            st.success(f"✅ Papel '{novo_papel_nome}' criado com sucesso!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"❌ Papel '{novo_papel_nome}' já existe")
                        except Exception as e:
                            st.error(f"❌ Erro: {e}")
        
        st.markdown("---")
        
        # ========================================================================
        # SEÇÃO 3: EDITAR PERMISSÕES DE UM PAPEL
        # ========================================================================
        
        st.markdown("### ✏️ Editar Permissões de um Papel")
        st.caption("Selecione um papel e defina quais permissões ele terá")
        
        # Seleção de papel
        papeis_opcoes = {f"{p[1].title()} ({p[3]} usuários)": p[0] for p in papeis_list}
        
        papel_editar_str = st.selectbox(
            "Selecione o papel para editar:",
            options=list(papeis_opcoes.keys()),
            key="papel_editar_select"
        )
        
        if papel_editar_str:
            papel_editar_id = papeis_opcoes[papel_editar_str]
            papel_editar_nome = papel_editar_str.split(' (')[0]
            
            st.info(f"📝 Editando permissões do papel: **{papel_editar_nome}**")
            
            # Busca permissões atuais do papel
            cursor_papeis.execute("""
                SELECT p.id, p.modulo, p.acao
                FROM permissoes p
                JOIN papel_permissao pp ON p.id = pp.permissao_id
                WHERE pp.papel_id = ?
            """, (papel_editar_id,))
            
            permissoes_atuais = cursor_papeis.fetchall()
            permissoes_atuais_ids = {p[0] for p in permissoes_atuais}
            
            # Busca TODAS as permissões disponíveis
            cursor_papeis.execute("""
                SELECT id, modulo, acao
                FROM permissoes
                ORDER BY modulo, acao
            """)
            todas_permissoes = cursor_papeis.fetchall()
            
            # Organiza por módulo
            permissoes_por_modulo = {}
            for perm_id, modulo, acao in todas_permissoes:
                if modulo not in permissoes_por_modulo:
                    permissoes_por_modulo[modulo] = []
                permissoes_por_modulo[modulo].append({
                    'id': perm_id,
                    'acao': acao,
                    'ativo': perm_id in permissoes_atuais_ids
                })
            
            st.markdown("#### 📦 Selecione as Permissões por Módulo")
            st.caption("Marque as permissões que este papel deve ter")
            
            # Dicionário para armazenar mudanças
            mudancas = {}
            
            # Cria 2 colunas para organizar melhor
            modulos_list = list(permissoes_por_modulo.keys())
            col_esq, col_dir = st.columns(2)
            
            for idx, modulo in enumerate(sorted(modulos_list)):
                permissoes = permissoes_por_modulo[modulo]
                
                # Alterna entre coluna esquerda e direita
                col_atual = col_esq if idx % 2 == 0 else col_dir
                
                with col_atual:
                    with st.expander(f"📦 {modulo.replace('_', ' ').title()}", expanded=True):
                        for perm in permissoes:
                            # Checkbox para cada permissão
                            key = f"perm_{papel_editar_id}_{perm['id']}"
                            
                            novo_estado = st.checkbox(
                                f"✓ {perm['acao'].replace('_', ' ').title()}",
                                value=perm['ativo'],
                                key=key
                            )
                            
                            # Registra se houve mudança
                            if novo_estado != perm['ativo']:
                                mudancas[perm['id']] = novo_estado
            
            # Botão para salvar
            st.markdown("---")
            
            col_btn1, col_btn2 = st.columns([1, 4])
            
            with col_btn1:
                if st.button("💾 Salvar Permissões", type="primary", key="btn_salvar_perms"):
                    if not mudancas:
                        st.info("ℹ️ Nenhuma alteração foi feita")
                    else:
                        try:
                            # Aplica as mudanças
                            for perm_id, ativo in mudancas.items():
                                if ativo:
                                    # Adiciona permissão
                                    try:
                                        cursor_papeis.execute(
                                            "INSERT INTO papel_permissao (papel_id, permissao_id) VALUES (?, ?)",
                                            (papel_editar_id, perm_id)
                                        )
                                    except sqlite3.IntegrityError:
                                        pass  # Já existe
                                else:
                                    # Remove permissão
                                    cursor_papeis.execute(
                                        "DELETE FROM papel_permissao WHERE papel_id = ? AND permissao_id = ?",
                                        (papel_editar_id, perm_id)
                                    )
                            
                            conn_papeis.commit()
                            st.success(f"✅ Permissões do papel '{papel_editar_nome}' atualizadas com sucesso!")
                            st.info(f"📊 {len(mudancas)} permissão(ões) modificada(s)")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar: {e}")
            
            with col_btn2:
                # Contador de permissões
                total_marcadas = sum(1 for m in permissoes_por_modulo.values() for p in m if p['ativo'])
                total_disponiveis = sum(len(m) for m in permissoes_por_modulo.values())
                st.caption(f"📊 {total_marcadas} de {total_disponiveis} permissões ativas")
        
        st.markdown("---")
        
        # ========================================================================
        # SEÇÃO 4: COMPARAR PAPÉIS
        # ========================================================================
        
        st.markdown("### 🔍 Comparar Papéis")
        st.caption("Compare as permissões entre diferentes papéis")
        
        with st.expander("🔍 Comparar Permissões", expanded=False):
            col_comp1, col_comp2 = st.columns(2)
            
            with col_comp1:
                papel1_str = st.selectbox(
                    "Papel 1:",
                    options=list(papeis_opcoes.keys()),
                    key="papel_comp1"
                )
            
            with col_comp2:
                papel2_str = st.selectbox(
                    "Papel 2:",
                    options=list(papeis_opcoes.keys()),
                    key="papel_comp2"
                )
            
            if st.button("📊 Comparar", key="btn_comparar"):
                if papel1_str == papel2_str:
                    st.warning("⚠️ Selecione papéis diferentes para comparar")
                else:
                    papel1_id = papeis_opcoes[papel1_str]
                    papel2_id = papeis_opcoes[papel2_str]
                    
                    # Busca permissões de cada um
                    cursor_papeis.execute("""
                        SELECT p.modulo, p.acao
                        FROM permissoes p
                        JOIN papel_permissao pp ON p.id = pp.permissao_id
                        WHERE pp.papel_id = ?
                        ORDER BY p.modulo, p.acao
                    """, (papel1_id,))
                    perms1 = set((m, a) for m, a in cursor_papeis.fetchall())
                    
                    cursor_papeis.execute("""
                        SELECT p.modulo, p.acao
                        FROM permissoes p
                        JOIN papel_permissao pp ON p.id = pp.permissao_id
                        WHERE pp.papel_id = ?
                        ORDER BY p.modulo, p.acao
                    """, (papel2_id,))
                    perms2 = set((m, a) for m, a in cursor_papeis.fetchall())
                    
                    # Compara
                    apenas_papel1 = perms1 - perms2
                    apenas_papel2 = perms2 - perms1
                    em_ambos = perms1 & perms2
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    
                    with col_r1:
                        st.metric("Em Ambos", len(em_ambos))
                    
                    with col_r2:
                        st.metric(f"Apenas {papel1_str.split(' (')[0]}", len(apenas_papel1))
                    
                    with col_r3:
                        st.metric(f"Apenas {papel2_str.split(' (')[0]}", len(apenas_papel2))
                    
                    # Detalhes
                    if apenas_papel1:
                        with st.expander(f"📋 Permissões exclusivas de {papel1_str.split(' (')[0]}"):
                            for mod, acao in sorted(apenas_papel1):
                                st.write(f"• {mod}.{acao}")
                    
                    if apenas_papel2:
                        with st.expander(f"📋 Permissões exclusivas de {papel2_str.split(' (')[0]}"):
                            for mod, acao in sorted(apenas_papel2):
                                st.write(f"• {mod}.{acao}")
        
        st.markdown("---")
        
        # ========================================================================
        # SEÇÃO 5: EXCLUIR PAPEL (CUIDADO!)
        # ========================================================================
        
        st.markdown("### 🗑️ Excluir Papel")
        st.caption("⚠️ CUIDADO: Esta ação não pode ser desfeita!")
        
        with st.expander("🗑️ Excluir Papel Personalizado", expanded=False):
            st.warning("⚠️ **ATENÇÃO:** Você só pode excluir papéis que não têm usuários associados")
            
            # Lista papéis sem usuários
            papeis_sem_usuarios = [(p[0], p[1]) for p in papeis_list if p[3] == 0]
            
            if not papeis_sem_usuarios:
                st.info("✅ Todos os papéis têm usuários associados. Não é possível excluir nenhum.")
            else:
                papel_excluir = st.selectbox(
                    "Selecione o papel para excluir:",
                    options=[f"{nome.title()}" for _, nome in papeis_sem_usuarios],
                    key="papel_excluir_select"
                )
                
                st.error(f"⚠️ Você está prestes a excluir o papel: **{papel_excluir}**")
                st.caption("Esta ação removerá o papel e todas as suas permissões associadas")
                
                confirma = st.checkbox("Confirmo que desejo excluir este papel", key="confirma_excluir_papel")
                
                if confirma:
                    if st.button("🗑️ EXCLUIR PAPEL", type="secondary", key="btn_excluir_papel"):
                        # Busca ID do papel
                        papel_excluir_lower = papel_excluir.lower()
                        papel_id_excluir = next((p[0] for p in papeis_sem_usuarios if p[1] == papel_excluir_lower), None)
                        
                        if papel_id_excluir:
                            try:
                                # Remove permissões associadas
                                cursor_papeis.execute(
                                    "DELETE FROM papel_permissao WHERE papel_id = ?",
                                    (papel_id_excluir,)
                                )
                                
                                # Remove o papel
                                cursor_papeis.execute(
                                    "DELETE FROM papeis WHERE id = ?",
                                    (papel_id_excluir,)
                                )
                                
                                conn_papeis.commit()
                                st.success(f"✅ Papel '{papel_excluir}' excluído com sucesso!")
                                time.sleep(1)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Erro ao excluir: {e}")
        
        conn_papeis.close()

    # ============================================================================
    # ABA 3: CONFIGURAÇÕES GERAIS (mantém o que já tinha)
    # ============================================================================
    with tab_sistema:
        st.subheader("⚙️ Configurações Gerais")
        st.caption("Altere sua senha e, em breve, outros dados do sistema.")
        
        # Alterar minha senha
        with st.expander("🔑 Alterar minha senha", expanded=True):
            with st.form("form_alterar_senha", clear_on_submit=True):
                senha_atual = st.text_input("Senha atual", type="password", key="config_senha_atual", placeholder="Digite sua senha atual")
                nova_senha = st.text_input("Nova senha (mínimo 8 caracteres)", type="password", key="config_nova_senha", placeholder="Mínimo 8 caracteres")
                nova_senha2 = st.text_input("Confirmar nova senha", type="password", key="config_nova_senha2", placeholder="Repita a nova senha")
                if st.form_submit_button("Alterar senha"):
                    if not senha_atual or not nova_senha or not nova_senha2:
                        st.error("Preencha todos os campos.")
                    elif len(nova_senha) < 8:
                        st.error("A nova senha deve ter no mínimo 8 caracteres.")
                    elif nova_senha != nova_senha2:
                        st.error("A nova senha e a confirmação não coincidem.")
                    else:
                        try:
                            from modules.auth import atualizar_senha
                            ok, msg = atualizar_senha(
                                st.session_state.get("usuario_id"),
                                senha_atual,
                                nova_senha,
                            )
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                        except Exception as e:
                            st.error(f"Erro ao alterar senha: {e}")
        
        st.markdown("---")
        st.markdown("#### Outras configurações (em breve)")
        st.markdown("- 👨‍⚕️ Dados profissionais (nome, CRMV)  \n- 📊 Valores de referência  \n- 📝 Frases personalizadas  \n- 🎁 Descontos por clínica")

    # ============================================================================
    # ABA: IMPORTAR DADOS (backup local após deploy)
    # ============================================================================
    with tab_importar:
        st.subheader("📥 Importar dados de backup")
        st.caption(
            "Após o deploy, o sistema fica vazio. Gere um backup no seu computador com o script "
            "exportar_backup.py (ou exportar_backup_partes.py se o arquivo for muito grande) e envie o(s) arquivo(s) .db aqui."
        )
        with st.expander("📦 Backup muito grande? Use backup em partes"):
            st.markdown(
                "Se o arquivo único der erro ao carregar, use **backup em partes**:\n\n"
                "1. No PC, execute: `python exportar_backup_partes.py` (na pasta do projeto).\n"
                "2. Será criada a pasta **backup_partes** com vários arquivos menores.\n"
                "3. Importe **na ordem**: primeiro **parte_01_base.db**, depois todos os **parte_02_laudos_*.db**, por último os **parte_03_arquivos_*.db**.\n"
                "4. **Não** marque «Limpar laudos antes de importar» após a primeira parte (só na primeira, se quiser)."
            )
        arquivo_backup = st.file_uploader(
            "Enviar arquivo de backup (.db)",
            type=["db"],
            key="upload_backup_db",
        )
        limpar_laudos_antes = st.checkbox(
            "🗑️ Limpar laudos antes de importar (recomendado se há muitos repetidos ou clínica/animal/tutor vazios)",
            key="import_limpar_laudos",
            help="Apaga todos os laudos do banco antes de importar. Use isso para começar do zero e preencher clínica/animal/tutor corretamente."
        )
        if arquivo_backup is not None:
            if st.button("🔄 Importar agora", key="btn_importar_backup", type="primary"):
                import tempfile
                import io
                import traceback
                erros_import = []
                tmp_path = None
                conn_backup = None
                conn_local = None
                try:
                    bytes_backup = arquivo_backup.read()
                    if not bytes_backup:
                        st.error("O arquivo está vazio. Gere o backup novamente com exportar_backup.py.")
                    else:
                        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                            tmp.write(bytes_backup)
                            tmp_path = tmp.name
                        del bytes_backup  # Libera memória antes de processar (importante em Cloud)
                    try:
                        conn_backup = sqlite3.connect(tmp_path)
                        conn_backup.row_factory = sqlite3.Row
                        cur_b = conn_backup.cursor()
                        # Tabelas presentes no backup (backup em partes pode ter só algumas)
                        cur_b.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                        tabelas_no_backup = {r[0] for r in cur_b.fetchall()}
                        def _count_backup(tabela):
                            try:
                                cur_b.execute(f"SELECT COUNT(*) FROM {tabela}")
                                return cur_b.fetchone()[0]
                            except sqlite3.OperationalError:
                                return 0
                        n_c_b, n_t_b = _count_backup("clinicas"), _count_backup("tutores")
                        n_p_b = _count_backup("pacientes")
                        n_l_b = _count_backup("laudos_ecocardiograma") + _count_backup("laudos_eletrocardiograma") + _count_backup("laudos_pressao_arterial")
                        n_cp_b = _count_backup("clinicas_parceiras")
                        n_laudos_arq_b = _count_backup("laudos_arquivos")
                        st.info(
                            f"📂 Conteúdo do backup: {n_c_b} clínicas, {n_t_b} tutores, {n_p_b} pacientes, {n_l_b} laudos, "
                            f"{n_cp_b} clínicas parceiras" + (f", **{n_laudos_arq_b} exames da pasta** (JSON/PDF)." if n_laudos_arq_b else ".")
                        )
                        # Usar apenas conexão nova (não _db_conn em cache) para evitar "Cannot operate on a closed database"
                        conn_local = sqlite3.connect(str(DB_PATH))
                        cur_l = conn_local.cursor()
                        # Inicializar tabelas com conn_local (sem chamar _db_init que usa cache)
                        cur_l.execute("""CREATE TABLE IF NOT EXISTS clinicas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome TEXT NOT NULL,
                            nome_key TEXT NOT NULL UNIQUE,
                            created_at TEXT NOT NULL
                        )""")
                        cur_l.execute("""CREATE TABLE IF NOT EXISTS tutores (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome TEXT NOT NULL,
                            nome_key TEXT NOT NULL UNIQUE,
                            telefone TEXT,
                            created_at TEXT NOT NULL
                        )""")
                        cur_l.execute("""CREATE TABLE IF NOT EXISTS pacientes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tutor_id INTEGER NOT NULL,
                            nome TEXT NOT NULL,
                            nome_key TEXT NOT NULL,
                            especie TEXT NOT NULL DEFAULT '',
                            raca TEXT,
                            sexo TEXT,
                            nascimento TEXT,
                            created_at TEXT NOT NULL,
                            UNIQUE(tutor_id, nome_key, especie),
                            FOREIGN KEY(tutor_id) REFERENCES tutores(id)
                        )""")
                        for col, tipo in [("ativo", "INTEGER DEFAULT 1"), ("peso_kg", "REAL"), ("microchip", "TEXT"), ("observacoes", "TEXT")]:
                            try:
                                cur_l.execute(f"ALTER TABLE pacientes ADD COLUMN {col} {tipo}")
                            except sqlite3.OperationalError:
                                pass
                        for col, tipo in [("whatsapp", "TEXT"), ("ativo", "INTEGER DEFAULT 1")]:
                            try:
                                cur_l.execute(f"ALTER TABLE tutores ADD COLUMN {col} {tipo}")
                            except sqlite3.OperationalError:
                                pass
                        _criar_tabelas_laudos_se_nao_existirem(cur_l)
                        # Garantir colunas nome_clinica e nome_tutor ANTES de importar laudos
                        for _tab in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
                            for _col, _tipo in [("nome_clinica", "TEXT"), ("nome_tutor", "TEXT")]:
                                try:
                                    cur_l.execute(f"ALTER TABLE {_tab} ADD COLUMN {_col} {_tipo}")
                                except sqlite3.OperationalError:
                                    pass
                        # Garantir que clinicas_parceiras existe (pode não existir em deploy novo)
                        cur_l.execute("""
                            CREATE TABLE IF NOT EXISTS clinicas_parceiras (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nome TEXT NOT NULL UNIQUE,
                                endereco TEXT,
                                bairro TEXT,
                                cidade TEXT,
                                telefone TEXT,
                                whatsapp TEXT,
                                email TEXT,
                                cnpj TEXT,
                                inscricao_estadual TEXT,
                                responsavel_veterinario TEXT,
                                crmv_responsavel TEXT,
                                observacoes TEXT,
                                ativo INTEGER DEFAULT 1,
                                data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                        cur_l.execute("""
                            CREATE TABLE IF NOT EXISTS laudos_arquivos (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                data_exame TEXT NOT NULL,
                                nome_animal TEXT,
                                nome_tutor TEXT,
                                nome_clinica TEXT,
                                tipo_exame TEXT DEFAULT 'ecocardiograma',
                                nome_base TEXT UNIQUE,
                                conteudo_json BLOB,
                                conteudo_pdf BLOB,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                        cur_l.execute("""
                            CREATE TABLE IF NOT EXISTS laudos_arquivos_imagens (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                laudo_arquivo_id INTEGER NOT NULL,
                                ordem INTEGER DEFAULT 0,
                                nome_arquivo TEXT,
                                conteudo BLOB,
                                FOREIGN KEY(laudo_arquivo_id) REFERENCES laudos_arquivos(id)
                            )
                        """)
                        conn_local.commit()
                        if limpar_laudos_antes:
                            for _t in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
                                try:
                                    cur_l.execute(f"DELETE FROM {_t}")
                                except sqlite3.OperationalError:
                                    pass
                            conn_local.commit()
                        map_clinica = {}
                        map_clinica_parceiras = {}
                        map_tutor = {}
                        map_paciente = {}
                        total_c, total_t, total_p, total_l, total_cp, total_laudos_arq = 0, 0, 0, 0, 0, 0
                        reused_c, reused_t = 0, 0
                        # 1) Clinicas (tabela simples) — evita duplicata por nome_key; SELECT só colunas que existem no backup
                        try:
                            if "clinicas" not in tabelas_no_backup:
                                pass  # backup em partes: este arquivo pode não ter base
                            else:
                                cur_b.execute("PRAGMA table_info(clinicas)")
                                cols_c = [c[1] for c in cur_b.fetchall()]
                                if not cols_c:
                                    erros_import.append(("clinicas", "Tabela clinicas vazia ou sem colunas no backup"))
                                else:
                                    tem_nome_key = "nome_key" in cols_c
                                    tem_created = "created_at" in cols_c
                                    sel_c = "SELECT " + ", ".join(cols_c) + " FROM clinicas"
                                    cur_b.execute(sel_c)
                                    for row in cur_b.fetchall():
                                        row = dict(row)
                                        nome_key = (row.get("nome_key") or "").strip() if tem_nome_key else _norm_key(row.get("nome") or "")
                                        if not nome_key:
                                            nome_key = _norm_key(row.get("nome") or "") or "sem_nome"
                                        r = cur_l.execute("SELECT id FROM clinicas WHERE nome_key=?", (nome_key,)).fetchone()
                                        if r:
                                            novo_id = r[0] if isinstance(r, (list, tuple)) else r["id"]
                                            reused_c += 1
                                        else:
                                            cur_l.execute(
                                                "INSERT INTO clinicas (nome, nome_key, created_at) VALUES (?,?,?)",
                                                (row.get("nome") or "", nome_key, row.get("created_at") if tem_created else datetime.now().isoformat()),
                                            )
                                            novo_id = cur_l.lastrowid
                                            total_c += 1
                                        map_clinica[int(row["id"])] = novo_id
                        except sqlite3.OperationalError as e:
                            erros_import.append(("clinicas", str(e)))
                        except Exception as e:
                            erros_import.append(("clinicas", f"{type(e).__name__}: {e}"))
                        # 2) Tutores — evita duplicata por nome_key; SELECT só colunas que existem no backup
                        try:
                            if "tutores" not in tabelas_no_backup:
                                pass
                            else:
                                cur_b.execute("PRAGMA table_info(tutores)")
                                cols_t = [c[1] for c in cur_b.fetchall()]
                                if not cols_t:
                                    erros_import.append(("tutores", "Tabela tutores vazia ou sem colunas no backup"))
                                else:
                                    tem_nome_key_t = "nome_key" in cols_t
                                    tem_created_t = "created_at" in cols_t
                                    sel_t = "SELECT " + ", ".join(cols_t) + " FROM tutores"
                                    cur_b.execute(sel_t)
                                    for row in cur_b.fetchall():
                                        row = dict(row)
                                        nome_key_t = (row.get("nome_key") or "").strip() if tem_nome_key_t else _norm_key(row.get("nome") or "")
                                        if not nome_key_t:
                                            nome_key_t = _norm_key(row.get("nome") or "") or "sem_nome"
                                        r = cur_l.execute("SELECT id FROM tutores WHERE nome_key=?", (nome_key_t,)).fetchone()
                                        if r:
                                            novo_id = r[0] if isinstance(r, (list, tuple)) else r["id"]
                                            reused_t += 1
                                        else:
                                            cur_l.execute(
                                                "INSERT INTO tutores (nome, nome_key, telefone, created_at) VALUES (?,?,?,?)",
                                                (row.get("nome") or "", nome_key_t, row.get("telefone") or None, row.get("created_at") if tem_created_t else datetime.now().isoformat()),
                                            )
                                            novo_id = cur_l.lastrowid
                                            total_t += 1
                                        map_tutor[int(row["id"])] = novo_id
                        except sqlite3.OperationalError as e:
                            erros_import.append(("tutores", str(e)))
                        except Exception as e:
                            erros_import.append(("tutores", f"{type(e).__name__}: {e}"))
                        # 3) Pacientes (usar map_tutor; evita duplicata por tutor_id + nome_key + especie; SELECT só colunas que existem no backup)
                        try:
                            if "pacientes" not in tabelas_no_backup:
                                pass
                            else:
                                cur_b.execute("PRAGMA table_info(pacientes)")
                                cols_p = [c[1] for c in cur_b.fetchall()]
                                tem_nome_key_p = "nome_key" in cols_p
                                tem_created_p = "created_at" in cols_p
                                sel_p = "SELECT " + ", ".join(cols_p) + " FROM pacientes"
                                cur_b.execute(sel_p)
                                for row in cur_b.fetchall():
                                    row = dict(row)
                                    novo_tutor_id = map_tutor.get(int(row["tutor_id"])) if row.get("tutor_id") is not None else None
                                    if novo_tutor_id is None:
                                        continue
                                    especie_val = row.get("especie") or ""
                                    nome_key_p = (row.get("nome_key") or "").strip() if tem_nome_key_p else _norm_key(row.get("nome") or "")
                                    if not nome_key_p:
                                        nome_key_p = _norm_key(row.get("nome") or "") or "sem_nome"
                                    r = cur_l.execute(
                                        "SELECT id FROM pacientes WHERE tutor_id=? AND nome_key=? AND especie=?",
                                        (novo_tutor_id, nome_key_p, especie_val),
                                    ).fetchone()
                                    if r:
                                        novo_id = r[0] if isinstance(r, (list, tuple)) else r["id"]
                                    else:
                                        cur_l.execute(
                                            """INSERT INTO pacientes (tutor_id, nome, nome_key, especie, raca, sexo, nascimento, created_at)
                                               VALUES (?,?,?,?,?,?,?,?)""",
                                            (
                                                novo_tutor_id,
                                                row.get("nome") or "",
                                                nome_key_p,
                                                especie_val,
                                                row.get("raca"),
                                                row.get("sexo"),
                                                row.get("nascimento"),
                                                row.get("created_at") if tem_created_p else datetime.now().isoformat(),
                                            ),
                                        )
                                        novo_id = cur_l.lastrowid
                                        total_p += 1
                                    map_paciente[int(row["id"])] = novo_id
                        except sqlite3.OperationalError as e:
                            erros_import.append(("pacientes", str(e)))
                        except Exception as e:
                            erros_import.append(("pacientes", f"{type(e).__name__}: {e}"))
                        # 4) Clinicas parceiras (INSERT OR IGNORE por nome; só colunas que existem no destino)
                        try:
                            cur_b.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinicas_parceiras'")
                            if cur_b.fetchone():
                                cur_l.execute("PRAGMA table_info(clinicas_parceiras)")
                                dest_cp = [c[1] for c in cur_l.fetchall()]
                                cur_b.execute("PRAGMA table_info(clinicas_parceiras)")
                                cols_cp = [c[1] for c in cur_b.fetchall()]
                                cols_cp_insert = [c for c in dest_cp if c != "id" and c in cols_cp]
                                if not cols_cp_insert:
                                    cols_cp_insert = [c for c in dest_cp if c != "id"]
                                cur_b.execute("SELECT * FROM clinicas_parceiras")
                                erro_cp_msg = None
                                for row in cur_b.fetchall():
                                    row_dict = dict(zip(cols_cp, row))
                                    old_id = row_dict.get("id")
                                    nome_cp = (row_dict.get("nome") or "").strip() if row_dict.get("nome") is not None else ""
                                    vals_cp = [row_dict.get(c) for c in cols_cp_insert]
                                    placeholders_cp = ", ".join(["?" for _ in cols_cp_insert])
                                    try:
                                        cur_l.execute(
                                            f"INSERT OR IGNORE INTO clinicas_parceiras ({', '.join(cols_cp_insert)}) VALUES ({placeholders_cp})",
                                            vals_cp,
                                        )
                                        # sqlite3 rowcount pode ser -1; lastrowid > 0 indica inserção nova
                                        if getattr(cur_l, "lastrowid", 0) and cur_l.lastrowid > 0:
                                            total_cp += 1
                                            if old_id is not None:
                                                map_clinica_parceiras[int(old_id)] = cur_l.lastrowid
                                    except sqlite3.OperationalError as e:
                                        if erro_cp_msg is None:
                                            erro_cp_msg = str(e)
                                    if nome_cp and old_id is not None and int(old_id) not in map_clinica_parceiras:
                                        r = cur_l.execute("SELECT id FROM clinicas_parceiras WHERE nome=?", (nome_cp,)).fetchone()
                                        novo_id = (r[0] if isinstance(r, (list, tuple)) else r["id"]) if r else None
                                        if novo_id is not None:
                                            map_clinica_parceiras[int(old_id)] = novo_id
                                if erro_cp_msg:
                                    erros_import.append(("clinicas_parceiras", erro_cp_msg))
                        except sqlite3.OperationalError as e:
                            erros_import.append(("clinicas_parceiras", str(e)))
                        except Exception as e:
                            erros_import.append(("clinicas_parceiras", f"{type(e).__name__}: {e}"))
                        # 5) Laudos (mapear paciente_id e clinica_id; só inserir colunas que existem no destino)
                        # Só processar tabelas de laudos que existem no backup (evitar "no such table")
                        cur_b.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('laudos_ecocardiograma','laudos_eletrocardiograma','laudos_pressao_arterial')")
                        tabelas_laudos_no_backup = [r[0] for r in cur_b.fetchall()]
                        BATCH_LAUDOS_TABELAS = 30  # Processar laudos em lotes para reduzir pico de memória
                        for tabela in tabelas_laudos_no_backup:
                            try:
                                cur_l.execute(f"PRAGMA table_info({tabela})")
                                colunas_destino = [c[1] for c in cur_l.fetchall()]
                                cur_b.execute(f"SELECT * FROM {tabela}")
                                cur_b.execute(f"PRAGMA table_info({tabela})")
                                colunas_laudo = [c[1] for c in cur_b.fetchall()]
                                colunas_sem_id = [c for c in colunas_laudo if c != "id" and c in colunas_destino]
                                for col_extra in ("nome_paciente", "nome_clinica", "nome_tutor"):
                                    if col_extra in colunas_destino and col_extra not in colunas_sem_id:
                                        colunas_sem_id.append(col_extra)
                                if not colunas_sem_id:
                                    continue
                                cur_b.execute(f"SELECT * FROM {tabela}")
                                while True:
                                    rows_laudo = cur_b.fetchmany(BATCH_LAUDOS_TABELAS)
                                    if not rows_laudo:
                                        break
                                    for row in rows_laudo:
                                        row_d = dict(zip(colunas_laudo, row))
                                        old_paciente_id = int(row_d["paciente_id"]) if row_d.get("paciente_id") else None
                                        novo_paciente_id = map_paciente.get(old_paciente_id) if old_paciente_id is not None else None
                                        old_clinica_id = int(row_d["clinica_id"]) if row_d.get("clinica_id") else None
                                        novo_clinica_id = (map_clinica_parceiras.get(old_clinica_id) or map_clinica.get(old_clinica_id)) if old_clinica_id is not None else None
                                        row_d["paciente_id"] = novo_paciente_id
                                        row_d["clinica_id"] = novo_clinica_id
                                        if old_paciente_id is not None:
                                            try:
                                                r_bp = cur_b.execute("SELECT nome FROM pacientes WHERE id=?", (old_paciente_id,)).fetchone()
                                                if r_bp:
                                                    row_d["nome_paciente"] = (r_bp[0] if isinstance(r_bp, (list, tuple)) else r_bp["nome"]) or ""
                                            except Exception:
                                                pass
                                        if old_clinica_id is not None:
                                            try:
                                                r_bc = cur_b.execute("SELECT nome FROM clinicas WHERE id=?", (old_clinica_id,)).fetchone()
                                                if not r_bc:
                                                    r_bc = cur_b.execute("SELECT nome FROM clinicas_parceiras WHERE id=?", (old_clinica_id,)).fetchone()
                                                if r_bc:
                                                    row_d["nome_clinica"] = (r_bc[0] if isinstance(r_bc, (list, tuple)) else r_bc["nome"]) or ""
                                            except Exception:
                                                pass
                                        if old_paciente_id is not None:
                                            try:
                                                r_bt = cur_b.execute(
                                                    "SELECT t.nome FROM pacientes p JOIN tutores t ON t.id = p.tutor_id WHERE p.id=?",
                                                    (old_paciente_id,),
                                                ).fetchone()
                                                if r_bt:
                                                    row_d["nome_tutor"] = (r_bt[0] if isinstance(r_bt, (list, tuple)) else r_bt["nome"]) or ""
                                            except Exception:
                                                pass
                                        vals = []
                                        for c in colunas_sem_id:
                                            if c == "arquivo_xml":
                                                vals.append(row_d.get("arquivo_xml") or row_d.get("arquivo_json"))
                                            elif c in ("nome_paciente", "nome_clinica", "nome_tutor"):
                                                vals.append(row_d.get(c) or "")
                                            else:
                                                vals.append(row_d.get(c))
                                        placeholders = ", ".join(["?" for _ in colunas_sem_id])
                                        try:
                                            cur_l.execute(
                                                f"INSERT INTO {tabela} ({', '.join(colunas_sem_id)}) VALUES ({placeholders})",
                                                vals,
                                            )
                                            total_l += 1
                                        except sqlite3.OperationalError as e:
                                            erros_import.append((f"laudos_{tabela}", str(e)))
                                    conn_local.commit()
                            except sqlite3.OperationalError as e:
                                erros_import.append((tabela, str(e)))
                        # Preencher nome_paciente, nome_clinica e nome_tutor quando vazios (a partir das tabelas vinculadas no destino)
                        for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
                            try:
                                cur_l.execute(f"""UPDATE {tabela} SET nome_paciente = (SELECT nome FROM pacientes WHERE pacientes.id = {tabela}.paciente_id)
                                    WHERE (nome_paciente IS NULL OR TRIM(COALESCE(nome_paciente, '')) = '') AND paciente_id IS NOT NULL""")
                                cur_l.execute(f"""UPDATE {tabela} SET nome_clinica = COALESCE(
                                    (SELECT nome FROM clinicas WHERE clinicas.id = {tabela}.clinica_id),
                                    (SELECT nome FROM clinicas_parceiras WHERE clinicas_parceiras.id = {tabela}.clinica_id)
                                    ) WHERE clinica_id IS NOT NULL AND (nome_clinica IS NULL OR TRIM(COALESCE(nome_clinica, '')) = '')""")
                                cur_l.execute(f"""UPDATE {tabela} SET nome_tutor = (SELECT t.nome FROM pacientes p JOIN tutores t ON t.id = p.tutor_id WHERE p.id = {tabela}.paciente_id)
                                    WHERE paciente_id IS NOT NULL AND (nome_tutor IS NULL OR TRIM(COALESCE(nome_tutor, '')) = '')""")
                            except sqlite3.OperationalError:
                                pass
                        # 6) Laudos da pasta (laudos_arquivos + laudos_arquivos_imagens) — copiar do backup com commit em lotes
                        cur_b.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_arquivos'")
                        if cur_b.fetchone():
                            try:
                                cur_b.execute("PRAGMA table_info(laudos_arquivos)")
                                cols_arq = [c[1] for c in cur_b.fetchall()]
                                cols_sem_id = [c for c in cols_arq if c != "id"]
                                cur_b.execute("SELECT * FROM laudos_arquivos")
                                map_laudo_arq = {}
                                BATCH_LAUDOS = 50
                                i = 0
                                while True:
                                    rows_batch = cur_b.fetchmany(BATCH_LAUDOS)
                                    if not rows_batch:
                                        break
                                    for row in rows_batch:
                                        row_d = dict(zip(cols_arq, row))
                                        old_id = row_d.get("id")
                                        vals = [row_d.get(c) for c in cols_sem_id]
                                        cur_l.execute(
                                            f"INSERT INTO laudos_arquivos ({', '.join(cols_sem_id)}) VALUES ({', '.join(['?'] * len(cols_sem_id))})",
                                            vals,
                                        )
                                        new_id = cur_l.lastrowid
                                        if old_id is not None:
                                            map_laudo_arq[int(old_id)] = new_id
                                        total_laudos_arq += 1
                                        i += 1
                                    conn_local.commit()
                                cur_b.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_arquivos_imagens'")
                                if cur_b.fetchone():
                                    cur_b.execute("PRAGMA table_info(laudos_arquivos_imagens)")
                                    cols_img = [c[1] for c in cur_b.fetchall()]
                                    cols_img_sem_id = [c for c in cols_img if c != "id"]
                                    cur_b.execute("SELECT * FROM laudos_arquivos_imagens")
                                    i2 = 0
                                    while True:
                                        rows_img_batch = cur_b.fetchmany(BATCH_LAUDOS)
                                        if not rows_img_batch:
                                            break
                                        for row in rows_img_batch:
                                            row_d = dict(zip(cols_img, row))
                                            old_laudo_id = row_d.get("laudo_arquivo_id")
                                            new_laudo_id = map_laudo_arq.get(int(old_laudo_id)) if old_laudo_id is not None else None
                                            if new_laudo_id is not None:
                                                vals_img = [new_laudo_id if c == "laudo_arquivo_id" else row_d.get(c) for c in cols_img_sem_id]
                                                cur_l.execute(
                                                    f"INSERT INTO laudos_arquivos_imagens ({', '.join(cols_img_sem_id)}) VALUES ({', '.join(['?'] * len(cols_img_sem_id))})",
                                                    vals_img,
                                                )
                                            i2 += 1
                                        conn_local.commit()
                            except sqlite3.OperationalError as e:
                                erros_import.append(("laudos_arquivos", str(e)))
                        conn_local.commit()
                        msg_c = f"{total_c + reused_c} clínicas ({total_c} novas, {reused_c} já existentes)" if (total_c or reused_c) else "0 clínicas"
                        msg_t = f"{total_t + reused_t} tutores ({total_t} novos, {reused_t} já existentes)" if (total_t or reused_t) else "0 tutores"
                        msg_arq = f", {total_laudos_arq} exames da pasta (JSON/PDF)" if total_laudos_arq else ""
                        st.success(
                            f"✅ Importação concluída: {msg_c}, {msg_t}, {total_p} pacientes, "
                            f"{total_l} laudos, {total_cp} clínicas parceiras{msg_arq}."
                        )
                        try:
                            _db_conn.clear()
                        except Exception:
                            pass
                        st.info(
                            "Se a página travar ou aparecer erro após a importação, **recarregue (F5)** e faça login de novo. "
                            "Os dados já foram salvos no banco."
                        )
                        if erros_import:
                            st.error("Alguns passos falharam: " + " | ".join(f"{k}: {v}" for k, v in erros_import))
                        if (n_p_b > 0 and total_p == 0) or (n_cp_b > 0 and total_cp == 0):
                            st.warning(
                                "Pacientes ou clínicas parceiras: nenhum *novo* inserido (podem já existir no banco). "
                                "Os **nomes** (clínica, animal, tutor) nos laudos são preenchidos a partir do backup durante a importação. "
                                "Se na aba «Buscar exames» continuarem vazios, confira se há erros acima e tente gerar um novo backup com exportar_backup.py e reimportar."
                            )
                        if n_l_b > 0 and total_l == 0:
                            st.warning(
                                "O backup tinha laudos mas nenhum foi inserido. "
                                "Possível causa: nomes de colunas diferentes. Gere o backup com exportar_backup.py na pasta do projeto FortCordis_Novo."
                            )
                        if (n_c_b or n_t_b or n_p_b or n_l_b or n_cp_b) and (total_c + reused_c + total_t + reused_t + total_p + total_l) == 0:
                            st.warning(
                                "O backup tinha dados mas nada foi inserido. Verifique se o arquivo .db foi gerado pelo exportar_backup.py e se as tabelas existem no backup."
                            )
                    except Exception as e:
                        st.error(f"Erro ao importar: {e}")
                        with st.expander("Detalhes técnicos do erro (para diagnóstico)"):
                            st.code(traceback.format_exc(), language="text")
                    finally:
                        try:
                            if conn_backup is not None:
                                conn_backup.close()
                        except Exception:
                            pass
                        try:
                            if conn_local is not None:
                                conn_local.close()
                        except Exception:
                            pass
                        try:
                            if tmp_path and os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {e}")
                    with st.expander("Detalhes técnicos do erro (para diagnóstico)"):
                        st.code(traceback.format_exc(), language="text")

    # ============================================================================
    # ABA: ASSINATURA/CARIMBO (usada nos laudos)
    # ============================================================================
    with tab_assinatura:
        st.subheader("🖊️ Assinatura/Carimbo")
        st.caption("Imagem usada nos laudos (ecocardiograma, pressão arterial, etc.). Salva em sua pasta FortCordis.")
        assin_atual = st.session_state.get("assinatura_path")
        if assin_atual and os.path.exists(assin_atual):
            st.info("Assinatura carregada automaticamente.")
            try:
                st.image(assin_atual, width=200)
            except Exception:
                pass
        else:
            st.warning("Nenhuma assinatura definida. Envie uma imagem para usar nos laudos.")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔁 Trocar assinatura", key="config_trocar_assin", use_container_width=True):
                st.session_state["trocar_assinatura"] = True
                st.rerun()
        with col_b:
            if st.button("🗑️ Remover assinatura", key="config_remover_assin", use_container_width=True):
                try:
                    if os.path.exists(ASSINATURA_PATH):
                        os.remove(ASSINATURA_PATH)
                except Exception:
                    pass
                st.session_state.pop("assinatura_path", None)
                st.session_state["trocar_assinatura"] = False
                st.success("Assinatura removida.")
                st.rerun()
        if st.session_state.get("trocar_assinatura"):
            st.markdown("---")
            up_assin = st.file_uploader(
                "Envie a assinatura (PNG/JPG)",
                type=["png", "jpg", "jpeg"],
                key="config_up_assinatura"
            )
            if up_assin is not None:
                try:
                    img = Image.open(up_assin)
                    img.save(ASSINATURA_PATH, format="PNG")
                    st.session_state["assinatura_path"] = ASSINATURA_PATH
                    st.session_state["trocar_assinatura"] = False
                    st.success("Assinatura salva para os próximos laudos.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar assinatura: {e}")

    # ============================================================================
    # ABA: DIAGNÓSTICO (memória/CPU) – monitoramento local com psutil
    # ============================================================================
    with tab_diagnostico:
        st.subheader("📊 Diagnóstico (memória/CPU)")
        st.caption(
            "Métricas do processo deste app. Útil para identificar vazamento de memória ou cache crescendo "
            "(recomendado pela comunidade Streamlit para profile de uso de memória)."
        )
        try:
            import psutil
            proc = psutil.Process()
            # Memória
            mem = proc.memory_info()
            mem_rss_mb = mem.rss / (1024 * 1024)
            mem_vms_mb = mem.vms / (1024 * 1024)
            mem_percent = proc.memory_percent()
            # CPU (janela recente)
            cpu_percent = proc.cpu_percent(interval=0.1)
            # Sistema (opcional)
            virt = psutil.virtual_memory()
            sys_used_pct = virt.percent
            sys_avail_gb = virt.available / (1024 ** 3)
        except Exception as e:
            st.error(f"Erro ao ler métricas: {e}")
            st.code(str(e), language="text")
        else:
            if st.button("🔄 Atualizar métricas", key="diagnostico_refresh"):
                st.rerun()
            st.markdown("---")
            st.markdown("#### Processo deste app")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("RAM (RSS)", f"{mem_rss_mb:.1f} MB", help="Memória residente do processo")
                st.metric("RAM (% sistema)", f"{mem_percent:.1f}%", help="Percentual da RAM do sistema usado por este processo")
            with c2:
                st.metric("Memória virtual (VMS)", f"{mem_vms_mb:.1f} MB", help="Espaço de endereço virtual")
                st.metric("CPU (processo)", f"{cpu_percent:.1f}%", help="Uso de CPU deste processo (janela recente)")
            with c3:
                st.metric("RAM sistema em uso", f"{sys_used_pct:.1f}%", help="Total da máquina")
                st.metric("RAM disponível (sistema)", f"{sys_avail_gb:.2f} GB", help="Memória livre no sistema")
            st.markdown("---")
            st.caption(
                "Se os valores de RAM (RSS) subirem muito ao usar o app, pode indicar vazamento ou cache. "
                "No Community Cloud, use esta aba para acompanhar o uso antes de atingir o limite."
            )
