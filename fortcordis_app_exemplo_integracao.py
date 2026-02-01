# ============================================================================
# FORT CORDIS - ARQUIVO PRINCIPAL COM MÓDULOS INTEGRADOS
# ============================================================================
# Este é um exemplo de como seu arquivo principal ficaria após a integração
# dos novos módulos de gestão clínica e financeira
# ============================================================================

import streamlit as st
from bs4 import BeautifulSoup
from fpdf import FPDF
import os
import json
import pandas as pd
from PIL import Image
import io
import hashlib
import re
import tempfile
import sqlite3
from pathlib import Path
import copy
from datetime import datetime, date, timedelta
import unicodedata

# ============================================================================
# IMPORTS DOS NOVOS MÓDULOS
# ============================================================================
import sys
sys.path.append(str(Path(__file__).parent / "fortcordis_modules"))

from fortcordis_modules.database import (
    inicializar_banco, 
    gerar_numero_os, 
    calcular_valor_final,
    registrar_cobranca_automatica,
    atualizar_status_acompanhamentos,
    DB_PATH
)

from fortcordis_modules.documentos import (
    gerar_receituario_pdf,
    gerar_atestado_saude_pdf,
    gerar_gta_pdf,
    gerar_termo_consentimento_pdf,
    calcular_posologia,
    formatar_posologia
)

# ============================================================================
# TODO O SEU CÓDIGO DE NORMALIZAÇÃO DE TEXTOS (MANTÉM INALTERADO)
# ============================================================================

_PREPS = {"da", "de", "do", "das", "dos", "e"}

def _clean_spaces(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def nome_proprio_ptbr(s: str) -> str:
    """Seu código atual - mantém inalterado"""
    s = _clean_spaces(s)
    if not s:
        return s
    def _cap_token(tok: str) -> str:
        if not tok:
            return tok
        if tok.isalpha() and tok.upper() == tok and len(tok) <= 4:
            return tok
        tl = tok.lower()
        if "-" in tl:
            partes = tl.split("-")
            partes = [(p[:1].upper() + p[1:]) if p else p for p in partes]
            return "-".join(partes)
        return tl[:1].upper() + tl[1:]
    palavras = s.split(" ")
    out = []
    for i, p in enumerate(palavras):
        pl = p.lower()
        if i > 0 and pl in _PREPS:
            out.append(pl)
        else:
            out.append(_cap_token(p))
    return " ".join(out)

def frase_ptbr(s: str) -> str:
    """Seu código atual - mantém inalterado"""
    s = _clean_spaces(s)
    if not s:
        return s
    if s == s.upper():
        s = s.lower()
        s = s[:1].upper() + s[1:]
    return s

def normalizar_cadastro(cad: dict) -> dict:
    """Seu código atual - mantém inalterado"""
    cad = dict(cad or {})
    for k in ["tutor", "nome_tutor", "paciente", "nome_paciente", "raca", "raça", "clinica", "clínica"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = nome_proprio_ptbr(cad[k])
    for k in ["endereco", "endereço", "bairro", "cidade", "observacoes", "observações", "anamnese"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = frase_ptbr(cad[k])
    for k in ["email", "e-mail"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = _clean_spaces(cad[k]).lower()
    for k in ["telefone", "celular", "whatsapp"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = _clean_spaces(cad[k])
    return cad

def normalizar_session_state():
    """Seu código atual - mantém inalterado"""
    cad = {
        "tutor": st.session_state.get("tutor", ""),
        "nome_tutor": st.session_state.get("nome_tutor", ""),
        "paciente": st.session_state.get("paciente", ""),
        "nome_paciente": st.session_state.get("nome_paciente", ""),
        "raca": st.session_state.get("raca", st.session_state.get("raça", "")),
        "clinica": st.session_state.get("clinica", st.session_state.get("clínica", "")),
        "endereco": st.session_state.get("endereco", st.session_state.get("endereço", "")),
        "bairro": st.session_state.get("bairro", ""),
        "cidade": st.session_state.get("cidade", ""),
        "email": st.session_state.get("email", st.session_state.get("e-mail", "")),
        "telefone": st.session_state.get("telefone", ""),
        "celular": st.session_state.get("celular", ""),
        "whatsapp": st.session_state.get("whatsapp", ""),
        "observacoes": st.session_state.get("observacoes", st.session_state.get("observações", "")),
        "anamnese": st.session_state.get("anamnese", ""),
    }
    cad = normalizar_cadastro(cad)
    if "tutor" in st.session_state: st.session_state["tutor"] = cad.get("tutor", st.session_state["tutor"])
    if "paciente" in st.session_state: st.session_state["paciente"] = cad.get("paciente", st.session_state["paciente"])
    if "raca" in st.session_state: st.session_state["raca"] = cad.get("raca", st.session_state["raca"])
    if "clinica" in st.session_state: st.session_state["clinica"] = cad.get("clinica", st.session_state["clinica"])
    if "endereco" in st.session_state: st.session_state["endereco"] = cad.get("endereco", st.session_state["endereco"])
    if "email" in st.session_state: st.session_state["email"] = cad.get("email", st.session_state["email"])
    if "telefone" in st.session_state: st.session_state["telefone"] = cad.get("telefone", st.session_state["telefone"])
    if "whatsapp" in st.session_state: st.session_state["whatsapp"] = cad.get("whatsapp", st.session_state["whatsapp"])
    if "observacoes" in st.session_state: st.session_state["observacoes"] = cad.get("observacoes", st.session_state["observacoes"])
    if "anamnese" in st.session_state: st.session_state["anamnese"] = cad.get("anamnese", st.session_state["anamnese"])

# ============================================================================
# CONFIGURAÇÕES E INICIALIZAÇÃO
# ============================================================================

st.set_page_config(page_title="Fort Cordis - Sistema Completo", layout="wide")

try:
    st.set_option("runner.magicEnabled", False)
except Exception:
    pass

# Inicializa banco de dados
inicializar_banco()

# Dicionário padrão de dados (seu código atual)
DADOS_DEFAULT = {
    "Ao": 0.0, "LA": 0.0, "LA_Ao": 0.0,
    "IVSd": 0.0, "LVIDd": 0.0, "LVPWd": 0.0,
    "IVSs": 0.0, "LVIDs": 0.0, "LVPWs": 0.0,
    "EDV": 0.0, "ESV": 0.0, "SV": 0.0,
    "EF": 0.0, "FS": 0.0,
    "MAPSE": 0.0, "TAPSE": 0.0,
    "Vmax_Ao": 0.0, "Grad_Ao": 0.0,
    "Vmax_Pulm": 0.0, "Grad_Pulm": 0.0,
    "MV_E": 0.0, "MV_A": 0.0, "MV_E_A": 0.0,
    "MV_DT": 0.0, "MV_Slope": 0.0,
    "IVRT": 0.0, "E_IVRT": 0.0,
    "TR_Vmax": 0.0,
    "LA_FS": 0.0,
    "AURICULAR_FLOW": 0.0, "MR_Vmax": 0.0,
    "MR_dPdt": 0.0,
    "TDI_e": 0.0, "TDI_a": 0.0, "TDI_e_a": 0.0,
    "EEp": 0.0,
    "PA_AP": 0.0, "PA_AO": 0.0, "PA_AP_AO": 0.0,
    "Delta_D": 0.0, "DIVEdN": 0.0
}

if "dados_atuais" not in st.session_state:
    st.session_state["dados_atuais"] = DADOS_DEFAULT.copy()

# Espécies
if "lista_especies" not in st.session_state:
    st.session_state["lista_especies"] = ["Canina", "Felina"]

if "cad_especie" not in st.session_state or not str(st.session_state.get("cad_especie") or "").strip():
    st.session_state["cad_especie"] = "Canina"

# Arquivos e pastas
MARCA_DAGUA_TEMP = "temp_watermark_faded.png"
ARQUIVO_FRASES = str((Path.home() / "FortCordis" / "frases_personalizadas.json"))
Path(ARQUIVO_FRASES).parent.mkdir(parents=True, exist_ok=True)
ARQUIVO_REF = "tabela_referencia.csv"
ARQUIVO_REF_FELINOS = "tabela_referencia_felinos.csv"

# Pastas de arquivos
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
PASTA_PRESCRICOES = Path.home() / "FortCordis" / "Prescricoes"
PASTA_DOCUMENTOS = Path.home() / "FortCordis" / "Documentos"

for pasta in [PASTA_LAUDOS, PASTA_PRESCRICOES, PASTA_DOCUMENTOS]:
    pasta.mkdir(parents=True, exist_ok=True)

# ============================================================================
# MENU PRINCIPAL (MODIFICADO)
# ============================================================================

st.sidebar.title("🏥 Fort Cordis")
st.sidebar.markdown("### Sistema Integrado de Gestão")
st.sidebar.markdown("---")

menu_principal = st.sidebar.radio(
    "Navegação",
    [
        "🏠 Dashboard",
        "📅 Agendamentos", 
        "🩺 Laudos e Exames",  # <- Sua tela atual
        "💊 Prescrições",
        "💰 Financeiro",
        "🏢 Cadastros",
        "⚙️ Configurações"
    ]
)

# ============================================================================
# TELAS DO SISTEMA
# ============================================================================

# ----------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------
if menu_principal == "🏠 Dashboard":
    st.title("📊 Dashboard - Fort Cordis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # Agendamentos hoje
    with col1:
        hoje = datetime.now().strftime("%Y-%m-%d")
        agend_hoje = pd.read_sql_query(
            f"SELECT COUNT(*) as total FROM agendamentos WHERE data_agendamento = '{hoje}' AND status != 'cancelado'",
            conn
        )
        st.metric("Agendamentos Hoje", agend_hoje['total'].iloc[0] if not agend_hoje.empty else 0)
    
    # Pendentes confirmação
    with col2:
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        pend_conf = pd.read_sql_query(
            f"SELECT COUNT(*) as total FROM agendamentos WHERE data_agendamento = '{amanha}' AND status = 'agendado'",
            conn
        )
        st.metric("Pendentes Confirmação", pend_conf['total'].iloc[0] if not pend_conf.empty else 0)
    
    # Contas a receber
    with col3:
        a_receber = pd.read_sql_query(
            "SELECT SUM(valor_final) as total FROM financeiro WHERE status_pagamento = 'pendente'",
            conn
        )
        valor = a_receber['total'].iloc[0] if not a_receber.empty and a_receber['total'].iloc[0] else 0
        st.metric("Contas a Receber", f"R$ {valor:,.2f}")
    
    # Retornos atrasados
    with col4:
        atrasados = pd.read_sql_query(
            "SELECT COUNT(*) as total FROM acompanhamentos WHERE status = 'atrasado'",
            conn
        )
        st.metric("Retornos Atrasados", atrasados['total'].iloc[0] if not atrasados.empty else 0)
    
    st.markdown("---")
    
    # Tabelas resumo
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📅 Próximos Agendamentos")
        proximos = pd.read_sql_query("""
            SELECT 
                a.data_agendamento as Data,
                a.hora_inicio as Hora,
                a.paciente_nome as Paciente,
                c.nome as Clínica,
                a.status as Status
            FROM agendamentos a
            LEFT JOIN clinicas_parceiras c ON a.clinica_id = c.id
            WHERE date(a.data_agendamento) >= date('now')
            AND a.status != 'cancelado'
            ORDER BY a.data_agendamento, a.hora_inicio
            LIMIT 10
        """, conn)
        
        if not proximos.empty:
            st.dataframe(proximos, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum agendamento próximo")
    
    with col_b:
        st.subheader("💰 Últimas Cobranças")
        ultimas_cob = pd.read_sql_query("""
            SELECT 
                f.numero_os as OS,
                c.nome as Clínica,
                f.valor_final as Valor,
                f.status_pagamento as Status
            FROM financeiro f
            LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
            ORDER BY f.data_cadastro DESC
            LIMIT 10
        """, conn)
        
        if not ultimas_cob.empty:
            ultimas_cob['Valor'] = ultimas_cob['Valor'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(ultimas_cob, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma cobrança registrada")
    
    conn.close()

# ----------------------------------------------------------------------------
# AGENDAMENTOS (código fornecido anteriormente no GUIA_IMPLEMENTACAO.md)
# ----------------------------------------------------------------------------
elif menu_principal == "📅 Agendamentos":
    st.title("📅 Gestão de Agendamentos")
    st.info("💡 Veja o arquivo GUIA_IMPLEMENTACAO.md para o código completo desta seção")
    # [Cole aqui o código da seção de Agendamentos do guia]

# ----------------------------------------------------------------------------
# LAUDOS E EXAMES (TODO O SEU CÓDIGO ATUAL FICA AQUI)
# ----------------------------------------------------------------------------
elif menu_principal == "🩺 Laudos e Exames":
    # ========================================================================
    # ATENÇÃO: AQUI VAI TODO O SEU CÓDIGO ATUAL DE LAUDOS
    # Copie desde a linha onde começa a interface de laudos até a linha 5100
    # NÃO MODIFICAR NADA - APENAS INDENTAR UM NÍVEL PARA DENTRO DESTE elif
    # ========================================================================
    
    st.title("🩺 Sistema de Laudos e Exames")
    
    # Todo o seu código de tabs (Cadastro, Medidas, Carregador XML, etc)
    # vai aqui exatamente como está, só indentado um nível
    
    st.info("💡 Cole todo o código das suas abas de laudos aqui")
    
    # EXEMPLO DA MODIFICAÇÃO NO BOTÃO GERAR PDF:
    # Encontre a parte do seu código que tem:
    # if st.button("🧾 Gerar PDF"):
    #     pdf_bytes = criar_pdf()
    #     ...
    # E adicione APÓS salvar o PDF:
    
    """
    # NOVO: Integração com financeiro
    try:
        clinica_nome = st.session_state.get("clinica", "")
        if clinica_nome:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Busca ID da clínica
            cursor.execute("SELECT id FROM clinicas_parceiras WHERE nome = ?", (clinica_nome,))
            resultado = cursor.fetchone()
            
            if resultado:
                clinica_id = resultado[0]
                
                # Identifica serviço (assumindo Ecocardiograma)
                cursor.execute("SELECT id FROM servicos WHERE nome = 'Ecocardiograma'")
                servico = cursor.fetchone()
                
                if servico:
                    servico_id = servico[0]
                    
                    # Calcula valor com desconto
                    valor_base, valor_desconto, valor_final = calcular_valor_final(servico_id, clinica_id)
                    
                    # Gera OS
                    numero_os = gerar_numero_os()
                    data_comp = datetime.now().strftime("%Y-%m-%d")
                    
                    cursor.execute('''
                        INSERT INTO financeiro (
                            clinica_id, numero_os, descricao,
                            valor_bruto, valor_desconto, valor_final,
                            status_pagamento, data_competencia
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
                    ''', (clinica_id, numero_os, 
                          f"Ecocardiograma - {nome_animal}",
                          valor_base, valor_desconto, valor_final, data_comp))
                    
                    conn.commit()
                    st.info(f"💰 OS {numero_os} criada automaticamente: R$ {valor_final:.2f}")
                    
                    if valor_desconto > 0:
                        st.success(f"✅ Desconto aplicado: R$ {valor_desconto:.2f}")
            
            conn.close()
    except Exception as e:
        pass  # Não quebra o fluxo se der erro na OS
    """

# ----------------------------------------------------------------------------
# PRESCRIÇÕES (código fornecido anteriormente no GUIA_IMPLEMENTACAO.md)
# ----------------------------------------------------------------------------
elif menu_principal == "💊 Prescrições":
    st.title("💊 Sistema de Prescrições")
    st.info("💡 Veja o arquivo GUIA_IMPLEMENTACAO.md para o código completo desta seção")
    # [Cole aqui o código da seção de Prescrições do guia]

# ----------------------------------------------------------------------------
# FINANCEIRO (código fornecido anteriormente no GUIA_IMPLEMENTACAO.md)
# ----------------------------------------------------------------------------
elif menu_principal == "💰 Financeiro":
    st.title("💰 Gestão Financeira")
    st.info("💡 Veja o arquivo GUIA_IMPLEMENTACAO.md para o código completo desta seção")
    # [Cole aqui o código da seção Financeiro do guia]

# ----------------------------------------------------------------------------
# CADASTROS (código fornecido anteriormente no GUIA_IMPLEMENTACAO.md)
# ----------------------------------------------------------------------------
elif menu_principal == "🏢 Cadastros":
    st.title("🏢 Cadastros")
    st.info("💡 Veja o arquivo GUIA_IMPLEMENTACAO.md para o código completo desta seção")
    # [Cole aqui o código da seção Cadastros do guia]

# ----------------------------------------------------------------------------
# CONFIGURAÇÕES (seu código atual + novos campos)
# ----------------------------------------------------------------------------
elif menu_principal == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    
    tab_conf1, tab_conf2, tab_conf3 = st.tabs([
        "👨‍⚕️ Dados Profissionais",
        "📊 Valores de Referência",
        "📝 Frases Personalizadas"
    ])
    
    with tab_conf1:
        st.subheader("Dados Profissionais")
        
        medico_nome = st.text_input(
            "Nome do Médico Veterinário",
            value=st.session_state.get("config_medico", "Dr. [Nome]")
        )
        
        medico_crmv = st.text_input(
            "CRMV",
            value=st.session_state.get("config_crmv", "CRMV-CE XXXXX")
        )
        
        if st.button("💾 Salvar Configurações"):
            st.session_state["config_medico"] = medico_nome
            st.session_state["config_crmv"] = medico_crmv
            st.success("✅ Configurações salvas!")
    
    with tab_conf2:
        st.info("💡 Cole aqui todo o código da sua aba de Valores de Referência")
        # Seu código atual da aba de valores de referência
    
    with tab_conf3:
        st.info("💡 Cole aqui todo o código da sua aba de Frases Personalizadas")
        # Seu código atual da aba de frases

# ============================================================================
# FIM DO ARQUIVO
# ============================================================================
