# app/pages/laudos.py
"""Página Laudos e Exames: cadastro, medidas, qualitativa, imagens, frases, referências, buscar, pressão arterial."""
import json
import os
import re
import sqlite3
import tempfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from fpdf import FPDF
from PIL import Image

from app.config import DB_PATH
from app.db import _db_init
from app.laudos_helpers import (
    ARQUIVO_FRASES,
    QUALI_DET,
    contar_laudos_arquivos_do_banco,
    contar_laudos_do_banco,
    det_para_txt,
    garantir_schema_det_frase,
    inferir_layout,
    listar_laudos_arquivos_do_banco,
    listar_laudos_do_banco,
    migrar_txt_para_det,
    obter_imagens_laudo_arquivo,
    obter_laudo_arquivo_por_id,
)
from modules.rbac import verificar_permissao


def render_laudos(deps=None):
    """
    Renderiza a página Laudos e Exames.
    deps: namespace com PASTA_LAUDOS, PARAMS, carregar_frases, etc. (passado pelo fortcordis_app para evitar import circular).
    """
    if deps is None:
        st.error("Laudos: configuração não fornecida. Faça commit e redeploy do app (fortcordis_app.py e app/pages/laudos.py).")
        return
    PASTA_LAUDOS = deps.PASTA_LAUDOS
    ARQUIVO_REF = deps.ARQUIVO_REF
    ARQUIVO_REF_FELINOS = deps.ARQUIVO_REF_FELINOS
    PARAMS = deps.PARAMS
    get_grupos_por_especie = deps.get_grupos_por_especie
    normalizar_especie_label = deps.normalizar_especie_label
    montar_nome_base_arquivo = deps.montar_nome_base_arquivo
    calcular_referencia_tabela = deps.calcular_referencia_tabela
    interpretar = deps.interpretar
    interpretar_divedn = deps.interpretar_divedn
    DIVEDN_REF_TXT = deps.DIVEDN_REF_TXT
    listar_registros_arquivados_cached = deps.listar_registros_arquivados_cached
    salvar_laudo_no_banco = deps.salvar_laudo_no_banco
    obter_imagens_para_pdf = deps.obter_imagens_para_pdf
    montar_qualitativa = deps.montar_qualitativa
    _caminho_marca_dagua = deps._caminho_marca_dagua
    montar_chave_frase = deps.montar_chave_frase
    carregar_frases = deps.carregar_frases
    gerar_tabela_padrao = deps.gerar_tabela_padrao
    gerar_tabela_padrao_felinos = deps.gerar_tabela_padrao_felinos
    limpar_e_converter_tabela = deps.limpar_e_converter_tabela
    limpar_e_converter_tabela_felinos = deps.limpar_e_converter_tabela_felinos
    carregar_tabela_referencia_cached = deps.carregar_tabela_referencia_cached
    carregar_tabela_referencia_felinos_cached = deps.carregar_tabela_referencia_felinos_cached
    _normalizar_data_str = deps._normalizar_data_str
    especie_is_felina = deps.especie_is_felina
    calcular_valor_final = deps.calcular_valor_final
    gerar_numero_os = deps.gerar_numero_os

    sb_patologia = st.session_state.get("sb_patologia", "Normal")
    sb_grau_refluxo = st.session_state.get("sb_grau_refluxo", "Leve")
    sb_grau_geral = st.session_state.get("sb_grau_geral", "Normal")

    st.title("🩺 Sistema de Laudos e Exames")
    
    # ============================================================================
    # INICIALIZAÇÃO DE VARIÁVEIS PADRÃO (evita erros de variáveis não definidas)
    # ============================================================================
    
    # Variáveis do paciente
    nome_animal = st.session_state.get("paciente", "")
    especie = st.session_state.get("especie", "Canino")
    raca = st.session_state.get("raca", "")
    sexo = st.session_state.get("sexo", "Macho")
    idade = st.session_state.get("idade", "")
    peso = st.session_state.get("peso", "")
    pelagem = st.session_state.get("pelagem", "")
    
    # Variáveis do tutor
    nome_tutor = st.session_state.get("tutor", "")
    tutor = st.session_state.get("tutor", "")
    endereco = st.session_state.get("endereco", "")
    telefone = st.session_state.get("telefone", "")
    
    # Variáveis do exame
    clinica = st.session_state.get("clinica", "")
    data_exame = st.session_state.get("cad_data", datetime.now().strftime("%d/%m/%Y"))
    veterinario_solicitante = st.session_state.get("veterinario_solicitante", "")
    solicitante = st.session_state.get("veterinario_solicitante", "")
    motivo = st.session_state.get("motivo", "")
    anamnese = st.session_state.get("anamnese", "")
    historico = st.session_state.get("historico", "")
    fc = st.session_state.get("cad_fc", "")
    
    # Variáveis de medidas ecocardiográficas (valores padrão zero)
    ao = st.session_state.get("ao", 0.0)
    ae = st.session_state.get("ae", 0.0)
    ae_ao = st.session_state.get("ae_ao", 0.0)
    vdfve = st.session_state.get("vdfve", 0.0)
    vsfve = st.session_state.get("vsfve", 0.0)
    fe = st.session_state.get("fe", 0.0)
    fs = st.session_state.get("fs", 0.0)
    sivd = st.session_state.get("sivd", 0.0)
    sivs = st.session_state.get("sivs", 0.0)
    plved = st.session_state.get("plved", 0.0)
    plves = st.session_state.get("plves", 0.0)
    vti = st.session_state.get("vti", 0.0)
    grad_max = st.session_state.get("grad_max", 0.0)
    grad_medio = st.session_state.get("grad_medio", 0.0)
    
    # Variáveis de achados
    conclusao = st.session_state.get("conclusao", "")
    achados = st.session_state.get("achados", "")
    
    # Outras variáveis comuns
    regurgitacao_mitral = st.session_state.get("regurgitacao_mitral", "Ausente")
    regurgitacao_tricuspide = st.session_state.get("regurgitacao_tricuspide", "Ausente")
    regurgitacao_aortica = st.session_state.get("regurgitacao_aortica", "Ausente")
    regurgitacao_pulmonar = st.session_state.get("regurgitacao_pulmonar", "Ausente")
    
    # ============================================================================
    # AQUI COMEÇAM AS TABS
    # ============================================================================
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Cadastro", 
        "Medidas", 
        "Qualitativa", 
        "📷 Imagens", 
        "⚙️ Frases", 
        "📏 Referências", 
        "🔎 Buscar exames", 
        "🩺 Pressão Arterial"
    ])

    def buscar_clinicas_cadastradas_laudos():
        """Busca clínicas do MESMO banco de Cadastros (clinicas_parceiras) para integração Laudos ↔ Cadastros."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT id, nome, COALESCE(endereco, '') as endereco,
                           COALESCE(telefone, whatsapp, '') as telefone
                    FROM clinicas_parceiras
                    WHERE (ativo = 1 OR ativo IS NULL)
                    ORDER BY nome
                """)
            except sqlite3.OperationalError:
                cursor.execute("""
                    SELECT id, nome, COALESCE(endereco, '') as endereco,
                           COALESCE(telefone, whatsapp, '') as telefone
                    FROM clinicas_parceiras
                    ORDER BY nome
                """)
            clinicas = cursor.fetchall()
            conn.close()
            return clinicas
        except Exception:
            return []

    def cadastrar_clinica_rapido_laudos(nome, endereco=None, telefone=None):
        """Cadastra nova clínica na mesma tabela de Cadastros (clinicas_parceiras) para integração Laudos ↔ Cadastros."""
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
            return clinica_id, "success"
        except sqlite3.IntegrityError:
            return None, "Clínica com este nome já existe."
        except Exception as e:
            return None, str(e)

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        if "cad_paciente" not in st.session_state:
            st.session_state["cad_paciente"] = nome_animal
        nome_animal = c1.text_input("Paciente", key="cad_paciente")
        # Espécie: menu flutuante (com opções editáveis)
        esp_atual = str(st.session_state.get("cad_especie") or "Canina").strip() or "Canina"
        if "lista_especies" not in st.session_state:
            st.session_state["lista_especies"] = ["Canina", "Felina"]
        if esp_atual not in st.session_state["lista_especies"]:
            st.session_state["lista_especies"].append(esp_atual)
        especie = c2.selectbox("Espécie", st.session_state["lista_especies"], key="cad_especie")
        if "cad_raca" not in st.session_state:
            st.session_state["cad_raca"] = raca
        raca = c3.text_input("Raça", key="cad_raca")
        if "cad_sexo" not in st.session_state:
            st.session_state["cad_sexo"] = sexo
        sexo_sel = c4.selectbox("Sexo", ["Macho", "Fêmea"], index=0 if str(sexo).strip().lower().startswith("m") else 1, key="cad_sexo")

        # Cadastro opcional de novas espécies (além de Canina/Felina)
        # Callback evita StreamlitAPIException (não pode setar cad_especie depois do selectbox no mesmo run)
        def _adicionar_especie_callback():
            nova = (st.session_state.get("nova_especie_txt") or "").strip()
            nova = normalizar_especie_label(nova)
            if nova:
                if "lista_especies" not in st.session_state:
                    st.session_state["lista_especies"] = ["Canina", "Felina"]
                if nova not in st.session_state["lista_especies"]:
                    st.session_state["lista_especies"].append(nova)
                st.session_state["cad_especie"] = nova

        with st.expander("Cadastrar nova espécie"):
            nova_especie = st.text_input("Nova espécie (ex.: Lagomorfo)", key="nova_especie_txt")
            c_add1, c_add2 = st.columns([1, 3])
            if c_add1.button("Adicionar", key="btn_add_especie", on_click=_adicionar_especie_callback):
                st.rerun()
            c_add2.caption("A espécie adicionada fica disponível no menu e pode ser selecionada a qualquer momento.")

        c5, c6, c7, c8 = st.columns(4)
        if "cad_idade" not in st.session_state:
            st.session_state["cad_idade"] = idade
        idade = c5.text_input("Idade", key="cad_idade")
        # garante um valor inicial para o key
        if "cad_peso" not in st.session_state:
            st.session_state["cad_peso"] = peso

        peso = c6.text_input("Peso (kg)", key="cad_peso")

        if "cad_tutor" not in st.session_state:
            st.session_state["cad_tutor"] = tutor
        tutor = c7.text_input("Tutor", key="cad_tutor")
        if "cad_solicitante" not in st.session_state:
            st.session_state["cad_solicitante"] = solicitante
        solicitante = c8.text_input("Solicitante", key="cad_solicitante")
        # ====================================================================
        # SELEÇÃO DE CLÍNICA (VERSÃO MELHORADA)
        # ====================================================================
        
        st.markdown("#### 🏥 Clínica Solicitante")
        
        # Busca clínicas do banco unificado
        clinicas_cadastradas = buscar_clinicas_cadastradas_laudos()
        
        if not clinicas_cadastradas:
            st.warning("⚠️ Nenhuma clínica cadastrada no sistema!")
            
            # Opção de cadastrar rapidamente
            with st.expander("➕ Cadastrar Nova Clínica Agora", expanded=True):
                col_nc1, col_nc2 = st.columns(2)
                with col_nc1:
                    nova_clinica_nome = st.text_input(
                        "Nome da Clínica *", 
                        key="nova_clinica_nome_rapido_laudo"
                    )
                    nova_clinica_end = st.text_input(
                        "Endereço", 
                        key="nova_clinica_end_rapido_laudo"
                    )
                with col_nc2:
                    nova_clinica_tel = st.text_input(
                        "Telefone", 
                        key="nova_clinica_tel_rapido_laudo"
                    )
                
                if st.button("✅ Cadastrar e Continuar", key="btn_cadastrar_clinica_rapido_laudo"):
                    if nova_clinica_nome:
                        clinica_id, msg = cadastrar_clinica_rapido_laudos(
                            nova_clinica_nome,
                            nova_clinica_end,
                            nova_clinica_tel
                        )
                        
                        if clinica_id:
                            st.success(f"✅ Clínica '{nova_clinica_nome}' cadastrada!")
                            st.balloons()
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Erro: {msg}")
                    else:
                        st.error("❌ Nome da clínica é obrigatório")
            
            # Fallback: campo manual se quiser prosseguir sem cadastrar
            clinica = st.text_input(
                "Ou digite manualmente (temporário)",
                key="cad_clinica_manual_fallback",
                help="Digite o nome da clínica para continuar. Recomendamos cadastrar no sistema."
            )
            clinica_id = None
            
        else:
            # Cria lista formatada para o dropdown
            clinicas_opcoes = {}
            
            for cli in clinicas_cadastradas:
                # Formato: "Nome (Endereço | Telefone)"
                endereco = cli[2] if len(cli) > 2 and cli[2] else "Sem endereço"
                telefone = cli[3] if len(cli) > 3 and cli[3] else "Sem telefone"
                
                display = f"{cli[1]} ({endereco} | {telefone})"
                
                clinicas_opcoes[display] = {
                    'id': cli[0],
                    'nome': cli[1]
                }
            
            # Adiciona opções especiais
            clinicas_opcoes["➕ Cadastrar Nova Clínica"] = {'id': None, 'nome': None}
            clinicas_opcoes["📝 Digitar Manualmente (não recomendado)"] = {'id': -1, 'nome': None}
            
            # Dropdown
            clinica_selecionada_display = st.selectbox(
                "Selecione a Clínica *",
                options=list(clinicas_opcoes.keys()),
                key="cad_clinica_dropdown",
                help="Selecione a clínica que solicitou o exame"
            )
            
            # Processa a seleção
            clinica_selecionada_info = clinicas_opcoes[clinica_selecionada_display]
            
            if clinica_selecionada_display == "➕ Cadastrar Nova Clínica":
                # Usuário quer cadastrar nova clínica
                st.info("💡 Cadastrando nova clínica no sistema...")
                
                with st.expander("📝 Dados da Nova Clínica", expanded=True):
                    col_nc1, col_nc2 = st.columns(2)
                    
                    with col_nc1:
                        nova_clinica_nome = st.text_input(
                            "Nome da Clínica *",
                            key="nova_clinica_nome_laudo"
                        )
                        nova_clinica_end = st.text_input(
                            "Endereço",
                            key="nova_clinica_end_laudo"
                        )
                    
                    with col_nc2:
                        nova_clinica_tel = st.text_input(
                            "Telefone",
                            key="nova_clinica_tel_laudo"
                        )
                    
                    if st.button("✅ Cadastrar Clínica", key="btn_cadastrar_clinica_laudo", type="primary"):
                        if nova_clinica_nome:
                            clinica_id, msg = cadastrar_clinica_rapido_laudos(
                                nova_clinica_nome,
                                nova_clinica_end,
                                nova_clinica_tel
                            )
                            
                            if clinica_id:
                                st.success(f"✅ Clínica '{nova_clinica_nome}' cadastrada com sucesso!")
                                st.info("💡 Selecione a clínica novamente no dropdown acima")
                                st.balloons()
                                import time
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f"❌ Erro ao cadastrar: {msg}")
                        else:
                            st.error("❌ Nome da clínica é obrigatório")
                
                # Variáveis temporárias
                clinica = None
                clinica_id = None
            
            elif clinica_selecionada_display == "📝 Digitar Manualmente (não recomendado)":
                # Usuário insiste em digitar manualmente
                st.warning("⚠️ Digitação manual não é recomendada!")
                st.caption("💡 Clínicas digitadas manualmente não ficam no cadastro e podem gerar duplicatas")
                
                clinica = st.text_input(
                    "Digite o nome da clínica",
                    key="cad_clinica_manual_insistencia"
                )
                clinica_id = None
            
            else:
                # Clínica válida selecionada
                clinica_id = clinica_selecionada_info['id']
                clinica = clinica_selecionada_info['nome']
                
                # Mostra confirmação
                st.success(f"✅ Clínica selecionada: **{clinica}**")
        
        # ====================================================================
        # FIM DA SELEÇÃO DE CLÍNICA
        # ====================================================================
        c9, c10, c11, c12 = st.columns(4)
        if "cad_data" not in st.session_state:
            st.session_state["cad_data"] = data_exame
        data_exame = c9.text_input("Data", key="cad_data")
        ritmo = c10.selectbox("Ritmo", ["Sinusal", "Sinusal Arritmico", "FA", "Outro"])
        fc = c11.text_input("FC (bpm)", value=fc)
        estado = c12.selectbox("Estado", ["Calmo", "Agitado", "Sedado"])

    with tab2:
        st.subheader("Medidas")
        dados = st.session_state["dados_atuais"]

        # mantém o peso numérico sincronizado com o campo de cadastro (para cálculos)
        try:
            st.session_state["peso_atual"] = float(str(st.session_state.get("cad_peso", "")).replace(",", "."))
        except:
            pass

        # Interpretação automática (apenas quando houver referência cadastrada; por enquanto, apenas para cães)
        especie_norm = normalizar_especie_label(st.session_state.get('cad_especie', 'Canina'))
        is_canina = (especie_norm == "Canina")

        try:
            peso_ref_num = float(st.session_state.get("peso_atual", 0.0) or 0.0)
        except Exception:
            peso_ref_num = 0.0

        
        def _ref_interp_para_ui(param_key: str, valor: float):
            """Retorna (texto_referencia, interpretacao) para exibir na aba de medidas."""
            especie_norm = str(st.session_state.get('cad_especie', 'Canina') or '').strip().lower()
            is_canina = especie_norm in ("canina", "canino", "cao", "cão", "dog")
            is_felina = especie_norm in ("felina", "felino", "gato", "gata", "cat")

            try:
                v = float(valor)
            except Exception:
                v = 0.0

            # Referência fixa: DIVEdN (somente caninos)
            if param_key == "DIVEdN":
                if not is_canina:
                    return "", ""
                return DIVEDN_REF_TXT, (interpretar_divedn(v) if v > 0 else "")

            # Referência fixa: E/E' (vale para ambas as espécies; ajuste se desejar)
            if param_key == "EEp":
                ref_txt = "<12"
                if v <= 0:
                    interp = ""
                elif v < 12:
                    interp = "Normal"
                else:
                    interp = "Aumentado"
                return ref_txt, interp

            # Referências fixas - felinos
            if is_felina and param_key == "LA_FS":
                ref_txt = "21 - 25%"
                if v <= 0:
                    interp = ""
                elif v < 21:
                    interp = "Reduzido"
                elif v > 25:
                    interp = "Aumentado"
                else:
                    interp = "Normal"
                return ref_txt, interp

            if is_felina and param_key == "AURICULAR_FLOW":
                ref_txt = ">0,25 m/s"
                if v <= 0:
                    interp = ""
                elif v > 0.25:
                    interp = "Normal"
                else:
                    interp = "Reduzido"
                return ref_txt, interp

            # Referência via tabela (quando houver chave de referência)
            try:
                _, _, ref_key = PARAMS[param_key]
            except Exception:
                ref_key = None

            # Regras de aplicação por espécie
            if is_canina:
                df_use = st.session_state.get("df_ref")
                allow = True
            elif is_felina:
                # por enquanto: apenas VE - Modo M e AE/Ao
                df_use = st.session_state.get("df_ref_felinos")
                allow = ref_key in {"LVIDd", "LVIDs", "IVSd", "IVSs", "LVPWd", "LVPWs", "FS", "EF", "LA", "Ao", "LA_Ao"}
            else:
                df_use = None
                allow = False

            if (not allow) or (not ref_key) or (peso_ref_num <= 0) or (df_use is None):
                return "", ""

            ref_tuple, ref_txt = calcular_referencia_tabela(ref_key, peso_ref_num, df=df_use)
            # quando não há referência real (ex.: 0-0), não exibe nada
            if (not ref_tuple) or (ref_tuple[0] == 0 and ref_tuple[1] == 0):
                return "", ""
            interp = interpretar(v, ref_tuple)
            if not ref_txt or ref_txt.strip() in ("--", ""):
                return "", ""
            return ref_txt, interp



        cols = st.columns(3)
        col_i = 0

        for titulo, chaves in get_grupos_por_especie(st.session_state.get('cad_especie', '')):
            with cols[col_i % 3]:
                st.markdown(f"### {titulo}")

                for k in chaves:
                    label, _, _ = PARAMS[k]

                    col_val, col_interp = st.columns([2.2, 1.0])

                    # Campo calculado automaticamente: DIVEdN (DIVEd normalizado)
                    if k == "DIVEdN":
                        # Verifica espécie
                        especie_atual = st.session_state.get("cad_especie", "Canina")
                        
                        # Só calcula e mostra para CANINOS
                        if especie_atual == "Canina":
                            with col_val:
                                try:
                                    dived = float(dados.get("LVIDd", 0.0) or 0.0)
                                except:
                                    dived = 0.0

                                try:
                                    peso_kg = float(st.session_state.get("peso_atual", 0.0) or 0.0)
                                except:
                                    peso_kg = 0.0

                                # dived está em mm -> converter para cm
                                dived_cm = dived / 10.0

                                if peso_kg > 0 and dived_cm > 0:
                                    dados["DIVEdN"] = round(dived_cm / (peso_kg ** 0.294), 2)
                                else:
                                    dados["DIVEdN"] = 0.0

                                st.session_state["DIVEdN_out"] = float(dados.get("DIVEdN", 0.0) or 0.0)
                                st.number_input(label, value=float(dados.get("DIVEdN", 0.0)), disabled=True, key="DIVEdN_out")

                            with col_interp:
                                ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                                if ref_txt:
                                    st.caption(f"Ref.: {ref_txt}")
                                if interp_txt:
                                    st.caption(f"Interp.: {interp_txt}")
                        else:
                            # Felinos: não mostra o campo e zera o valor
                            dados["DIVEdN"] = None

                        continue

                    # Campos manuais + cálculo automático: Doppler tecidual (Relação e'/a')
                    if k == "TDI_e_a":
                        with col_val:
                            # valores medidos manualmente (o equipamento não calcula a razão)
                            dados["TDI_e"] = st.number_input("e' (Doppler tecidual)", value=float(dados.get("TDI_e", 0.0)), step=0.01, key="TDI_e_in")
                            dados["TDI_a"] = st.number_input("a' (Doppler tecidual)", value=float(dados.get("TDI_a", 0.0)), step=0.01, key="TDI_a_in")

                            try:
                                e_val = float(dados.get("TDI_e", 0.0) or 0.0)
                                a_val = float(dados.get("TDI_a", 0.0) or 0.0)
                            except Exception:
                                e_val, a_val = 0.0, 0.0

                            if e_val > 0 and a_val > 0:
                                dados["TDI_e_a"] = round(e_val / a_val, 2)
                            else:
                                dados["TDI_e_a"] = 0.0

                            # mantém o widget sincronizado (key fixa)
                            st.session_state["TDI_ea_out"] = float(dados.get("TDI_e_a", 0.0) or 0.0)
                            st.number_input(label, value=float(dados.get("TDI_e_a", 0.0)), disabled=True, key="TDI_ea_out")

                        # sem referência por tabela aqui (campo manual)
                        continue

                    # Felinos: passos mais amigáveis
                    if k == "LA_FS":
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=0.1, key=f"med_{k}")
                        with col_interp:
                            ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                            if ref_txt:
                                st.caption(f"Ref.: {ref_txt}")
                            if interp_txt:
                                st.caption(f"Interp.: {interp_txt}")
                        continue

                    if k == "AURICULAR_FLOW":
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=0.01, key=f"med_{k}")
                        with col_interp:
                            ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                            if ref_txt:
                                st.caption(f"Ref.: {ref_txt}")
                            if interp_txt:
                                st.caption(f"Interp.: {interp_txt}")
                        continue

                    # Ajuste de passo para dp/dt (variação de pressão/tempo)
                    if k == "MR_dPdt":
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=10.0, key=f"med_{k}")
                        # sem referência por tabela
                        continue

                    # Relação E/E' (apenas valor final; pode vir do XML)
                    if k == "EEp":
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=0.01, key="EEp_in")
                        with col_interp:
                            ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                            if ref_txt:
                                st.caption(f"Ref.: {ref_txt}")
                            if interp_txt:
                                st.caption(f"Interp.: {interp_txt}")
                        continue

                    # Artéria pulmonar / Aorta (AP/Ao): passos mais adequados
                    if k in ("PA_AP", "PA_AO"):
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=0.1, key=f"med_{k}")
                        continue
                    if k == "PA_AP_AO":
                        with col_val:
                            dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), step=0.001, key=f"med_{k}")
                        continue

                    # padrão
                    with col_val:
                        dados[k] = st.number_input(label, value=float(dados.get(k, 0.0)), key=f"med_{k}")

                    with col_interp:
                        ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                        if ref_txt:
                            st.caption(f"Ref.: {ref_txt}")
                        if interp_txt:
                            st.caption(f"Interp.: {interp_txt}")

                st.markdown("---")

            col_i += 1

        st.session_state["dados_atuais"] = dados

    with tab3:
        st.subheader("Análise Qualitativa")

        # garante db_frases carregado uma única vez
        if "db_frases" not in st.session_state:
            st.session_state["db_frases"] = carregar_frases()

        db = st.session_state["db_frases"]
        # 1) Chave da frase selecionada
        chave_atual = montar_chave_frase(sb_patologia, sb_grau_refluxo, sb_grau_geral)

        # 2) Pega do banco; se não existir, cria uma entrada válida
        entry_atual = db.get(chave_atual)
        if not entry_atual:
            entry_atual = garantir_schema_det_frase({})
            entry_atual = migrar_txt_para_det(entry_atual)
            entry_atual["layout"] = inferir_layout(entry_atual, chave_atual)
            db[chave_atual] = entry_atual  # salva no banco em memória

        # 3) Decide layout
        is_enxuto = (sb_patologia == "Normal") or (entry_atual.get("layout") == "enxuto")

        # guarda o layout atual (útil para arquivar e recarregar exames)
        st.session_state["layout_qualitativa"] = "enxuto" if is_enxuto else "detalhado"

        if is_enxuto:
            # ===== layout enxuto (igual ao Normal) =====
            st.markdown("### Valvas")
            st.text_area("Valvas (texto corrido)", key="txt_valvas", height=90)

            st.markdown("### Câmaras")
            st.text_area("Câmaras (texto corrido)", key="txt_camaras", height=90)

            st.markdown("### Função")
            st.text_area("Função (texto corrido)", key="txt_funcao", height=90)

            st.markdown("### Pericárdio")
            st.text_area("Pericárdio (texto corrido)", key="txt_pericardio", height=90)

            st.markdown("### Vasos")
            st.text_area("Vasos (texto corrido)", key="txt_vasos", height=90)

            st.markdown("### AD/VD (átrio direito/ventrículo direito) (Subjetivo)")
            st.text_area(
                "AD/VD (átrio direito/ventrículo direito) (texto corrido)",
                key="txt_ad_vd",
                height=90
            )

            st.markdown("**CONCLUSÃO**")
            st.text_area("Conclusão", key="txt_conclusao", height=120)

        else:
            # ===== layout detalhado =====
            st.markdown("### Valvas")
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Mitral", key="q_valvas_mitral", height=70)
                st.text_area("Tricúspide", key="q_valvas_tricuspide", height=70)
            with c2:
                st.text_area("Aórtica", key="q_valvas_aortica", height=70)
                st.text_area("Pulmonar", key="q_valvas_pulmonar", height=70)

            st.markdown("### Câmaras")
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Átrio esquerdo", key="q_camaras_ae", height=70)
                st.text_area("Ventrículo esquerdo", key="q_camaras_ve", height=70)
            with c2:
                st.text_area("Átrio direito", key="q_camaras_ad", height=70)
                st.text_area("Ventrículo direito", key="q_camaras_vd", height=70)

            st.markdown("### Vasos")
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Aorta", key="q_vasos_aorta", height=70)
                st.text_area("Artéria pulmonar", key="q_vasos_art_pulmonar", height=70)
            with c2:
                st.text_area("Veias pulmonares", key="q_vasos_veias_pulmonares", height=70)
                st.text_area("Cava/Hepáticas", key="q_vasos_cava_hepaticas", height=70)

            st.markdown("### Função")
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Sistólica VE", key="q_funcao_sistolica_ve", height=70)
                st.text_area("Diastólica", key="q_funcao_diastolica", height=70)
            with c2:
                st.text_area("Sistólica VD", key="q_funcao_sistolica_vd", height=70)
                st.text_area("Sincronia", key="q_funcao_sincronia", height=70)

            st.markdown("### Pericárdio")
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Efusão", key="q_pericardio_efusao", height=70)
                st.text_area("Espessamento", key="q_pericardio_espessamento", height=70)
            with c2:
                st.text_area("Sinais de tamponamento", key="q_pericardio_tamponamento", height=70)

            st.markdown("**CONCLUSÃO**")
            st.text_area("Conclusão", key="txt_conclusao", height=150)

    with tab4:
        st.subheader("📷 Imagens do exame")

        # Imagens carregadas do exame arquivado (quando existirem)
        imgs_carregadas = st.session_state.get("imagens_carregadas", []) or []
        if imgs_carregadas:
            st.caption("Imagens carregadas do exame arquivado:")
            cols = st.columns(4)
            for idx, it in enumerate(imgs_carregadas):
                b = it.get("bytes") if isinstance(it, dict) else None
                if b:
                    cols[idx % 4].image(b, use_container_width=True)

            cL, cR = st.columns([1, 3])
            with cL:
                if st.button("🧹 Remover imagens carregadas", key="btn_limpar_imagens_carregadas"):
                    st.session_state["imagens_carregadas"] = []
                    st.rerun()

        st.divider()

        st.caption("Adicionar novas imagens (essas também entram no PDF):")
        novas = st.file_uploader(
            "Adicionar imagens",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="imagens_upload_novas"
        )
        if novas:
            cols = st.columns(4)
            for idx, img in enumerate(novas):
                cols[idx % 4].image(img, use_container_width=True)

    with tab5:
        st.header("⚙️ Editor de Frases")

        if "db_frases" not in st.session_state:
            st.session_state["db_frases"] = carregar_frases()

        db = st.session_state["db_frases"]

        # DEBUG sempre aparece
        st.caption(f"ARQUIVO_FRASES: {ARQUIVO_FRASES} | existe? {os.path.exists(ARQUIVO_FRASES)}")
        st.caption(f"Total de chaves no banco: {len(db)}")
        st.caption(f"Exemplos: {list(db.keys())[:5]}")
        st.caption("Selecione uma patologia (com grau) para editar os textos. Depois clique em Salvar.")

        lista_chaves = sorted(list(db.keys()))
        st.write("DEBUG: lista_chaves =", len(lista_chaves))

        if not lista_chaves:
            st.warning("Nenhuma frase cadastrada no banco (db vazio).")
            st.stop()

        # ✅ Selectbox SEM try/except gigante (se der erro, você quer ver o erro mesmo)
        chave_sel = st.selectbox(
            "Patologia / Grau",
            options=lista_chaves,
            index=0,
            key="frase_chave_sel"
        )

        # -----------------------------
        # A PARTIR DAQUI É O EDITOR (SEMPRE EXECUTA)
        # -----------------------------
        layout_atual = db.get(chave_sel, {}).get("layout", "detalhado")
        layout_sel = st.radio(
            "Modo de descrição desta patologia",
            options=["enxuto", "detalhado"],
            index=0 if layout_atual == "enxuto" else 1,
            horizontal=True,
            key=f"tab5_layout_{chave_sel}"
        )

        db[chave_sel]["layout"] = layout_sel

        # Campos padrão do seu laudo
        campos = ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]

        # Garante que a entrada selecionada exista e tenha todos os campos
        if chave_sel not in db:
            db[chave_sel] = {c: "" for c in campos}
        for c in campos:
            if c not in db[chave_sel]:
                db[chave_sel][c] = ""

        # Garante schema novo
        db[chave_sel] = garantir_schema_det_frase(db[chave_sel])
        db[chave_sel] = migrar_txt_para_det(db[chave_sel])

        col1, col2 = st.columns([2, 1])

        with col1:
            layout = db[chave_sel].get("layout", "detalhado")

            if layout == "enxuto":
                st.subheader("Textos (Enxutos)")

                is_normal = (chave_sel == "Normal (Normal)")

                # (mantive sua lógica do Normal)
                if is_normal:
                    if not (db[chave_sel].get("valvas") or "").strip():
                        db[chave_sel]["valvas"] = (
                            "Valvas mitral, tricúspide, aórtica e pulmonar com morfologia, espessura e mobilidade preservadas, "
                            "sem regurgitações valvares significativas ou sinais de estenose."
                        )
                    if not (db[chave_sel].get("camaras") or "").strip():
                        db[chave_sel]["camaras"] = (
                            "Dimensões cavitárias preservadas, sem evidências ecocardiográficas de remodelamento significativo."
                        )
                    if not (db[chave_sel].get("funcao") or "").strip():
                        db[chave_sel]["funcao"] = "Função sistólica e diastólica global preservadas."
                    if not (db[chave_sel].get("pericardio") or "").strip():
                        db[chave_sel]["pericardio"] = "Pericárdio com aspecto preservado. Ausência de efusão pericárdica."
                    if not (db[chave_sel].get("vasos") or "").strip():
                        db[chave_sel]["vasos"] = "Grandes vasos da base com diâmetros e relações anatômicas preservadas."
                    if not (db[chave_sel].get("ad_vd") or "").strip():
                        db[chave_sel]["ad_vd"] = "Átrio direito e ventrículo direito com dimensões e contratilidade preservadas."
                    db[chave_sel]["conclusao"] = "EXAME NORMAL"

                db[chave_sel]["valvas"] = st.text_area("Valvas (texto corrido)", value=db[chave_sel]["valvas"], height=90)
                db[chave_sel]["camaras"] = st.text_area("Câmaras (texto corrido)", value=db[chave_sel]["camaras"], height=90)
                db[chave_sel]["funcao"] = st.text_area("Função (texto corrido)", value=db[chave_sel]["funcao"], height=70)
                db[chave_sel]["pericardio"] = st.text_area("Pericárdio (texto corrido)", value=db[chave_sel]["pericardio"], height=70)
                db[chave_sel]["vasos"] = st.text_area("Vasos (texto corrido)", value=db[chave_sel]["vasos"], height=70)
                db[chave_sel]["ad_vd"] = st.text_area("AD/VD (texto corrido)", value=db[chave_sel]["ad_vd"], height=70)

                st.subheader("Conclusão")
                if is_normal:
                    st.text_area("Conclusão", value=db[chave_sel]["conclusao"], height=60, disabled=True)
                else:
                    db[chave_sel]["conclusao"] = st.text_area("Conclusão", value=db[chave_sel]["conclusao"], height=90)

            else:
                st.subheader("Textos (Detalhados)")

                det = db[chave_sel]["det"]

                with st.expander("Valvas", expanded=True):
                    det["valvas"]["mitral"] = st.text_area("Mitral", value=det["valvas"]["mitral"], height=80)
                    det["valvas"]["tricuspide"] = st.text_area("Tricúspide", value=det["valvas"]["tricuspide"], height=80)
                    det["valvas"]["aortica"] = st.text_area("Aórtica", value=det["valvas"]["aortica"], height=80)
                    det["valvas"]["pulmonar"] = st.text_area("Pulmonar", value=det["valvas"]["pulmonar"], height=80)

                with st.expander("Câmaras", expanded=False):
                    det["camaras"]["ae"] = st.text_area("Átrio esquerdo", value=det["camaras"]["ae"], height=80)
                    det["camaras"]["ad"] = st.text_area("Átrio direito", value=det["camaras"]["ad"], height=80)
                    det["camaras"]["ve"] = st.text_area("Ventrículo esquerdo", value=det["camaras"]["ve"], height=80)
                    det["camaras"]["vd"] = st.text_area("Ventrículo direito", value=det["camaras"]["vd"], height=80)

                with st.expander("Vasos", expanded=False):
                    det["vasos"]["aorta"] = st.text_area("Aorta", value=det["vasos"]["aorta"], height=80)
                    det["vasos"]["art_pulmonar"] = st.text_area("Artéria pulmonar", value=det["vasos"]["art_pulmonar"], height=80)
                    det["vasos"]["veias_pulmonares"] = st.text_area("Veias pulmonares", value=det["vasos"]["veias_pulmonares"], height=80)
                    det["vasos"]["cava_hepaticas"] = st.text_area("Cava/Hepáticas", value=det["vasos"]["cava_hepaticas"], height=80)

                with st.expander("Função", expanded=False):
                    det["funcao"]["sistolica_ve"] = st.text_area("Sistólica VE", value=det["funcao"]["sistolica_ve"], height=80)
                    det["funcao"]["sistolica_vd"] = st.text_area("Sistólica VD", value=det["funcao"]["sistolica_vd"], height=80)
                    det["funcao"]["diastolica"] = st.text_area("Diastólica", value=det["funcao"]["diastolica"], height=80)
                    det["funcao"]["sincronia"] = st.text_area("Sincronia", value=det["funcao"]["sincronia"], height=80)

                with st.expander("Pericárdio", expanded=False):
                    det["pericardio"]["efusao"] = st.text_area("Efusão", value=det["pericardio"]["efusao"], height=80)
                    det["pericardio"]["espessamento"] = st.text_area("Espessamento", value=det["pericardio"]["espessamento"], height=80)
                    det["pericardio"]["tamponamento"] = st.text_area("Sinais de tamponamento", value=det["pericardio"]["tamponamento"], height=80)

                st.subheader("Conclusão")
                db[chave_sel]["conclusao"] = st.text_area("Conclusão", value=db[chave_sel]["conclusao"], height=120)

                # sincroniza textos corridos
                txts = det_para_txt(det)
                db[chave_sel]["valvas"] = txts.get("valvas", "")
                db[chave_sel]["camaras"] = txts.get("camaras", "")
                db[chave_sel]["vasos"] = txts.get("vasos", "")
                db[chave_sel]["funcao"] = txts.get("funcao", "")
                db[chave_sel]["pericardio"] = txts.get("pericardio", "")

        with col2:
            st.subheader("Ações")

            nova_chave = st.text_input("Nova patologia (com grau)", placeholder="Ex.: Hipertensão Pulmonar (Moderada)")
            layout_novo = st.radio(
                "Layout padrão para novas patologias",
                options=["detalhado", "enxuto"],
                index=0,
                horizontal=True
            )

            if st.button("➕ Adicionar", use_container_width=True):
                nova = (nova_chave or "").strip()
                if not nova:
                    st.error("Informe um nome para a nova patologia.")
                else:
                    def _criar_entry_vazia(layout_padrao="detalhado"):
                        entry = {c: "" for c in campos}
                        entry["layout"] = layout_padrao
                        entry = garantir_schema_det_frase(entry)
                        return entry

                    if nova.endswith(")") and " (" in nova:
                        if nova in db:
                            st.warning("Essa patologia já existe.")
                        else:
                            db[nova] = _criar_entry_vazia(layout_novo)
                            with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
                                json.dump(db, f, indent=4, ensure_ascii=False)
                            st.session_state["db_frases"] = db
                            st.success("Adicionada e salva.")
                            st.rerun()
                    else:
                        criadas = 0
                        for g in ["Leve", "Moderada", "Importante", "Grave"]:
                            chave = f"{nova} ({g})"
                            if chave not in db:
                                db[chave] = _criar_entry_vazia(layout_novo)
                                criadas += 1
                        with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
                            json.dump(db, f, indent=4, ensure_ascii=False)
                        st.session_state["db_frases"] = db
                        st.success(f"Criadas {criadas} variações e salvo no JSON.")
                        st.rerun()

            st.divider()

            if st.button("💾 Salvar frases", use_container_width=True):
                with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=4, ensure_ascii=False)
                st.session_state["db_frases"] = db
                st.success("Salvo no arquivo frases_personalizadas.json.")
                st.rerun()

            st.divider()

            if st.button("🗑️ Excluir patologia selecionada", use_container_width=True):
                if chave_sel in db:
                    del db[chave_sel]
                    with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
                        json.dump(db, f, indent=4, ensure_ascii=False)
                    st.session_state["db_frases"] = db
                    st.success("Excluída.")
                    st.rerun()


    with tab6:
        st.subheader("Tabela de referência (editar / importar / exportar)")

        # Escolha da tabela (Canina x Felina)
        ref_especie = st.radio("Tabela", ["Canina", "Felina"], horizontal=True, key="ref_tab_especie")
        is_ref_canina = (ref_especie == "Canina")

        if is_ref_canina:
            df_ref_local = st.session_state.get("df_ref")
            arquivo_ref_local = ARQUIVO_REF
            gerar_padrao_local = gerar_tabela_padrao
            limpar_local = limpar_e_converter_tabela
            cache_clear_local = carregar_tabela_referencia_cached.clear
            session_key_local = "df_ref"
            label_upload = "Importar nova tabela (CSV) - CANINOS"
            label_download = "Baixar tabela atual (CSV) - CANINOS"
            label_reset = "Restaurar tabela padrão (CANINOS)"
        else:
            df_ref_local = st.session_state.get("df_ref_felinos")
            arquivo_ref_local = ARQUIVO_REF_FELINOS
            gerar_padrao_local = gerar_tabela_padrao_felinos
            limpar_local = limpar_e_converter_tabela_felinos
            cache_clear_local = carregar_tabela_referencia_felinos_cached.clear
            session_key_local = "df_ref_felinos"
            label_upload = "Importar nova tabela (CSV) - FELINOS"
            label_download = "Baixar tabela atual (CSV) - FELINOS"
            label_reset = "Restaurar tabela padrão (FELINOS)"

        if df_ref_local is None:
            # garante carregamento
            if is_ref_canina:
                df_ref_local = carregar_tabela_referencia_cached()
            else:
                df_ref_local = carregar_tabela_referencia_felinos_cached()
            st.session_state[session_key_local] = df_ref_local

        st.caption("Edite a tabela abaixo, salve, ou importe um CSV. A referência será usada automaticamente onde houver mapeamento.")
        df_edit = st.data_editor(df_ref_local, num_rows="dynamic", use_container_width=True)

        colA, colB, colC = st.columns([1.2, 1.2, 1.2])

        with colA:
            if st.button("💾 Salvar tabela", key="btn_save_ref_table"):
                try:
                    df_to_save = limpar_local(pd.DataFrame(df_edit))
                    df_to_save.to_csv(arquivo_ref_local, index=False)
                    cache_clear_local()
                    st.session_state[session_key_local] = df_to_save
                    st.success(f"Tabela salva em {arquivo_ref_local}.")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        with colB:
            up = st.file_uploader(label_upload, type=["csv"], key="upload_ref_table")
            if up is not None:
                try:
                    df_up = pd.read_csv(up)
                    df_up = limpar_local(df_up)
                    df_up.to_csv(arquivo_ref_local, index=False)
                    cache_clear_local()
                    st.session_state[session_key_local] = df_up
                    st.success("Tabela importada com sucesso.")
                except Exception as e:
                    st.error(f"Falha ao importar: {e}")

        with colC:
            if st.button(label_reset, key="btn_reset_ref_table"):
                try:
                    df_def = gerar_padrao_local()
                    df_def.to_csv(arquivo_ref_local, index=False)
                    cache_clear_local()
                    st.session_state[session_key_local] = df_def
                    st.success("Tabela padrão restaurada.")
                except Exception as e:
                    st.error(f"Falha ao restaurar: {e}")

        st.download_button(
            label_download,
            data=pd.DataFrame(df_edit).to_csv(index=False).encode("utf-8"),
            file_name=("tabela_referencia_caninos.csv" if is_ref_canina else "tabela_referencia_felinos.csv"),
            mime="text/csv"
        )

        st.markdown("---")
        st.subheader("Consulta rápida")

        peso_test = st.number_input("Peso do paciente (kg)", value=10.0, step=0.5, key="peso_consulta_ref")
        parametro = st.selectbox(
            "Parâmetro",
            ["LA_Ao", "LVIDd", "LVIDs", "IVSd", "IVSs", "LVPWd", "LVPWs", "FS", "EF"],
            key="param_consulta_ref"
        )

        ref_tuple, ref_txt = calcular_referencia_tabela(parametro, peso_test, df=st.session_state.get(session_key_local))
        if ref_tuple:
            st.info(f"Referência: {ref_txt}")
        else:
            st.warning("Referência indisponível para esse parâmetro na tabela selecionada.")


    with tab7:
        _db_init()
        st.header("🔎 Buscar exames arquivados")
        st.caption("Busque por tutor, clínica ou pet. Exames importados do backup ou da pasta (JSON/PDF) aparecem abaixo.")

        # ---------- Exames no banco (importados) — visíveis após restaurar backup ----------
        st.subheader("📂 Exames no banco (importados do backup)")
        st.caption("Laudos que vieram do backup. **Deixe os filtros vazios para ver todos os laudos.** Use os filtros para achar por tutor, clínica ou pet.")
        lb_tutor = st.text_input("Tutor (contém)", key="busca_exame_tutor_db", placeholder="Nome do tutor")
        lb_clinica = st.text_input("Clínica (contém)", key="busca_exame_clinica_db", placeholder="Nome da clínica")
        lb_animal = st.text_input("Animal / pet (contém)", key="busca_exame_animal_db", placeholder="Nome do animal")
        lb_livre = st.text_input("🔍 Busca livre (tutor, clínica ou pet)", key="busca_exame_livre_db", placeholder="Ex.: Pipoca — deixe vazio para ver todos")
        laudos_banco = listar_laudos_do_banco(
            tutor_filtro=lb_tutor or None,
            clinica_filtro=lb_clinica or None,
            animal_filtro=lb_animal or None,
            busca_livre=lb_livre or None,
        )
        total_banco = contar_laudos_do_banco()
        if laudos_banco:
            df_banco = pd.DataFrame(laudos_banco)
            df_banco["data"] = df_banco["data"].astype(str)
            # Deduplicar por data + clinica + animal + tutor + tipo (evita dezenas de repetidos quando backup foi importado várias vezes)
            colunas_exib = ["data", "clinica", "animal", "tutor", "tipo_exame"]
            df_uniq = df_banco[colunas_exib].drop_duplicates(keep="first")
            n_uniq, n_total = len(df_uniq), len(df_banco)
            st.dataframe(df_uniq, use_container_width=True, hide_index=True)
            texto_total = f"**{n_uniq}** exame(s) únicos" + (f" (de **{n_total}** no banco — repetidos por importações anteriores; importe o backup **apenas uma vez**)." if n_uniq < n_total else ".")
            st.caption(
                f"{texto_total} "
                "O banco guarda o caminho do seu PC (ex.: C:\\...\\Laudos\\arquivo.pdf); no sistema online os arquivos não existem — aqui você vê só os dados (data, clínica, animal, tutor, tipo)."
            )
            if df_uniq["clinica"].fillna("").str.strip().eq("").all() and df_uniq["animal"].fillna("").str.strip().eq("").all():
                st.info(
                    "**Clínica, animal e tutor vazios?** Em Configurações > Importar dados: marque **«Limpar laudos antes de importar»** e importe o backup **uma vez**. "
                    "Isso apaga os laudos repetidos e reimporta com os vínculos corretos — os nomes passam a aparecer aqui."
                )
        else:
            if total_banco > 0:
                st.warning(
                    f"Nenhum exame **com esses filtros**. Há **{total_banco}** laudo(s) no banco. "
                    "Limpe a Busca livre e os outros filtros para ver todos."
                )
            else:
                st.info("Nenhum exame no banco. Se importou backup, confira se o .db continha laudos (ecocardiograma, eletro, pressão) e se a importação concluiu com sucesso.")

        # ---------- Exames da pasta importados para o banco (disponíveis no sistema online) ----------
        st.markdown("---")
        st.subheader("📂 Exames da pasta (importados para o banco)")
        st.caption("Laudos que você importou da pasta local (script importar_pasta_laudos_para_banco.py). Aparecem no sistema online após importar o backup.")
        laudos_arq = listar_laudos_arquivos_do_banco(
            tutor_filtro=lb_tutor or None,
            clinica_filtro=lb_clinica or None,
            animal_filtro=lb_animal or None,
            busca_livre=lb_livre or None,
        )
        n_arq = contar_laudos_arquivos_do_banco()
        if laudos_arq:
            df_arq = pd.DataFrame(laudos_arq)
            df_arq["data"] = df_arq["data"].astype(str)
            colunas_exib_arq = ["data", "clinica", "animal", "tutor", "tipo_exame"]
            st.dataframe(df_arq[colunas_exib_arq], use_container_width=True, hide_index=True)
            st.caption(f"**{len(laudos_arq)}** exame(s) da pasta no banco.")
            opcoes_arq = [f'{r["data"]} | {r["animal"]} | {r["tutor"]} | {r["clinica"]}' for r in laudos_arq]
            idx_arq = st.selectbox("Selecione um exame para baixar (JSON/PDF)", range(len(opcoes_arq)), format_func=lambda i: opcoes_arq[i], key="sel_laudo_arquivo")
            row_arq = laudos_arq[idx_arq]
            blob_row = obter_laudo_arquivo_por_id(row_arq["id_laudo_arquivo"])
            if blob_row:
                cj, cp, cl = st.columns(3)
                with cj:
                    if blob_row.get("conteudo_json"):
                        st.download_button(
                            "⬇️ Baixar JSON",
                            data=blob_row["conteudo_json"],
                            file_name=(blob_row.get("nome_base") or "laudo") + ".json",
                            mime="application/json",
                            key="dl_json_arquivo",
                        )
                    else:
                        st.caption("JSON não armazenado.")
                with cp:
                    if blob_row.get("conteudo_pdf"):
                        st.download_button(
                            "⬇️ Baixar PDF",
                            data=blob_row["conteudo_pdf"],
                            file_name=(blob_row.get("nome_base") or "laudo") + ".pdf",
                            mime="application/pdf",
                            key="dl_pdf_arquivo",
                        )
                    else:
                        st.caption("PDF não armazenado.")
                with cl:
                    if blob_row.get("conteudo_json"):
                        if st.button("📥 Carregar JSON", key="btn_carregar_json_banco", help="Carrega dados e imagens do exame para edição nas abas Cadastro, Medidas, Imagens, etc."):
                            try:
                                obj = json.loads(blob_row["conteudo_json"].decode("utf-8") if isinstance(blob_row["conteudo_json"], bytes) else blob_row["conteudo_json"])
                                imagens = obter_imagens_laudo_arquivo(row_arq["id_laudo_arquivo"])
                                st.session_state["__carregar_exame_json_content"] = obj
                                st.session_state["__carregar_exame_imagens"] = [
                                    {"name": (img.get("nome_arquivo") or f"imagem_{i}.jpg"), "bytes": img.get("conteudo") or b""}
                                    for i, img in enumerate(imagens)
                                ]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao carregar exame: {e}")
                    else:
                        st.caption("—")
        else:
            if n_arq > 0:
                st.warning("Nenhum exame com esses filtros. Limpe a busca para ver todos.")
            else:
                st.info("Nenhum exame da pasta no banco. Execute o script **importar_pasta_laudos_para_banco.py** na pasta do projeto (apontando para a pasta Laudos) e depois importe o backup no sistema online.")

        st.markdown("---")
        st.subheader("📁 Exames na pasta (arquivos JSON/PDF)")
        st.caption(f"Pasta: {PASTA_LAUDOS}")

        # varre apenas JSON (JavaScript Object Notation) e usa cache com TTL (Time To Live)
        registros = listar_registros_arquivados_cached(str(PASTA_LAUDOS))

        if not registros:
            st.warning("Nenhum exame na pasta. No sistema online essa pasta não existe; use a seção «Exames no banco» acima para ver os importados.")
        else:
            df_busca = pd.DataFrame(registros)

            # --- filtros ---
            st.markdown("### Filtros")

            # linha 1: datas
            c1, c2 = st.columns(2)
            with c1:
                dt_ini = st.date_input("Data inicial", value=date.today().replace(day=1))
            with c2:
                dt_fim = st.date_input("Data final", value=date.today())

            # linha 2: clínica + animal + tutor
            c3, c4, c5 = st.columns(3)
            with c3:
                clinicas = ["(todas)"] + sorted([c for c in df_busca["clinica"].dropna().unique().tolist() if str(c).strip()])
                clin_sel = st.selectbox("Clínica", options=clinicas)

            with c4:
                animal_txt = st.text_input("Animal (contém)", value="")

            with c5:
                tutor_txt = st.text_input("Tutor (contém)", value="")

            # linha 3: busca livre (animal+tutor+clínica)
            busca_livre = st.text_input("Busca livre (animal / tutor / clínica)", value="")


            # normaliza datas do DF para filtrar
            def _to_date_safe(s):
                try:
                    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
                except:
                    return None

            df_busca["data_dt"] = df_busca["data"].apply(_to_date_safe)

            # aplica filtros
            m = df_busca["data_dt"].notna()
            m &= (df_busca["data_dt"] >= dt_ini) & (df_busca["data_dt"] <= dt_fim)

            if clin_sel != "(todas)":
                m &= (df_busca["clinica"].astype(str) == str(clin_sel))

            if animal_txt.strip():
                m &= df_busca["animal"].astype(str).str.lower().str.contains(animal_txt.strip().lower(), na=False)

            if tutor_txt.strip():
                m &= df_busca["tutor"].astype(str).str.lower().str.contains(tutor_txt.strip().lower(), na=False)

            # Busca livre (AND): separa em termos e exige que TODOS apareçam
            if busca_livre.strip():
                combinado = (
                    df_busca["animal"].astype(str).str.lower() + " " +
                    df_busca["tutor"].astype(str).str.lower() + " " +
                    df_busca["clinica"].astype(str).str.lower()
                )

                # termos = palavras digitadas (ignora múltiplos espaços)
                termos = [t for t in busca_livre.strip().lower().split() if t]

                # AND: todos os termos precisam aparecer no combinado
                for termo in termos:
                    m &= combinado.str.contains(re.escape(termo), na=False)


            df_f = df_busca[m].sort_values(["data_dt", "clinica", "animal"], ascending=[False, True, True])

            st.write(f"**Resultados:** {len(df_f)}")
            st.dataframe(df_f[["data", "clinica", "animal", "tutor"]], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Baixar arquivo do exame encontrado")

            # seleção por linha (simples: selectbox com o stem)
            opcoes = df_f.apply(lambda r: f'{r["data"]} | {r["animal"]} | {r["tutor"]} | {r["clinica"]}', axis=1).tolist()

            if not opcoes:
                st.info("Nenhum exame corresponde aos filtros.")
            else:
                idx_sel = st.selectbox("Selecione um exame", options=list(range(len(opcoes))), format_func=lambda i: opcoes[i])
                row = df_f.iloc[idx_sel]

                st.markdown("### Ações")
                if st.button("📥 Carregar exame para edição", use_container_width=True):
                    st.session_state["__carregar_exame_json_path"] = row["arquivo_json"]
                    st.rerun()

                # download JSON
                try:
                    json_bytes = Path(row["arquivo_json"]).read_bytes()
                    st.download_button(
                        "⬇️ Baixar JSON (arquivo arquivado)",
                        data=json_bytes,
                        file_name=Path(row["arquivo_json"]).name,
                        mime="application/json"
                    )
                except Exception as e:
                    st.warning(f"Não consegui ler o JSON: {e}")

                # download PDF
                try:
                    pdf_path = Path(row["arquivo_pdf"])
                    if pdf_path.exists():
                        pdf_bytes = pdf_path.read_bytes()
                        st.download_button(
                            "⬇️ Baixar PDF (arquivo arquivado)",
                            data=pdf_bytes,
                            file_name=pdf_path.name,
                            mime="application/pdf"
                        )
                    else:
                        st.info("PDF correspondente não encontrado (talvez você tenha arquivado só o JSON em algum momento).")
                except Exception as e:
                    st.warning(f"Não consegui ler o PDF: {e}")


    # PDF E SALVAR
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c2:
        # nome padrão base
        nome_base = montar_nome_base_arquivo(
            data_exame=data_exame,
            animal=nome_animal,
            tutor=tutor,
            clinica=clinica
        )

        # inclui metadados no JSON (isso facilita MUITO a busca)
        dados_save = {
            "paciente": {
                "nome": nome_animal,
                "peso": peso,
                "tutor": tutor,
                "clinica": clinica,
                "data_exame": _normalizar_data_str(data_exame),
                "especie": especie,
                "raca": raca,
                "sexo": sexo_sel,
                "idade": idade,
                "solicitante": solicitante,
                "fc": fc
            },
            "medidas": dados,
            "textos": {k: st.session_state[f"txt_{k}"] for k in ['valvas','camaras','funcao','pericardio','vasos','ad_vd','conclusao']},
            # guarda também o layout e os subcampos detalhados (para recarregar e editar fielmente)
            "layout_qualitativa": st.session_state.get("layout_qualitativa", "detalhado"),
            "quali_det": {
                sec: {it: (st.session_state.get(f"q_{sec}_{it}", "") or "").strip() for it in itens}
                for sec, itens in QUALI_DET.items()
            },
            "qualitativa_meta": {
                "patologia": st.session_state.get("sb_patologia", "Normal"),
                "grau_refluxo": st.session_state.get("sb_grau_refluxo", "Leve"),
                "congestao": bool(st.session_state.get("sb_congestao", False)),
                "grau_geral": st.session_state.get("sb_grau_geral", "Normal"),
            },
            # lista de arquivos de imagem arquivados junto do exame (quando houver)
            "imagens": []
        }


        json_str = json.dumps(dados_save, indent=4, ensure_ascii=False)

        st.download_button(
            "💾 Baixar JSON",
            data=json_str,
            file_name=f"{nome_base}.json",
            mime="application/json"
        )



    with tab8:
        st.header("🩺 Laudo de Pressão Arterial")
        st.caption("Preencha as aferições manualmente. O sistema gera um PDF separado do laudo ecocardiográfico, com o mesmo cabeçalho e padrão de nome de arquivo.")

        # =========================
        # Entradas (manual)
        # =========================
        cA, cB, cC = st.columns(3)
        pa_pas1 = cA.number_input("1ª aferição: Pressão Sistólica (mmHg)", min_value=0, max_value=400, value=int(st.session_state.get("pa_pas1", 0) or 0), step=1, key="pa_pas1")
        pa_pas2 = cB.number_input("2ª aferição: Pressão Sistólica (mmHg)", min_value=0, max_value=400, value=int(st.session_state.get("pa_pas2", 0) or 0), step=1, key="pa_pas2")
        pa_pas3 = cC.number_input("3ª aferição: Pressão Sistólica (mmHg)", min_value=0, max_value=400, value=int(st.session_state.get("pa_pas3", 0) or 0), step=1, key="pa_pas3")

        vals = [v for v in [pa_pas1, pa_pas2, pa_pas3] if isinstance(v, (int, float)) and v > 0]
        pa_media = int(round(sum(vals)/len(vals))) if vals else 0

        c1_pa, c2_pa = st.columns([1, 1])
        with c1_pa:
            st.text_input("PA Sistólica Média (mmHg)", value=str(pa_media), disabled=True)
        with c2_pa:
            st.text_input("Método", value="Doppler", disabled=True)

        st.markdown("### Observações")
        opcoes_manguito = ["Manguito 01", "Manguito 02", "Manguito 03", "Manguito 04", "Manguito 05", "Manguito 06", "Outro"]
        opcoes_membro = ["Membro anterior direito", "Membro anterior esquerdo", "Membro posterior direito", "Membro posterior esquerdo", "Cauda", "Outro"]
        opcoes_decubito = ["Decúbito lateral direito", "Decúbito lateral esquerdo", "Decúbito esternal", "Decúbito dorsal", "Em estação", "Outro"]

        o1, o2, o3 = st.columns(3)
        with o1:
            pa_manguito_sel = str(st.session_state.get("pa_manguito", "") or "Manguito 02")
            idx_manguito = opcoes_manguito.index(pa_manguito_sel) if pa_manguito_sel in opcoes_manguito else 1
            manguito_sel = st.selectbox("Manguito", options=opcoes_manguito, index=idx_manguito, key="pa_manguito_select")
            if manguito_sel == "Outro":
                manguito = st.text_input("Manguito (especificar)", value=str(st.session_state.get("pa_manguito_outro", "") or ""), key="pa_manguito_outro", placeholder="Ex.: Manguito pediátrico")
            else:
                manguito = manguito_sel
        with o2:
            pa_membro_sel = str(st.session_state.get("pa_membro", "") or "Membro anterior esquerdo")
            idx_membro = opcoes_membro.index(pa_membro_sel) if pa_membro_sel in opcoes_membro else 1
            membro_sel = st.selectbox("Membro em que o exame foi realizado", options=opcoes_membro, index=idx_membro, key="pa_membro_select")
            if membro_sel == "Outro":
                membro = st.text_input("Membro (especificar)", value=str(st.session_state.get("pa_membro_outro", "") or ""), key="pa_membro_outro", placeholder="Ex.: Membro anterior direito")
            else:
                membro = membro_sel
        with o3:
            pa_decubito_sel = str(st.session_state.get("pa_decubito", "") or "Decúbito lateral direito")
            idx_decubito = opcoes_decubito.index(pa_decubito_sel) if pa_decubito_sel in opcoes_decubito else 0
            decubito_sel = st.selectbox("Decúbito", options=opcoes_decubito, index=idx_decubito, key="pa_decubito_select")
            if decubito_sel == "Outro":
                decubito = st.text_input("Decúbito (especificar)", value=str(st.session_state.get("pa_decubito_outro", "") or ""), key="pa_decubito_outro", placeholder="Ex.: Em estação")
            else:
                decubito = decubito_sel

        obs_extra = st.text_area("Outras observações (opcional)", value=str(st.session_state.get("pa_obs_extra", "") or ""), key="pa_obs_extra", height=80)

        st.markdown("### Valores de referência (PAS - pressão arterial sistólica)")
        st.write("• Normal: 110 a 140 mmHg")
        st.write("• Levemente elevada: 141 a 159 mmHg (recomendado monitoramento e reavaliação periódica)")
        st.write("• Moderadamente elevada: 160 a 179 mmHg (potencial risco de lesão em órgãos-alvo)")
        st.write("• Severamente elevada: ≥180 mmHg")

        # Clínica para o nome do arquivo (mesmo padrão do laudo de ecocardiograma: data__animal__tutor__clinica__PA)
        st.markdown("### Clínica (incluída no nome do arquivo)")
        clinicas_pa = buscar_clinicas_cadastradas_laudos()
        cad_clinica_atual = str(st.session_state.get("cad_clinica", "") or "").strip()
        if clinicas_pa:
            nomes_clinicas = [c[1] for c in clinicas_pa]
            idx_clinica_pa = nomes_clinicas.index(cad_clinica_atual) if cad_clinica_atual in nomes_clinicas else 0
            clinica_pa_sel = st.selectbox(
                "Selecione a clínica *",
                options=nomes_clinicas,
                index=idx_clinica_pa,
                key="pa_clinica_select",
                help="Será usada no nome do arquivo (igual ao laudo de ecocardiograma): data_animal_tutor_clinica__PA.pdf"
            )
            st.session_state["cad_clinica"] = clinica_pa_sel
        else:
            st.caption("Cadastre clínicas em Cadastros > Clínicas Parceiras para selecionar aqui.")
            if not cad_clinica_atual:
                clinica_pa_manual = st.text_input("Ou digite a clínica (para o nome do arquivo)", key="pa_clinica_manual")
                if clinica_pa_manual:
                    st.session_state["cad_clinica"] = clinica_pa_manual.strip()

        # =========================
        # Geração do PDF (separado)
        # =========================
        def criar_pdf_pressao_arterial():
            # --- Helpers ---
            def pdf_safe(v):
                if v is None:
                    return ""
                s = str(v)
                s = (s.replace("–", "-")
                    .replace("—", "-")
                    .replace("−", "-")
                    .replace("“", '"')
                    .replace("”", '"')
                    .replace("’", "'")
                    .replace("•", "-")
                    .replace("≥", ">=")
                    .replace("≤", "<="))
                return s.encode("latin-1", "ignore").decode("latin-1")

            class PDF_Export_PA(FPDF):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.set_margins(10, 30, 10)
                    self.set_auto_page_break(True, 15)

                def header(self):
                    # Marca d'água / logo (mesmo padrão do ECO)
                    bg = _caminho_marca_dagua() or ("logo.png" if os.path.exists("logo.png") else None)
                    if bg:
                        # Marca d'água menor e mais alta para não conflitar com carimbo/assinatura
                        self.image(bg, x=55, y=65, w=100)
                    if os.path.exists("logo.png"):
                        self.image("logo.png", x=10, y=8, w=35)

                    self.set_xy(52, 15)
                    self.set_font("Arial", "B", 16)
                    self.set_text_color(0, 0, 0)
                    self.cell(0, 10, "LAUDO DE PRESSÃO ARTERIAL", ln=1, align="L")

                    # onde começa o corpo (mantém a regra do ECO)
                    if self.page_no() == 1:
                        y_corpo = 45
                    else:
                        y_corpo = 55
                    self.set_xy(self.l_margin, y_corpo)

                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 9)
                    self.set_text_color(100, 100, 100)
                    self.cell(0, 10, "Fort Cordis Cardiologia Veterinária | Fortaleza-CE", align="C")

            pdf = PDF_Export_PA()
            pdf.add_page()

            # Cabeçalho do paciente (mesmo padrão do ECO)
            nome_animal = str(st.session_state.get("cad_paciente", "") or "")
            especie = str(st.session_state.get("cad_especie", "Canina") or "Canina")
            raca = str(st.session_state.get("cad_raca", "") or "")
            sexo = str(st.session_state.get("cad_sexo", "") or "")
            idade = str(st.session_state.get("cad_idade", "") or "")
            peso = str(st.session_state.get("cad_peso", "") or "")
            tutor = str(st.session_state.get("cad_tutor", "") or "")
            solicitante = str(st.session_state.get("cad_solicitante", "") or "")
            clinica = str(st.session_state.get("cad_clinica", "") or "")
            data_exame = str(st.session_state.get("cad_data", "") or "")

            X = 50
            pdf.set_y(pdf.t_margin)
            pdf.set_font("Arial", size=10)
            pdf.set_x(X); pdf.cell(0, 5, pdf_safe(f"Paciente: {nome_animal} | Espécie: {especie} | Raça: {raca}"), ln=1)
            pdf.set_x(X); pdf.cell(0, 5, pdf_safe(f"Sexo: {sexo} | Idade: {idade} | Peso: {peso} kg"), ln=1)
            pdf.set_x(X); pdf.cell(0, 5, pdf_safe(f"Tutor: {tutor} | Solicitante: {solicitante}"), ln=1)
            if clinica:
                pdf.set_x(X); pdf.cell(0, 5, pdf_safe(f"Clínica: {clinica}"), ln=1)
            pdf.set_x(X); pdf.cell(0, 5, pdf_safe(f"Data: {data_exame}"), ln=1)
            y = pdf.get_y() + 3
            pdf.line(10, y, 200, y)
            pdf.set_y(y + 4)

            # Barra do título (como no modelo)
            pdf.set_fill_color(255, 210, 210)
            pdf.set_text_color(0)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "LAUDO PRESSÃO ARTERIAL", ln=1, align="C", fill=True)
            pdf.ln(4)

            # Quadros: aferições (esq) e observações (dir)
            x0 = 10
            y0 = pdf.get_y()
            w_total = 190
            w_left = 95
            w_right = 95
            h_box = 36

            # bordas
            pdf.set_draw_color(0, 0, 0)
            pdf.rect(x0, y0, w_left, h_box)
            pdf.rect(x0 + w_left, y0, w_right, h_box)

            # Títulos
            pdf.set_xy(x0 + 2, y0 + 2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(w_left - 4, 5, "Aferição de Pressão Arterial:", ln=1)

            pdf.set_xy(x0 + w_left + 2, y0 + 2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(w_right - 4, 5, "Observações:", ln=1)

            # Conteúdo esquerdo
            pdf.set_font("Arial", "", 10)
            pdf.set_xy(x0 + 2, y0 + 10)
            pdf.cell(w_left - 4, 5, pdf_safe(f"1ª aferição: Pressão Sistólica  {pa_pas1} mmHg"), ln=1)
            pdf.set_x(x0 + 2)
            pdf.cell(w_left - 4, 5, pdf_safe(f"2ª aferição: Pressão Sistólica  {pa_pas2} mmHg"), ln=1)
            pdf.set_x(x0 + 2)
            pdf.cell(w_left - 4, 5, pdf_safe(f"3ª aferição: Pressão Sistólica  {pa_pas3} mmHg"), ln=1)
            pdf.ln(1)
            pdf.set_x(x0 + 2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(w_left - 4, 5, pdf_safe(f"PA Sistólica Média:  {pa_media} mmHg"), ln=1)

            # Conteúdo direito (observações)
            pdf.set_font("Arial", "B", 10)
            pdf.set_xy(x0 + w_left + 2, y0 + 10)
            linhas_obs = []
            if manguito: linhas_obs.append(str(manguito).upper())
            if membro: linhas_obs.append(str(membro).upper())
            if decubito: linhas_obs.append(str(decubito).upper())

            for ln in linhas_obs[:4]:
                pdf.set_x(x0 + w_left + 2)
                pdf.cell(w_right - 4, 5, pdf_safe(ln), ln=1)

            pdf.set_y(y0 + h_box + 6)

            # Outras observações (fora do quadro, com quebra de linha)
            extra_txt = str(obs_extra or "").strip()
            if extra_txt:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 5, "Outras observações:", ln=1)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 5, pdf_safe(extra_txt))
                pdf.ln(2)

            # Box de referência (borda verde)
            y_ref = pdf.get_y()
            pdf.set_draw_color(0, 120, 0)
            h_ref = 40
            pdf.rect(10, y_ref, 190, h_ref)
            pdf.set_xy(12, y_ref + 2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5, "Valores de Referência", ln=1)
            pdf.set_font("Arial", "", 10)
            pdf.set_x(12); pdf.cell(0, 5, "Pressão arterial sistólica (PAS):", ln=1)
            pdf.set_x(12); pdf.cell(0, 5, "Normal: 110 a 140 mmHg", ln=1)
            pdf.set_x(12); pdf.cell(0, 5, "Levemente elevada: 141 a 159 mmHg (recomendado monitoramento e reavaliação periódica)", ln=1)
            pdf.set_x(12); pdf.cell(0, 5, "Moderadamente elevada: 160 a 179 mmHg (potencial risco de lesão em órgãos-alvo)", ln=1)
            pdf.set_x(12); pdf.cell(0, 5, pdf_safe("Severamente elevada: ≥180 mmHg"), ln=1)

            pdf.set_draw_color(0, 0, 0)

            # Ajuste de layout: inicia os disclaimers abaixo do box de referência
            y_after_ref = max(pdf.get_y(), y_ref + h_ref) + 8
            pdf.set_y(y_after_ref)

            # Disclaimers (mesmo texto do modelo)
            # Garante espaço para texto + assinatura
            def garantir_espaco(mm):
                if pdf.get_y() + mm > (pdf.page_break_trigger):
                    pdf.add_page()

            garantir_espaco(55)

            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(0)
            d1 = "* Os valores de pressão arterial podem apresentar variações individuais, sendo necessário correlacioná-los com o quadro clínico do paciente e repetir as medições em intervalos adequados para garantir a precisão dos resultados."
            d2 = "* A pressão arterial foi aferida pelo método Doppler, que pode apresentar pequenas variações em relação ao método invasivo. Para maior precisão, a avaliação deve ser correlacionada com exames complementares."
            pdf.multi_cell(0, 4.5, pdf_safe(d1))
            pdf.ln(1)
            pdf.multi_cell(0, 4.5, pdf_safe(d2))
            pdf.ln(4)

            # Assinatura (mesma do ECO)
            assin_path = st.session_state.get("assinatura_path")
            if assin_path and os.path.exists(assin_path):
                garantir_espaco(35)
                y_ass = pdf.get_y()
                w_ass = 40
                # Mantém proporção da imagem (evita distorção e "contorno" aparente)
                try:
                    iw, ih = Image.open(assin_path).size
                    h_ass = (w_ass * float(ih) / float(iw)) if iw else 30
                except Exception:
                    h_ass = 30

                # Alinha à direita e fora da área central da marca d'água
                x_ass = pdf.w - pdf.r_margin - w_ass
                try:
                    # Evita que o carimbo/assinatura evidencie a marca d'água: aplica uma máscara branca atrás da imagem.
                    pad = 2  # mm de margem ao redor da assinatura
                    pdf.set_fill_color(255, 255, 255)
                    pdf.rect(x_ass - pad, y_ass - pad, w_ass + 2*pad, h_ass + 2*pad, style="F")
                    pdf.image(assin_path, x=x_ass, y=y_ass, w=w_ass, h=h_ass)
                except Exception:
                    pass
                pdf.ln(h_ass + 2)

            out = pdf.output(dest="S")
            if isinstance(out, (bytes, bytearray)):
                return bytes(out)
            return out.encode("latin-1")

        # Botões
        cbtn1, cbtn2 = st.columns([1, 1])
        if cbtn1.button("🧾 Gerar PDF - Pressão Arterial", key="btn_pdf_pa"):
            pdf_pa_bytes = criar_pdf_pressao_arterial()
            st.session_state["pdf_pa_bytes"] = pdf_pa_bytes

            # arquiva PDF e JSON (separados) na mesma pasta, com sufixo __PA
            try:
                nome_base = montar_nome_base_arquivo(
                    data_exame=str(st.session_state.get("cad_data", "") or ""),
                    animal=str(st.session_state.get("cad_paciente", "") or ""),
                    tutor=str(st.session_state.get("cad_tutor", "") or ""),
                    clinica=str(st.session_state.get("cad_clinica", "") or "")
                )
                nome_base_pa = f"{nome_base}__PA"

                dados_pa = {
                    "tipo_exame": "pressao_arterial",
                    "paciente": {
                        "data_exame": str(st.session_state.get("cad_data", "") or ""),
                        "clinica": str(st.session_state.get("cad_clinica", "") or ""),
                        "nome": str(st.session_state.get("cad_paciente", "") or ""),
                        "tutor": str(st.session_state.get("cad_tutor", "") or ""),
                        "especie": str(st.session_state.get("cad_especie", "") or ""),
                        "raca": str(st.session_state.get("cad_raca", "") or ""),
                        "sexo": str(st.session_state.get("cad_sexo", "") or ""),
                        "idade": str(st.session_state.get("cad_idade", "") or ""),
                        "peso": str(st.session_state.get("cad_peso", "") or ""),
                        "solicitante": str(st.session_state.get("cad_solicitante", "") or "")
                    },
                    "pressao_arterial": {
                        "pas_1": int(pa_pas1),
                        "pas_2": int(pa_pas2),
                        "pas_3": int(pa_pas3),
                        "pas_media": int(pa_media),
                        "manguito": str(manguito or ""),
                        "membro": str(membro or ""),
                        "decubito": str(decubito or ""),
                        "obs_extra": str(obs_extra or ""),
                        "metodo": "Doppler"
                    }
                }

                (PASTA_LAUDOS / f"{nome_base_pa}.pdf").write_bytes(pdf_pa_bytes)
                (PASTA_LAUDOS / f"{nome_base_pa}.json").write_text(json.dumps(dados_pa, indent=4, ensure_ascii=False), encoding="utf-8")

                st.success(f"PDF de Pressão Arterial gerado e arquivado em: {PASTA_LAUDOS}")
            except Exception as e:
                st.warning(f"PDF gerado, mas não consegui arquivar automaticamente: {e}")

        if "pdf_pa_bytes" in st.session_state:
            # nome do arquivo para download
            nome_base = montar_nome_base_arquivo(
                data_exame=str(st.session_state.get("cad_data", "") or ""),
                animal=str(st.session_state.get("cad_paciente", "") or ""),
                tutor=str(st.session_state.get("cad_tutor", "") or ""),
                clinica=str(st.session_state.get("cad_clinica", "") or "")
            )
            nome_base_pa = f"{nome_base}__PA"
            cbtn2.download_button(
                "⬇️ Baixar PDF - Pressão Arterial",
                data=st.session_state["pdf_pa_bytes"],
                file_name=f"{nome_base_pa}.pdf",
                mime="application/pdf",
                use_container_width=True
            )



    with c1:
        class PDF_Export(FPDF):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.set_margins(10, 30, 10)
                self.set_auto_page_break(True,15)
            def header(self):
                # --- cabeçalho FIXO (sempre igual) ---
                bg = _caminho_marca_dagua() or ("logo.png" if os.path.exists("logo.png") else None)
                if bg:
                    # Marca d'água menor e mais alta para não conflitar com carimbo/assinatura
                    self.image(bg, x=55, y=65, w=100)

                if os.path.exists("logo.png"):
                    self.image("logo.png", x=10, y=8, w=35)

                self.set_xy(52, 15)
                self.set_font("Arial", "B", 16)
                self.set_text_color(0, 0, 0)
                self.cell(0, 10, "LAUDO ECOCARDIOGRÁFICO", ln=1, align="L")

                # --- regra: onde começa o CORPO ---
                if self.page_no() == 1:
                    y_corpo = 45   # 1ª página (fica como está)
                else:
                    y_corpo = 55   # 2ª página em diante (desce pra não pegar no logo)

                self.set_xy(self.l_margin, y_corpo)



            def footer(self):
                self.set_y(-15); self.set_font("Arial", 'I', 9); self.set_text_color(100,100,100)
                self.cell(0, 10, "Fort Cordis Cardiologia Veterinária | Fortaleza-CE", align='C')

        def criar_pdf():
            pdf = PDF_Export()
            pdf.add_page()
            def pdf_safe(txt):
                if txt is None:
                    return ""
                s = str(txt)
                s = (s.replace("–", "-")
                    .replace("—", "-")
                    .replace("−", "-")
                    .replace("“", '"')
                    .replace("”", '"')
                    .replace("’", "'")
                    .replace("•", "-"))
                return s.encode("latin-1", "ignore").decode("latin-1")

            def espaco_restante():
                return pdf.h - pdf.get_y() - pdf.b_margin
            def garantir_espaco(min_mm):
                if espaco_restante() < min_mm:
                    pdf.add_page()
            X = 50
            pdf.set_y(pdf.t_margin)
            pdf.set_font("Arial", size=10)
            pdf.set_x(X); pdf.cell(0,5,f"Paciente: {nome_animal} | Espécie: {especie} | Raça: {raca}", ln=1)
            pdf.set_x(X); pdf.cell(0,5,f"Sexo: {sexo_sel} | Idade: {idade} | Peso: {peso} kg", ln=1)
            pdf.set_x(X); pdf.cell(0,5,f"Tutor: {tutor} | Solicitante: {solicitante}", ln=1)
            if clinica: pdf.set_x(X); pdf.cell(0,5,f"Clínica: {clinica}", ln=1)
            pdf.set_x(X); pdf.cell(0,5,f"Data: {data_exame}", ln=1)
            y=pdf.get_y()+3; pdf.line(10,y,200,y); pdf.set_y(y+2)
            pdf.set_font("Arial",'B',10); pdf.cell(0,8,f"Ritmo: {ritmo} | FC: {fc} bpm | Estado: {estado}", ln=1, align='C')
            pdf.ln(3); pdf.set_font("Arial",'B',11); pdf.cell(0,8,"ANÁLISE QUANTITATIVA",ln=1)
            pdf.line(10,pdf.get_y(),200,pdf.get_y()); pdf.ln(2)

            ALT_TITULO = 7
            ALT_CABEC  = 6
            ALT_LINHA  = 6
            ESPACO_POS = 2

            def cabecalho_tabela(titulo):
                pdf.set_fill_color(50,50,60); pdf.set_text_color(255); pdf.set_font("Arial",'B',10)
                pdf.cell(0, ALT_TITULO, pdf_safe(f"  {titulo}"), ln=1, fill=True)

                pdf.set_fill_color(220); pdf.set_text_color(0); pdf.set_font("Arial",'B',9)
                pdf.cell(60, ALT_CABEC, "  Parâmetro", 0, fill=True)
                pdf.cell(30, ALT_CABEC, "Valor", 0, align='C', fill=True)
                pdf.cell(45, ALT_CABEC, "Referência", 0, align='C', fill=True)
                pdf.cell(0,  ALT_CABEC, "Interpretação", 0, ln=1, align='C', fill=True)

                pdf.set_font("Arial",'',9)

            def tab_auto(titulo, chaves):
                is_felina_pdf = especie_is_felina(especie)
                df_ref_pdf = st.session_state.get("df_ref_felinos") if is_felina_pdf else st.session_state.get("df_ref")
                is_grupo_ve_mm = str(titulo or "").strip().lower().startswith("ve - modo m")
                # garante que título + cabeçalho + 1 linha caibam juntos
                min_bloco = ALT_TITULO + ALT_CABEC + ALT_LINHA + ESPACO_POS
                garantir_espaco(min_bloco)

                # imprime título + cabeçalho
                cabecalho_tabela(titulo)

                fill = False
                for k in chaves:
                    # se não couber uma linha, quebra e repete cabeçalho
                    garantir_espaco(ALT_LINHA + ESPACO_POS)

                    label, un, ref_key = PARAMS[k]
                    v = float(dados.get(k, 0.0))
                    if k == "DIVEdN":
                        txt_ref = DIVEDN_REF_TXT
                        interp = interpretar_divedn(v)
                    elif k == "LA_FS":
                        txt_ref = "21 a 25 %"
                        if v <= 0:
                            interp = ""
                        elif v < 21:
                            interp = "Abaixo da referência"
                        elif v > 25:
                            interp = "Acima da referência"
                        else:
                            interp = "Dentro da referência"
                    elif k == "AURICULAR_FLOW":
                        txt_ref = "> 0,25 m/s"
                        if v <= 0:
                            interp = ""
                        elif v <= 0.25:
                            interp = "Abaixo da referência"
                        else:
                            interp = "Dentro da referência"
                    elif k == "EEp":
                        txt_ref = "<12"
                        if v <= 0:
                            interp = ""
                        elif v < 12:
                            interp = "Normal"
                        else:
                            interp = "Aumentado"
                    elif ref_key:
                        ref, txt_ref = calcular_referencia_tabela(ref_key, peso, df=df_ref_pdf)
                        interp = interpretar(v, ref)
                    else:
                        txt_ref = "--"
                        interp = ""

                    pdf.set_fill_color(245) if fill else pdf.set_fill_color(255)
                    pdf.cell(65, ALT_LINHA, pdf_safe(f"  {label}"), 0, fill=fill)
                    # formatação de casas decimais por parâmetro
                    if k == "PA_AP_AO":
                        vtxt = f"{v:.3f} {un}".strip()
                    else:
                        vtxt = f"{v:.2f} {un}".strip()
                    pdf.cell(30, ALT_LINHA, pdf_safe(vtxt), 0, align='C', fill=fill)
                    pdf.cell(40, ALT_LINHA, pdf_safe(txt_ref), 0, align='C', fill=fill)
                    pdf.cell(0,  ALT_LINHA, pdf_safe(interp), 0, ln=1, align='C', fill=fill)

                    fill = not fill

                pdf.ln(ESPACO_POS)


            for titulo, chaves in get_grupos_por_especie(st.session_state.get('cad_especie', '')):
                tab_auto(titulo, chaves)


            pdf.set_fill_color(230); pdf.set_font("Arial",'B',10); pdf.cell(0,6,"  AD/VD (Subjetivo)", ln=1, fill=True)
            pdf.set_font("Arial",'',10); pdf.multi_cell(0,5, pdf_safe(st.session_state.get('txt_ad_vd', ""))); pdf.ln(3)
            pdf.ln(2); pdf.set_font("Arial",'B',11); pdf.cell(0,8,"ANÁLISE QUALITATIVA",ln=1); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            
            # ====== QUALITATIVA NO PDF ======
            # Dentro de criar_pdf(), antes da parte qualitativa:
            chave_pdf = montar_chave_frase(sb_patologia, sb_grau_refluxo, sb_grau_geral)
            entry_pdf = st.session_state.get("db_frases", {}).get(chave_pdf, {}) or {}

            is_enxuto_pdf = (sb_patologia == "Normal") or (entry_pdf.get("layout") == "enxuto")


            if is_enxuto_pdf:
                # imprime 1 texto corrido por categoria (bullets), sem "Átrio esquerdo:", etc.
                pdf.set_font("Arial", "", 10)

                def bullet(label, texto):
                    texto = (texto or "").strip()
                    if not texto:
                        return
                    linha = f"* {label}: {texto}"
                    pdf.multi_cell(0, 5, pdf_safe(linha))
                    pdf.ln(1)

                bullet("Valvas", st.session_state.get("txt_valvas", ""))
                bullet("Câmaras", st.session_state.get("txt_camaras", ""))
                bullet("Função", st.session_state.get("txt_funcao", ""))
                bullet("Pericárdio", st.session_state.get("txt_pericardio", ""))

                bullet("Vasos sanguíneos", (st.session_state.get("txt_vasos", "") or montar_qualitativa().get("vasos","")))

            else:
                # mantém o formato detalhado (q_...) para as outras patologias
                q = montar_qualitativa()

                def item(t, txt):
                    t = pdf_safe(t)
                    txt = pdf_safe(txt)

                    pdf.set_font("Arial",'B',10)
                    pdf.cell(40,5,t,ln=0)

                    pdf.set_font("Arial",'',10)
                    y = pdf.get_y()
                    pdf.set_xy(50, y)
                    pdf.multi_cell(0,5,txt)

                    pdf.ln(2)
                    pdf.set_x(10)

                item("Valvas:", q.get("valvas",""))
                item("Câmaras:", q.get("camaras",""))
                item("Função:", q.get("funcao",""))
                item("Pericárdio:", q.get("pericardio",""))
                item("Vasos sanguíneos:", q.get("vasos",""))


            # Queremos: barra do título + pelo menos ~3 linhas de texto junto (ajuste como preferir)
            garantir_espaco(8 + 20)  # 8mm do título + 20mm de “corpo mínimo”

            pdf.ln(5)
            pdf.set_fill_color(50,50,60); pdf.set_text_color(255); pdf.set_font("Arial",'B',12)
            pdf.cell(0,8,"  CONCLUSÃO",ln=1,fill=True)

            pdf.set_text_color(0); pdf.set_font("Arial",'',11)
            pdf.ln(2)
            import re

            conc = st.session_state.get("txt_conclusao", "") or ""
            conc = conc.replace("\r\n", "\n")

            # remove espaços no fim das linhas
            conc = re.sub(r"[ \t]+\n", "\n", conc)

            # se você NÃO quer linha em branco nenhuma dentro da conclusão:
            conc = re.sub(r"\n{2,}", "\n", conc)

            pdf.multi_cell(0, 6, pdf_safe(conc.strip()))

            # ==========================================================
            # ✅ Carimbo/assinatura logo após a conclusão
            # ==========================================================
            assin_path = st.session_state.get("assinatura_path")

            if assin_path and os.path.exists(assin_path):
                # reserva espaço mínimo para a imagem
                # ajuste este número conforme o tamanho da sua assinatura
                garantir_espaco(30)

                pdf.ln(4)

                # posiciona à direita e fora da área central da marca d'água
                y_ass = pdf.get_y()
                w_ass = 40  # largura (mm)
                # Mantém proporção da imagem (evita distorção e "contorno" aparente)
                try:
                    iw, ih = Image.open(assin_path).size
                    h_ass = (w_ass * float(ih) / float(iw)) if iw else 40
                except Exception:
                    h_ass = 40

                x_ass = pdf.w - pdf.r_margin - w_ass

                # Evita que o carimbo/assinatura evidencie a marca d'água: aplica uma máscara branca atrás da imagem.
                pad = 2  # mm de margem ao redor da assinatura
                pdf.set_fill_color(255, 255, 255)
                pdf.rect(x_ass - pad, y_ass - pad, w_ass + 2*pad, h_ass + 2*pad, style="F")
                pdf.image(assin_path, x=x_ass, y=y_ass, w=w_ass, h=h_ass)

                # desce o cursor para não sobrepor nada depois
                pdf.ln(h_ass + 2)


            
            imgs_pdf = obter_imagens_para_pdf()
            if imgs_pdf:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "IMAGENS", ln=1, align='C')
                pdf.ln(5)

                x_s, y_s = 10, 50
                x, y = x_s, y_s

                for i, it in enumerate(imgs_pdf):
                    ext = (it.get("ext") or ".jpg").lower()
                    if ext not in [".jpg", ".png"]:
                        ext = ".jpg"

                    t = os.path.join(tempfile.gettempdir(), f"fc_img_{i}{ext}")
                    try:
                        with open(t, "wb") as fi:
                            fi.write(it.get("bytes", b"") or b"")
                    except Exception:
                        continue

                    if y + 65 > 270:
                        pdf.add_page()
                        y, x = 50, x_s

                    pdf.image(t, x=x, y=y, w=90, h=65)

                    try:
                        os.remove(t)
                    except Exception:
                        pass

                    if x == x_s:
                        x += 95
                    else:
                        x = x_s
                        y += 70
            out = pdf.output(dest="S")

            # fpdf2 -> bytes/bytearray | fpdf antigo -> str
            if isinstance(out, (bytes, bytearray)):
                return bytes(out)

            return out.encode("latin-1")


        if verificar_permissao("laudos", "criar"):
            if st.button("🧾 Gerar PDF"):
                pdf_bytes = criar_pdf()
                st.session_state["pdf_bytes"] = pdf_bytes
                
                # ============================================================
                # ✅ ARQUIVA PDF, JSON, IMAGENS E SALVA NO BANCO
                # ============================================================
                try:
                    # garante nome_base existindo
                    if "nome_base" not in locals():
                        nome_base = montar_nome_base_arquivo(
                            data_exame=data_exame,
                            animal=nome_animal,
                            tutor=tutor,
                            clinica=clinica
                        )

                    # 1) salva PDF
                    (PASTA_LAUDOS / f"{nome_base}.pdf").write_bytes(pdf_bytes)

                    # 2) salva imagens (quando existirem) e registra no JSON
                    imgs = obter_imagens_para_pdf()
                    imgs_saved = []

                    # remove imagens antigas do mesmo exame (caso esteja re-gerando)
                    try:
                        for p in PASTA_LAUDOS.glob(f"{nome_base}__IMG_*.*"):
                            p.unlink(missing_ok=True)
                    except Exception:
                        pass

                    for i, it in enumerate(imgs, start=1):
                        b = it.get("bytes")
                        if not b:
                            continue
                        ext = (it.get("ext") or ".jpg").lower()
                        if ext not in [".jpg", ".png"]:
                            ext = ".jpg"
                        fname = f"{nome_base}__IMG_{i:02d}{ext}"
                        (PASTA_LAUDOS / fname).write_bytes(b)
                        imgs_saved.append(fname)

                    # 3) salva JSON já com as imagens referenciadas
                    dados_save_arch = dict(dados_save)
                    dados_save_arch["imagens"] = imgs_saved
                    json_str_arch = json.dumps(dados_save_arch, indent=4, ensure_ascii=False)
                    (PASTA_LAUDOS / f"{nome_base}.json").write_text(json_str_arch, encoding="utf-8")

                    _ = st.success(f"PDF gerado e arquivado em: {PASTA_LAUDOS}")
                    
                    # 4) ✅ SALVA NO BANCO DE DADOS
                    try:
                        laudo_id, erro = salvar_laudo_no_banco(
                            tipo_exame="ecocardiograma",  # ← AJUSTE CONFORME O TIPO!
                            dados_laudo=dados_save,
                            caminho_json=PASTA_LAUDOS / f"{nome_base}.json",
                            caminho_pdf=PASTA_LAUDOS / f"{nome_base}.pdf"
                        )
                        
                        if laudo_id:
                            _ = st.success(f"✅ Laudo #{laudo_id} registrado no sistema!")
                        else:
                            _ = st.warning(f"⚠️ Laudo gerado mas não registrado: {erro}")
                    except Exception as e_banco:
                        _ = st.warning(f"⚠️ Erro ao registrar no banco: {e_banco}")

                    # 5) ✅ CRIA ORDEM DE SERVIÇO (OS) AUTOMÁTICA NO FINANCEIRO
                    try:
                        clinica_nome = (clinica or "").strip()
                        if clinica_nome:
                            conn_fin = sqlite3.connect(str(DB_PATH))
                            try:
                                cursor_fin = conn_fin.cursor()
                                cursor_fin.execute(
                                    "SELECT id FROM clinicas_parceiras WHERE nome = ? AND (ativo = 1 OR ativo IS NULL)",
                                    (clinica_nome,)
                                )
                                res_clinica = cursor_fin.fetchone()
                                if res_clinica:
                                    clinica_id_os = res_clinica[0]
                                    cursor_fin.execute(
                                        "SELECT id, valor_base FROM servicos WHERE (ativo = 1 OR ativo IS NULL) AND (nome = 'Ecocardiograma' OR nome LIKE '%Ecocardiograma%') LIMIT 1"
                                    )
                                    serv_row = cursor_fin.fetchone()
                                    if serv_row:
                                        servico_id_os = serv_row[0]
                                        vb, vd, vf = calcular_valor_final(servico_id_os, clinica_id_os)
                                        numero_os = gerar_numero_os()
                                        data_comp = datetime.now().strftime("%Y-%m-%d")
                                        descricao_os = f"Ecocardiograma - {nome_animal or 'Paciente'}"
                                        cursor_fin.execute("""
                                            INSERT INTO financeiro (
                                                clinica_id, numero_os, descricao,
                                                valor_bruto, valor_desconto, valor_final,
                                                status_pagamento, data_competencia
                                            ) VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
                                        """, (clinica_id_os, numero_os, descricao_os, vb, vd, vf, data_comp))
                                        conn_fin.commit()
                                        _ = st.success(f"💰 OS {numero_os} criada: R$ {vf:,.2f} (pendente)")
                                    else:
                                        _ = st.info("💡 Cadastre o serviço 'Ecocardiograma' em Cadastros > Serviços para gerar OS automática.")
                                else:
                                    _ = st.info("💡 Cadastre a clínica com o mesmo nome em Cadastros > Clínicas Parceiras para gerar OS automática.")
                            finally:
                                conn_fin.close()
                    except Exception as e_os:
                        _ = st.warning(f"PDF e laudo ok; OS não criada: {e_os}")
                        
                except Exception as e:
                    _ = st.warning(f"PDF gerado, mas não consegui arquivar automaticamente: {e}")
                # ============================================================

        else:
            _ = st.warning("⚠️ Você não tem permissão para gerar laudos")
            _ = st.info("💡 Apenas cardiologistas podem gerar laudos. Contate o administrador se precisar de acesso.")

        # Download button (fora do if/else de permissão) — retorno atribuído a _ para não exibir "None"
        if "pdf_bytes" in st.session_state:
            _ = st.download_button(
                "⬇️ Baixar PDF",
                data=st.session_state["pdf_bytes"],
                file_name=f"{nome_base}.pdf",
                mime="application/pdf",
                key="download_pdf_laudo_eco"
            )
    
    


# ============================================================================
# TELA: PRESCRIÇÕES
# ============================================================================
