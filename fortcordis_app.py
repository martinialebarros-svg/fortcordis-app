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
import secrets

# ============================================================
# VERSÃO DO DEPLOY (atualize ao fazer push para conferir no app)
# ============================================================
VERSAO_DEPLOY = "2026-02-01"  # Altere para a data de hoje ao fazer commit/push

# ============================================================
# CONFIGURAÇÃO DA PÁGINA E DESIGN (primeiro comando Streamlit)
# ============================================================
st.set_page_config(
    page_title="Fort Cordis - Sistema Integrado",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS global para melhorar o design (sem alterar funcionalidades)
st.markdown("""
<style>
    /* Tema geral */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    /* Títulos principais */
    h1 { font-size: 1.85rem !important; font-weight: 600 !important; color: #1e3a5f !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.35rem !important; font-weight: 600 !important; color: #2c5282 !important; }
    h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #2d3748 !important; }
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2c5282 100%); }
    [data-testid="stSidebar"] .stMarkdown { color: rgba(255,255,255,0.95); }
    [data-testid="stSidebar"] h1 { color: #fff !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: rgba(255,255,255,0.9) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }
    [data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.95) !important; }
    [data-testid="stSidebar"] .stRadio label div { color: inherit !important; }
    /* Métricas / cards */
    [data-testid="stMetric"] { background: #f7fafc; padding: 1rem 1.25rem; border-radius: 8px; border-left: 4px solid #2c5282; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    [data-testid="stMetric"] label { font-weight: 600 !important; color: #2d3748 !important; }
    /* Botões primários */
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%); font-weight: 600; border-radius: 6px; }
    .stButton > button[kind="primary"]:hover { box-shadow: 0 4px 12px rgba(44,82,130,0.35); }
    /* Expanders */
    .streamlit-expanderHeader { background: #f7fafc; border-radius: 6px; }
    /* Separadores */
    hr { margin: 1.25rem 0 !important; border-color: #e2e8f0 !important; }
    /* Mensagens de sucesso/aviso/info */
    [data-testid="stAlert"] { border-radius: 8px; }
    /* Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px 6px 0 0; padding: 0.5rem 1rem; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #edf2f7; }
    /* Sidebar caption/versão */
    [data-testid="stSidebar"] .stCaptionContainer { color: rgba(255,255,255,0.75); }
    /* Alertas na sidebar: texto claro para boa legibilidade no fundo azul */
    [data-testid="stSidebar"] [data-testid="stAlert"] { background: rgba(255,255,255,0.12) !important; color: #fff !important; border: 1px solid rgba(255,255,255,0.25); }
    [data-testid="stSidebar"] [data-testid="stAlert"] p { color: #fff !important; }
    [data-testid="stSidebar"] [data-testid="stAlert"] a { color: #a5d6ff !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔴 BOTÃO DE EMERGÊNCIA - RESETA TUDO
# ============================================================
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    if st.button("🔴 RESET COMPLETO", type="secondary"):
        st.session_state.clear()
        if "auth_token" in st.query_params:
            st.query_params.clear()
        st.success("✅ Sistema resetado!")
        st.rerun()

with col2:
    if st.button("🏠 VOLTAR AO INÍCIO", type="primary"):
        # Limpa só as chaves de navegação
        keys_to_remove = [k for k in st.session_state.keys() 
                         if k not in ["autenticado", "usuario_id", "usuario_nome", 
                                     "usuario_email", "permissoes"]]
        for k in keys_to_remove:
            del st.session_state[k]
        st.query_params.clear()
        st.rerun()

st.markdown("---")
# ============================================================


def _criar_tabelas_laudos_se_nao_existirem(cursor):
    """Cria tabelas de laudos se não existirem (Streamlit Cloud / primeiro deploy)."""
    for nome_tabela, sql in [
        ("laudos_ecocardiograma", """
            CREATE TABLE IF NOT EXISTS laudos_ecocardiograma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'ecocardiograma',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                modo_m TEXT, modo_bidimensional TEXT, doppler TEXT, conclusao TEXT, observacoes TEXT,
                achados_normais TEXT, achados_alterados TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
        ("laudos_eletrocardiograma", """
            CREATE TABLE IF NOT EXISTS laudos_eletrocardiograma (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'eletrocardiograma',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                ritmo TEXT, frequencia_cardiaca INTEGER, conclusao TEXT, observacoes TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
        ("laudos_pressao_arterial", """
            CREATE TABLE IF NOT EXISTS laudos_pressao_arterial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER, data_exame TEXT, clinica_id INTEGER, veterinario_id INTEGER,
                tipo_exame TEXT DEFAULT 'pressao_arterial',
                nome_paciente TEXT, especie TEXT, raca TEXT, idade TEXT, peso REAL,
                pressao_sistolica INTEGER, pressao_diastolica INTEGER, conclusao TEXT, observacoes TEXT,
                arquivo_xml TEXT, arquivo_pdf TEXT, status TEXT DEFAULT 'finalizado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, criado_por INTEGER
            )
        """),
    ]:
        cursor.execute(sql)


def salvar_laudo_no_banco(tipo_exame, dados_laudo, caminho_json, caminho_pdf):
    """Salva o laudo no banco de dados - VERSÃO FINAL AJUSTADA"""
    # Usar pasta do projeto (funciona no Streamlit Cloud)
    _db = Path(__file__).resolve().parent / "fortcordis.db"
    try:
        conn = sqlite3.connect(str(_db))
        cursor = conn.cursor()
        _criar_tabelas_laudos_se_nao_existirem(cursor)
        conn.commit()
        
        tabelas = {
            "ecocardiograma": "laudos_ecocardiograma",
            "eletrocardiograma": "laudos_eletrocardiograma",
            "pressao_arterial": "laudos_pressao_arterial"
        }
        
        tabela = tabelas.get(tipo_exame.lower())
        
        if not tabela:
            return None, f"Tipo inválido: {tipo_exame}"
        
        # Descobre quais colunas existem
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        
        # Mapeamento completo baseado na estrutura real
        dados_possiveis = {
            # Paciente
            'nome_paciente': dados_laudo.get('nome_animal', ''),
            'especie': dados_laudo.get('especie', ''),
            'raca': dados_laudo.get('raca', ''),
            'idade': dados_laudo.get('idade', ''),
            'peso': float(dados_laudo.get('peso', 0)) if dados_laudo.get('peso') else None,
            
            # Data e tipo
            'data_exame': dados_laudo.get('data', datetime.now().strftime('%Y-%m-%d')),
            'tipo_exame': tipo_exame,
            
            # IDs (deixa NULL por enquanto, você pode preencher depois)
            'paciente_id': None,
            'clinica_id': None,
            'veterinario_id': None,
            'criado_por': None,
            
            # Achados (específico de eco)
            'modo_m': dados_laudo.get('modo_m', ''),
            'modo_bidimensional': dados_laudo.get('modo_2d', ''),
            'doppler': dados_laudo.get('doppler', ''),
            'achados_normais': dados_laudo.get('achados_normais', ''),
            'achados_alterados': dados_laudo.get('achados_alterados', ''),
            
            # Conclusão
            'conclusao': dados_laudo.get('conclusao', ''),
            'observacoes': dados_laudo.get('observacoes', ''),
            
            # Arquivos
            'arquivo_xml': str(caminho_json),  # Usa JSON no lugar do XML
            'arquivo_pdf': str(caminho_pdf),
            
            # Status
            'status': 'finalizado'
        }
        
        # Filtra apenas colunas que existem
        colunas_usar = []
        valores_usar = []
        
        for col in colunas_existentes:
            # Pula colunas auto-geradas ou com constraints especiais
            if col in ['id', 'data_criacao', 'data_modificacao']:
                continue
            
            if col in dados_possiveis:
                valor = dados_possiveis[col]
                # Só adiciona se não for None ou se a coluna aceitar NULL
                colunas_usar.append(col)
                valores_usar.append(valor)
        
        if not colunas_usar:
            return None, "Nenhuma coluna para inserir"
        
        # Monta query
        placeholders = ', '.join(['?' for _ in colunas_usar])
        colunas_str = ', '.join(colunas_usar)
        
        query = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
        
        cursor.execute(query, valores_usar)
        
        laudo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return laudo_id, None
        
    except Exception as e:
        return None, str(e)

def buscar_laudos(tipo_exame=None, nome_paciente=None):
    """Busca laudos no banco"""
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
        
        # Atualiza banco se necessário (usa pasta do projeto - Streamlit Cloud)
        if novo_pdf_path:
            _db = Path(__file__).resolve().parent / "fortcordis.db"
            conn = sqlite3.connect(str(_db))
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
# MÓDULOS DE GESTÃO (NOVOS)
# ============================================================================
import sys
sys.path.append(str(Path(__file__).parent / "fortcordis_modules"))

from database import (
    inicializar_banco,
    gerar_numero_os,
    calcular_valor_final,
    registrar_cobranca_automatica,
    criar_agendamento,
    listar_agendamentos,
    atualizar_agendamento,
    deletar_agendamento,
    buscar_agendamento_por_id,
    contar_agendamentos_por_status,
    dar_baixa_os,
    excluir_os,
    listar_financeiro_pendentes,
    garantir_colunas_financeiro,
    criar_os_ao_marcar_realizado,
)

from integrations import (
    whatsapp_link,
    mensagem_confirmacao_agendamento,
    exportar_agendamento_ics,
)

from documentos import (
    gerar_receituario_pdf,
    gerar_atestado_saude_pdf,
    gerar_gta_pdf,
    calcular_posologia
)

# ============================================================================
# SISTEMA DE AUTENTICAÇÃO E PERMISSÕES
# ============================================================================
import sys
from pathlib import Path

# Adiciona pasta modules ao path
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

try:
    from auth import (
        mostrar_tela_login,
        mostrar_info_usuario,
        fazer_logout
    )
    from rbac import (
        verificar_permissao,
        exigir_permissao,
        mostrar_permissoes_usuario
    )
    AUTH_DISPONIVEL = True
    print("✅ Autenticação importada com sucesso!")
    
except ImportError as e:
    print(f"❌ ERRO: {e}")
    import streamlit as st
    st.error(f"❌ Erro ao importar autenticação: {e}")
    AUTH_DISPONIVEL = False
    st.stop()

def _clean_spaces(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

_PREPS = {"da", "de", "do", "das", "dos", "e"}

def nome_proprio_ptbr(s: str) -> str:
    """
    Converte 'JOAO DA SILVA' -> 'Joao da Silva'
    Mantém preposições em minúsculo (de/da/do/das/dos/e)
    Mantém siglas curtas (ex.: SRD, PUG) em maiúsculo
    Trata hífen (ex.: 'SPITZ-ALEMÃO' -> 'Spitz-Alemão')
    """
    s = _clean_spaces(s)
    if not s:
        return s

    def _cap_token(tok: str) -> str:
        if not tok:
            return tok

        # mantém sigla curta (tudo maiúsculo e <= 4)
        if tok.isalpha() and tok.upper() == tok and len(tok) <= 4:
            return tok

        tl = tok.lower()

        # trata hífen: "spitz-alemao" -> "Spitz-Alemão"
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
    """
    Para textos livres (ex.: endereço/observações):
    deixa tudo "normal" (não grita), mas sem inventar pontuação.
    """
    s = _clean_spaces(s)
    if not s:
        return s
    # Se estiver TODO em maiúsculo, baixa tudo
    if s == s.upper():
        s = s.lower()
        s = s[:1].upper() + s[1:]  # só a primeira letra em maiúsculo
    return s

def normalizar_session_state():
    # mapeia seus campos do session_state -> dict
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

    # devolve pro session_state (só os que você usa de verdade)
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


def normalizar_cadastro(cad: dict) -> dict:
    """
    Recebe o dicionário do cadastro e devolve uma cópia normalizada.
    Ajuste as chaves conforme o seu cadastro real.
    """
    cad = dict(cad or {})

    # Campos "nome próprio"
    for k in ["tutor", "nome_tutor", "paciente", "nome_paciente", "raca", "raça", "clinica", "clínica"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = nome_proprio_ptbr(cad[k])

    # Campos de texto livre
    for k in ["endereco", "endereço", "bairro", "cidade", "observacoes", "observações", "anamnese"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = frase_ptbr(cad[k])

    # Email sempre minúsculo
    for k in ["email", "e-mail"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = _clean_spaces(cad[k]).lower()

    # Telefones: só limpa espaços
    for k in ["telefone", "celular", "whatsapp"]:
        if k in cad and isinstance(cad[k], str):
            cad[k] = _clean_spaces(cad[k])

    return cad

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
st.sidebar.caption("Sistema carregado")

# Evita o Streamlit "Magic" imprimir retornos None na tela
try:
    st.set_option("runner.magicEnabled", False)
except Exception:
    pass

# Dicionário padrão (zeros) para evitar KeyError antes do XML
DADOS_DEFAULT = {
    "Ao": 0.0, "LA": 0.0, "LA_Ao": 0.0,
    "IVSd": 0.0, "LVIDd": 0.0, "LVPWd": 0.0,
    "IVSs": 0.0, "LVIDs": 0.0, "LVPWs": 0.0,
    "EDV": 0.0, "ESV": 0.0, "SV": 0.0,
    "EF": 0.0, "FS": 0.0,
    "MAPSE": 0.0,
        "TAPSE": 0.0,
"Vmax_Ao": 0.0, "Grad_Ao": 0.0,
    "Vmax_Pulm": 0.0, "Grad_Pulm": 0.0,
    "MV_E": 0.0, "MV_A": 0.0, "MV_E_A": 0.0,
    "MV_DT": 0.0, "MV_Slope": 0.0,
    "IVRT": 0.0, "E_IVRT": 0.0,
    "TR_Vmax": 0.0,
    "LA_FS": 0.0,
    "AURICULAR_FLOW": 0.0, "MR_Vmax": 0.0,
    "MR_dPdt": 0.0,
    # Doppler tecidual (Tissue Doppler Imaging): valores manuais + razão automática
    "TDI_e": 0.0, "TDI_a": 0.0, "TDI_e_a": 0.0,
    "EEp": 0.0,  # E/E' (relação E/E')
    # Artéria pulmonar / Aorta (AP/Ao)
    "PA_AP": 0.0, "PA_AO": 0.0, "PA_AP_AO": 0.0,
    "Delta_D": 0.0, "DIVEdN": 0.0
}


if "dados_atuais" not in st.session_state:
    st.session_state["dados_atuais"] = DADOS_DEFAULT.copy()


# ===============================
# Espécies (menu flutuante)
# ===============================
if "lista_especies" not in st.session_state:
    st.session_state["lista_especies"] = ["Canina", "Felina"]

# padrão: Canina (você pode mudar quando necessário)
if "cad_especie" not in st.session_state or not str(st.session_state.get("cad_especie") or "").strip():
    st.session_state["cad_especie"] = "Canina"

# ===============================
# Arquivos do sistema
# ===============================
MARCA_DAGUA_TEMP = "temp_watermark_faded.png"
ARQUIVO_FRASES = str((Path.home() / "FortCordis" / "frases_personalizadas.json"))
Path(ARQUIVO_FRASES).parent.mkdir(parents=True, exist_ok=True)

# Arquivos de referência (SEPARADOS por espécie)
ARQUIVO_REF = "tabela_referencia_caninos.csv"  # ← CORRIGIDO!
ARQUIVO_REF_FELINOS = "tabela_referencia_felinos.csv"

# ==========================================================
# 📁 Pasta fixa para arquivar exames (para busca)
# ==========================================================
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
PASTA_LAUDOS.mkdir(parents=True, exist_ok=True)

# ==========================================================
# 📷 Imagens do exame (carregadas do arquivo e/ou adicionadas manualmente)
# ==========================================================
def _img_ext_from_name(nome: str) -> str:
    try:
        ext = (Path(nome).suffix or "").lower()
    except Exception:
        ext = ""
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".jpg"
    # padroniza jpeg para .jpg
    if ext == ".jpeg":
        ext = ".jpg"
    return ext


def obter_imagens_para_pdf():
    """Retorna lista de imagens do exame (bytes) para preview e PDF.
    - imagens_carregadas: vindas do JSON arquivado
    - imagens_upload_novas: adicionadas manualmente na aba 📷 Imagens
    """
    imgs = []

    # 1) Imagens carregadas do exame arquivado
    carregadas = st.session_state.get("imagens_carregadas", []) or []
    for it in carregadas:
        if isinstance(it, dict) and it.get("bytes"):
            imgs.append({
                "name": str(it.get("name") or "imagem"),
                "bytes": bytes(it.get("bytes")),
                "ext": _img_ext_from_name(it.get("name") or "")
            })

    # 2) Novas imagens do uploader
    novas = st.session_state.get("imagens_upload_novas", None)
    if novas:
        for f in novas:
            try:
                b = bytes(f.getbuffer())
            except Exception:
                try:
                    b = f.getvalue()
                except Exception:
                    b = None
            if not b:
                continue
            imgs.append({
                "name": getattr(f, "name", "imagem"),
                "bytes": b,
                "ext": _img_ext_from_name(getattr(f, "name", "") or "")
            })

    return imgs


# ==========================================================
# 🗄️ Banco local (SQLite) - mesmo arquivo para Cadastros e Agendamentos
# Usar pasta do projeto para que as clínicas cadastradas apareçam no dropdown
# ==========================================================
PASTA_DB = Path(__file__).resolve().parent
DB_PATH = PASTA_DB / "fortcordis.db"
# Usar o mesmo banco no módulo (financeiro, clinicas_parceiras, OS automática)
if "database" in sys.modules:
    sys.modules["database"].DB_PATH = DB_PATH

def _norm_key(s: str) -> str:
    """Normaliza texto para chave (minúsculo, sem acentos, espaços colapsados)."""
    s = (s or "").strip().lower()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

@st.cache_resource(show_spinner=False)
def _db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _db_init():
    conn = _db_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS clinicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        nome_key TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tutores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        nome_key TEXT NOT NULL UNIQUE,
        telefone TEXT,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pacientes (
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
    # Colunas usadas pelo Prontuário (adiciona se não existirem)
    for col, tipo in [("ativo", "INTEGER DEFAULT 1"), ("peso_kg", "REAL"), ("microchip", "TEXT"), ("observacoes", "TEXT")]:
        try:
            conn.execute(f"ALTER TABLE pacientes ADD COLUMN {col} {tipo}")
        except sqlite3.OperationalError:
            pass
    for col, tipo in [("whatsapp", "TEXT"), ("ativo", "INTEGER DEFAULT 1")]:
        try:
            conn.execute(f"ALTER TABLE tutores ADD COLUMN {col} {tipo}")
        except sqlite3.OperationalError:
            pass
    conn.commit()

def db_upsert_clinica(nome: str):
    _db_init()
    conn = _db_conn()
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    if not key:
        return None
    row = conn.execute("SELECT id, nome FROM clinicas WHERE nome_key=?", (key,)).fetchone()
    if row:
        # atualiza grafia se mudou
        if nome and row["nome"] != nome:
            conn.execute("UPDATE clinicas SET nome=? WHERE id=?", (nome, row["id"]))
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO clinicas(nome, nome_key, created_at) VALUES(?,?,?)", (nome, key, now))
    conn.commit()
    return conn.execute("SELECT id FROM clinicas WHERE nome_key=?", (key,)).fetchone()["id"]

def db_upsert_tutor(nome: str, telefone: str = None):
    _db_init()
    conn = _db_conn()
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    if not key:
        return None
    row = conn.execute("SELECT id, nome, telefone FROM tutores WHERE nome_key=?", (key,)).fetchone()
    if row:
        updates = []
        params = []
        if nome and row["nome"] != nome:
            updates.append("nome=?"); params.append(nome)
        if telefone and (row["telefone"] or "") != telefone:
            updates.append("telefone=?"); params.append(telefone)
        if updates:
            params.append(row["id"])
            conn.execute(f"UPDATE tutores SET {', '.join(updates)} WHERE id=?", params)
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO tutores(nome, nome_key, telefone, created_at) VALUES(?,?,?,?)",
                 (nome, key, telefone, now))
    conn.commit()
    return conn.execute("SELECT id FROM tutores WHERE nome_key=?", (key,)).fetchone()["id"]

def db_upsert_paciente(tutor_id: int, nome: str, especie: str = None, raca: str = None,
                      sexo: str = None, nascimento: str = None):
    _db_init()
    conn = _db_conn()
    if not tutor_id:
        return None
    nome = nome_proprio_ptbr(nome)
    key = _norm_key(nome)
    especie = (especie or "").strip()
    raca = nome_proprio_ptbr(raca or "")
    sexo = (sexo or "").strip()
    nascimento = (nascimento or "").strip()
    if not key:
        return None
    row = conn.execute(
        "SELECT id, especie, raca, sexo, nascimento FROM pacientes WHERE tutor_id=? AND nome_key=? AND especie=?",
        (tutor_id, key, especie)
    ).fetchone()
    if row:
        updates = []
        params = []
        if raca and (row["raca"] or "") != raca:
            updates.append("raca=?"); params.append(raca)
        if sexo and (row["sexo"] or "") != sexo:
            updates.append("sexo=?"); params.append(sexo)
        if nascimento and (row["nascimento"] or "") != nascimento:
            updates.append("nascimento=?"); params.append(nascimento)
        if updates:
            params.append(row["id"])
            conn.execute(f"UPDATE pacientes SET {', '.join(updates)} WHERE id=?", params)
            conn.commit()
        return row["id"]
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO pacientes(tutor_id, nome, nome_key, especie, raca, sexo, nascimento, created_at) VALUES(?,?,?,?,?,?,?,?)",
                 (tutor_id, nome, key, especie, raca, sexo, nascimento, now))
    conn.commit()
    return conn.execute(
        "SELECT id FROM pacientes WHERE tutor_id=? AND nome_key=? AND especie=?",
        (tutor_id, key, especie)
    ).fetchone()["id"]


def _limpar_texto_filename(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "SEM_DADO"
    # remove acentos
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    # troca espaços por underscore
    s = re.sub(r"\s+", "_", s)
    # mantém só letras, números, _ e -
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    # evita nomes enormes
    return s[:60] if len(s) > 60 else s

import re
import unicodedata

_PREPOSICOES_MINUSCULAS = {
    "de", "da", "das", "do", "dos",
    "e", "em", "na", "nas", "no", "nos",
    "para", "por", "com", "sem", "a", "as", "o", "os"
}

def _limpar_espacos(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s

def capitalizar_nome(s: str) -> str:
    """
    'spike' -> 'Spike'
    'shih tzu' -> 'Shih Tzu'
    'filhote de srd' -> 'Filhote de Srd' (mantém preposições minúsculas)
    """
    s = _limpar_espacos(s)
    if not s:
        return ""

    palavras = s.split(" ")
    out = []
    for i, w in enumerate(palavras):
        wl = w.lower()
        # mantém preposições minúsculas (exceto se for primeira palavra)
        if i != 0 and wl in _PREPOSICOES_MINUSCULAS:
            out.append(wl)
        else:
            out.append(wl[:1].upper() + wl[1:])
    return " ".join(out)

def capitalizar_frase(s: str) -> str:
    """
    'canina' -> 'Canina'
    'FÊMEA' -> 'Fêmea' (desde que venha com acento correto; se vier sem acento, mantém sem acento)
    """
    s = _limpar_espacos(s).lower()
    if not s:
        return ""
    return s[:1].upper() + s[1:]


def _normalizar_data_str(data_exame: str) -> str:
    """
    Aceita formatos comuns:
    - 'YYYYMMDD' (ex.: 20251220)
    - 'YYYY-MM-DD'
    - 'DD/MM/YYYY'
    Se não conseguir, usa data de hoje.
    Retorna 'YYYY-MM-DD'
    """
    s = (data_exame or "").strip()
    if not s:
        return date.today().strftime("%Y-%m-%d")

    # YYYYMMDD
    if re.fullmatch(r"\d{8}", s):
        try:
            dt = datetime.strptime(s, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    # YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    # DD/MM/YYYY
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
        try:
            dt = datetime.strptime(s, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    # tentativa genérica: pega só números e tenta YYYYMMDD
    nums = re.sub(r"\D", "", s)
    if len(nums) >= 8:
        try:
            dt = datetime.strptime(nums[:8], "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    return date.today().strftime("%Y-%m-%d")

def montar_nome_base_arquivo(*, data_exame: str, animal: str, tutor: str, clinica: str) -> str:
    d = _normalizar_data_str(data_exame)
    a = _limpar_texto_filename(animal)
    t = _limpar_texto_filename(tutor)
    c = _limpar_texto_filename(clinica)
    return f"{d}__{a}__{t}__{c}"


PARAMS = {
    # chave_interna: (label_na_tela, unidade, chave_referencia)
    "Ao":      ("Aorta", "mm", "Ao"),
    "LA":      ("Átrio esquerdo", "mm", "LA"),
    "LA_Ao":   ("AE/Ao (Átrio esquerdo/Aorta)", "", "LA_Ao"),

    # Artéria pulmonar / Aorta (AP/Ao)
    "PA_AP":    ("AP (Artéria pulmonar)", "mm", None),
    "PA_AO":    ("Ao (Aorta - nível AP)", "mm", None),
    "PA_AP_AO": ("AP/Ao (Artéria pulmonar/Aorta)", "", None),

    "IVSd":  ("SIVd (Septo interventricular em diástole)", "mm", "IVSd"),
    "LVPWd": ("PLVEd (Parede livre do VE em diástole)", "mm", "LVPWd"),
    "LVIDd": ("DIVEd (Diâmetro interno do VE em diástole)", "mm", "LVIDd"),

    "IVSs":  ("SIVs (Septo interventricular em sístole)", "mm", "IVSs"),
    "LVPWs": ("PLVEs (Parede livre do VE em sístole)", "mm", "LVPWs"),
    "LVIDs": ("DIVEs (Diâmetro interno do VE em sístole)", "mm", "LVIDs"),


    "EDV": ("VDF (Teicholz)", "ml", "EDV"),
    "ESV": ("VSF (Teicholz)", "ml", "ESV"),
    "EF":  ("FE (Teicholz)", "%", "EF"),
    "FS":  ("Delta D / %FS", "%", "FS"),


    
    "MAPSE": ("MAPSE (excursão sistólica do plano anular mitral)", "mm", None),
    "TAPSE": ("TAPSE (excursão sistólica do plano anular tricúspide)", "mm", None),
"Vmax_Ao":   ("Vmax aorta", "m/s", "Vmax_Ao"),
    "Grad_Ao":   ("Gradiente aorta", "mmHg", None),   # sem referência
    "Vmax_Pulm": ("Vmax pulmonar", "m/s", "Vmax_Pulm"),
    "Grad_Pulm": ("Gradiente pulmonar", "mmHg", None),

    "MV_E":     ("Onda E", "m/s", "MV_E"),
    "MV_A":     ("Onda A", "m/s", "MV_A"),
    "MV_E_A":   ("E/A (relação E/A)", "", "MV_E_A"),
    "MV_DT":    ("TD (tempo desaceleração)", "ms", "MV_DT"),
    "IVRT":     ("TRIV (tempo relaxamento isovolumétrico)", "ms", "IVRT"),

    
    "LA_FS": ("Fração de encurtamento do AE (átrio esquerdo)", "%", None),
    "AURICULAR_FLOW": ("Fluxo auricular", "m/s", None),
"MR_dPdt":  ("MR dp/dt", "mmHg/s", None),
    "TDI_e_a":  ("Doppler tecidual (Relação e'/a'):", "", None),

    "EEp":     ("E/E'", "", None),

    "MR_Vmax":  ("IM (insuficiência mitral) Vmax", "m/s", None),
    "TR_Vmax":  ("IT (insuficiência tricúspide) Vmax", "m/s", None),
    "AR_Vmax":  ("IA (insuficiência aórtica) Vmax", "m/s", None),
    "PR_Vmax":  ("IP (insuficiência pulmonar) Vmax", "m/s", None),

    "Delta_D": ("Delta D (DIVEd - DIVEs)", "mm", None),
    "DIVEdN":  ("DIVEd normalizado (DIVEd / peso^0,294)", "", None),

}


GRUPOS_CANINO = [
    ("VE - Modo M", ["LVIDd","DIVEdN","IVSd","LVPWd","LVIDs","IVSs","LVPWs","EDV","ESV","EF","FS","TAPSE","MAPSE"]),
    ("Átrio esquerdo/ Aorta", ["Ao","LA","LA_Ao"]),
    ("Artéria pulmonar/ Aorta", ["PA_AP","PA_AO","PA_AP_AO"]),
    ("Doppler - Saídas", ["Vmax_Ao","Grad_Ao","Vmax_Pulm","Grad_Pulm"]),
    ("Diastólica", ["MV_E","MV_A","MV_E_A","MV_DT","IVRT","MR_dPdt","TDI_e_a","EEp"]),
    ("Regurgitações", ["MR_Vmax","TR_Vmax","AR_Vmax","PR_Vmax"]),
]

GRUPOS_FELINO = [
    ("VE - Modo M", ["LVIDd","IVSd","LVPWd","LVIDs","IVSs","LVPWs","EDV","ESV","EF","FS"]),
    # Felinos: incluir parâmetros exclusivos (Fração de encurtamento do AE e Fluxo auricular)
    # na categoria de Átrio esquerdo/Aorta, junto do AE/Ao.
    ("Átrio esquerdo/ Aorta", ["Ao","LA","LA_Ao","LA_FS","AURICULAR_FLOW"]),
    ("Artéria pulmonar/ Aorta", ["PA_AP","PA_AO","PA_AP_AO"]),
    ("Doppler - Saídas", ["Vmax_Ao","Grad_Ao","Vmax_Pulm","Grad_Pulm"]),
    ("Diastólica", ["MV_E","MV_A","MV_E_A","MV_DT","IVRT","MR_dPdt","TDI_e_a","EEp"]),
    ("Regurgitações", ["MR_Vmax","TR_Vmax","AR_Vmax","PR_Vmax"]),
]

def especie_is_felina(especie_txt: str) -> bool:
    s = str(especie_txt or "").strip().lower()
    return any(x in s for x in ["fel", "gato", "cat", "feline"])

def get_grupos_por_especie(especie_txt: str):
    return GRUPOS_FELINO if especie_is_felina(especie_txt) else GRUPOS_CANINO



def normalizar_especie_label(especie_txt: str) -> str:
    """Normaliza a espécie para labels padrão (Canina/Felina) quando reconhecida."""
    s = str(especie_txt or "").strip()
    if not s:
        return ""
    sl = s.lower()
    if especie_is_felina(sl):
        return "Felina"
    if any(x in sl for x in ["can", "cao", "cão", "dog", "canine"]):
        return "Canina"
    # outras espécies: aplica formatação de nome próprio
    return nome_proprio_ptbr(s)



# Função de imagem (Mantida)
def criar_imagem_esmaecida(input_path, output_path, opacidade=0.10):
    try:
        img = Image.open(input_path).convert("RGBA")
        dados = img.getdata()
        novos_dados = []
        for item in dados:
            novo_alpha = int(item[3] * opacidade)
            novos_dados.append((item[0], item[1], item[2], novo_alpha))
        img.putdata(novos_dados)
        img.save(output_path, "PNG")
        return True
    except: return False

if os.path.exists("logo.png"):
    if os.path.exists(MARCA_DAGUA_TEMP):
        try: os.remove(MARCA_DAGUA_TEMP)
        except: pass
    criar_imagem_esmaecida("logo.png", MARCA_DAGUA_TEMP, opacidade=0.10)

# Funções de Referência (Mantidas)
def gerar_tabela_padrao():
    data = []
    for p in range(1, 81):
        peso = float(p)
        row = {
            "Peso (kg)": peso,
            "LVIDd_Min": round(1.2 * (peso**0.29), 2), "LVIDd_Max": round(1.7 * (peso**0.29), 2),
            "IVSd_Min":  round(0.6 * (peso**0.24), 2), "IVSd_Max":  round(0.9 * (peso**0.24), 2),
            "LVPWd_Min": round(0.6 * (peso**0.24), 2), "LVPWd_Max": round(0.9 * (peso**0.24), 2),
            "LVIDs_Min": round(0.7 * (peso**0.31), 2), "LVIDs_Max": round(1.0 * (peso**0.31), 2),
            "IVSs_Min":  round(0.9 * (peso**0.24), 2), "IVSs_Max":  round(1.4 * (peso**0.24), 2),
            "LVPWs_Min": round(0.9 * (peso**0.24), 2), "LVPWs_Max": round(1.4 * (peso**0.24), 2),
            "Ao_Min": round(0.9 * (peso**0.24), 2), "Ao_Max": round(1.35 * (peso**0.24), 2),
            "LA_Min": round(0.8 * (peso**0.29), 2), "LA_Max": round(1.5 * (peso**0.29), 2),
            "LA_Ao_Min": 0.8, "LA_Ao_Max": 1.6,
            "EF_Min": 50.0, "EF_Max": 85.0,
            "FS_Min": 25.0, "FS_Max": 45.0,
            "Vmax_Ao_Min": 0.0, "Vmax_Ao_Max": 1.70,
            "Vmax_Pulm_Min": 0.0, "Vmax_Pulm_Max": 1.70,
            "MV_E_Min": 0.50, "MV_E_Max": 1.20,
            "MV_A_Min": 0.30, "MV_A_Max": 0.80,
            "MV_EA_Min": 1.0, "MV_EA_Max": 2.0,
            "MV_DT_Min": 0.0, "MV_DT_Max": 160.0,
            "MV_Slope_Min": 0.0, "MV_Slope_Max": 10.0,
            "IVRT_Min": 0.0, "IVRT_Max": 0.0,
            "E_IVRT_Min": 0.0, "E_IVRT_Max": 0.0,
            "TR_Vmax_Min": 0.0, "TR_Vmax_Max": 2.80,
            "MR_Vmax_Min": 0.0, "MR_Vmax_Max": 6.00,
            "EDV_Min": 0.0, "EDV_Max": round(3.0 * peso, 1), 
            "ESV_Min": 0.0, "ESV_Max": round(1.0 * peso, 1),
            "SV_Min": 0.0, "SV_Max": 0.0
        }
        data.append(row)
    return pd.DataFrame(data)

# ==========================================
# 1.B TABELA DE REFERÊNCIA - FELINOS (Haggström et al., 2016)
# ==========================================
# Observação: por padrão, aplicamos referência automática apenas para:
# - VE - Modo M
# - Átrio esquerdo / Aorta (AE/Ao)
# (Outros grupos ficam sem referência automática, até você desejar expandir.)
TABELA_REF_FELINOS_DEFAULT = [
  {
    "Peso": 1.5,
    "IVSd_Min": 2.3,
    "IVSd_Max": 4.0,
    "LVIDd_Min": 9.5,
    "LVIDd_Max": 15.0,
    "LVPWd_Min": 2.2,
    "LVPWd_Max": 3.8,
    "IVSs_Min": 3.5,
    "IVSs_Max": 6.7,
    "LVIDs_Min": 4.2,
    "LVIDs_Max": 9.6,
    "LVPWs_Min": 3.6,
    "LVPWs_Max": 6.5,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 5.8,
    "LA_Max": 10.2,
    "Ao_Min": 5.5,
    "Ao_Max": 8.8,
    "LA_Ao_Min": 0.85,
    "LA_Ao_Max": 1.4,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 2.0,
    "IVSd_Min": 2.5,
    "IVSd_Max": 4.3,
    "LVIDd_Min": 10.2,
    "LVIDd_Max": 16.0,
    "LVPWd_Min": 2.4,
    "LVPWd_Max": 4.1,
    "IVSs_Min": 3.7,
    "IVSs_Max": 7.2,
    "LVIDs_Min": 4.6,
    "LVIDs_Max": 10.5,
    "LVPWs_Min": 3.9,
    "LVPWs_Max": 7.1,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 6.3,
    "LA_Max": 11.2,
    "Ao_Min": 6.0,
    "Ao_Max": 9.5,
    "LA_Ao_Min": 0.85,
    "LA_Ao_Max": 1.4,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 2.5,
    "IVSd_Min": 2.6,
    "IVSd_Max": 4.5,
    "LVIDd_Min": 10.9,
    "LVIDd_Max": 17.0,
    "LVPWd_Min": 2.5,
    "LVPWd_Max": 4.4,
    "IVSs_Min": 3.9,
    "IVSs_Max": 7.6,
    "LVIDs_Min": 4.8,
    "LVIDs_Max": 11.2,
    "LVPWs_Min": 4.1,
    "LVPWs_Max": 7.5,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 6.8,
    "LA_Max": 12.0,
    "Ao_Min": 6.3,
    "Ao_Max": 10.1,
    "LA_Ao_Min": 0.86,
    "LA_Ao_Max": 1.41,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 3.0,
    "IVSd_Min": 2.7,
    "IVSd_Max": 4.7,
    "LVIDd_Min": 11.4,
    "LVIDd_Max": 17.8,
    "LVPWd_Min": 2.6,
    "LVPWd_Max": 4.5,
    "IVSs_Min": 4.1,
    "IVSs_Max": 7.9,
    "LVIDs_Min": 5.1,
    "LVIDs_Max": 11.7,
    "LVPWs_Min": 4.3,
    "LVPWs_Max": 7.9,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 7.2,
    "LA_Max": 12.7,
    "Ao_Min": 6.7,
    "Ao_Max": 10.7,
    "LA_Ao_Min": 0.86,
    "LA_Ao_Max": 1.42,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 3.5,
    "IVSd_Min": 2.8,
    "IVSd_Max": 4.9,
    "LVIDd_Min": 11.9,
    "LVIDd_Max": 18.5,
    "LVPWd_Min": 2.7,
    "LVPWd_Max": 4.7,
    "IVSs_Min": 4.2,
    "IVSs_Max": 8.2,
    "LVIDs_Min": 5.3,
    "LVIDs_Max": 12.2,
    "LVPWs_Min": 4.5,
    "LVPWs_Max": 8.2,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 7.6,
    "LA_Max": 13.4,
    "Ao_Min": 7.0,
    "Ao_Max": 11.1,
    "LA_Ao_Min": 0.87,
    "LA_Ao_Max": 1.42,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 4.0,
    "IVSd_Min": 2.8,
    "IVSd_Max": 4.9,
    "LVIDd_Min": 12.2,
    "LVIDd_Max": 19.2,
    "LVPWd_Min": 2.8,
    "LVPWd_Max": 4.8,
    "IVSs_Min": 4.3,
    "IVSs_Max": 8.4,
    "LVIDs_Min": 5.5,
    "LVIDs_Max": 12.6,
    "LVPWs_Min": 4.6,
    "LVPWs_Max": 8.5,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 7.9,
    "LA_Max": 13.9,
    "Ao_Min": 7.2,
    "Ao_Max": 11.6,
    "LA_Ao_Min": 0.88,
    "LA_Ao_Max": 1.43,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 4.5,
    "IVSd_Min": 2.9,
    "IVSd_Max": 5.1,
    "LVIDd_Min": 12.7,
    "LVIDd_Max": 19.8,
    "LVPWd_Min": 2.9,
    "LVPWd_Max": 5.0,
    "IVSs_Min": 4.4,
    "IVSs_Max": 8.7,
    "LVIDs_Min": 5.7,
    "LVIDs_Max": 13.0,
    "LVPWs_Min": 4.8,
    "LVPWs_Max": 8.7,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 8.2,
    "LA_Max": 14.5,
    "Ao_Min": 7.5,
    "Ao_Max": 11.9,
    "LA_Ao_Min": 0.88,
    "LA_Ao_Max": 1.43,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 5.0,
    "IVSd_Min": 3.0,
    "IVSd_Max": 5.2,
    "LVIDd_Min": 13.0,
    "LVIDd_Max": 20.3,
    "LVPWd_Min": 3.0,
    "LVPWd_Max": 5.1,
    "IVSs_Min": 4.6,
    "IVSs_Max": 8.9,
    "LVIDs_Min": 5.8,
    "LVIDs_Max": 13.4,
    "LVPWs_Min": 4.9,
    "LVPWs_Max": 9.0,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 8.4,
    "LA_Max": 14.9,
    "Ao_Min": 7.7,
    "Ao_Max": 12.3,
    "LA_Ao_Min": 0.88,
    "LA_Ao_Max": 1.43,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 5.5,
    "IVSd_Min": 3.0,
    "IVSd_Max": 5.3,
    "LVIDd_Min": 13.4,
    "LVIDd_Max": 20.9,
    "LVPWd_Min": 3.0,
    "LVPWd_Max": 5.3,
    "IVSs_Min": 4.7,
    "IVSs_Max": 9.1,
    "LVIDs_Min": 6.0,
    "LVIDs_Max": 13.7,
    "LVPWs_Min": 5.0,
    "LVPWs_Max": 9.2,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 8.7,
    "LA_Max": 15.4,
    "Ao_Min": 7.9,
    "Ao_Max": 12.6,
    "LA_Ao_Min": 0.89,
    "LA_Ao_Max": 1.44,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 6.0,
    "IVSd_Min": 3.1,
    "IVSd_Max": 5.4,
    "LVIDd_Min": 13.7,
    "LVIDd_Max": 21.4,
    "LVPWd_Min": 3.1,
    "LVPWd_Max": 5.4,
    "IVSs_Min": 4.7,
    "IVSs_Max": 9.3,
    "LVIDs_Min": 6.1,
    "LVIDs_Max": 14.1,
    "LVPWs_Min": 5.1,
    "LVPWs_Max": 9.4,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 8.9,
    "LA_Max": 15.8,
    "Ao_Min": 8.1,
    "Ao_Max": 12.9,
    "LA_Ao_Min": 0.89,
    "LA_Ao_Max": 1.44,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 6.5,
    "IVSd_Min": 3.1,
    "IVSd_Max": 5.5,
    "LVIDd_Min": 14.0,
    "LVIDd_Max": 21.8,
    "LVPWd_Min": 3.1,
    "LVPWd_Max": 5.5,
    "IVSs_Min": 4.8,
    "IVSs_Max": 9.4,
    "LVIDs_Min": 6.2,
    "LVIDs_Max": 14.3,
    "LVPWs_Min": 5.3,
    "LVPWs_Max": 9.6,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 9.2,
    "LA_Max": 16.2,
    "Ao_Min": 8.3,
    "Ao_Max": 13.2,
    "LA_Ao_Min": 0.9,
    "LA_Ao_Max": 1.45,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 7.0,
    "IVSd_Min": 3.2,
    "IVSd_Max": 5.6,
    "LVIDd_Min": 14.2,
    "LVIDd_Max": 22.2,
    "LVPWd_Min": 3.2,
    "LVPWd_Max": 5.6,
    "IVSs_Min": 4.9,
    "IVSs_Max": 9.6,
    "LVIDs_Min": 6.3,
    "LVIDs_Max": 14.6,
    "LVPWs_Min": 5.4,
    "LVPWs_Max": 9.8,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 9.4,
    "LA_Max": 16.6,
    "Ao_Min": 8.4,
    "Ao_Max": 13.5,
    "LA_Ao_Min": 0.9,
    "LA_Ao_Max": 1.46,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 7.5,
    "IVSd_Min": 3.2,
    "IVSd_Max": 5.7,
    "LVIDd_Min": 14.5,
    "LVIDd_Max": 22.6,
    "LVPWd_Min": 3.3,
    "LVPWd_Max": 5.7,
    "IVSs_Min": 5.0,
    "IVSs_Max": 9.7,
    "LVIDs_Min": 6.5,
    "LVIDs_Max": 14.9,
    "LVPWs_Min": 5.5,
    "LVPWs_Max": 10.0,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 9.6,
    "LA_Max": 16.9,
    "Ao_Min": 8.6,
    "Ao_Max": 13.8,
    "LA_Ao_Min": 0.91,
    "LA_Ao_Max": 1.46,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 8.0,
    "IVSd_Min": 3.3,
    "IVSd_Max": 5.8,
    "LVIDd_Min": 14.7,
    "LVIDd_Max": 23.0,
    "LVPWd_Min": 3.3,
    "LVPWd_Max": 5.8,
    "IVSs_Min": 5.1,
    "IVSs_Max": 9.9,
    "LVIDs_Min": 6.6,
    "LVIDs_Max": 15.1,
    "LVPWs_Min": 5.6,
    "LVPWs_Max": 10.2,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 9.8,
    "LA_Max": 17.3,
    "Ao_Min": 8.8,
    "Ao_Max": 14.0,
    "LA_Ao_Min": 0.91,
    "LA_Ao_Max": 1.47,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 8.5,
    "IVSd_Min": 3.3,
    "IVSd_Max": 5.8,
    "LVIDd_Min": 15.0,
    "LVIDd_Max": 23.4,
    "LVPWd_Min": 3.4,
    "LVPWd_Max": 5.9,
    "IVSs_Min": 5.1,
    "IVSs_Max": 10.0,
    "LVIDs_Min": 6.7,
    "LVIDs_Max": 15.4,
    "LVPWs_Min": 5.6,
    "LVPWs_Max": 10.3,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 10.0,
    "LA_Max": 17.6,
    "Ao_Min": 8.9,
    "Ao_Max": 14.3,
    "LA_Ao_Min": 0.92,
    "LA_Ao_Max": 1.47,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 9.0,
    "IVSd_Min": 3.3,
    "IVSd_Max": 5.9,
    "LVIDd_Min": 15.2,
    "LVIDd_Max": 23.7,
    "LVPWd_Min": 3.4,
    "LVPWd_Max": 5.9,
    "IVSs_Min": 5.2,
    "IVSs_Max": 10.2,
    "LVIDs_Min": 6.8,
    "LVIDs_Max": 15.6,
    "LVPWs_Min": 5.7,
    "LVPWs_Max": 10.5,
    "FS_Min": 28.0,
    "FS_Max": 62.0,
    "LA_Min": 10.1,
    "LA_Max": 17.9,
    "Ao_Min": 9.1,
    "Ao_Max": 14.5,
    "LA_Ao_Min": 0.92,
    "LA_Ao_Max": 1.47,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 9.5,
    "IVSd_Min": 3.4,
    "IVSd_Max": 6.0,
    "LVIDd_Min": 15.4,
    "LVIDd_Max": 24.0,
    "LVPWd_Min": 3.4,
    "LVPWd_Max": 5.9,
    "IVSs_Min": 5.3,
    "IVSs_Max": 10.3,
    "LVIDs_Min": 6.9,
    "LVIDs_Max": 15.8,
    "LVPWs_Min": 5.8,
    "LVPWs_Max": 10.6,
    "FS_Min": 28.0,
    "FS_Max": 63.0,
    "LA_Min": 10.3,
    "LA_Max": 18.2,
    "Ao_Min": 9.1,
    "Ao_Max": 14.7,
    "LA_Ao_Min": 0.92,
    "LA_Ao_Max": 1.48,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 10.0,
    "IVSd_Min": 3.4,
    "IVSd_Max": 6.0,
    "LVIDd_Min": 15.6,
    "LVIDd_Max": 24.4,
    "LVPWd_Min": 3.5,
    "LVPWd_Max": 6.1,
    "IVSs_Min": 5.3,
    "IVSs_Max": 10.4,
    "LVIDs_Min": 6.9,
    "LVIDs_Max": 16.0,
    "LVPWs_Min": 5.9,
    "LVPWs_Max": 10.8,
    "FS_Min": 28.0,
    "FS_Max": 63.0,
    "LA_Min": 10.5,
    "LA_Max": 18.5,
    "Ao_Min": 9.3,
    "Ao_Max": 14.9,
    "LA_Ao_Min": 0.92,
    "LA_Ao_Max": 1.48,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  },
  {
    "Peso": 10.5,
    "IVSd_Min": 3.5,
    "IVSd_Max": 6.1,
    "LVIDd_Min": 15.8,
    "LVIDd_Max": 24.7,
    "LVPWd_Min": 3.5,
    "LVPWd_Max": 6.2,
    "IVSs_Min": 5.4,
    "IVSs_Max": 10.5,
    "LVIDs_Min": 7.1,
    "LVIDs_Max": 16.3,
    "LVPWs_Min": 6.0,
    "LVPWs_Max": 10.9,
    "FS_Min": 28.0,
    "FS_Max": 63.0,
    "LA_Min": 10.6,
    "LA_Max": 18.8,
    "Ao_Min": 9.5,
    "Ao_Max": 15.1,
    "LA_Ao_Min": 0.94,
    "LA_Ao_Max": 1.49,
    "EF_Min": 72.0,
    "EF_Max": 85.0
  }
]

def gerar_tabela_padrao_felinos() -> pd.DataFrame:
    """Gera DataFrame de referência para felinos a partir de tabela fixa por peso."""
    df = pd.DataFrame(TABELA_REF_FELINOS_DEFAULT)
    # Garantir colunas e tipos
    cols_num = [c for c in df.columns if c != "Peso"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Peso"] = pd.to_numeric(df["Peso"], errors="coerce")
    df = df.dropna(subset=["Peso"]).sort_values("Peso").reset_index(drop=True)
    return df

def limpar_e_converter_tabela_felinos(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas mínimas da tabela felina (mantém a tabela enxuta)."""
    df = df.copy()

    # Normaliza nomes
    df.columns = [str(c).strip() for c in df.columns]

    # Aceita variantes comuns do peso
    if "Peso" not in df.columns:
        for alt in ["Peso (kg)", "Peso_kg", "peso", "PESO"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "Peso"})
                break

    # Colunas esperadas (enxutas)
    colunas_esperadas = [
        "Peso",
        "IVSd_Min", "IVSd_Max",
        "LVIDd_Min", "LVIDd_Max",
        "LVPWd_Min", "LVPWd_Max",
        "IVSs_Min", "IVSs_Max",
        "LVIDs_Min", "LVIDs_Max",
        "LVPWs_Min", "LVPWs_Max",
        "FS_Min", "FS_Max",
        "EF_Min", "EF_Max",
        "LA_Min", "LA_Max",
        "Ao_Min", "Ao_Max",
        "LA_Ao_Min", "LA_Ao_Max",
    ]

    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = np.nan

    # Converte numéricos
    for col in colunas_esperadas:
        if col == "Peso":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Peso"]).sort_values("Peso").reset_index(drop=True)
    return df[colunas_esperadas]

@st.cache_data(show_spinner=False)
def carregar_tabela_referencia_felinos_cached() -> pd.DataFrame:
    """Carrega tabela felina (CSV), ou cria uma padrão se não existir."""
    if os.path.exists(ARQUIVO_REF_FELINOS):
        try:
            df = pd.read_csv(ARQUIVO_REF_FELINOS)
            df = limpar_e_converter_tabela_felinos(df)
            return df
        except Exception:
            # Se der problema, recria padrão
            df = gerar_tabela_padrao_felinos()
            try:
                df.to_csv(ARQUIVO_REF_FELINOS, index=False)
            except Exception:
                pass
            return df
    else:
        df = gerar_tabela_padrao_felinos()
        try:
            df.to_csv(ARQUIVO_REF_FELINOS, index=False)
        except Exception:
            pass
        return df


def limpar_e_converter_tabela(df):
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '.')
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

def carregar_tabela_referencia():
    if os.path.exists(ARQUIVO_REF):
        try:
            df = pd.read_csv(ARQUIVO_REF)
            df = limpar_e_converter_tabela(df)
            cols_check = ["LVIDd_Min", "MV_Slope_Max", "TR_Vmax_Max", "EDV_Max", "IVSs_Max"]
            for c in cols_check:
                if c not in df.columns: 
                    df[c] = 0.0
                    df[c.replace("_Max","_Min")] = 0.0
            return df
        except: return gerar_tabela_padrao()
    else:
        df = gerar_tabela_padrao()
        df.to_csv(ARQUIVO_REF, index=False)
        return df


@st.cache_data(show_spinner=False)
def carregar_tabela_referencia_cached():
    """Wrapper cacheado para evitar re-leitura do CSV a cada reinício."""
    return carregar_tabela_referencia()


@st.cache_data(show_spinner=False, ttl=10)
def listar_registros_arquivados_cached(pasta_str: str):
    """Lê metadados dos laudos arquivados (JSON (JavaScript Object Notation)) com TTL (Time To Live)."""
    pasta = Path(pasta_str)
    arquivos = sorted(pasta.glob("*.json"), reverse=True)

    registros = []
    for p in arquivos:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            pac = obj.get("paciente", {}) if isinstance(obj, dict) else {}
            registros.append({
                "data": pac.get("data_exame", ""),
                "clinica": pac.get("clinica", ""),
                "animal": pac.get("nome", ""),
                "tutor": pac.get("tutor", ""),
                "arquivo_json": str(p),
                "arquivo_pdf": str(pasta / (p.stem + ".pdf"))
            })
        except Exception:
            # se algum JSON estiver corrompido, ignora
            pass
    return registros


def contar_laudos_do_banco():
    """Retorna o total de laudos em todas as tabelas (sem filtros). Usado para mensagem quando filtros retornam 0."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        total = 0
        for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                total += cur.fetchone()[0]
            except sqlite3.OperationalError:
                pass
        conn.close()
        return total
    except Exception:
        return 0


def _backfill_nomes_laudos():
    """Preenche nome_paciente, nome_clinica e nome_tutor nos laudos a partir das tabelas vinculadas (pacientes, clinicas, tutores).
    Corrige laudos já importados que ficaram com essas colunas vazias."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
            try:
                cur.execute(f"PRAGMA table_info({tabela})")
                cols = [r[1] for r in cur.fetchall()]
                if "nome_paciente" not in cols or "nome_clinica" not in cols or "nome_tutor" not in cols:
                    continue
                cur.execute(f"""UPDATE {tabela} SET nome_paciente = (SELECT nome FROM pacientes WHERE pacientes.id = {tabela}.paciente_id)
                    WHERE (nome_paciente IS NULL OR TRIM(COALESCE(nome_paciente, '')) = '') AND paciente_id IS NOT NULL""")
                cur.execute(f"""UPDATE {tabela} SET nome_clinica = COALESCE(
                    (SELECT nome FROM clinicas WHERE clinicas.id = {tabela}.clinica_id),
                    (SELECT nome FROM clinicas_parceiras WHERE clinicas_parceiras.id = {tabela}.clinica_id)
                    ) WHERE clinica_id IS NOT NULL AND (nome_clinica IS NULL OR TRIM(COALESCE(nome_clinica, '')) = '')""")
                cur.execute(f"""UPDATE {tabela} SET nome_tutor = (SELECT t.nome FROM pacientes p JOIN tutores t ON t.id = p.tutor_id WHERE p.id = {tabela}.paciente_id)
                    WHERE paciente_id IS NOT NULL AND (nome_tutor IS NULL OR TRIM(COALESCE(nome_tutor, '')) = '')""")
            except sqlite3.OperationalError:
                pass
        conn.commit()
        conn.close()
    except Exception:
        pass


def listar_laudos_do_banco(tutor_filtro=None, clinica_filtro=None, animal_filtro=None, busca_livre=None):
    """Lista exames (laudos) do banco com tutor e clínica (JOIN). Para busca por tutor, clínica ou pet após importação.
    busca_livre: se preenchido, busca o termo em animal, tutor e clínica ao mesmo tempo (OR)."""
    try:
        _backfill_nomes_laudos()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        out = []
        for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
            try:
                # Coluna de arquivo pode ser arquivo_xml ou arquivo_json
                cur.execute(f"PRAGMA table_info({tabela})")
                cols = [r[1] for r in cur.fetchall()]
                col_arquivo = "arquivo_json" if "arquivo_json" in cols else "arquivo_xml"
                # Fallback: se a tabela tiver nome_clinica/nome_tutor em texto, usar quando JOIN vier vazio
                sel_clinica = "COALESCE(c.nome, cp.nome, l.nome_clinica, '') AS clinica" if "nome_clinica" in cols else "COALESCE(c.nome, cp.nome, '') AS clinica"
                sel_tutor = "COALESCE(t.nome, l.nome_tutor, '') AS tutor" if "nome_tutor" in cols else "COALESCE(t.nome, '') AS tutor"
                query = f"""
                    SELECT
                        l.id, l.tipo_exame,
                        COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '') AS animal,
                        l.data_exame AS data,
                        {sel_clinica},
                        {sel_tutor},
                        l.{col_arquivo} AS arquivo_json,
                        l.arquivo_pdf AS arquivo_pdf
                    FROM {tabela} l
                    LEFT JOIN clinicas c ON l.clinica_id = c.id
                    LEFT JOIN clinicas_parceiras cp ON l.clinica_id = cp.id
                    LEFT JOIN pacientes p ON l.paciente_id = p.id
                    LEFT JOIN tutores t ON p.tutor_id = t.id
                    WHERE 1=1
                """
                params = []
                if tutor_filtro and str(tutor_filtro).strip():
                    if "nome_tutor" in cols:
                        query += " AND UPPER(COALESCE(t.nome, l.nome_tutor, '')) LIKE UPPER(?)"
                    else:
                        query += " AND UPPER(COALESCE(t.nome, '')) LIKE UPPER(?)"
                    params.append(f"%{tutor_filtro.strip()}%")
                if clinica_filtro and str(clinica_filtro).strip():
                    if "nome_clinica" in cols:
                        query += " AND (UPPER(COALESCE(c.nome, '')) LIKE UPPER(?) OR UPPER(COALESCE(cp.nome, '')) LIKE UPPER(?) OR UPPER(COALESCE(l.nome_clinica, '')) LIKE UPPER(?))"
                        params.append(f"%{clinica_filtro.strip()}%")
                        params.append(f"%{clinica_filtro.strip()}%")
                        params.append(f"%{clinica_filtro.strip()}%")
                    else:
                        query += " AND (UPPER(COALESCE(c.nome, '')) LIKE UPPER(?) OR UPPER(COALESCE(cp.nome, '')) LIKE UPPER(?))"
                        params.append(f"%{clinica_filtro.strip()}%")
                        params.append(f"%{clinica_filtro.strip()}%")
                if animal_filtro and str(animal_filtro).strip():
                    query += " AND UPPER(COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '')) LIKE UPPER(?)"
                    params.append(f"%{animal_filtro.strip()}%")
                if busca_livre and str(busca_livre).strip():
                    termo = f"%{busca_livre.strip()}%"
                    # Busca em animal (laudo ou paciente), tutor, clínica (e fallbacks nome_clinica/nome_tutor se existirem)
                    parte_clinica = "COALESCE(c.nome, cp.nome, l.nome_clinica, '')" if "nome_clinica" in cols else "COALESCE(c.nome, cp.nome, '')"
                    parte_tutor = "COALESCE(t.nome, l.nome_tutor, '')" if "nome_tutor" in cols else "COALESCE(t.nome, '')"
                    query += f""" AND (
                        UPPER(COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '')) LIKE UPPER(?)
                        OR UPPER({parte_tutor}) LIKE UPPER(?)
                        OR UPPER({parte_clinica}) LIKE UPPER(?)
                    )"""
                    params.extend([termo, termo, termo])
                query += " ORDER BY l.data_exame DESC, l.id DESC"
                cur.execute(query, params)
                for row in cur.fetchall():
                    r = dict(row)
                    r["arquivo_json"] = r.get("arquivo_json") or ""
                    r["arquivo_pdf"] = r.get("arquivo_pdf") or ""
                    out.append(r)
            except sqlite3.OperationalError:
                continue
        conn.close()
        return out
    except Exception:
        return []

if 'df_ref' not in st.session_state: st.session_state['df_ref'] = carregar_tabela_referencia_cached()
if 'df_ref_felinos' not in st.session_state:
    st.session_state['df_ref_felinos'] = carregar_tabela_referencia_felinos_cached()
if 'sugestao_dados' not in st.session_state: st.session_state['sugestao_dados'] = {}

# Textos
keys_texto = ['txt_valvas', 'txt_camaras', 'txt_funcao', 'txt_pericardio', 'txt_vasos', 'txt_ad_vd', 'txt_conclusao']
QUALI_DET = {
    "valvas": ["mitral", "tricuspide", "aortica", "pulmonar"],
    "camaras": ["ae", "ad", "ve", "vd"],
    "vasos": ["aorta", "art_pulmonar", "veias_pulmonares", "cava_hepaticas"],
    "funcao": ["sistolica_ve", "sistolica_vd", "diastolica", "sincronia"],
    "pericardio": ["efusao", "espessamento", "tamponamento"],
}

ROTULOS = {
    "mitral":"Mitral", "tricuspide":"Tricúspide", "aortica":"Aórtica", "pulmonar":"Pulmonar",
    "ae":"Átrio esquerdo", "ad":"Átrio direito", "ve":"Ventrículo esquerdo", "vd":"Ventrículo direito",
    "aorta":"Aorta", "art_pulmonar":"Artéria pulmonar", "veias_pulmonares":"Veias pulmonares", "cava_hepaticas":"Cava/Hepáticas",
    "sistolica_ve":"Sistólica VE", "sistolica_vd":"Sistólica VD", "diastolica":"Diastólica", "sincronia":"Sincronia",
    "efusao":"Efusão", "espessamento":"Espessamento", "tamponamento":"Sinais de tamponamento",
}

def frase_det(
    *,
    valvas=None, camaras=None, vasos=None, funcao=None, pericardio=None,
    resumo=None, ad_vd="", conclusao=""
):
    """
    Cria uma entrada de frase compatível com:
    - campos antigos: valvas/camaras/vasos/funcao/pericardio/ad_vd/conclusao
    - e com subcampos novos: q_valvas_mitral, q_camaras_ae, etc.
    """
    valvas = valvas or {}
    camaras = camaras or {}
    vasos = vasos or {}
    funcao = funcao or {}
    pericardio = pericardio or {}
    resumo = resumo or {}

    entry = {"layout": "detalhado",
        "valvas": resumo.get("valvas", ""),
        "camaras": resumo.get("camaras", ""),
        "vasos": resumo.get("vasos", ""),
        "funcao": resumo.get("funcao", ""),
        "pericardio": resumo.get("pericardio", ""),
        "ad_vd": ad_vd or "",
        "conclusao": conclusao or "",
        "det": {  # opcional, mas útil
            "valvas": {k: "" for k in QUALI_DET["valvas"]},
            "camaras": {k: "" for k in QUALI_DET["camaras"]},
            "vasos": {k: "" for k in QUALI_DET["vasos"]},
            "funcao": {k: "" for k in QUALI_DET["funcao"]},
            "pericardio": {k: "" for k in QUALI_DET["pericardio"]},
        }
    }

    # preenche o det
    for k, v in valvas.items(): entry["det"]["valvas"][k] = v
    for k, v in camaras.items(): entry["det"]["camaras"][k] = v
    for k, v in vasos.items(): entry["det"]["vasos"][k] = v
    for k, v in funcao.items(): entry["det"]["funcao"][k] = v
    for k, v in pericardio.items(): entry["det"]["pericardio"][k] = v

    # cria também as chaves planas q_... (que o Streamlit usa direto nos text_area)
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (entry["det"][sec].get(it, "") or "")

    return entry


def aplicar_frase_det_na_tela(frase: dict):
    """Joga os subcampos q_... da frase para o session_state (preenche a aba Qualitativa)."""
    if not isinstance(frase, dict):
        return

    # 1) tenta via det
    det = frase.get("det") if isinstance(frase.get("det"), dict) else {}

    for sec, itens in QUALI_DET.items():
        for it in itens:
            k = f"q_{sec}_{it}"
            val = ""

            if det and isinstance(det.get(sec), dict) and (it in det[sec]):
                val = det[sec].get(it, "") or ""
            elif k in frase:
                val = frase.get(k, "") or ""

            st.session_state[k] = val


def garantir_schema_det_frase(entry: dict) -> dict:
    """Garante que entry tenha o formato com 'det' (detalhado) completo."""
    if "det" not in entry or not isinstance(entry["det"], dict):
        entry["det"] = {}

    for sec, itens in QUALI_DET.items():
        if sec not in entry["det"] or not isinstance(entry["det"][sec], dict):
            entry["det"][sec] = {}
        for it in itens:
            entry["det"][sec].setdefault(it, "")

    # mantém também os campos antigos (compatibilidade)
    for c in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
        entry.setdefault(c, "")

    # ✅ NOVO: layout da patologia
    # valores recomendados: "enxuto" | "detalhado"
    entry.setdefault("layout", "detalhado")

    return entry


def migrar_txt_para_det(entry: dict) -> dict:
    """
    Se a frase veio do modelo antigo (valvas/camaras/vasos/funcao/pericardio)
    e o 'det' estiver vazio, joga esse texto para subcampos padrão do 'det'
    para aparecer no Editor de Frases.
    """
    entry = garantir_schema_det_frase(entry)
    det = entry.get("det", {})

    def bloco_vazio(sec: str) -> bool:
        return not any((det.get(sec, {}).get(it, "") or "").strip() for it in QUALI_DET[sec])

    # Valvas -> joga no principal (Mitral)
    if bloco_vazio("valvas"):
        txt = (entry.get("valvas", "") or "").strip()
        if txt:
            det["valvas"]["mitral"] = txt

    # Câmaras -> joga em AE e VE
    if bloco_vazio("camaras"):
        txt = (entry.get("camaras", "") or "").strip()
        if txt:
            det["camaras"]["ae"] = txt
            det["camaras"]["ve"] = txt

    # Vasos -> joga em Aorta
    if bloco_vazio("vasos"):
        txt = (entry.get("vasos", "") or "").strip()
        if txt:
            det["vasos"]["aorta"] = txt

    # Função -> joga em Sistólica VE
    if bloco_vazio("funcao"):
        txt = (entry.get("funcao", "") or "").strip()
        if txt:
            det["funcao"]["sistolica_ve"] = txt

    # Pericárdio -> joga em Efusão
    if bloco_vazio("pericardio"):
        txt = (entry.get("pericardio", "") or "").strip()
        if txt:
            det["pericardio"]["efusao"] = txt

    entry["det"] = det

    # Mantém também as chaves planas q_... coerentes (se você usar em algum lugar)
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (det.get(sec, {}).get(it, "") or "")

    return entry


def det_para_txt(det: dict) -> dict:
    """Converte det{sec:{it:txt}} em txt_{sec} (com linhas 'Rótulo: texto')."""
    out = {}
    for sec, itens in QUALI_DET.items():
        linhas = []
        bloco = det.get(sec, {}) if isinstance(det, dict) else {}
        for it in itens:
            v = (bloco.get(it, "") or "").strip()
            if v:
                linhas.append(f"{ROTULOS[it]}: {v}")
        out[sec] = "\n".join(linhas).strip()
    return out


def aplicar_det_nos_subcampos(chave_frase: str, sobrescrever=False):
    """Aplica db_frases[chave]['det'] nos st.session_state['q_...']."""
    db = st.session_state.get("db_frases", {})
    entry = db.get(chave_frase)
    if not entry:
        return False

    entry = garantir_schema_det_frase(entry)
    det = entry.get("det", {})

    for sec, itens in QUALI_DET.items():
        for it in itens:
            k = f"q_{sec}_{it}"
            novo = (det.get(sec, {}).get(it, "") or "").strip()
            if not novo:
                continue
            atual = (st.session_state.get(k, "") or "").strip()
            if sobrescrever or not atual:
                st.session_state[k] = novo

    # opcional: manter txt_* coerente com det (ótimo para PDF e fallback)
    txts = det_para_txt(det)
    for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos"]:
        if txts.get(sec):
            st.session_state[f"txt_{sec}"] = txts[sec]

    return True


# inicializa subcampos
for sec, itens in QUALI_DET.items():
    for it in itens:
        k = f"q_{sec}_{it}"
        if k not in st.session_state:
            st.session_state[k] = ""

import re
import streamlit as st

def complementar_regurgitacao_valvar(valva: str, grau: str):
    """
    Injeta/atualiza "Refluxo <valva> <grau>." em:
      - q_valvas_<valva>
      - txt_valvas

    Regra: remove qualquer linha que comece com "Refluxo <valva>" antes de inserir,
    evitando duplicar com textos do Doppler (Vmax...) ou do banco.
    """
    if not valva or not grau:
        return

    valva = str(valva).strip().lower()
    grau_in = str(grau).strip().lower()

    mapa_grau = {
        "leve": "leve",
        "moderada": "moderado",
        "moderado": "moderado",
        "importante": "importante",
        "grave": "grave",
        "severa": "grave",
        "severo": "grave",
        "significativa": "importante",
        "significativo": "importante",
    }
    grau = mapa_grau.get(grau_in, grau_in)

    nomes = {
        "mitral": "mitral",
        "tricuspide": "tricúspide",
        "aortica": "aórtico",
        "pulmonar": "pulmonar",
    }
    if valva not in nomes:
        return

    nome_valva = nomes[valva]
    frase = f"Refluxo {nome_valva} {grau}."

    # remove qualquer linha que comece com "Refluxo <valva>"
    pattern_linha = re.compile(rf"^\s*refluxo\s+{re.escape(nome_valva)}\b.*$", re.IGNORECASE)

    def upsert(key: str):
        atual = (st.session_state.get(key, "") or "").strip()
        linhas = [l for l in atual.splitlines() if not pattern_linha.match(l.strip())]
        # adiciona a frase padronizada
        linhas.append(frase)
        st.session_state[key] = "\n".join([l for l in linhas if l.strip()]).strip()

    upsert(f"q_valvas_{valva}")  # subcampo detalhado
    upsert("txt_valvas")         # texto corrido


def montar_qualitativa():
    """Monta valvas/camaras/vasos/funcao/pericardio.
    Se os subcampos (q_...) estiverem vazios, usa fallback nos txt_* (frases antigas).
    """
    saida = {}
    for sec, itens in QUALI_DET.items():
        linhas = []
        for it in itens:
            val = (st.session_state.get(f"q_{sec}_{it}", "") or "").strip()
            if val:
                linhas.append(f"- {ROTULOS[it]}: {val}")

        bloco = "\n".join(linhas).strip()

        # fallback: se não preencheu os subcampos, usa o texto antigo
        if not bloco:
            bloco = (st.session_state.get(f"txt_{sec}", "") or "").strip()

        saida[sec] = bloco

    return saida


for k in keys_texto:
    if k not in st.session_state: st.session_state[k] = ""

# Banco de Frases (Mantido)
FRASES_DEFAULT = {
    "Normal (Normal)": {"layout": "enxuto", "valvas": "Valvas atrioventriculares e semilunares com morfologia, espessura e mobilidade preservadas. Ausência de refluxos valvulares significativos.", "camaras": "Dimensões cavitárias preservadas. Espessura parietal diastólica preservada.", "funcao": "Função sistólica e diastólica dos ventrículos preservada.", "pericardio": "Pericárdio com aspecto ecocardiográfico normal. Ausência de efusão.", "vasos": "Grandes vasos da base com diâmetros e relações anatômicas preservadas.", "ad_vd": "Átrio direito e Ventrículo direito com dimensões e contratilidade preservadas.", "conclusao": "Exame ecocardiográfico dentro dos padrões de normalidade."},
    "Endocardiose Mitral (Leve)": {"valvas": "Valva mitral com espessamento nodular (degeneração mixomatosa inicial). Refluxo mitral leve.", "camaras": "Dimensões de câmaras esquerdas preservadas.", "funcao": "Função sistólica preservada.", "pericardio": "Normal.", "vasos": "Normais.", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Estágio B1."},
    "Endocardiose Mitral (Moderada)": {"valvas": "Valva mitral espessada. Refluxo moderado.", "camaras": "Aumento moderado de AE e VE.", "funcao": "Preservada.", "pericardio": "Normal.", "vasos": "Relação AE/Ao aumentada.", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Estágio B2."},
    "Endocardiose Mitral (Importante)": {"valvas": "Espessamento importante. Refluxo significativo.", "camaras": "Dilatação importante AE/VE.", "funcao": "Preservada.", "pericardio": "Normal.", "vasos": "Congestão venosa?", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Importante."}
}
FRASES_DEFAULT.update({

    # =========================================================
    # ESTENOSE AÓRTICA
    # =========================================================
    "Estenose Aórtica (Leve)": frase_det(
        valvas={
            "aortica": "Valva aórtica com alterações compatíveis com estenose leve. Fluxo turbulento discreto em via de saída do ventrículo esquerdo.",
            "mitral": "Valva mitral com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
            "tricuspide": "Valva tricúspide com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
            "pulmonar": "Valva pulmonar com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas. Espessuras parietais preservadas ou discretamente aumentadas (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões e contratilidade preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Pode haver discreta dilatação pós-estenótica da aorta ascendente, a depender do caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada (por vezes discretamente hiperdinâmica).",
            "diastolica": "Função diastólica sem alterações significativas; avaliar padrão de relaxamento conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica leve.",
            "camaras": "Sem remodelamento significativo ou com hipertrofia concêntrica discreta de ventrículo esquerdo.",
            "vasos": "Aorta com aspecto preservado; possível discreta dilatação pós-estenótica.",
            "funcao": "Função sistólica global preservada.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Moderada)": frase_det(
        valvas={
            "aortica": "Valva aórtica com estenose moderada, com fluxo turbulento e aumento de velocidade ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente com dimensões preservadas; avaliar discreto aumento secundário a alteração de relaxamento, quando presente.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica discreta a moderada, com aumento de espessura de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Possível dilatação pós-estenótica da aorta ascendente, a depender do caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo geralmente preservada; pode estar discretamente hiperdinâmica.",
            "diastolica": "Possível padrão de relaxamento alterado associado à hipertrofia (disfunção diastólica grau I (alteração do relaxamento)), conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica moderada.",
            "camaras": "Hipertrofia concêntrica de ventrículo esquerdo (PLVE e SIV).",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Função sistólica global preservada; avaliar diástole.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Importante)": frase_det(
        valvas={
            "aortica": "Estenose aórtica importante, com turbulência acentuada e aumento expressivo de velocidades ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada ou com refluxo discreto secundário, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente preservado; pode haver discreto aumento secundário, conforme alterações de enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica moderada a importante, com aumento de espessura de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo frequentemente preservada; avaliar sinais de repercussão funcional conforme caso.",
            "diastolica": "Padrão de relaxamento frequentemente alterado em função da hipertrofia; avaliar disfunção diastólica ao Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica importante.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão diastólica e sistólica.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Grave)": frase_det(
        valvas={
            "aortica": "Estenose aórtica grave, com turbulência severa e velocidades muito elevadas ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo secundário discreto, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo pode estar preservado ou discretamente aumentado, conforme repercussões de enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica importante. Avaliar espessuras de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), além de eventuais sinais de repercussão hemodinâmica.",
            "ad": "Átrio direito geralmente preservado.",
            "vd": "Ventrículo direito geralmente preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar sinais de congestão conforme hemodinâmica e Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Avaliar cuidadosamente função sistólica do ventrículo esquerdo, pois pode haver repercussão funcional em casos graves.",
            "diastolica": "Avaliar diástole ao Doppler (alterações de relaxamento e aumento de pressões de enchimento podem ocorrer).",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica grave.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão sistólica/diastólica.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),


    # =========================================================
    # ESTENOSE SUBAÓRTICA
    # =========================================================
    "Estenose Subaórtica (Leve)": frase_det(
        valvas={
            "aortica": "Valva aórtica com morfologia preservada ou alterações discretas. Fluxo turbulento discreto em via de saída do ventrículo esquerdo, compatível com estenose subaórtica leve.",
            "mitral": "Valva mitral com morfologia preservada. Ausência de refluxo significativo.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Ausência de refluxo significativo.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas. Espessuras parietais preservadas ou discretamente aumentadas, conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Avaliar dilatação pós-estenótica da aorta ascendente conforme o caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações significativas; avaliar relaxamento conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica leve.",
            "camaras": "Sem remodelamento significativo.",
            "vasos": "Aorta preservada; avaliar dilatação pós-estenótica.",
            "funcao": "Função sistólica preservada.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Moderada)": frase_det(
        valvas={
            "aortica": "Valva aórtica com morfologia preservada ou alterações discretas. Turbulência e aumento de velocidade em via de saída do ventrículo esquerdo, compatível com estenose subaórtica moderada.",
            "mitral": "Valva mitral com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente com dimensões preservadas.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica discreta a moderada (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo geralmente preservada; pode estar discretamente hiperdinâmica.",
            "diastolica": "Possível alteração de relaxamento associada à hipertrofia (disfunção diastólica grau I (alteração do relaxamento)), conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica moderada.",
            "camaras": "Hipertrofia concêntrica de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Função sistólica preservada; avaliar diástole.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Importante)": frase_det(
        valvas={
            "aortica": "Turbulência acentuada e velocidades elevadas em via de saída do ventrículo esquerdo, compatível com estenose subaórtica importante.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo discreto secundário, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente preservado; pode haver discreto aumento secundário conforme enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica moderada a importante (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito preservado.",
            "vd": "Ventrículo direito preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar sinais indiretos de congestão conforme Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo frequentemente preservada; avaliar repercussão funcional conforme caso.",
            "diastolica": "Alterações de relaxamento são frequentes em presença de hipertrofia; avaliar Doppler diastólico.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica importante.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão diastólica/sistólica.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Grave)": frase_det(
        valvas={
            "aortica": "Turbulência severa e velocidades muito elevadas em via de saída do ventrículo esquerdo, compatível com estenose subaórtica grave.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo secundário discreto, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo pode estar preservado ou discretamente aumentado.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica importante; avaliar repercussões hemodinâmicas conforme demais parâmetros.",
            "ad": "Átrio direito geralmente preservado.",
            "vd": "Ventrículo direito geralmente preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar congestão conforme hemodinâmica e Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Avaliar cuidadosamente função sistólica do ventrículo esquerdo; repercussão funcional pode ocorrer em casos graves.",
            "diastolica": "Avaliar diástole ao Doppler (alterações de relaxamento e aumento de pressões de enchimento podem ocorrer).",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica grave.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão sistólica/diastólica.",
            "pericardio": "Sem efusão.",
        }
    ),


    # =========================================================
    # ESTENOSE PULMONAR
    # =========================================================
    "Estenose Pulmonar (Leve)": frase_det(
        valvas={
            "pulmonar": "Valva pulmonar com alterações compatíveis com estenose leve. Fluxo turbulento discreto em via de saída do ventrículo direito.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas; espessura parietal preservada ou discretamente aumentada, conforme medidas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional.",
            "art_pulmonar": "Artéria pulmonar: avaliar discreta dilatação pós-estenótica do tronco pulmonar, a depender do caso.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Pulmonar leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar leve.",
            "camaras": "Sem remodelamento significativo.",
            "vasos": "Artéria pulmonar preservada; possível dilatação pós-estenótica discreta.",
            "funcao": "Função sistólica preservada.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Moderada)": frase_det(
        valvas={
            "pulmonar": "Valva pulmonar com estenose moderada, com aumento de velocidades em via de saída do ventrículo direito ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito com dimensões preservadas ou discretamente aumentadas, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia concêntrica discreta a moderada, conforme medidas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: possível dilatação pós-estenótica do tronco pulmonar, conforme o caso.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Função sistólica do ventrículo direito geralmente preservada; avaliar repercussão conforme severidade.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Repercussão em câmaras direitas pode estar presente conforme severidade.",
        conclusao="Achados compatíveis com Estenose Pulmonar moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar moderada.",
            "camaras": "Hipertrofia/dilatação de câmaras direitas conforme severidade.",
            "vasos": "Possível dilatação pós-estenótica de artéria pulmonar.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Importante)": frase_det(
        valvas={
            "pulmonar": "Estenose pulmonar importante, com aumento expressivo de velocidades ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide: pode haver refluxo funcional secundário, conforme remodelamento.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito: possível dilatação moderada a importante, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia concêntrica moderada a importante; pode haver dilatação associada, conforme severidade.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: dilatação pós-estenótica do tronco pulmonar pode estar presente.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas: avaliar sinais de congestão sistêmica conforme hemodinâmica.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Avaliar função sistólica do ventrículo direito; repercussão funcional pode ocorrer em casos avançados.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Remodelamento de câmaras direitas pode estar presente.",
        conclusao="Achados compatíveis com Estenose Pulmonar importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar importante.",
            "camaras": "Remodelamento de câmaras direitas.",
            "vasos": "Dilatação pós-estenótica de artéria pulmonar pode estar presente.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Grave)": frase_det(
        valvas={
            "pulmonar": "Estenose pulmonar grave, com turbulência severa e velocidades muito elevadas ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide: refluxo funcional secundário pode estar presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito: dilatação importante provável, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia importante e possível dilatação; avaliar repercussões hemodinâmicas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: dilatação pós-estenótica pode estar presente.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas: avaliar sinais de congestão sistêmica conforme hemodinâmica.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Avaliar cuidadosamente função sistólica do ventrículo direito; disfunção pode estar presente em casos graves.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Dilatação/hipertrofia de câmaras direitas provável.",
        conclusao="Achados compatíveis com Estenose Pulmonar grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar grave.",
            "camaras": "Remodelamento importante de câmaras direitas.",
            "vasos": "Dilatação pós-estenótica de artéria pulmonar pode estar presente.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),




    # ----------------------------
    # PDA
    # ----------------------------
    "Persistência do Ducto Arterioso (PDA) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA, com fluxo anômalo em região de artéria pulmonar/aorta descendente, conforme janelas disponíveis.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com Persistência do Ducto Arterioso (PDA) leve."
    },
    "Persistência do Ducto Arterioso (PDA) (Moderada)": {
        "valvas": "Possível insuficiência funcional secundária (ex.: mitral) conforme remodelamento.",
        "camaras": "Sugere sobrecarga volumétrica esquerda moderada (aumento de AE e VE), conforme medidas.",
        "funcao": "Função sistólica preservada ou discretamente hiperdinâmica.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA com shunt predominante esquerda→direita.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com PDA com repercussão hemodinâmica moderada."
    },
    "Persistência do Ducto Arterioso (PDA) (Importante)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme dilatação de câmaras.",
        "camaras": "Importante sobrecarga volumétrica esquerda provável (dilatação de AE e VE), conforme medidas.",
        "funcao": "Função sistólica pode estar preservada ou já apresentar repercussão, conforme o caso.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA com shunt significativa esquerda→direita.",
        "ad_vd": "Avaliar sinais de hipertensão pulmonar associada, quando aplicável.",
        "conclusao": "Achados compatíveis com PDA com repercussão hemodinâmica importante."
    },
    "Persistência do Ducto Arterioso (PDA) (Grave)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável (sobrecarga volumétrica importante e/ou alterações compatíveis com evolução avançada), conforme medidas.",
        "funcao": "Avaliar cuidadosamente função sistólica e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA. Considerar avaliação de hipertensão pulmonar e direção do shunt, quando aplicável.",
        "ad_vd": "Repercussões em câmaras direitas podem ocorrer em cenários avançados/hipertensão pulmonar.",
        "conclusao": "Achados compatíveis com PDA grave."
    },

    # ----------------------------
    # CIV
    # ----------------------------
    "Comunicação Interventricular (CIV) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV, com fluxo de shunt ao Doppler, conforme janelas disponíveis.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) leve."
    },
    "Comunicação Interventricular (CIV) (Moderada)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento.",
        "camaras": "Sugere repercussão em câmaras esquerdas em grau moderado, conforme magnitude do shunt e medidas.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV com shunt predominante esquerda→direita.",
        "ad_vd": "Avaliar repercussão em câmaras direitas e sinais de hipertensão pulmonar, quando aplicável.",
        "conclusao": "Achados compatíveis com CIV com repercussão hemodinâmica moderada."
    },
    "Comunicação Interventricular (CIV) (Importante)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento.",
        "camaras": "Repercussão hemodinâmica importante provável, conforme medidas e magnitude do shunt.",
        "funcao": "Avaliar repercussão funcional associada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV com shunt significativa. Avaliar hipertensão pulmonar associada.",
        "ad_vd": "Repercussões em câmaras direitas podem estar presentes.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) importante."
    },
    "Comunicação Interventricular (CIV) (Grave)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável, conforme medidas e avaliação do shunt.",
        "funcao": "Avaliar cuidadosamente função sistólica e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV. Considerar avaliação detalhada da direção do shunt e hipertensão pulmonar, quando aplicável.",
        "ad_vd": "Repercussões em câmaras direitas podem ocorrer em cenários avançados.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) grave."
    },

    # ----------------------------
    # CIA
    # ----------------------------
    "Comunicação Interatrial (CIA) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA, com fluxo de shunt ao Doppler, conforme janelas disponíveis.",
        "ad_vd": "Sem alterações significativas em câmaras direitas.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) leve."
    },
    "Comunicação Interatrial (CIA) (Moderada)": {
        "valvas": "Possíveis insuficiências funcionais secundárias conforme remodelamento.",
        "camaras": "Pode haver aumento de câmaras direitas conforme magnitude do shunt (direita), conforme medidas.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA com shunt predominante esquerda→direita.",
        "ad_vd": "Possível repercussão moderada em AD/VD, conforme medidas.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) moderada."
    },
    "Comunicação Interatrial (CIA) (Importante)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme dilatação de câmaras direitas.",
        "camaras": "Repercussão hemodinâmica importante provável em câmaras direitas, conforme medidas.",
        "funcao": "Avaliar repercussão funcional associada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA. Avaliar sinais de hipertensão pulmonar quando aplicável.",
        "ad_vd": "Remodelamento importante de AD/VD pode estar presente.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) importante."
    },
    "Comunicação Interatrial (CIA) (Grave)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável em câmaras direitas.",
        "funcao": "Avaliar cuidadosamente função sistólica do VD e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA. Considerar avaliação detalhada de hipertensão pulmonar e direção do shunt.",
        "ad_vd": "Repercussões avançadas em AD/VD podem estar presentes.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) grave."
    },
})


def inferir_layout(entry: dict, chave: str) -> str:
    # Normal sempre enxuto
    if chave == "Normal (Normal)":
        return "enxuto"

    # se já foi definido, respeita
    layout = (entry.get("layout") or "").strip().lower()
    if layout in ("enxuto", "detalhado"):
        return layout

    # heurística
    det = entry.get("det", {})
    det_tem_algo = any(
        (det.get(sec, {}).get(it, "") or "").strip()
        for sec, itens in QUALI_DET.items()
        for it in itens
    )

    txt_tem_algo = any(
        (entry.get(k, "") or "").strip()
        for k in ["valvas", "camaras", "vasos", "funcao", "pericardio", "ad_vd", "conclusao"]
    )

    if txt_tem_algo and not det_tem_algo:
        return "enxuto"
    return "detalhado"


def carregar_frases():
    if not os.path.exists(ARQUIVO_FRASES):
        with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
            json.dump(FRASES_DEFAULT, f, indent=4, ensure_ascii=False)
        base = copy.deepcopy(FRASES_DEFAULT)
    else:
        try:
            with open(ARQUIVO_FRASES, "r", encoding="utf-8") as f:
                base = {**FRASES_DEFAULT, **json.load(f)}
        except:
            base = copy.deepcopy(FRASES_DEFAULT)

    # MIGRA / GARANTE 'det' EM TODAS AS FRASES + layout correto
    for k in list(base.keys()):
        entry = base[k]
        entry = garantir_schema_det_frase(entry)
        entry = migrar_txt_para_det(entry)
        entry["layout"] = inferir_layout(entry, k)
        base[k] = entry

    return base




# ==========================================
# 2. CLASSE PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        bg = MARCA_DAGUA_TEMP if os.path.exists(MARCA_DAGUA_TEMP) else ("logo.png" if os.path.exists("logo.png") else None)
        # Marca d'água: ligeiramente menor e mais alta para não conflitar com carimbo/assinatura.
        if bg: self.image(bg, x=55, y=65, w=100)
        if os.path.exists("logo.png"): self.image("logo.png", x=10, y=8, w=35)
        self.set_y(15); self.set_x(52)
        self.set_font("Arial", 'B', 16); self.set_text_color(0,0,0)
        self.cell(0, 10, "LAUDO ECOCARDIOGRÁFICO", ln=1, align='L')
        self.set_y(35) # Margem segurança

    def footer(self):
        self.set_y(-15); self.set_font("Arial", 'I', 9); self.set_text_color(100,100,100)
        self.cell(0, 10, "Fort Cordis Cardiologia Veterinária | Fortaleza-CE", align='C')

# ==========================================
# 3. LÓGICA
# ==========================================
def calcular_referencia_tabela(parametro, peso_kg, df=None):
    """Retorna a faixa de referência (min,max) e um texto "min - max".

    ✅ Importante: agora respeita o *df* passado (ex.: felinos) e aceita coluna de peso como
    "Peso (kg)" **ou** "Peso".
    """
    # Usa o df fornecido (ex.: tabela felina) ou cai no padrão canino
    if df is None:
        df = st.session_state.get('df_ref')
    if df is None:
        return None, ""

    # Trabalha em cópia para não alterar o df em sessão
    try:
        df = df.copy()
    except Exception:
        return None, ""

    # Normaliza peso
    try:
        peso_kg = float(str(peso_kg).replace(",", "."))
    except Exception:
        return None, ""

    # Normaliza coluna de peso (felinos vinha como "Peso")
    if "Peso (kg)" not in df.columns:
        if "Peso" in df.columns:
            df = df.rename(columns={"Peso": "Peso (kg)"})
        else:
            return None, ""

    # MAPA ATUALIZADO COM OS DADOS QUE VOCÊ PEDIU
    mapa = {
        "LVIDd": ("LVIDd_Min", "LVIDd_Max"), "Ao": ("Ao_Min", "Ao_Max"), "LA": ("LA_Min", "LA_Max"),
        "IVSd": ("IVSd_Min", "IVSd_Max"), "LVPWd": ("LVPWd_Min", "LVPWd_Max"),
        "LVIDs": ("LVIDs_Min", "LVIDs_Max"), "IVSs": ("IVSs_Min", "IVSs_Max"), "LVPWs": ("LVPWs_Min", "LVPWs_Max"),
        "EDV": ("EDV_Min", "EDV_Max"), "ESV": ("ESV_Min", "ESV_Max"), "SV": ("SV_Min", "SV_Max"),
        "Vmax_Ao": ("Vmax_Ao_Min", "Vmax_Ao_Max"), "Vmax_Pulm": ("Vmax_Pulm_Min", "Vmax_Pulm_Max"),
        "LA_Ao": ("LA_Ao_Min", "LA_Ao_Max"), "EF": ("EF_Min", "EF_Max"), "FS": ("FS_Min", "FS_Max"),
        "MV_E": ("MV_E_Min", "MV_E_Max"), "MV_A": ("MV_A_Min", "MV_A_Max"),
        "MV_E_A": ("MV_EA_Min", "MV_EA_Max"), "MV_DT": ("MV_DT_Min", "MV_DT_Max"), "MV_Slope": ("MV_Slope_Min", "MV_Slope_Max"),
        "IVRT": ("IVRT_Min", "IVRT_Max"), "E_IVRT": ("E_IVRT_Min", "E_IVRT_Max"),
        "TR_Vmax": ("TR_Vmax_Min", "TR_Vmax_Max"), "MR_Vmax": ("MR_Vmax_Min", "MR_Vmax_Max")
    }

    if parametro not in mapa:
        return None, ""

    col_min, col_max = mapa[parametro]
    if col_min not in df.columns or col_max not in df.columns:
        return (0.0, 0.0), "--"

    # Ordena e busca/interpola
    df = df.sort_values("Peso (kg)").reset_index(drop=True)

    # Garantir numérico (importações CSV podem vir como texto)
    df["Peso (kg)"] = pd.to_numeric(df["Peso (kg)"], errors="coerce")
    df[col_min] = pd.to_numeric(df[col_min], errors="coerce")
    df[col_max] = pd.to_numeric(df[col_max], errors="coerce")

    if peso_kg in set(df["Peso (kg)"].dropna().values.tolist()):
        row = df[df["Peso (kg)"] == peso_kg].iloc[0]
        min_val, max_val = row[col_min], row[col_max]
    else:
        # Insere linha e interpola
        row_new = {"Peso (kg)": peso_kg}
        for c in df.columns:
            if c != "Peso (kg)":
                row_new[c] = pd.NA
        df_temp = pd.concat([df, pd.DataFrame([row_new])], ignore_index=True)
        df_temp = df_temp.sort_values("Peso (kg)").reset_index(drop=True)

        # Converte tudo que dá para numérico; NA vira NaN
        df_temp = df_temp.apply(pd.to_numeric, errors="coerce")
        df_temp = df_temp.interpolate(method='linear', limit_direction='both')

        row = df_temp[(df_temp["Peso (kg)"] - peso_kg).abs() < 1e-9].iloc[0]
        min_val, max_val = row[col_min], row[col_max]

    if pd.isna(min_val) or pd.isna(max_val):
        return None, "--"
    if float(min_val) == 0.0 and float(max_val) == 0.0:
        return None, "--"
    return (float(min_val), float(max_val)), f"{float(min_val):.2f} - {float(max_val):.2f}"

def interpretar(valor, ref_tuple):
    if not ref_tuple or (ref_tuple[0] == 0 and ref_tuple[1] == 0): return ""
    min_v, max_v = ref_tuple
    if valor < min_v: return "Reduzido"
    if valor > max_v: return "Aumentado"
    return "Normal"


# Referência fixa para DIVEdN (DIVEd normalizado / LVIDdN)
# Observação: esta fórmula (peso^0,294) é a mais usada para cães; para felinos, o expoente e as referências diferem.
DIVEDN_REF_MIN = 1.27
DIVEDN_REF_MAX = 1.85
DIVEDN_REF_TXT = f"{DIVEDN_REF_MIN:.2f}-{DIVEDN_REF_MAX:.2f}"

def interpretar_divedn(divedn: float) -> str:
    """Interpretação prática para DIVEdN (LVIDdN) em cães.
    Mantém uma leitura clínica mais útil do que apenas 'Aumentado/Normal/Reduzido'.
    """
    try:
        v = float(divedn)
    except Exception:
        return ""
    if v <= 0:
        return ""
    if v < DIVEDN_REF_MIN:
        return "Abaixo do esperado"
    # Faixa considerada "normal"
    if v <= 1.70:
        return "Normal"
    # Zona limítrofe (acima do ponto de corte clínico mais usado, mas ainda dentro do teto de referência)
    if v <= DIVEDN_REF_MAX:
        return "Limítrofe"
    # Dilatação: gradação prática
    if v <= 2.00:
        return "Dilatação leve"
    if v <= 2.30:
        return "Dilatação moderada"
    return "Dilatação importante"

# Cérebro Clínico (Mantido)
def analisar_criterios_clinicos(dados, peso, patologia, grau_refluxo, tem_congestao, grau_geral):
    chave = montar_chave_frase(patologia, grau_refluxo, grau_geral)

    res_base = st.session_state['db_frases'].get(chave, {})
    if not res_base and patologia != "Normal":
        for k, v in st.session_state['db_frases'].items():
            if patologia in k:
                res_base = v.copy()
                break

    if not res_base:
        res_base = {'conclusao': f"{patologia}"}

    txt = res_base.copy()

    # ... (resto do seu código igual)


    if patologia == "Endocardiose Mitral":
        # pega o que veio do editor
        conclusao_editor = (txt.get("conclusao") or "").strip()

        try:
            r_lvidd = calcular_referencia_tabela("LVIDd", peso)[0]
            l_lvidd = r_lvidd[1] if r_lvidd[1] else 999

            r_laao = calcular_referencia_tabela("LA_Ao", peso)[0]
            l_laao = r_laao[1] if r_laao[1] else 1.6
        except:
            l_lvidd, l_laao = 999, 1.6

        val_laao, val_lvidd = dados.get('LA_Ao', 0), dados.get('LVIDd', 0)
        aum_ae, aum_ve = (val_laao >= l_laao), (val_lvidd > l_lvidd)

        # você pode manter valvas automático OU só se estiver vazio também
        if not (txt.get("valvas") or "").strip():
            txt['valvas'] = f"Valva mitral espessada. Insuficiência {grau_refluxo.lower()}."

        # ✅ só calcula e escreve a conclusão automática se o editor NÃO tiver conclusão
        if not conclusao_editor:
            if tem_congestao:
                txt['conclusao'] = f"Endocardiose Mitral Estágio C (ACVIM). Refluxo {grau_refluxo}. Sinais de ICC."
            elif aum_ae and aum_ve:
                txt['conclusao'] = f"Endocardiose Mitral Estágio B2 (ACVIM). Refluxo {grau_refluxo} com remodelamento."
            elif aum_ae:
                txt['conclusao'] = f"Endocardiose Mitral (Refluxo {grau_refluxo}) com aumento atrial esquerdo."
            else:
                txt['conclusao'] = f"Endocardiose Mitral Estágio B1 (ACVIM). Refluxo {grau_refluxo}."



    """
    Copia os textos corridos (txt_*) para os subcampos detalhados (q_*).
    Eu, particularmente, recomendo preencher só os campos mais prováveis
    e não “inventar” texto para válvulas/câmaras que não foram citadas.
    """

    """
    Complementa os campos qualitativos de valvas (q_valvas_*) com informação de regurgitação
    quando houver Vmax > 0 nas medidas.

    Observação (opinião técnica): Vmax NÃO classifica bem gravidade do refluxo sozinho.
    Então eu descrevo 'presente' + Vmax, e só uso o grau da mitral quando você já seleciona no sidebar.
    """
    dados = st.session_state.get("dados_atuais", {}) or {}

    mr = float(dados.get("MR_Vmax", 0.0) or 0.0)
    tr = float(dados.get("TR_Vmax", 0.0) or 0.0)
    ar = float(dados.get("AR_Vmax", 0.0) or 0.0)
    pr = float(dados.get("PR_Vmax", 0.0) or 0.0)

    def append_if_needed(key: str, extra: str):
        extra = (extra or "").strip()
        if not extra:
            return
        atual = (st.session_state.get(key, "") or "").strip()
        if extra.lower() in atual.lower():
            return
        st.session_state[key] = (atual + ("\n" if atual else "") + extra).strip()

    # Mitral
    if mr > 0:
        extra = f"Refluxo mitral presente ao Doppler (Vmax {mr:.2f} m/s)."
        append_if_needed("q_valvas_mitral", extra)

    # Se for Endocardiose Mitral, aí sim usa o grau escolhido
    if mr > 0 and patologia == "Endocardiose Mitral" and grau_refluxo:
        extra = f"Refluxo mitral {grau_refluxo.lower()} ao Doppler (Vmax {mr:.2f} m/s)."
        append_if_needed("q_valvas_mitral", extra)

    # Tricúspide
    if tr > 0:
        extra = f"Refluxo tricúspide presente ao Doppler (Vmax {tr:.2f} m/s)."
        append_if_needed("q_valvas_tricuspide", extra)

    # Aórtica
    if ar > 0:
        extra = f"Refluxo aórtico presente ao Doppler (Vmax {ar:.2f} m/s)."
        append_if_needed("q_valvas_aortica", extra)

    # Pulmonar
    if pr > 0:
        extra = f"Refluxo pulmonar presente ao Doppler (Vmax {pr:.2f} m/s)."
        append_if_needed("q_valvas_pulmonar", extra)



    def set_if_empty(key, value):
        value = (value or "").strip()
        if not value:
            return
        # só preenche se o campo ainda estiver vazio (pra não apagar o que você digitou)
        if not (st.session_state.get(key, "") or "").strip():
            st.session_state[key] = value

    txt_valvas = st.session_state.get("txt_valvas", "")
    txt_camaras = st.session_state.get("txt_camaras", "")
    txt_funcao = st.session_state.get("txt_funcao", "")
    txt_pericardio = st.session_state.get("txt_pericardio", "")
    txt_vasos = st.session_state.get("txt_vasos", "")
    txt_ad_vd = st.session_state.get("txt_ad_vd", "")

    # --- Valvas ---
    # Endocardiose mitral: joga a sugestão principalmente no campo Mitral
    if patologia == "Endocardiose Mitral":
        set_if_empty("q_valvas_mitral", txt_valvas)
    else:
        # outras patologias: coloca a sugestão em Mitral como “campo principal”
        set_if_empty("q_valvas_mitral", txt_valvas)

    # --- Câmaras ---
    # Texto corrido geralmente fala de câmaras esquerdas; joga em AE e VE
    set_if_empty("q_camaras_ae", txt_camaras)
    set_if_empty("q_camaras_ve", txt_camaras)

    # Texto subjetivo AD/VD joga para as câmaras direitas
    set_if_empty("q_camaras_ad", txt_ad_vd)
    set_if_empty("q_camaras_vd", txt_ad_vd)

    # --- Função ---
    # Texto corrido vai em “Sistólica VE” como principal
    set_if_empty("q_funcao_sistolica_ve", txt_funcao)

    # --- Pericárdio ---
    set_if_empty("q_pericardio_efusao", txt_pericardio)

    # --- Vasos ---
    set_if_empty("q_vasos_aorta", txt_vasos)

# ==========================================
# 5. APP PRINCIPAL
# ==========================================
if os.path.exists("logo.png"): st.sidebar.image("logo.png", width=150)
# Sempre recarrega do disco para capturar novas patologias salvas no JSON
st.session_state["db_frases"] = carregar_frases()
usuario_nome = st.session_state.get("usuario_nome", "Usuário")
st.sidebar.title(f"👤 {usuario_nome}")
# ==========================================================
# ✅ Assinatura/Carimbo PERSISTENTE (não precisa reenviar)
# Salva em: C:\Users\<SeuUsuario>\FortCordis\assinatura.png  (Windows)
# ==========================================================
PASTA_FORTCORDIS = Path.home() / "FortCordis"
PASTA_FORTCORDIS.mkdir(parents=True, exist_ok=True)

ASSINATURA_PATH = str(PASTA_FORTCORDIS / "assinatura.png")

# Se já existir assinatura salva, usa automaticamente (configuração em Configurações > Assinatura/Carimbo)
if "assinatura_path" not in st.session_state:
    if os.path.exists(ASSINATURA_PATH):
        st.session_state["assinatura_path"] = ASSINATURA_PATH
if "trocar_assinatura" not in st.session_state:
    st.session_state["trocar_assinatura"] = False

# ============================================================================
# MENU PRINCIPAL (definido cedo para condicionar XML e Suspeita apenas a Laudos)
# ============================================================================
st.sidebar.markdown("## 🏥 Fort Cordis")
st.sidebar.markdown("*Sistema Integrado de Gestão*")
st.sidebar.markdown("---")
menu_principal = st.sidebar.radio(
    "Navegação",
    [
        "🏠 Dashboard",
        "📅 Agendamentos",
        "📋 Prontuário",
        "🩺 Laudos e Exames",
        "💊 Prescrições",
        "💰 Financeiro",
        "🏢 Cadastros",
        "⚙️ Configurações"
    ],
    label_visibility="collapsed"
)
st.sidebar.markdown("---")
st.sidebar.caption("Versão 2.0 — Sistema Integrado")
st.sidebar.caption(f"Deploy: {VERSAO_DEPLOY}")

# --- Sidebar: Suspeita (dinâmica) ---
# --- helpers: quebrar "Patologia (Grau)" ---
def _split_pat_grau(chave: str):
    s = (chave or "").strip()
    if s.endswith(")") and " (" in s:
        base, resto = s.rsplit(" (", 1)
        grau = resto[:-1].strip()  # tira o ")"
        return base.strip(), grau
    return s, ""

def _listar_patologias_base(db: dict):
    bases = set()
    for k in (db or {}).keys():
        base, _ = _split_pat_grau(k)
        if base and base != "Normal":
            bases.add(base)
    return sorted(bases)

def _graus_da_patologia(db: dict, patologia_base: str):
    graus = set()
    for k in (db or {}).keys():
        base, grau = _split_pat_grau(k)
        if base == patologia_base and grau:
            graus.add(grau)
    return sorted(graus)


# ==========================
# ✅ Carregamento de exame arquivado (JSON) para edição
# --------------------------
# OBS: não podemos setar st.session_state[...] de widgets *depois* que os widgets
# já foram instanciados no mesmo rerun. Por isso, o botão da aba "Buscar exames"
# apenas agenda o carregamento e faz st.rerun(); o apply acontece aqui, antes
# dos widgets do cadastro/medidas serem criados.
# ==========================
def _aplicar_carregamento_exame_pendente():
    arq = st.session_state.pop("__carregar_exame_json_path", None)
    if not arq:
        return

    try:
        obj = json.loads(Path(arq).read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"Não consegui abrir o JSON selecionado: {e}")
        return

    if not isinstance(obj, dict):
        st.error("JSON inválido (estrutura inesperada).")
        return

    pac = obj.get("paciente", {}) if isinstance(obj.get("paciente"), dict) else {}
    medidas = obj.get("medidas", {}) if isinstance(obj.get("medidas"), dict) else {}
    textos = obj.get("textos", {}) if isinstance(obj.get("textos"), dict) else {}
    qualidet = obj.get("quali_det", {}) if isinstance(obj.get("quali_det"), dict) else {}
    meta = obj.get("qualitativa_meta", {}) if isinstance(obj.get("qualitativa_meta"), dict) else {}

    # --------------------------
    # Cadastro
    # --------------------------
    st.session_state["cad_data"] = str(pac.get("data_exame", "") or "")
    st.session_state["cad_paciente"] = str(pac.get("nome", "") or "")
    st.session_state["cad_tutor"] = str(pac.get("tutor", "") or "")
    st.session_state["cad_raca"] = str(pac.get("raca", "") or "")
    st.session_state["cad_sexo"] = str(pac.get("sexo", "") or "")
    st.session_state["cad_idade"] = str(pac.get("idade", "") or "")
    st.session_state["cad_peso"] = str(pac.get("peso", "") or "")
    st.session_state["cad_clinica"] = str(pac.get("clinica", "") or "")
    st.session_state["cad_solicitante"] = str(pac.get("solicitante", "") or "")

    especie_norm = str(pac.get("especie", "Canina") or "Canina").strip() or "Canina"
    if "lista_especies" not in st.session_state:
        st.session_state["lista_especies"] = ["Canina", "Felina"]
    if especie_norm not in st.session_state["lista_especies"]:
        st.session_state["lista_especies"] = sorted(set(st.session_state["lista_especies"] + [especie_norm]))
    st.session_state["cad_especie"] = especie_norm

    # peso numérico (para cálculos e referências)
    try:
        st.session_state["peso_atual"] = float(str(st.session_state.get("cad_peso", "0")).replace(",", "."))
    except Exception:
        st.session_state["peso_atual"] = 0.0

    # --------------------------
    # Medidas (dados_atuais + widgets med_*)
    # --------------------------
    dados_local = st.session_state.get("dados_atuais", {}) or {}
    if not isinstance(dados_local, dict):
        dados_local = {}
    dados_local = dict(dados_local)

    for k in PARAMS.keys():
        try:
            dados_local[k] = float(medidas.get(k, 0.0) or 0.0)
        except Exception:
            dados_local[k] = 0.0

    # extras (TDI manual, se existirem no JSON)
    for extra in ["TDI_e", "TDI_a"]:
        if extra in medidas:
            try:
                dados_local[extra] = float(medidas.get(extra, 0.0) or 0.0)
            except Exception:
                dados_local[extra] = 0.0

    st.session_state["dados_atuais"] = dados_local

    # sincroniza widgets numéricos (mesma lógica do import XML)
    try:
        for _k in PARAMS.keys():
            st.session_state[f"med_{_k}"] = float(dados_local.get(_k, 0.0) or 0.0)

        st.session_state["EEp_in"] = float(dados_local.get("EEp", 0.0) or 0.0)
        st.session_state["TDI_e_in"] = float(dados_local.get("TDI_e", 0.0) or 0.0)
        st.session_state["TDI_a_in"] = float(dados_local.get("TDI_a", 0.0) or 0.0)
        st.session_state["TDI_ea_out"] = float(dados_local.get("TDI_e_a", 0.0) or 0.0)
        st.session_state["DIVEdN_out"] = float(dados_local.get("DIVEdN", 0.0) or 0.0)
    except Exception:
        pass

    # --------------------------
    # Textos (qualitativa/conclusão)
    # --------------------------
    if isinstance(textos, dict):
        for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
            st.session_state[f"txt_{sec}"] = str(textos.get(sec, "") or "")

    # --------------------------
    # Qualitativa detalhada (subcampos)
    # --------------------------
    for sec, itens in QUALI_DET.items():
        for it in itens:
            st.session_state[f"q_{sec}_{it}"] = ""

    if isinstance(qualidet, dict) and qualidet:
        for sec, itens in QUALI_DET.items():
            bloco = qualidet.get(sec, {}) if isinstance(qualidet.get(sec), dict) else {}
            for it in itens:
                st.session_state[f"q_{sec}_{it}"] = str(bloco.get(it, "") or "")

    # layout (detalhado/enxuto)
    st.session_state["layout_qualitativa"] = str(obj.get("layout_qualitativa", st.session_state.get("layout_qualitativa", "detalhado")) or "detalhado")

    # meta (suspeita/grau)
    if isinstance(meta, dict):
        st.session_state["sb_patologia"] = str(meta.get("patologia", st.session_state.get("sb_patologia", "Normal")) or "Normal")
        st.session_state["sb_grau_refluxo"] = str(meta.get("grau_refluxo", st.session_state.get("sb_grau_refluxo", "Leve")) or "Leve")
        st.session_state["sb_congestao"] = bool(meta.get("congestao", st.session_state.get("sb_congestao", False)))
        st.session_state["sb_grau_geral"] = str(meta.get("grau_geral", st.session_state.get("sb_grau_geral", "Normal")) or "Normal")

    # sinaliza para UI (se quiser mostrar feedback)
    st.session_state["__exame_carregado_ok"] = True

# aplica antes de criar widgets (sidebar/tabs)
_aplicar_carregamento_exame_pendente()

# --- Sidebar: Suspeita (base) + Grau — APENAS no menu Laudos e Exames ---
if menu_principal == "🩺 Laudos e Exames":
    db_frases = st.session_state.get("db_frases", {}) or {}
    op_patologias = ["Normal"] + _listar_patologias_base(db_frases)
    if st.session_state.get("sb_patologia") not in op_patologias:
        st.session_state["sb_patologia"] = "Normal"
    sb_patologia = st.sidebar.selectbox(
        "Suspeita:",
        options=op_patologias,
        index=0,
        key="sb_patologia"
    )
    # -------- Sidebar: Grau / Congestão (APENAS UM BLOCO) --------
    sb_grau_refluxo = "Leve"
    sb_congestao = False
    sb_grau_geral = "Normal"
    if sb_patologia == "Normal":
        sb_grau_geral = "Normal"
    elif sb_patologia == "Endocardiose Mitral":
        if st.session_state.get("sb_grau_refluxo") not in ["Leve", "Moderada", "Importante"]:
            st.session_state["sb_grau_refluxo"] = "Leve"
        sb_grau_refluxo = st.sidebar.select_slider(
            "Grau Refluxo:",
            options=["Leve", "Moderada", "Importante"],
            key="sb_grau_refluxo"
        )
        sb_congestao = st.sidebar.checkbox(
            "Sinais de Congestão (Estágio C)?",
            key="sb_congestao"
        )
    else:
        graus_existentes = _graus_da_patologia(db_frases, sb_patologia)
        if not graus_existentes:
            graus_existentes = ["Leve", "Moderada", "Importante", "Grave"]
        if graus_existentes and st.session_state.get("sb_grau_geral") not in graus_existentes:
            st.session_state["sb_grau_geral"] = graus_existentes[0]
        if len(graus_existentes) >= 2:
            sb_grau_geral = st.sidebar.select_slider(
                "Grau:",
                options=graus_existentes,
                key="sb_grau_geral"
            )
        else:
            sb_grau_geral = st.sidebar.selectbox(
                "Grau:",
                options=graus_existentes,
                index=0,
                disabled=True,
                key="sb_grau_geral"
            )
    if sb_patologia == "Normal":
        sb_grau_geral = "Normal"
    st.sidebar.markdown("---")
else:
    sb_patologia = "Normal"
    sb_grau_refluxo = "Leve"
    sb_congestao = False
    sb_grau_geral = "Normal"


def montar_chave_frase(patologia: str, grau_refluxo: str, grau_geral: str) -> str:
    if patologia == "Normal":
        return "Normal (Normal)"
    if patologia == "Endocardiose Mitral":
        return f"{patologia} ({grau_refluxo})"
    return f"{patologia} ({grau_geral})"


# ==========================================================
# ✅ Match robusto de chaves no banco de frases
# (evita falhas por variações de caixa/acentos/"Moderado" vs "Moderada")
# ==========================================================
import unicodedata


def _norm_key(s: str) -> str:
    s = (s or "").strip().casefold()
    s = "".join(
        ch for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )
    s = re.sub(r"\s+", " ", s)
    return s


def _variantes_grau(grau: str) -> list[str]:
    g = (grau or "").strip()
    if not g:
        return [g]
    # cobre divergências comuns (moderada/moderado; severa/severo)
    trocas = {
        "Moderada": ["Moderado"],
        "Moderado": ["Moderada"],
        "Severa": ["Severo", "Grave"],
        "Severo": ["Severa", "Grave"],
        "Grave": ["Severa", "Severo"],
    }
    return [g] + trocas.get(g, [])


def obter_entry_frase(db: dict, chave: str):
    """Obtém a entry do banco tentando (1) exato, (2) normalizado e (3) variações de grau."""
    if not isinstance(db, dict):
        return None
    chave = (chave or "").strip()
    if not chave:
        return None

    # 1) match exato
    if chave in db:
        return db.get(chave)

    # 2) variação de grau (Moderado/Moderada etc)
    base, grau = _split_pat_grau(chave)
    for g in _variantes_grau(grau):
        alt = f"{base} ({g})" if g else base
        if alt in db:
            return db.get(alt)

    # 3) match normalizado (acentos/caixa/espaços)
    alvo = _norm_key(chave)
    for k in db.keys():
        if _norm_key(k) == alvo:
            return db.get(k)

    # 4) normalizado com variações de grau
    for g in _variantes_grau(grau):
        alt = f"{base} ({g})" if g else base
        alvo2 = _norm_key(alt)
        for k in db.keys():
            if _norm_key(k) == alvo2:
                return db.get(k)

    return None


def aplicar_entry_salva(entry: dict, *, layout: str = "detalhado"):
    """Aplica uma entry do banco na tela (session_state) respeitando o layout salvo."""
    if not isinstance(entry, dict):
        return

    entry = garantir_schema_det_frase(entry)
    entry = migrar_txt_para_det(entry)
    layout = (layout or entry.get("layout") or "detalhado").strip().lower()

    if layout == "enxuto":
        # limpa subcampos detalhados
        for sec, itens in QUALI_DET.items():
            for it in itens:
                st.session_state[f"q_{sec}_{it}"] = ""

        # aplica textos corridos
        for k in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
            st.session_state[f"txt_{k}"] = (entry.get(k, "") or "").strip()
        return

    # ===== detalhado =====
    det = entry.get("det", {}) if isinstance(entry.get("det"), dict) else {}

    # limpa tudo primeiro (evita "sobras" de outra patologia)
    for sec, itens in QUALI_DET.items():
        for it in itens:
            st.session_state[f"q_{sec}_{it}"] = ""

    # aplica (mesmo vazio, para refletir exatamente o que foi salvo)
    for sec, itens in QUALI_DET.items():
        bloco = det.get(sec, {}) if isinstance(det.get(sec), dict) else {}
        for it in itens:
            st.session_state[f"q_{sec}_{it}"] = (bloco.get(it, "") or "").strip()

    # conclusão
    st.session_state["txt_conclusao"] = (entry.get("conclusao", "") or "").strip()

    # mantém txt_* coerente (útil para PDF)
    txts = det_para_txt(det)
    for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos"]:
        st.session_state[f"txt_{sec}"] = (txts.get(sec, "") or "").strip()

if menu_principal == "🩺 Laudos e Exames":
    chave = montar_chave_frase(sb_patologia, sb_grau_refluxo, sb_grau_geral)
    if st.sidebar.button("🔄 Gerar Texto"):
        db_local = st.session_state.get("db_frases", {}) or {}
        # ✅ Busca robusta (evita falhas por acentos/caixa ou "Moderado" vs "Moderada")
        entry = obter_entry_frase(db_local, chave)
        if entry:
            aplicar_entry_salva(entry, layout=entry.get("layout", "detalhado"))
        else:
        # ✅ Se não existe no banco, segue o fluxo “automático” (como antes)
            analisar_criterios_clinicos(
                st.session_state.get('dados_atuais',{}),
                st.session_state.get('peso_atual',10.0),
                sb_patologia,
                sb_grau_refluxo,
                sb_congestao,
                sb_grau_geral
            )

        if (not entry) and (sb_patologia == "Endocardiose Mitral"):
            complementar_regurgitacao_valvar("mitral", sb_grau_refluxo)

def aplicar_sugestao_nos_subcampos(patologia: str):
    """
    Copia os textos corridos (txt_*) para os subcampos detalhados (q_*),
    SEM sobrescrever o que você já digitou.
    """
    def set_if_empty(key, value):
        value = (value or "").strip()
        if not value:
            return
        if not (st.session_state.get(key, "") or "").strip():
            st.session_state[key] = value
    
    txt_valvas = st.session_state.get("txt_valvas", "")
    txt_camaras = st.session_state.get("txt_camaras", "")
    txt_funcao = st.session_state.get("txt_funcao", "")
    txt_pericardio = st.session_state.get("txt_pericardio", "")
    txt_vasos = st.session_state.get("txt_vasos", "")
    txt_ad_vd = st.session_state.get("txt_ad_vd", "")

    # Valvas: joga no campo “Mitral” como principal (você pode trocar essa regra depois)
    set_if_empty("q_valvas_mitral", txt_valvas)

    # Câmaras: normalmente fala mais de AE/VE
    set_if_empty("q_camaras_ae", txt_camaras)
    set_if_empty("q_camaras_ve", txt_camaras)

    # Direitas
    set_if_empty("q_camaras_ad", txt_ad_vd)
    set_if_empty("q_camaras_vd", txt_ad_vd)

    # Função
    set_if_empty("q_funcao_sistolica_ve", txt_funcao)

    # Pericárdio
    set_if_empty("q_pericardio_efusao", txt_pericardio)

    # Vasos
    set_if_empty("q_vasos_aorta", txt_vasos)


def complementar_regurgitacoes_nas_valvas(patologia: str = "", grau_mitral: str | None = None):
    """
    Complementa os campos qualitativos de valvas (q_valvas_*) com informação de regurgitação
    quando houver Vmax > 0 nas medidas.
    """
    dados = st.session_state.get("dados_atuais", {}) or {}

    mr = float(dados.get("MR_Vmax", 0.0) or 0.0)
    tr = float(dados.get("TR_Vmax", 0.0) or 0.0)
    ar = float(dados.get("AR_Vmax", 0.0) or 0.0)
    pr = float(dados.get("PR_Vmax", 0.0) or 0.0)

    def append_if_needed(key: str, extra: str):
        extra = (extra or "").strip()
        if not extra:
            return
        atual = (st.session_state.get(key, "") or "").strip()
        if extra.lower() in atual.lower():
            return
        st.session_state[key] = (atual + ("\n" if atual else "") + extra).strip()

    if mr > 0:
        if patologia == "Endocardiose Mitral" and grau_mitral:
            extra = f"Refluxo mitral {grau_mitral.lower()} ao Doppler (Vmax {mr:.2f} m/s)."
        else:
            extra = f"Refluxo mitral presente ao Doppler (Vmax {mr:.2f} m/s)."
        append_if_needed("q_valvas_mitral", extra)

    if tr > 0:
        append_if_needed("q_valvas_tricuspide", f"Refluxo tricúspide presente ao Doppler (Vmax {tr:.2f} m/s).")

    if ar > 0:
        append_if_needed("q_valvas_aortica", f"Refluxo aórtico presente ao Doppler (Vmax {ar:.2f} m/s).")

    if pr > 0:
        append_if_needed("q_valvas_pulmonar", f"Refluxo pulmonar presente ao Doppler (Vmax {pr:.2f} m/s).")


if menu_principal == "🩺 Laudos e Exames":
    st.sidebar.success("Texto aplicado!")


    st.title("🫀 Fort Cordis - Laudo V.28.0")
    if st.session_state.pop("toast_carregar_exame", False):
        st.success("Exame arquivado carregado para edição. Ajuste o que precisar e gere um novo PDF/JSON.")
    st.markdown("---")
    uploaded_xml = st.file_uploader("1. XML Vivid IQ", type=['xml'])
else:
    uploaded_xml = None

nome_animal, especie, raca, tutor, solicitante, clinica = "", "", "", "", "", ""
peso, idade, data_exame, sexo = "10.0", "", "", "" 
fc = ""
dados = st.session_state["dados_atuais"]

import re

def _parse_num(texto: str):
    """
    Extrai o primeiro número decimal de uma string.
    Aceita '4,2', '4.2', '4,2kg', 'Weight: 4.2 kg' etc.
    """
    if not texto:
        return None
    s = str(texto).strip().lower()
    # pega primeiro número (com , ou .)
    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not m:
        return None
    num = m.group(1).replace(",", ".")
    try:
        return float(num)
    except:
        return None

def extrair_peso_kg(soup):
    """
    Tenta encontrar peso no XML:
    1) tags (weight/patientweight/etc) case-insensitive
    2) parameters (parameter NAME="...") case-insensitive
    Faz conversão de lb->kg se detectar unidade.
    Retorna float (kg) ou None.
    """
    # --- 1) procurar em TAGS (case-insensitive) ---
    candidatos_tags = {
        "weight", "patientweight", "patient_weight", "bodyweight", "bw"
    }

    # procura qualquer tag cujo nome bata ignorando case
    tags = soup.find_all(True)
    for t in tags:
        if not getattr(t, "name", None):
            continue
        nome = t.name.lower()
        if nome in candidatos_tags:
            txt = (t.get_text() or "").strip()
            val = _parse_num(txt)
            if val is None:
                continue
            # unidade (se houver)
            txt_l = txt.lower()
            unit_attr = (t.get("unit") or t.get("Unit") or "").lower()
            if "lb" in txt_l or "lb" in unit_attr:
                val = val / 2.20462
            return val

    # --- 2) procurar em PARAMETERS ---
    candidatos_param = {
        "weight", "patient weight", "patientweight", "body weight", "bodyweight", "bw"
    }

    for p in soup.find_all("parameter"):
        # atributos podem variar: NAME, Name, name
        name_attr = p.get("NAME") or p.get("Name") or p.get("name") or ""
        name_l = str(name_attr).strip().lower()
        if name_l in candidatos_param or any(k == name_l.replace("_", " ") for k in candidatos_param):
            node_val = p.find("aver") or p.find("val") or p.find("value")
            txt = (node_val.get_text() if node_val else p.get_text() or "").strip()
            val = _parse_num(txt)
            if val is None:
                continue
            txt_l = txt.lower()
            if "lb" in txt_l:
                val = val / 2.20462
            return val

    return None

def _find_text_ci(soup, tag_names):
    """Retorna o texto do primeiro tag encontrado (case-insensitive)."""
    for nm in tag_names:
        try:
            tag = soup.find(lambda t, nm=nm: getattr(t, "name", None) and str(t.name).lower() == str(nm).lower())
        except Exception:
            tag = None
        if tag:
            txt = (tag.get_text() or "").strip()
            if txt:
                return txt
    return ""




if uploaded_xml:
    # bytes estáveis (evita ponteiro do .read()) + hash para não reprocessar em todo rerun
    try:
        content = uploaded_xml.getvalue()
    except Exception:
        content = uploaded_xml.read()

    xml_hash = hashlib.sha256(content).hexdigest()

    # Só reprocessa quando o XML (Extensible Markup Language) muda
    if st.session_state.get('_xml_hash') != xml_hash:
        st.session_state['_xml_hash'] = xml_hash
        try:
            soup = BeautifulSoup(content, 'xml')
        except Exception:
            try:
                soup = BeautifulSoup(content, 'lxml')
            except Exception:
                soup = BeautifulSoup(content, 'html.parser')
        try:
            raw_last = soup.find('lastName').text if soup.find('lastName') else ""
            raw_first = soup.find('firstName').text if soup.find('firstName') else ""
            if not raw_first and "," in raw_last:
                parts = raw_last.split(",", 1); tutor = parts[0].strip(); rest = parts[1].strip()
                if " " in rest: nome_animal, raca = rest.split(" ", 1)
                else: nome_animal = rest
            else:
                tutor = raw_last.strip()
                if " " in raw_first: nome_animal, raca = raw_first.split(" ", 1)
                else: nome_animal = raw_first.strip()
            if soup.find('Species'): especie = soup.find('Species').text
            # fallback: alguns XMLs trazem apenas Category (C/F)
            if not especie:
                cat = _find_text_ci(soup, ["Category", "category"]) or ""
                cat = (cat or "").strip().upper()
                if cat == "C": especie = "Canina"
                elif cat == "F": especie = "Felina"

            # ✅ normaliza espécie (Canina/Felina) e garante opção no menu
            especie = normalizar_especie_label(especie)
            if especie:
                if especie not in st.session_state.get("lista_especies", []):
                    st.session_state["lista_especies"].append(especie)
                st.session_state["cad_especie"] = especie
            peso_xml = extrair_peso_kg(soup)
            if peso_xml is not None:
                peso = f"{peso_xml:.2f}".rstrip("0").rstrip(".")  # ex.: "4.2" em vez de "4.20"
            else:
                # mantém o que já estava (ex.: default "10.0")
                peso = peso
    
            data_exame = _find_text_ci(soup, ["StudyDate", "ExamDate", "ExamDateTime", "ExamDateTimeUTC", "StudyDateUTC"]) or data_exame
            idade = _find_text_ci(soup, ["age", "Age", "PatientAge"]) or idade
            nascimento = _find_text_ci(soup, ["birthdate", "BirthDate", "Birthdate", "PatientBirthDate"]) or ""
            telefone = _find_text_ci(soup, ["phone", "Phone", "Telephone"]) or ""

            # ✅ Clínica digitada no equipamento (tag <freeTextAddress>)
            clinica_xml = _find_text_ci(soup, ["freeTextAddress"])
            if clinica_xml:
                clinica = clinica_xml
            if soup.find('HeartRate'): fc = soup.find('HeartRate').text
            tag_sex = soup.find('Sex'); 
            if tag_sex: sexo = "Macho" if "m" in tag_sex.text.lower() else "Fêmea"
            # ✅ normaliza textos vindos do XML (cadastro)
            tutor = nome_proprio_ptbr(tutor)
            nome_animal = nome_proprio_ptbr(nome_animal)
            raca = nome_proprio_ptbr(raca)
    
            clinica = nome_proprio_ptbr(clinica)
            # ✅ joga no session_state para persistir na UI
            st.session_state["cad_tutor"] = tutor
            st.session_state["cad_paciente"] = nome_animal
            st.session_state["cad_raca"] = raca
            st.session_state["cad_idade"] = idade
            st.session_state["cad_data"] = data_exame
            st.session_state["cad_clinica"] = clinica
            st.session_state["cad_sexo"] = sexo
            st.session_state["cad_solicitante"] = solicitante
            # ✅ Auto-cadastro local ao importar XML (Extensible Markup Language)
            try:
                clinica_id = db_upsert_clinica(clinica)
                tutor_id = db_upsert_tutor(tutor, telefone if 'telefone' in locals() else None)
                paciente_id = db_upsert_paciente(tutor_id, nome_animal, especie=especie, raca=raca, sexo=sexo,
                                                 nascimento=(nascimento if 'nascimento' in locals() else None))
                st.session_state["cad_clinica_id"] = clinica_id
                st.session_state["cad_tutor_id"] = tutor_id
                st.session_state["cad_paciente_id"] = paciente_id
            except Exception:
                pass

        except: pass
        st.session_state['peso_temp'] = peso
        # sincroniza o input do cadastro com o XML
        st.session_state["cad_peso"] = peso
    
        # mantém também o peso numérico para referências
        try:
            st.session_state["peso_atual"] = float(str(peso).replace(",", "."))
        except:
            st.session_state["peso_atual"] = 10.0
    
    
        def get_val(tags):
            if isinstance(tags, str): tags = [tags]
            for t in tags:
                # tenta match exato (como vinha antes) e depois case-insensitive
                p = soup.find('parameter', {'NAME': t})
                if not p:
                    try:
                        tl = str(t).lower()
                        p = soup.find(lambda x, tl=tl: getattr(x, 'name', None) == 'parameter' and str(x.get('NAME', '')).lower() == tl)
                    except Exception:
                        p = None
                # fallback: normaliza espaços no NAME="..."
                if not p:
                    try:
                        tn = re.sub(r"\s+", "", str(t).lower())
                        p = soup.find(lambda x, tn=tn: getattr(x, 'name', None) == 'parameter' and re.sub(r"\s+", "", str(x.get('NAME', '')).lower()) == tn)
                    except Exception:
                        p = None
                if p and (val := p.find('aver') or p.find('val')):
                    try: return float(val.text)
                    except: pass
            return 0.0
    
        
        def _norm_meas_name(s: str) -> str:
            s = (s or "").strip()
            # normaliza "prime" (′) e aspas curvas (’)
            s = s.replace("′", "'").replace("’", "'").replace("´", "'")
            s = re.sub(r"\s+", " ", s)
            return s.lower()

        def get_val_by_measname(names):
            """Lê valores quando o equipamento grava o identificador dentro de <name>...</name>."""
            if isinstance(names, str):
                names = [names]
            targets = {_norm_meas_name(n) for n in names}
            for p in soup.find_all("parameter"):
                # busca QUALQUER <name> dentro do parâmetro
                for nm_tag in p.find_all("name"):
                    nm = _norm_meas_name(nm_tag.get_text())
                    if nm in targets:
                        node = p.find("aver") or p.find("val") or p.find("value")
                        if node:
                            try:
                                return float(node.get_text())
                            except:
                                pass
            return 0.0

# ========================================================
        # AQUI ESTA O BLOCO QUE VOCÊ PEDIU - LEITURA COMPLETA
        # ========================================================
        dados['Ao'] = get_val(["2D/Ao Root Diam", "Ao Root Diam"])
        dados['LA'] = get_val(["2D/LA", "LA Dimension"])
        dados['LA_Ao'] = get_val(["2D/LA/Ao", "LA/Ao Ratio"])
        # Artéria pulmonar / Aorta (AP/Ao) - medidas user-defined (2D) via <name>AP</name>, <name>Ao</name>, <name>AP/Ao</name>
        # tenta primeiro pelas tags fixas (USERDEFP-...), depois por <name>...</name>
        dados['PA_AP'] = get_val(["USERDEFP-E1D489E4-5035-4159-A936-44407BA574FB"]) or get_val_by_measname(["AP", "PA", "Pulmonary Artery"])
        dados['PA_AO'] = get_val(["USERDEFP-D46BA2A2-B7AA-4839-B36A-36291FFF690D"]) or get_val_by_measname(["Ao (AP)", "Ao_AP", "Ao", "Aorta"])
        dados['PA_AP_AO'] = get_val(["USERDEFP-5799533D-8698-4EC5-800A-464654356AC9"]) or get_val_by_measname(["AP/Ao", "AP/AO", "PA/Ao", "PA/AO"])
        # se a razão não vier pronta do equipamento, calcula AP/Ao
        if float(dados.get('PA_AP_AO', 0.0) or 0.0) <= 0 and float(dados.get('PA_AP', 0.0) or 0.0) > 0 and float(dados.get('PA_AO', 0.0) or 0.0) > 0:
            try:
                dados['PA_AP_AO'] = round(float(dados['PA_AP']) / float(dados['PA_AO']), 3)
            except Exception:
                dados['PA_AP_AO'] = 0.0

        dados['IVSd'] = get_val(["MM/IVSd", "IVSd", "2D/IVSd"])
        dados['LVIDd'] = get_val(["MM/LVIDd", "LVIDd", "2D/LVIDd"])
        dados['LVPWd'] = get_val(["MM/LVPWd", "LVPWd", "2D/LVPWd"])
        dados['IVSs'] = get_val(["MM/IVSs", "IVSs", "2D/IVSs"])
        dados['LVIDs'] = get_val(["MM/LVIDs", "LVIDs", "2D/LVIDs"])
        dados['LVPWs'] = get_val(["MM/LVPWs", "LVPWs", "2D/LVPWs"])
        dados['EDV'] = get_val(["MM/EDV(Teich)", "EDV", "2D/EDV(Teich)"])
        dados['ESV'] = get_val(["MM/ESV(Teich)", "ESV", "2D/ESV(Teich)"])
        dados['EF'] = get_val(["MM/EF(Teich)", "EF", "2D/EF(Teich)"])
        dados['FS'] = get_val(["MM/%FS", "FS", "2D/%FS"])
        dados['TAPSE'] = get_val(["MM/TAPSE", "TAPSE", "MM/Tapse", "MM/TAPSe"])
        dados['MAPSE'] = get_val(["MM/MAPSE", "MAPSE"])
        dados['Vmax_Ao'] = get_val(["LVOT Vmax P", "LVOT Vmax"])
        dados['Grad_Ao'] = get_val(["LVOT maxPG"])
        dados['Vmax_Pulm'] = get_val(["RVOT Vmax P", "RVOT Vmax"])
        dados['Grad_Pulm'] = get_val(["RVOT maxPG"])
        
        # NOVOS CAMPOS QUE ESTAVAM FALTANDO NA TELA ANTES
        dados['MV_E'] = get_val(["MV E Velocity", "MV E Vel"])
        dados['MV_A'] = get_val(["MV A Velocity", "MV A Vel"])
        dados['MV_DT'] = get_val(["MV Dec Time", "MV Decel Time", "MV DT"]) 
        dados['MV_Slope'] = get_val(["MV Dec Slope", "MV Decel Slope"])
        dados['IVRT'] = get_val(["IVRT", "Left Ventricular IVRT"])
        # Felinos: medidas adicionais (quando disponíveis no XML)
        dados['LA_FS'] = get_val(["LA Fractional Shortening", "LA %FS", "LA FS", "LA %FS (2D)", "LA FS%"])
        dados['AURICULAR_FLOW'] = get_val(["Auricular Flow", "Atrial Flow", "LA Appendage Flow", "LAA Flow", "LA Appendage Velocity", "Auricular Flow Velocity"])
        dados['TR_Vmax'] = get_val(["TR Vmax", "TV Regurg Vmax"])
        dados['MR_Vmax'] = get_val(["MR Vmax", "Mitral Regurg Vmax"])
        dados['AR_Vmax'] = get_val(["AR Vmax", "AV Regurg Vmax", "Aortic Regurg Vmax"])
        dados['PR_Vmax'] = get_val(["PR Vmax", "PV Regurg Vmax", "Pulmonic Regurg Vmax"])
        dados['MR_dPdt'] = get_val(["MR dp/dt", "MR dP/dt", "MR dpdt"])
        # ========================================================
        # Doppler tecidual: preencher automaticamente e' e a' a partir do XML (quando disponível)
        # E linha  -> <name>E'</name>
        # A linha  -> (por estratégia do seu fluxo) <name>E' Sept</name>
        # ========================================================
        tdi_e_xml = get_val_by_measname(["E'", "E′"])
        tdi_a_xml = get_val_by_measname(["a'", "a´", "a′", "a’", "E' Sept", "E′ Sept"])

        if tdi_e_xml > 0:
            dados["TDI_e"] = tdi_e_xml
            st.session_state["TDI_e_in"] = tdi_e_xml

        if tdi_a_xml > 0:
            dados["TDI_a"] = tdi_a_xml
            st.session_state["TDI_a_in"] = tdi_a_xml

        # Razão e'/a' (automática)
        try:
            _e = float(dados.get("TDI_e", 0.0) or 0.0)
            _a = float(dados.get("TDI_a", 0.0) or 0.0)
        except Exception:
            _e, _a = 0.0, 0.0

        if _e > 0 and _a > 0:
            dados["TDI_e_a"] = round(_e / _a, 2)
        else:
            dados["TDI_e_a"] = 0.0

        # E/E' (pode vir pronto do equipamento; se não vier, calcula usando Onda E / e')
        ee_xml = get_val_by_measname(["E/E'", "E/E′"])
        if ee_xml > 0:
            dados["EEp"] = round(float(ee_xml), 2)
        else:
            try:
                _mv_e = float(dados.get("MV_E", 0.0) or 0.0)
                _eprime = float(dados.get("TDI_e", 0.0) or 0.0)
            except Exception:
                _mv_e, _eprime = 0.0, 0.0
            dados["EEp"] = round((_mv_e / _eprime), 2) if (_mv_e > 0 and _eprime > 0) else 0.0

        # sincroniza o campo do Streamlit (para refletir no input)
        st.session_state["EEp_in"] = float(dados.get("EEp", 0.0) or 0.0)


    
        
        # Cálculos
        if dados['MV_E'] > 0 and dados['MV_A'] > 0: dados['MV_E_A'] = dados['MV_E'] / dados['MV_A']
        else: dados['MV_E_A'] = 0.0
        if dados['MV_E'] > 0 and dados['IVRT'] > 0: dados['E_IVRT'] = dados['MV_E'] / dados['IVRT']
        else: dados['E_IVRT'] = 0.0
    

        # ✅ Sincroniza os widgets numéricos com o XML importado
        # (evita que valores antigos do session_state sobrescrevam os defaults do XML)
        try:
            for _k in PARAMS.keys():
                st.session_state[f"med_{_k}"] = float(dados.get(_k, 0.0) or 0.0)

            # chaves especiais usadas na UI
            st.session_state["EEp_in"] = float(dados.get("EEp", 0.0) or 0.0)
            st.session_state["TDI_e_in"] = float(dados.get("TDI_e", 0.0) or 0.0)
            st.session_state["TDI_a_in"] = float(dados.get("TDI_a", 0.0) or 0.0)
            st.session_state["TDI_ea_out"] = float(dados.get("TDI_e_a", 0.0) or 0.0)
        except Exception:
            pass

        st.session_state['dados_atuais'] = dados


# Inicializa banco de dados
inicializar_banco()

# Garante tabelas de auth e RBAC para Configurações (evita OperationalError no deploy)
try:
    from auth import inicializar_tabelas_auth, inserir_papeis_padrao
    inicializar_tabelas_auth()
    inserir_papeis_padrao()
except Exception:
    pass
try:
    from rbac import inicializar_tabelas_permissoes, inserir_permissoes_padrao, associar_permissoes_papeis
    inicializar_tabelas_permissoes()
    inserir_permissoes_padrao()
    associar_permissoes_papeis()
except Exception:
    pass

DADOS_DEFAULT = {
    "Ao": 0.0, "LA": 0.0, "LA_Ao": 0.0,
    "IVSd": 0.0, "LVIDd": 0.0, "LVPWd": 0.0,
    "IVSs": 0.0, "LVIDs": 0.0, "LVPWs": 0.0,
    "EDV": 0.0, "ESV": 0.0, "SV": 0.0,
    "EF": 0.0, "FS": 0.0,
    "MAPSE": 0.0,
        "TAPSE": 0.0,
"Vmax_Ao": 0.0, "Grad_Ao": 0.0,
    "Vmax_Pulm": 0.0, "Grad_Pulm": 0.0,
    "MV_E": 0.0, "MV_A": 0.0, "MV_E_A": 0.0,
    "MV_DT": 0.0, "MV_Slope": 0.0,
    "IVRT": 0.0, "E_IVRT": 0.0,
    "TR_Vmax": 0.0,
    "LA_FS": 0.0,
    "AURICULAR_FLOW": 0.0, "MR_Vmax": 0.0,
    "MR_dPdt": 0.0,
    # Doppler tecidual (Tissue Doppler Imaging): valores manuais + razão automática
    "TDI_e": 0.0, "TDI_a": 0.0, "TDI_e_a": 0.0,
    "EEp": 0.0,  # E/E' (relação E/E')
    # Artéria pulmonar / Aorta (AP/Ao)
    "PA_AP": 0.0, "PA_AO": 0.0, "PA_AP_AO": 0.0,
    "Delta_D": 0.0, "DIVEdN": 0.0
}


if "dados_atuais" not in st.session_state:
    st.session_state["dados_atuais"] = DADOS_DEFAULT.copy()



# ===============================
# Espécies (menu flutuante)
# ===============================
if "lista_especies" not in st.session_state:
    st.session_state["lista_especies"] = ["Canina", "Felina"]

# padrão: Canina (você pode mudar quando necessário)
if "cad_especie" not in st.session_state or not str(st.session_state.get("cad_especie") or "").strip():
    st.session_state["cad_especie"] = "Canina"

MARCA_DAGUA_TEMP = "temp_watermark_faded.png"
ARQUIVO_FRASES = str((Path.home() / "FortCordis" / "frases_personalizadas.json"))
Path(ARQUIVO_FRASES).parent.mkdir(parents=True, exist_ok=True)
ARQUIVO_REF = "tabela_referencia.csv"

ARQUIVO_REF_FELINOS = "tabela_referencia_felinos.csv"
import unicodedata
from datetime import datetime, date
from pathlib import Path

# ==========================================================
# 📁 Pasta fixa para arquivar exames (para busca)
# ==========================================================
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
PASTA_LAUDOS.mkdir(parents=True, exist_ok=True)

# Novas pastas para os módulos de gestão
PASTA_PRESCRICOES = Path.home() / "FortCordis" / "Prescricoes"
PASTA_DOCUMENTOS = Path.home() / "FortCordis" / "Documentos"

for pasta in [PASTA_LAUDOS, PASTA_PRESCRICOES, PASTA_DOCUMENTOS]:
    pasta.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CONTROLE DE ACESSO
# ============================================================================

# Se não estiver logado, mostra tela de login (ou cria primeiro usuário e entra)
if not st.session_state.get("autenticado"):
    mostrar_tela_login()
    if not st.session_state.get("autenticado"):
        st.stop()

# Se chegou aqui, está logado!
# Mostra info do usuário na sidebar
mostrar_info_usuario()

# Menu principal já definido no início do script (único radio, evita StreamlitDuplicateElementId)

# ============================================================================
# TELA: DASHBOARD
# ============================================================================

if menu_principal == "🏠 Dashboard":
    st.title("📊 Dashboard - Fort Cordis")
    
    st.markdown("### Resumo do Sistema")
    
    col1, col2, col3, col4 = st.columns(4)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    with col1:
        hoje = datetime.now().strftime("%Y-%m-%d")
        try:
            agends_hoje = listar_agendamentos(data_inicio=hoje, data_fim=hoje)
            total = len([a for a in agends_hoje if (a.get("status") or "") != "Cancelado"])
        except Exception:
            total = 0
        st.metric("Agendamentos Hoje", total)
    
    with col2:
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            agends_amanha = listar_agendamentos(data_inicio=amanha, data_fim=amanha)
            total = len([a for a in agends_amanha if (a.get("status") or "") in ("Agendado", "") or a.get("status") is None])
        except Exception:
            total = 0
        st.metric("Pendentes Confirmação", total)
    
    with col3:
        try:
            a_receber = pd.read_sql_query(
                "SELECT SUM(valor_final) as total FROM financeiro WHERE status_pagamento = 'pendente'",
                conn
            )
            valor = a_receber['total'].iloc[0] if not a_receber.empty and a_receber['total'].iloc[0] else 0
        except:
            valor = 0
        st.metric("Contas a Receber", f"R$ {valor:,.2f}")
    
    with col4:
        try:
            atrasados = pd.read_sql_query(
                "SELECT COUNT(*) as total FROM acompanhamentos WHERE status = 'atrasado'",
                conn
            )
            total = atrasados['total'].iloc[0] if not atrasados.empty else 0
        except:
            total = 0
        st.metric("Retornos Atrasados", total)
    
    conn.close()
    
    st.markdown("---")
    
    st.success("✅ Sistema inicializado com sucesso!")
    
    st.info("""
    ### 🎯 Fluxo integrado:
    
    1. **Agendamentos:** Crie agendamentos; use **"📲 Confirmar amanhã"** para listar os de amanhã e abrir o link WhatsApp da clínica e confirmar 24h antes.
    2. **Laudos:** Em "🩺 Laudos e Exames" emita o laudo; a OS é criada automaticamente em Financeiro.
    3. **Financeiro:** Veja as OS em **"💳 Contas a Receber"**; quando receber o pagamento, use **"✅ Dar baixa"** para marcar como pago (data e forma) e unificar tudo no sistema.
    4. **Cadastros:** Mantenha clínicas com **WhatsApp** preenchido para o link de confirmação funcionar.
    """)

# ============================================================================
# TELA: AGENDAMENTOS
# ============================================================================

elif menu_principal == "📅 Agendamentos":
    st.title("📅 Gestão de Agendamentos")
    
    # Abas do módulo (inclui "Confirmar amanhã" para secretárias confirmarem 24h antes via WhatsApp)
    tab_novo, tab_lista, tab_calendario, tab_confirmar = st.tabs([
        "➕ Novo Agendamento",
        "📋 Lista de Agendamentos",
        "📅 Calendário",
        "📲 Confirmar amanhã (24h)"
    ])
    
    # ========== ABA 1: NOVO AGENDAMENTO ==========
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
            # Busca clínicas cadastradas no MESMO banco de Cadastros > Clínicas Parceiras (DB_PATH)
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
                if not lista_clinicas:
                    lista_clinicas = []
                lista_clinicas.append("📝 Digitar manualmente")
                clinica_agend_sel = st.selectbox(
                    "Clínica",
                    options=lista_clinicas,
                    key="novo_agend_clinica_sel",
                    help="Clínicas cadastradas em Cadastros > Clínicas Parceiras"
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
                    
                    # Limpa os campos
                    for key in ['novo_agend_paciente', 'novo_agend_tutor', 'novo_agend_telefone', 'novo_agend_clinica', 'novo_agend_obs']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar agendamento: {e}")
    
    # ========== ABA 2: LISTA DE AGENDAMENTOS ==========
    with tab_lista:
        st.subheader("Lista de Agendamentos")
        
        # Filtros
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
        
        # Busca agendamentos
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
            
            # Exibe cada agendamento
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
                        status_badge = {
                            "Agendado": "🟢",
                            "Confirmado": "📲",
                            "Realizado": "✅",
                            "Cancelado": "❌"
                        }
                        st.write(f"**Status:** {status_badge.get(agend['status'], '⚪')} {agend['status']}")
                    
                    # Exportar para Google Agenda (.ics)
                    titulo_ics = f"{agend.get('servico', 'Atendimento')} - {agend.get('paciente', '')} ({agend.get('clinica', '')})"
                    desc_ics = f"Paciente: {agend.get('paciente', '')} | Tutor: {agend.get('tutor', '')} | Clínica: {agend.get('clinica', '')}"
                    ics_content = exportar_agendamento_ics(
                        agend.get("data", ""),
                        agend.get("hora", "09:00"),
                        titulo_ics,
                        desc_ics,
                        duracao_minutos=60
                    )
                    st.download_button(
                        "📅 Exportar .ics (Google Agenda)",
                        data=ics_content.encode("utf-8"),
                        file_name=f"agendamento_{agend.get('id', '')}_{agend.get('data', '')}.ics",
                        mime="text/calendar",
                        key=f"ics_agend_{agend['id']}"
                    )
                    
                    # Ações
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    
                    with col_btn1:
                        if agend['status'] == 'Agendado':
                            if st.button("📲 Marcar como confirmado", key=f"confirmado_{agend['id']}", help="Clínica parceira confirmou o agendamento"):
                                now = datetime.now().isoformat(timespec="seconds")
                                atualizar_agendamento(
                                    agend['id'],
                                    status='Confirmado',
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
    
    # ========== ABA 3: CALENDÁRIO (VIEW MENSAL) ==========
    with tab_calendario:
        st.subheader("📅 Visão de Calendário")
        
        # Seletor de mês
        col_mes1, col_mes2 = st.columns([3, 1])
        
        with col_mes1:
            mes_sel = st.date_input("Selecione o mês", value=date.today(), key="calendario_mes")
        
        # Busca agendamentos do mês
        primeiro_dia = date(mes_sel.year, mes_sel.month, 1)
        
        if mes_sel.month == 12:
            ultimo_dia = date(mes_sel.year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(mes_sel.year, mes_sel.month + 1, 1) - timedelta(days=1)
        
        agendamentos_mes = listar_agendamentos(
            data_inicio=str(primeiro_dia),
            data_fim=str(ultimo_dia)
        )
        
        # Agrupa por data
        agendamentos_por_dia = {}
        for agend in agendamentos_mes:
            data = agend['data']
            if data not in agendamentos_por_dia:
                agendamentos_por_dia[data] = []
            agendamentos_por_dia[data].append(agend)
        
        # Estatísticas do mês
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
        
        # Lista por dia
        st.markdown("### Agendamentos do Mês")
        
        if not agendamentos_por_dia:
            st.info("📭 Nenhum agendamento neste mês.")
        else:
            for data in sorted(agendamentos_por_dia.keys()):
                agends_dia = agendamentos_por_dia[data]
                
                # Formata a data
                try:
                    data_obj = datetime.strptime(data, "%Y-%m-%d")
                    data_fmt = data_obj.strftime("%d/%m/%Y - %A")
                except:
                    data_fmt = data
                
                with st.expander(f"📅 {data_fmt} - {len(agends_dia)} agendamento(s)"):
                    for agend in agends_dia:
                        status_icon = {"Agendado": "🟢", "Confirmado": "📲", "Realizado": "✅", "Cancelado": "❌"}
                        st.write(f"{status_icon.get(agend['status'], '⚪')} **{agend['hora']}** - {agend['paciente']} ({agend['servico']})")

    # ========== ABA 4: CONFIRMAR AMANHÃ (24h) – integração WhatsApp ==========
    with tab_confirmar:
        st.subheader("📲 Confirmar agendamentos de amanhã (24h antes)")
        st.caption("Lista de agendamentos para amanhã. Use o link WhatsApp da clínica para confirmar com a parceira.")
        amanha_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        agends_amanha = listar_agendamentos(
            data_inicio=amanha_str,
            data_fim=amanha_str,
            status=None
        )
        agends_amanha = [a for a in agends_amanha if (a.get("status") or "") in ("Agendado", "") or a.get("status") is None]
        if not agends_amanha:
            st.info("📭 Nenhum agendamento para amanhã que precise de confirmação.")
        else:
            # Busca WhatsApp das clínicas cadastradas
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


# ============================================================================
# MÓDULO: PRONTUÁRIO ELETRÔNICO - VERSÃO MELHORADA
# ============================================================================
#
# SUBSTITUA O CÓDIGO ANTERIOR POR ESTE
#
# Melhorias:
# - Cadastro integrado: Tutor → Animal (fluxo direto)
# - Identificação melhor dos tutores (CPF/Telefone visível)
# - Botão "Cadastrar Animal" logo após cadastrar tutor
# - Session state para fluxo contínuo
#
# ============================================================================

elif menu_principal == "📋 Prontuário":
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
                            now = datetime.now().isoformat()
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
                tutores_df['Contato'] = tutores_df['Contato'].fillna('Não informado')
                
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
                                    now = datetime.now().isoformat()
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
        
        conn_list_pac = sqlite3.connect(str(DB_PATH))
        
        try:
            pacientes_df = pd.read_sql_query("""
                SELECT 
                    p.id,
                    p.nome as 'Paciente',
                    p.especie as 'Espécie',
                    p.raca as 'Raça',
                    COALESCE(p.nascimento, '-') as 'Nascimento',
                    t.nome as 'Tutor',
                    t.telefone as 'Contato'
                FROM pacientes p
                JOIN tutores t ON p.tutor_id = t.id
                WHERE (p.ativo = 1 OR p.ativo IS NULL)
                ORDER BY t.nome, p.nome
            """, conn_list_pac)
            
            if not pacientes_df.empty:
                pacientes_df['Raça'] = pacientes_df['Raça'].fillna('SRD')
                pacientes_df['Contato'] = pacientes_df['Contato'].fillna('Não informado')
                
                st.dataframe(pacientes_df.drop('id', axis=1), use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(pacientes_df)} paciente(s)")
            else:
                st.info("Nenhum paciente cadastrado ainda")
        
        except Exception as e:
            st.error(f"Erro ao carregar pacientes: {e}")
        finally:
            conn_list_pac.close()
    
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
            
            conn_cons = sqlite3.connect(str(DB_PATH))
            
            # Busca pacientes com dados do tutor (mesmo banco dos cadastros: /DB/fortcordis.db)
            pacientes_query = """
                SELECT 
                    p.id,
                    p.nome as paciente,
                    p.especie,
                    p.raca,
                    p.nascimento,
                    p.peso_kg,
                    t.id as tutor_id,
                    t.nome as tutor,
                    t.telefone
                FROM pacientes p
                JOIN tutores t ON p.tutor_id = t.id
                WHERE (p.ativo = 1 OR p.ativo IS NULL)
                ORDER BY p.nome
            """
            
            try:
                pacientes_df = pd.read_sql_query(pacientes_query, conn_cons)
            except Exception:
                pacientes_df = pd.DataFrame()
            
            if pacientes_df.empty:
                st.warning("⚠️ Nenhum paciente cadastrado. Cadastre um paciente primeiro!")
                conn_cons.close()
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
                        value=datetime.now().date(),
                        key="cons_data"
                    )
                
                with col_info2:
                    hora_consulta = st.time_input(
                        "Hora",
                        value=datetime.now().time(),
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
                        try:
                            usuario = st.session_state.get("usuario_id")
                            
                            cursor_cons = conn_cons.cursor()
                            
                            cursor_cons.execute("""
                                INSERT INTO consultas (
                                    paciente_id, tutor_id, data_consulta, hora_consulta, tipo_atendimento,
                                    motivo_consulta, anamnese, historico_atual, alimentacao, ambiente, comportamento,
                                    peso_kg, temperatura_c, frequencia_cardiaca, frequencia_respiratoria,
                                    tpc, mucosas, hidratacao, linfonodos, auscultacao_cardiaca, auscultacao_respiratoria,
                                    palpacao_abdominal, exame_fisico_geral,
                                    diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
                                    conduta_terapeutica, exames_solicitados, procedimentos_realizados, orientacoes,
                                    prognostico, data_retorno, observacoes,
                                    veterinario_id, status
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                paciente_id, paciente_dados['tutor_id'], data_consulta, hora_consulta.strftime("%H:%M"),
                                tipo_atendimento, motivo_consulta, anamnese, anamnese, alimentacao, ambiente, comportamento,
                                peso_atual, temperatura, fc, fr,
                                tpc, mucosas, hidratacao, linfonodos, auscultacao_card, auscultacao_resp,
                                palpacao_abd, exame_fisico_geral,
                                diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
                                conduta, exames_solicitados, procedimentos, orientacoes,
                                prognostico, data_retorno, observacoes,
                                usuario["id"], "finalizado"
                            ))
                            
                            consulta_id = cursor_cons.lastrowid
                            
                            # Atualiza peso do paciente (se a coluna existir no banco)
                            try:
                                cursor_cons.execute(
                                    "UPDATE pacientes SET peso_kg = ? WHERE id = ?",
                                    (peso_atual, paciente_id)
                                )
                            except Exception:
                                pass
                            
                            conn_cons.commit()
                            
                            st.success(f"✅ Consulta registrada com sucesso! (ID: {consulta_id})")
                            st.balloons()
                            
                            # Limpa session state
                            if 'paciente_consulta_id' in st.session_state:
                                del st.session_state['paciente_consulta_id']
                            
                            st.info("💡 A consulta foi salva no prontuário do paciente")
                            
                            import time
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao registrar consulta: {e}")
            
            conn_cons.close()
            
            # ====================================================================
            # HISTÓRICO DE CONSULTAS
            # ====================================================================
            
            st.markdown("---")
            st.markdown("### 📋 Consultas Recentes")
            
            conn_hist = sqlite3.connect(str(DB_PATH))
            
            try:
                consultas_df = pd.read_sql_query("""
                    SELECT 
                        c.id,
                        c.data_consulta as 'Data',
                        p.nome as 'Paciente',
                        t.nome as 'Tutor',
                        c.tipo_atendimento as 'Tipo',
                        c.diagnostico_presuntivo as 'Diagnóstico',
                        u.nome as 'Veterinário'
                    FROM consultas c
                    JOIN pacientes p ON c.paciente_id = p.id
                    JOIN tutores t ON c.tutor_id = t.id
                    JOIN usuarios u ON c.veterinario_id = u.id
                    ORDER BY c.data_consulta DESC, c.id DESC
                    LIMIT 10
                """, conn_hist)
                
                if not consultas_df.empty:
                    # Formata dados
                    consultas_df['Paciente'] = consultas_df['Paciente'].str.title()
                    consultas_df['Tutor'] = consultas_df['Tutor'].str.title()
                    
                    st.dataframe(
                        consultas_df.drop('id', axis=1),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.caption(f"Mostrando as {len(consultas_df)} consultas mais recentes")
                else:
                    st.info("📋 Nenhuma consulta registrada ainda")
            
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar histórico: {e}")
            finally:
                conn_hist.close()

# ============================================================================
# TELA: LAUDOS E EXAMES (AQUI VIRÁ TODO O SEU CÓDIGO)
# ============================================================================

    # ============================================================================
    # FUNÇÕES DE GERENCIAMENTO DE LAUDOS NO BANCO
    # ============================================================================

    import json
    from datetime import datetime

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
                dados_laudo.get('data', datetime.now().strftime('%Y-%m-%d')),
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
elif menu_principal == "🩺 Laudos e Exames":
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
        st.header("🔎 Buscar exames arquivados")
        st.caption("Busque por tutor, clínica ou pet. Exames importados do backup aparecem na seção «Exames no banco».")

        # ---------- Exames no banco (importados) — visíveis após restaurar backup ----------
        st.subheader("📂 Exames no banco (importados)")
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
                    bg = MARCA_DAGUA_TEMP if os.path.exists(MARCA_DAGUA_TEMP) else ("logo.png" if os.path.exists("logo.png") else None)
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
                bg = MARCA_DAGUA_TEMP if os.path.exists(MARCA_DAGUA_TEMP) else ("logo.png" if os.path.exists("logo.png") else None)
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

elif menu_principal == "💊 Prescrições":
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
        except:
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
        except:
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
                        except:
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
            # Busca pacientes no banco
            conn_busca = sqlite3.connect(str(DB_PATH))
            try:
                query_pac = """
                    SELECT p.id, p.nome as paciente, p.especie, p.raca, p.sexo, p.nascimento,
                           t.nome as tutor, t.telefone
                    FROM pacientes p
                    LEFT JOIN tutores t ON p.tutor_id = t.id
                    WHERE 1=1
                """
                params_pac = []

                if busca_nome_pac:
                    query_pac += " AND UPPER(p.nome) LIKE UPPER(?)"
                    params_pac.append(f"%{busca_nome_pac}%")

                if busca_nome_tut:
                    query_pac += " AND UPPER(t.nome) LIKE UPPER(?)"
                    params_pac.append(f"%{busca_nome_tut}%")

                query_pac += " ORDER BY p.nome LIMIT 20"

                pacientes_encontrados = pd.read_sql_query(query_pac, conn_busca, params=params_pac)
            except Exception as e:
                pacientes_encontrados = pd.DataFrame()
                st.warning(f"Erro na busca: {e}")
            conn_busca.close()

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
        except:
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
        except:
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
                with st.expander(f"📄 {presc['paciente_nome']} - {presc['data_prescricao']}", expanded=False):
                    col_h1, col_h2 = st.columns(2)

                    with col_h1:
                        st.markdown(f"**Paciente:** {presc['paciente_nome']}")
                        st.markdown(f"**Tutor:** {presc['tutor_nome']}")
                        st.markdown(f"**Espécie:** {presc['especie']}")
                        st.markdown(f"**Peso:** {presc['peso_kg']} kg")

                    with col_h2:
                        st.markdown(f"**Data:** {presc['data_prescricao']}")
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

elif menu_principal == "💰 Financeiro":
    st.title("💰 Gestão Financeira")
    
    if not verificar_permissao("financeiro", "ver"):
        st.error("❌ Acesso Negado")
        st.warning("⚠️ Você não tem permissão para acessar o módulo financeiro")
        st.info("💡 Contate o administrador se precisar de acesso")
        st.stop()

    garantir_colunas_financeiro()

    tab_fin_lista, tab_fin_baixa = st.tabs(["💳 Contas a Receber", "✅ Dar baixa (pagamento recebido)"])

    with tab_fin_lista:
        st.markdown("### Todas as OS (últimas 20)")
        conn = sqlite3.connect(str(DB_PATH))
        contas = None
        try:
            contas = pd.read_sql_query("""
                SELECT 
                    f.id, f.numero_os as 'Número OS',
                    c.nome as 'Clínica',
                    f.descricao as 'Descrição',
                    f.valor_final as 'Valor',
                    f.status_pagamento as 'Status',
                    f.data_competencia as 'Data',
                    f.data_pagamento as 'Data pagamento',
                    f.forma_pagamento as 'Forma'
                FROM financeiro f
                LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                ORDER BY f.data_competencia DESC
                LIMIT 20
            """, conn)
            if not contas.empty:
                contas_display = contas.drop(columns=["id"], errors="ignore")
                contas_display["Valor"] = contas_display["Valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                st.dataframe(contas_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma OS gerada ainda. Faça um laudo para gerar a primeira!")
        except sqlite3.OperationalError:
            try:
                contas = pd.read_sql_query("""
                    SELECT f.id, f.id as 'Número OS', c.nome as 'Clínica', f.descricao as 'Descrição',
                           f.valor_final as 'Valor', f.status_pagamento as 'Status',
                           f.data_competencia as 'Data'
                    FROM financeiro f
                    LEFT JOIN clinicas_parceiras c ON f.clinica_id = c.id
                    ORDER BY f.id DESC LIMIT 20
                """, conn)
                if not contas.empty:
                    contas_display = contas.drop(columns=["id"], errors="ignore")
                    if "Valor" in contas_display.columns:
                        contas_display["Valor"] = contas_display["Valor"].apply(lambda x: f"R$ {float(x):,.2f}" if x is not None else "—")
                    st.dataframe(contas_display, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma OS gerada ainda. Faça um laudo para gerar a primeira!")
            except Exception:
                st.info("Nenhuma OS gerada ainda.")
        except Exception:
            st.info("Nenhuma OS gerada ainda.")
        conn.close()

        # Excluir ordem de serviço (ex.: testes ou cobranças indevidas)
        if contas is not None and not contas.empty:
            st.markdown("---")
            st.markdown("### 🗑️ Excluir ordem de serviço")
            st.caption("Use para remover OS de teste ou cobranças que não devem permanecer. A exclusão é definitiva.")
            opcoes_os = []
            for _, row in contas.iterrows():
                num_os = row.get("Número OS", row.get("id", ""))
                clinica = row.get("Clínica", "") or "—"
                valor = float(row.get("Valor", 0) or 0)
                opcoes_os.append((int(row["id"]), f"{num_os} – {clinica} – R$ {valor:,.2f}"))
            if opcoes_os:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    os_para_excluir = st.selectbox(
                        "Selecione a OS a excluir",
                        options=[x[0] for x in opcoes_os],
                        format_func=lambda x: next(n for i, n in opcoes_os if i == x),
                        key="excluir_os_sel"
                    )
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Excluir OS", key="btn_excluir_os", type="secondary"):
                        if excluir_os(os_para_excluir):
                            st.success("OS excluída.")
                            st.rerun()
                        else:
                            st.error("Não foi possível excluir.")

    with tab_fin_baixa:
        st.markdown("### Cobranças pendentes – dar baixa quando o pagamento for recebido")
        st.caption("Marque como pago e informe a data e a forma de pagamento. Assim você unifica tudo no sistema e dispensa a planilha.")
        pendentes = listar_financeiro_pendentes()
        if not pendentes:
            st.success("✅ Nenhuma cobrança pendente.")
        else:
            total_pend = sum(float(p.get("valor_final") or 0) for p in pendentes)
            st.metric("Total a receber (pendentes)", f"R$ {total_pend:,.2f}")
            st.markdown("---")
            for p in pendentes:
                with st.expander(f"📄 {p.get('numero_os', '')} – {p.get('clinica_nome', 'Clínica')} – R$ {float(p.get('valor_final') or 0):,.2f}"):
                    st.write(f"**Descrição:** {p.get('descricao', '')}")
                    st.write(f"**Data competência:** {p.get('data_competencia', '')}")
                    with st.form(key=f"form_baixa_{p.get('id')}"):
                        data_pag = st.date_input("Data do pagamento", value=date.today(), key=f"data_pag_{p.get('id')}")
                        forma_pag = st.selectbox(
                            "Forma de pagamento",
                            ["PIX", "Transferência", "Dinheiro", "Cartão (crédito)", "Cartão (débito)", "Outro"],
                            key=f"forma_pag_{p.get('id')}"
                        )
                        if st.form_submit_button("✅ Dar baixa (marcar como pago)"):
                            ok = dar_baixa_os(
                                p["id"],
                                data_pagamento=data_pag.strftime("%Y-%m-%d"),
                                forma_pagamento=forma_pag
                            )
                            if ok:
                                st.success("Baixa registrada!")
                                st.rerun()
                            else:
                                st.warning("Não foi possível dar baixa (talvez já esteja paga).")


# ============================================================================
# TELA: CADASTROS
# ============================================================================

elif menu_principal == "🏢 Cadastros":
    st.title("🏢 Cadastros")
    
    tab_c1, tab_c2 = st.tabs(["🏥 Clínicas Parceiras", "🛠️ Serviços"])
    
    with tab_c1:
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
            
            if not clinicas.empty:
                st.dataframe(clinicas.drop('id', axis=1), use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(clinicas)} clínica(s)")
                
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
                                
                                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                                    try:
                                        if nome_by_id:
                                            cursor.execute("""
                                                UPDATE clinicas_parceiras 
                                                SET nome = ?, endereco = ?, cidade = ?, telefone = ?,
                                                    whatsapp = ?, cnpj = ?, responsavel_veterinario = ?,
                                                    crmv_responsavel = ?, tabela_preco_id = ?
                                                WHERE id = ?
                                            """, (edit_nome, edit_end, edit_cidade, edit_tel, edit_whats,
                                                edit_cnpj, edit_resp, edit_crmv, edit_tabela_id, clinica_id))
                                        else:
                                            cursor.execute("""
                                                UPDATE clinicas_parceiras 
                                                SET nome = ?, endereco = ?, cidade = ?, telefone = ?,
                                                    whatsapp = ?, cnpj = ?, responsavel_veterinario = ?,
                                                    crmv_responsavel = ?
                                                WHERE id = ?
                                            """, (edit_nome, edit_end, edit_cidade, edit_tel, edit_whats,
                                                edit_cnpj, edit_resp, edit_crmv, clinica_id))
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

        except:
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
                    valor_base as 'Valor Base',
                    duracao_minutos as 'Duração (min)'
                FROM servicos
                WHERE (ativo = 1 OR ativo IS NULL)
                ORDER BY nome
            """, conn)
            
            if not servicos.empty:
                servicos_display = servicos.copy()
                servicos_display['Valor Base'] = servicos_display['Valor Base'].apply(lambda x: f"R$ {float(x):,.2f}")
                st.dataframe(servicos_display, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Execute o script inicializar_dados.py ou reinicie o app para popular os serviços")
            
            # Tabelas de preço (valores por serviço por tabela) — com edição direta
            st.markdown("---")
            st.markdown("### 📋 Valores por Tabela de Preço")
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
                        # Serviços que ainda não estão nesta tabela (para incluir)
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
                        # Incluir serviço nesta tabela
                        st.markdown("**➕ Incluir serviço**")
                        col_add1, col_add2, col_add3 = st.columns([2, 1, 1])
                        with col_add1:
                            opcoes_add = [(0, "— Selecione um serviço —")] + [(int(r['id']), r['nome']) for _, r in df_resto.iterrows()]
                            servico_add_id = st.selectbox(
                                "Serviço a incluir",
                                options=[x[0] for x in opcoes_add],
                                format_func=lambda x: next(n for i, n in opcoes_add if i == x),
                                key=f"add_servico_t{tb_id}"
                            )
                        with col_add2:
                            valor_add = st.number_input("Valor (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key=f"add_valor_t{tb_id}")
                        with col_add3:
                            st.write("")
                            st.write("")
                            if st.button("Incluir", key=f"btn_incluir_t{tb_id}", type="primary"):
                                if servico_add_id and servico_add_id != 0:
                                    try:
                                        cur_add = conn.cursor()
                                        cur_add.execute(
                                            "INSERT INTO servico_preco (servico_id, tabela_preco_id, valor) VALUES (?, ?, ?)",
                                            (servico_add_id, tb_id, valor_add)
                                        )
                                        conn.commit()
                                        st.success(f"Serviço incluído na tabela.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao incluir: {e}")
                                else:
                                    st.warning("Selecione um serviço.")
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


# ============================================================================
# TELA: CONFIGURAÇÕES
# ============================================================================

elif menu_principal == "⚙️ Configurações":
        
        # Verifica se pode acessar configurações
        if not verificar_permissao("configuracoes", "ver"):
            st.error("❌ Acesso Negado")
            st.warning("⚠️ Apenas administradores podem acessar as configurações do sistema")
            st.info("💡 Se você precisa de acesso, contate o administrador")
            st.stop()
        
        st.title("⚙️ Configurações do Sistema")
        # Cria abas
        tab_permissoes, tab_usuarios, tab_papeis, tab_sistema, tab_importar, tab_assinatura = st.tabs([
            "🔐 Minhas Permissões",
            "👥 Usuários do Sistema",
            "🎭 Papéis e Permissões",
            "⚙️ Configurações Gerais",
            "📥 Importar dados",
            "🖊️ Assinatura/Carimbo"
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
                from rbac import obter_permissoes_usuario
                
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
                        from rbac import obter_permissoes_usuario
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
                        from rbac import obter_permissoes_usuario
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
                                    from auth import hash_senha
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
                            from auth import criar_usuario
                            
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
                                from auth import atualizar_senha
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
                "exportar_backup.py e envie o arquivo .db aqui para restaurar clínicas, tutores, pacientes e laudos."
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
                    erros_import = []
                    try:
                        bytes_backup = arquivo_backup.read()
                        if not bytes_backup:
                            st.error("O arquivo está vazio. Gere o backup novamente com exportar_backup.py.")
                        else:
                            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                                tmp.write(bytes_backup)
                                tmp_path = tmp.name
                        try:
                            conn_backup = sqlite3.connect(tmp_path)
                            conn_backup.row_factory = sqlite3.Row
                            cur_b = conn_backup.cursor()
                            # Pré-visualizar conteúdo do backup
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
                            st.info(f"📂 Conteúdo do backup: {n_c_b} clínicas, {n_t_b} tutores, {n_p_b} pacientes, {n_l_b} laudos, {n_cp_b} clínicas parceiras.")
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
                            total_c, total_t, total_p, total_l, total_cp = 0, 0, 0, 0, 0
                            reused_c, reused_t = 0, 0
                            # 1) Clinicas (tabela simples) — evita duplicata por nome_key; SELECT só colunas que existem no backup
                            try:
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
                            for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
                                try:
                                    cur_l.execute(f"PRAGMA table_info({tabela})")
                                    colunas_destino = [c[1] for c in cur_l.fetchall()]
                                    cur_b.execute(f"SELECT * FROM {tabela}")
                                    rows_laudo = cur_b.fetchall()
                                    if not rows_laudo:
                                        continue
                                    cur_b.execute(f"PRAGMA table_info({tabela})")
                                    colunas_laudo = [c[1] for c in cur_b.fetchall()]
                                    colunas_sem_id = [c for c in colunas_laudo if c != "id" and c in colunas_destino]
                                    # Incluir nome_paciente, nome_clinica, nome_tutor do destino para preencher no INSERT (backup pode não ter essas colunas)
                                    for col_extra in ("nome_paciente", "nome_clinica", "nome_tutor"):
                                        if col_extra in colunas_destino and col_extra not in colunas_sem_id:
                                            colunas_sem_id.append(col_extra)
                                    if not colunas_sem_id:
                                        continue
                                    for row in rows_laudo:
                                        row_d = dict(zip(colunas_laudo, row))
                                        old_paciente_id = int(row_d["paciente_id"]) if row_d.get("paciente_id") else None
                                        novo_paciente_id = map_paciente.get(old_paciente_id) if old_paciente_id is not None else None
                                        old_clinica_id = int(row_d["clinica_id"]) if row_d.get("clinica_id") else None
                                        # Tentar clinicas_parceiras primeiro (laudos costumam apontar para elas)
                                        novo_clinica_id = (map_clinica_parceiras.get(old_clinica_id) or map_clinica.get(old_clinica_id)) if old_clinica_id is not None else None
                                        row_d["paciente_id"] = novo_paciente_id
                                        row_d["clinica_id"] = novo_clinica_id
                                        # Preencher nomes a partir do backup para clínica/animal/tutor aparecerem na tabela
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
                            conn_local.commit()
                            conn_backup.close()
                            conn_local.close()
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                            msg_c = f"{total_c + reused_c} clínicas ({total_c} novas, {reused_c} já existentes)" if (total_c or reused_c) else "0 clínicas"
                            msg_t = f"{total_t + reused_t} tutores ({total_t} novos, {reused_t} já existentes)" if (total_t or reused_t) else "0 tutores"
                            st.success(
                                f"✅ Importação concluída: {msg_c}, {msg_t}, {total_p} pacientes, "
                                f"{total_l} laudos, {total_cp} clínicas parceiras."
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
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                    except Exception as e:
                        st.error(f"Erro ao processar arquivo: {e}")

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
                    st.image(assin_atual, use_container_width=True, width=200)
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

QUALI_DET = {
    "valvas": ["mitral", "tricuspide", "aortica", "pulmonar"],
    "camaras": ["ae", "ad", "ve", "vd"],
    "vasos": ["aorta", "art_pulmonar", "veias_pulmonares", "cava_hepaticas"],
    "funcao": ["sistolica_ve", "sistolica_vd", "diastolica", "sincronia"],
    "pericardio": ["efusao", "espessamento", "tamponamento"],
}

ROTULOS = {
    "mitral":"Mitral", "tricuspide":"Tricúspide", "aortica":"Aórtica", "pulmonar":"Pulmonar",
    "ae":"Átrio esquerdo", "ad":"Átrio direito", "ve":"Ventrículo esquerdo", "vd":"Ventrículo direito",
    "aorta":"Aorta", "art_pulmonar":"Artéria pulmonar", "veias_pulmonares":"Veias pulmonares", "cava_hepaticas":"Cava/Hepáticas",
    "sistolica_ve":"Sistólica VE", "sistolica_vd":"Sistólica VD", "diastolica":"Diastólica", "sincronia":"Sincronia",
    "efusao":"Efusão", "espessamento":"Espessamento", "tamponamento":"Sinais de tamponamento",
}

def frase_det(
    *,
    valvas=None, camaras=None, vasos=None, funcao=None, pericardio=None,
    resumo=None, ad_vd="", conclusao=""
):
    """
    Cria uma entrada de frase compatível com:
    - campos antigos: valvas/camaras/vasos/funcao/pericardio/ad_vd/conclusao
    - e com subcampos novos: q_valvas_mitral, q_camaras_ae, etc.
    """
    valvas = valvas or {}
    camaras = camaras or {}
    vasos = vasos or {}
    funcao = funcao or {}
    pericardio = pericardio or {}
    resumo = resumo or {}

    entry = {"layout": "detalhado",
        "valvas": resumo.get("valvas", ""),
        "camaras": resumo.get("camaras", ""),
        "vasos": resumo.get("vasos", ""),
        "funcao": resumo.get("funcao", ""),
        "pericardio": resumo.get("pericardio", ""),
        "ad_vd": ad_vd or "",
        "conclusao": conclusao or "",
        "det": {  # opcional, mas útil
            "valvas": {k: "" for k in QUALI_DET["valvas"]},
            "camaras": {k: "" for k in QUALI_DET["camaras"]},
            "vasos": {k: "" for k in QUALI_DET["vasos"]},
            "funcao": {k: "" for k in QUALI_DET["funcao"]},
            "pericardio": {k: "" for k in QUALI_DET["pericardio"]},
        }
    }

    # preenche o det
    for k, v in valvas.items(): entry["det"]["valvas"][k] = v
    for k, v in camaras.items(): entry["det"]["camaras"][k] = v
    for k, v in vasos.items(): entry["det"]["vasos"][k] = v
    for k, v in funcao.items(): entry["det"]["funcao"][k] = v
    for k, v in pericardio.items(): entry["det"]["pericardio"][k] = v

    # cria também as chaves planas q_... (que o Streamlit usa direto nos text_area)
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (entry["det"][sec].get(it, "") or "")

    return entry


def aplicar_frase_det_na_tela(frase: dict):
    """Joga os subcampos q_... da frase para o session_state (preenche a aba Qualitativa)."""
    if not isinstance(frase, dict):
        return

    # 1) tenta via det
    det = frase.get("det") if isinstance(frase.get("det"), dict) else {}

    for sec, itens in QUALI_DET.items():
        for it in itens:
            k = f"q_{sec}_{it}"
            val = ""

            if det and isinstance(det.get(sec), dict) and (it in det[sec]):
                val = det[sec].get(it, "") or ""
            elif k in frase:
                val = frase.get(k, "") or ""

            st.session_state[k] = val


def garantir_schema_det_frase(entry: dict) -> dict:
    """Garante que entry tenha o formato com 'det' (detalhado) completo."""
    if "det" not in entry or not isinstance(entry["det"], dict):
        entry["det"] = {}

    for sec, itens in QUALI_DET.items():
        if sec not in entry["det"] or not isinstance(entry["det"][sec], dict):
            entry["det"][sec] = {}
        for it in itens:
            entry["det"][sec].setdefault(it, "")

    # mantém também os campos antigos (compatibilidade)
    for c in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
        entry.setdefault(c, "")

    # ✅ NOVO: layout da patologia
    # valores recomendados: "enxuto" | "detalhado"
    entry.setdefault("layout", "detalhado")

    return entry


def migrar_txt_para_det(entry: dict) -> dict:
    """
    Se a frase veio do modelo antigo (valvas/camaras/vasos/funcao/pericardio)
    e o 'det' estiver vazio, joga esse texto para subcampos padrão do 'det'
    para aparecer no Editor de Frases.
    """
    entry = garantir_schema_det_frase(entry)
    det = entry.get("det", {})

    def bloco_vazio(sec: str) -> bool:
        return not any((det.get(sec, {}).get(it, "") or "").strip() for it in QUALI_DET[sec])

    # Valvas -> joga no principal (Mitral)
    if bloco_vazio("valvas"):
        txt = (entry.get("valvas", "") or "").strip()
        if txt:
            det["valvas"]["mitral"] = txt

    # Câmaras -> joga em AE e VE
    if bloco_vazio("camaras"):
        txt = (entry.get("camaras", "") or "").strip()
        if txt:
            det["camaras"]["ae"] = txt
            det["camaras"]["ve"] = txt

    # Vasos -> joga em Aorta
    if bloco_vazio("vasos"):
        txt = (entry.get("vasos", "") or "").strip()
        if txt:
            det["vasos"]["aorta"] = txt

    # Função -> joga em Sistólica VE
    if bloco_vazio("funcao"):
        txt = (entry.get("funcao", "") or "").strip()
        if txt:
            det["funcao"]["sistolica_ve"] = txt

    # Pericárdio -> joga em Efusão
    if bloco_vazio("pericardio"):
        txt = (entry.get("pericardio", "") or "").strip()
        if txt:
            det["pericardio"]["efusao"] = txt

    entry["det"] = det

    # Mantém também as chaves planas q_... coerentes (se você usar em algum lugar)
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (det.get(sec, {}).get(it, "") or "")

    return entry


def det_para_txt(det: dict) -> dict:
    """Converte det{sec:{it:txt}} em txt_{sec} (com linhas 'Rótulo: texto')."""
    out = {}
    for sec, itens in QUALI_DET.items():
        linhas = []
        bloco = det.get(sec, {}) if isinstance(det, dict) else {}
        for it in itens:
            v = (bloco.get(it, "") or "").strip()
            if v:
                linhas.append(f"{ROTULOS[it]}: {v}")
        out[sec] = "\n".join(linhas).strip()
    return out


def aplicar_det_nos_subcampos(chave_frase: str, sobrescrever=False):
    """Aplica db_frases[chave]['det'] nos st.session_state['q_...']."""
    db = st.session_state.get("db_frases", {})
    entry = db.get(chave_frase)
    if not entry:
        return False

    entry = garantir_schema_det_frase(entry)
    det = entry.get("det", {})

    for sec, itens in QUALI_DET.items():
        for it in itens:
            k = f"q_{sec}_{it}"
            novo = (det.get(sec, {}).get(it, "") or "").strip()
            if not novo:
                continue
            atual = (st.session_state.get(k, "") or "").strip()
            if sobrescrever or not atual:
                st.session_state[k] = novo

    # opcional: manter txt_* coerente com det (ótimo para PDF e fallback)
    txts = det_para_txt(det)
    for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos"]:
        if txts.get(sec):
            st.session_state[f"txt_{sec}"] = txts[sec]

    return True


# inicializa subcampos
for sec, itens in QUALI_DET.items():
    for it in itens:
        k = f"q_{sec}_{it}"
        if k not in st.session_state:
            st.session_state[k] = ""

import re
import streamlit as st

def complementar_regurgitacao_valvar(valva: str, grau: str):
    """
    Injeta/atualiza "Refluxo <valva> <grau>." em:
      - q_valvas_<valva>
      - txt_valvas

    Regra: remove qualquer linha que comece com "Refluxo <valva>" antes de inserir,
    evitando duplicar com textos do Doppler (Vmax...) ou do banco.
    """
    if not valva or not grau:
        return

    valva = str(valva).strip().lower()
    grau_in = str(grau).strip().lower()

    mapa_grau = {
        "leve": "leve",
        "moderada": "moderado",
        "moderado": "moderado",
        "importante": "importante",
        "grave": "grave",
        "severa": "grave",
        "severo": "grave",
        "significativa": "importante",
        "significativo": "importante",
    }
    grau = mapa_grau.get(grau_in, grau_in)

    nomes = {
        "mitral": "mitral",
        "tricuspide": "tricúspide",
        "aortica": "aórtico",
        "pulmonar": "pulmonar",
    }
    if valva not in nomes:
        return

    nome_valva = nomes[valva]
    frase = f"Refluxo {nome_valva} {grau}."

    # remove qualquer linha que comece com "Refluxo <valva>"
    pattern_linha = re.compile(rf"^\s*refluxo\s+{re.escape(nome_valva)}\b.*$", re.IGNORECASE)

    def upsert(key: str):
        atual = (st.session_state.get(key, "") or "").strip()
        linhas = [l for l in atual.splitlines() if not pattern_linha.match(l.strip())]
        # adiciona a frase padronizada
        linhas.append(frase)
        st.session_state[key] = "\n".join([l for l in linhas if l.strip()]).strip()

    upsert(f"q_valvas_{valva}")  # subcampo detalhado
    upsert("txt_valvas")         # texto corrido


def montar_qualitativa():
    """Monta valvas/camaras/vasos/funcao/pericardio.
    Se os subcampos (q_...) estiverem vazios, usa fallback nos txt_* (frases antigas).
    """
    saida = {}
    for sec, itens in QUALI_DET.items():
        linhas = []
        for it in itens:
            val = (st.session_state.get(f"q_{sec}_{it}", "") or "").strip()
            if val:
                linhas.append(f"- {ROTULOS[it]}: {val}")

        bloco = "\n".join(linhas).strip()

        # fallback: se não preencheu os subcampos, usa o texto antigo
        if not bloco:
            bloco = (st.session_state.get(f"txt_{sec}", "") or "").strip()

        saida[sec] = bloco

    return saida


for k in keys_texto:
    if k not in st.session_state: st.session_state[k] = ""

# Banco de Frases (Mantido)
FRASES_DEFAULT = {
    "Normal (Normal)": {"layout": "enxuto", "valvas": "Valvas atrioventriculares e semilunares com morfologia, espessura e mobilidade preservadas. Ausência de refluxos valvulares significativos.", "camaras": "Dimensões cavitárias preservadas. Espessura parietal diastólica preservada.", "funcao": "Função sistólica e diastólica dos ventrículos preservada.", "pericardio": "Pericárdio com aspecto ecocardiográfico normal. Ausência de efusão.", "vasos": "Grandes vasos da base com diâmetros e relações anatômicas preservadas.", "ad_vd": "Átrio direito e Ventrículo direito com dimensões e contratilidade preservadas.", "conclusao": "Exame ecocardiográfico dentro dos padrões de normalidade."},
    "Endocardiose Mitral (Leve)": {"valvas": "Valva mitral com espessamento nodular (degeneração mixomatosa inicial). Refluxo mitral leve.", "camaras": "Dimensões de câmaras esquerdas preservadas.", "funcao": "Função sistólica preservada.", "pericardio": "Normal.", "vasos": "Normais.", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Estágio B1."},
    "Endocardiose Mitral (Moderada)": {"valvas": "Valva mitral espessada. Refluxo moderado.", "camaras": "Aumento moderado de AE e VE.", "funcao": "Preservada.", "pericardio": "Normal.", "vasos": "Relação AE/Ao aumentada.", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Estágio B2."},
    "Endocardiose Mitral (Importante)": {"valvas": "Espessamento importante. Refluxo significativo.", "camaras": "Dilatação importante AE/VE.", "funcao": "Preservada.", "pericardio": "Normal.", "vasos": "Congestão venosa?", "ad_vd": "Normais.", "conclusao": "Endocardiose Mitral Importante."}
}
FRASES_DEFAULT.update({

    # =========================================================
    # ESTENOSE AÓRTICA
    # =========================================================
    "Estenose Aórtica (Leve)": frase_det(
        valvas={
            "aortica": "Valva aórtica com alterações compatíveis com estenose leve. Fluxo turbulento discreto em via de saída do ventrículo esquerdo.",
            "mitral": "Valva mitral com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
            "tricuspide": "Valva tricúspide com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
            "pulmonar": "Valva pulmonar com morfologia e mobilidade preservadas. Ausência de refluxo significativo.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas. Espessuras parietais preservadas ou discretamente aumentadas (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões e contratilidade preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Pode haver discreta dilatação pós-estenótica da aorta ascendente, a depender do caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada (por vezes discretamente hiperdinâmica).",
            "diastolica": "Função diastólica sem alterações significativas; avaliar padrão de relaxamento conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica leve.",
            "camaras": "Sem remodelamento significativo ou com hipertrofia concêntrica discreta de ventrículo esquerdo.",
            "vasos": "Aorta com aspecto preservado; possível discreta dilatação pós-estenótica.",
            "funcao": "Função sistólica global preservada.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Moderada)": frase_det(
        valvas={
            "aortica": "Valva aórtica com estenose moderada, com fluxo turbulento e aumento de velocidade ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente com dimensões preservadas; avaliar discreto aumento secundário a alteração de relaxamento, quando presente.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica discreta a moderada, com aumento de espessura de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Possível dilatação pós-estenótica da aorta ascendente, a depender do caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo geralmente preservada; pode estar discretamente hiperdinâmica.",
            "diastolica": "Possível padrão de relaxamento alterado associado à hipertrofia (disfunção diastólica grau I (alteração do relaxamento)), conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica moderada.",
            "camaras": "Hipertrofia concêntrica de ventrículo esquerdo (PLVE e SIV).",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Função sistólica global preservada; avaliar diástole.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Importante)": frase_det(
        valvas={
            "aortica": "Estenose aórtica importante, com turbulência acentuada e aumento expressivo de velocidades ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada ou com refluxo discreto secundário, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente preservado; pode haver discreto aumento secundário, conforme alterações de enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica moderada a importante, com aumento de espessura de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo frequentemente preservada; avaliar sinais de repercussão funcional conforme caso.",
            "diastolica": "Padrão de relaxamento frequentemente alterado em função da hipertrofia; avaliar disfunção diastólica ao Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica importante.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão diastólica e sistólica.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),

    "Estenose Aórtica (Grave)": frase_det(
        valvas={
            "aortica": "Estenose aórtica grave, com turbulência severa e velocidades muito elevadas ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo secundário discreto, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo pode estar preservado ou discretamente aumentado, conforme repercussões de enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica importante. Avaliar espessuras de PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular), além de eventuais sinais de repercussão hemodinâmica.",
            "ad": "Átrio direito geralmente preservado.",
            "vd": "Ventrículo direito geralmente preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar sinais de congestão conforme hemodinâmica e Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Avaliar cuidadosamente função sistólica do ventrículo esquerdo, pois pode haver repercussão funcional em casos graves.",
            "diastolica": "Avaliar diástole ao Doppler (alterações de relaxamento e aumento de pressões de enchimento podem ocorrer).",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Aórtica grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose aórtica grave.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão sistólica/diastólica.",
            "pericardio": "Sem efusão pericárdica.",
        }
    ),


    # =========================================================
    # ESTENOSE SUBAÓRTICA
    # =========================================================
    "Estenose Subaórtica (Leve)": frase_det(
        valvas={
            "aortica": "Valva aórtica com morfologia preservada ou alterações discretas. Fluxo turbulento discreto em via de saída do ventrículo esquerdo, compatível com estenose subaórtica leve.",
            "mitral": "Valva mitral com morfologia preservada. Ausência de refluxo significativo.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Ausência de refluxo significativo.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas. Espessuras parietais preservadas ou discretamente aumentadas, conforme medidas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional. Avaliar dilatação pós-estenótica da aorta ascendente conforme o caso.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações significativas; avaliar relaxamento conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica leve.",
            "camaras": "Sem remodelamento significativo.",
            "vasos": "Aorta preservada; avaliar dilatação pós-estenótica.",
            "funcao": "Função sistólica preservada.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Moderada)": frase_det(
        valvas={
            "aortica": "Valva aórtica com morfologia preservada ou alterações discretas. Turbulência e aumento de velocidade em via de saída do ventrículo esquerdo, compatível com estenose subaórtica moderada.",
            "mitral": "Valva mitral com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente com dimensões preservadas.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica discreta a moderada (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares sem sinais indiretos de congestão ao Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo geralmente preservada; pode estar discretamente hiperdinâmica.",
            "diastolica": "Possível alteração de relaxamento associada à hipertrofia (disfunção diastólica grau I (alteração do relaxamento)), conforme Doppler.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica moderada.",
            "camaras": "Hipertrofia concêntrica de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Função sistólica preservada; avaliar diástole.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Importante)": frase_det(
        valvas={
            "aortica": "Turbulência acentuada e velocidades elevadas em via de saída do ventrículo esquerdo, compatível com estenose subaórtica importante.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo discreto secundário, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo geralmente preservado; pode haver discreto aumento secundário conforme enchimento.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica moderada a importante (avaliar PLVE (parede livre do ventrículo esquerdo) e SIV (septo interventricular) conforme medidas).",
            "ad": "Átrio direito preservado.",
            "vd": "Ventrículo direito preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar sinais indiretos de congestão conforme Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo frequentemente preservada; avaliar repercussão funcional conforme caso.",
            "diastolica": "Alterações de relaxamento são frequentes em presença de hipertrofia; avaliar Doppler diastólico.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica importante.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão diastólica/sistólica.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Subaórtica (Grave)": frase_det(
        valvas={
            "aortica": "Turbulência severa e velocidades muito elevadas em via de saída do ventrículo esquerdo, compatível com estenose subaórtica grave.",
            "mitral": "Valva mitral com morfologia preservada ou refluxo secundário discreto, conforme remodelamento.",
            "tricuspide": "Valva tricúspide com morfologia preservada.",
            "pulmonar": "Valva pulmonar com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo pode estar preservado ou discretamente aumentado.",
            "ve": "Ventrículo esquerdo: hipertrofia concêntrica importante; avaliar repercussões hemodinâmicas conforme demais parâmetros.",
            "ad": "Átrio direito geralmente preservado.",
            "vd": "Ventrículo direito geralmente preservado.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado. Dilatação pós-estenótica da aorta ascendente pode estar presente.",
            "art_pulmonar": "Artéria pulmonar com diâmetro preservado.",
            "veias_pulmonares": "Veias pulmonares: avaliar congestão conforme hemodinâmica e Doppler, quando avaliadas.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Avaliar cuidadosamente função sistólica do ventrículo esquerdo; repercussão funcional pode ocorrer em casos graves.",
            "diastolica": "Avaliar diástole ao Doppler (alterações de relaxamento e aumento de pressões de enchimento podem ocorrer).",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Subaórtica grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose subaórtica grave.",
            "camaras": "Hipertrofia concêntrica importante de ventrículo esquerdo.",
            "vasos": "Possível dilatação pós-estenótica da aorta.",
            "funcao": "Avaliar repercussão sistólica/diastólica.",
            "pericardio": "Sem efusão.",
        }
    ),


    # =========================================================
    # ESTENOSE PULMONAR
    # =========================================================
    "Estenose Pulmonar (Leve)": frase_det(
        valvas={
            "pulmonar": "Valva pulmonar com alterações compatíveis com estenose leve. Fluxo turbulento discreto em via de saída do ventrículo direito.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito com dimensões preservadas.",
            "vd": "Ventrículo direito com dimensões preservadas; espessura parietal preservada ou discretamente aumentada, conforme medidas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado ao estudo bidimensional.",
            "art_pulmonar": "Artéria pulmonar: avaliar discreta dilatação pós-estenótica do tronco pulmonar, a depender do caso.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado.",
            "sistolica_vd": "Função sistólica do ventrículo direito preservada.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Câmaras direitas sem alterações significativas.",
        conclusao="Achados compatíveis com Estenose Pulmonar leve (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar leve.",
            "camaras": "Sem remodelamento significativo.",
            "vasos": "Artéria pulmonar preservada; possível dilatação pós-estenótica discreta.",
            "funcao": "Função sistólica preservada.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Moderada)": frase_det(
        valvas={
            "pulmonar": "Valva pulmonar com estenose moderada, com aumento de velocidades em via de saída do ventrículo direito ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide com morfologia preservada. Refluxo ausente ou discreto, quando presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito com dimensões preservadas ou discretamente aumentadas, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia concêntrica discreta a moderada, conforme medidas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: possível dilatação pós-estenótica do tronco pulmonar, conforme o caso.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas com padrão preservado.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Função sistólica do ventrículo direito geralmente preservada; avaliar repercussão conforme severidade.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Repercussão em câmaras direitas pode estar presente conforme severidade.",
        conclusao="Achados compatíveis com Estenose Pulmonar moderada (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar moderada.",
            "camaras": "Hipertrofia/dilatação de câmaras direitas conforme severidade.",
            "vasos": "Possível dilatação pós-estenótica de artéria pulmonar.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Importante)": frase_det(
        valvas={
            "pulmonar": "Estenose pulmonar importante, com aumento expressivo de velocidades ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide: pode haver refluxo funcional secundário, conforme remodelamento.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito: possível dilatação moderada a importante, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia concêntrica moderada a importante; pode haver dilatação associada, conforme severidade.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: dilatação pós-estenótica do tronco pulmonar pode estar presente.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas: avaliar sinais de congestão sistêmica conforme hemodinâmica.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Avaliar função sistólica do ventrículo direito; repercussão funcional pode ocorrer em casos avançados.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Remodelamento de câmaras direitas pode estar presente.",
        conclusao="Achados compatíveis com Estenose Pulmonar importante (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar importante.",
            "camaras": "Remodelamento de câmaras direitas.",
            "vasos": "Dilatação pós-estenótica de artéria pulmonar pode estar presente.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),

    "Estenose Pulmonar (Grave)": frase_det(
        valvas={
            "pulmonar": "Estenose pulmonar grave, com turbulência severa e velocidades muito elevadas ao Doppler.",
            "mitral": "Valva mitral com morfologia preservada.",
            "tricuspide": "Valva tricúspide: refluxo funcional secundário pode estar presente.",
            "aortica": "Valva aórtica com morfologia preservada.",
        },
        camaras={
            "ae": "Átrio esquerdo com dimensões preservadas.",
            "ve": "Ventrículo esquerdo com dimensões preservadas.",
            "ad": "Átrio direito: dilatação importante provável, conforme severidade.",
            "vd": "Ventrículo direito: hipertrofia importante e possível dilatação; avaliar repercussões hemodinâmicas.",
        },
        vasos={
            "aorta": "Aorta com aspecto preservado.",
            "art_pulmonar": "Artéria pulmonar: dilatação pós-estenótica pode estar presente.",
            "veias_pulmonares": "Veias pulmonares com padrão preservado.",
            "cava_hepaticas": "Veia cava caudal e veias hepáticas: avaliar sinais de congestão sistêmica conforme hemodinâmica.",
        },
        funcao={
            "sistolica_ve": "Função sistólica do ventrículo esquerdo preservada.",
            "diastolica": "Sem alterações diastólicas significativas atribuíveis ao achado no ventrículo esquerdo.",
            "sistolica_vd": "Avaliar cuidadosamente função sistólica do ventrículo direito; disfunção pode estar presente em casos graves.",
            "sincronia": "Sem dissincronia interventricular evidente.",
        },
        pericardio={
            "efusao": "Ausência de efusão pericárdica.",
            "espessamento": "Pericárdio sem espessamento.",
            "tamponamento": "Sem sinais ecocardiográficos de tamponamento.",
        },
        ad_vd="Dilatação/hipertrofia de câmaras direitas provável.",
        conclusao="Achados compatíveis com Estenose Pulmonar grave (confirmar grau pelo gradiente ao Doppler).",
        resumo={
            "valvas": "Estenose pulmonar grave.",
            "camaras": "Remodelamento importante de câmaras direitas.",
            "vasos": "Dilatação pós-estenótica de artéria pulmonar pode estar presente.",
            "funcao": "Avaliar função do ventrículo direito.",
            "pericardio": "Sem efusão.",
        }
    ),




    # ----------------------------
    # PDA
    # ----------------------------
    "Persistência do Ducto Arterioso (PDA) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA, com fluxo anômalo em região de artéria pulmonar/aorta descendente, conforme janelas disponíveis.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com Persistência do Ducto Arterioso (PDA) leve."
    },
    "Persistência do Ducto Arterioso (PDA) (Moderada)": {
        "valvas": "Possível insuficiência funcional secundária (ex.: mitral) conforme remodelamento.",
        "camaras": "Sugere sobrecarga volumétrica esquerda moderada (aumento de AE e VE), conforme medidas.",
        "funcao": "Função sistólica preservada ou discretamente hiperdinâmica.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA com shunt predominante esquerda→direita.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com PDA com repercussão hemodinâmica moderada."
    },
    "Persistência do Ducto Arterioso (PDA) (Importante)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme dilatação de câmaras.",
        "camaras": "Importante sobrecarga volumétrica esquerda provável (dilatação de AE e VE), conforme medidas.",
        "funcao": "Função sistólica pode estar preservada ou já apresentar repercussão, conforme o caso.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA com shunt significativa esquerda→direita.",
        "ad_vd": "Avaliar sinais de hipertensão pulmonar associada, quando aplicável.",
        "conclusao": "Achados compatíveis com PDA com repercussão hemodinâmica importante."
    },
    "Persistência do Ducto Arterioso (PDA) (Grave)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável (sobrecarga volumétrica importante e/ou alterações compatíveis com evolução avançada), conforme medidas.",
        "funcao": "Avaliar cuidadosamente função sistólica e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com PDA. Considerar avaliação de hipertensão pulmonar e direção do shunt, quando aplicável.",
        "ad_vd": "Repercussões em câmaras direitas podem ocorrer em cenários avançados/hipertensão pulmonar.",
        "conclusao": "Achados compatíveis com PDA grave."
    },

    # ----------------------------
    # CIV
    # ----------------------------
    "Comunicação Interventricular (CIV) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV, com fluxo de shunt ao Doppler, conforme janelas disponíveis.",
        "ad_vd": "Câmaras direitas sem alterações significativas.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) leve."
    },
    "Comunicação Interventricular (CIV) (Moderada)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento.",
        "camaras": "Sugere repercussão em câmaras esquerdas em grau moderado, conforme magnitude do shunt e medidas.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV com shunt predominante esquerda→direita.",
        "ad_vd": "Avaliar repercussão em câmaras direitas e sinais de hipertensão pulmonar, quando aplicável.",
        "conclusao": "Achados compatíveis com CIV com repercussão hemodinâmica moderada."
    },
    "Comunicação Interventricular (CIV) (Importante)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento.",
        "camaras": "Repercussão hemodinâmica importante provável, conforme medidas e magnitude do shunt.",
        "funcao": "Avaliar repercussão funcional associada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV com shunt significativa. Avaliar hipertensão pulmonar associada.",
        "ad_vd": "Repercussões em câmaras direitas podem estar presentes.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) importante."
    },
    "Comunicação Interventricular (CIV) (Grave)": {
        "valvas": "Possíveis refluxos funcionais secundários, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável, conforme medidas e avaliação do shunt.",
        "funcao": "Avaliar cuidadosamente função sistólica e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIV. Considerar avaliação detalhada da direção do shunt e hipertensão pulmonar, quando aplicável.",
        "ad_vd": "Repercussões em câmaras direitas podem ocorrer em cenários avançados.",
        "conclusao": "Achados compatíveis com Comunicação Interventricular (CIV) grave."
    },

    # ----------------------------
    # CIA
    # ----------------------------
    "Comunicação Interatrial (CIA) (Leve)": {
        "valvas": "Valvas sem alterações morfológicas relevantes, salvo repercussões secundárias conforme severidade.",
        "camaras": "Sem remodelamento significativo associado ao achado.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA, com fluxo de shunt ao Doppler, conforme janelas disponíveis.",
        "ad_vd": "Sem alterações significativas em câmaras direitas.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) leve."
    },
    "Comunicação Interatrial (CIA) (Moderada)": {
        "valvas": "Possíveis insuficiências funcionais secundárias conforme remodelamento.",
        "camaras": "Pode haver aumento de câmaras direitas conforme magnitude do shunt (direita), conforme medidas.",
        "funcao": "Função sistólica global preservada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA com shunt predominante esquerda→direita.",
        "ad_vd": "Possível repercussão moderada em AD/VD, conforme medidas.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) moderada."
    },
    "Comunicação Interatrial (CIA) (Importante)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme dilatação de câmaras direitas.",
        "camaras": "Repercussão hemodinâmica importante provável em câmaras direitas, conforme medidas.",
        "funcao": "Avaliar repercussão funcional associada.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA. Avaliar sinais de hipertensão pulmonar quando aplicável.",
        "ad_vd": "Remodelamento importante de AD/VD pode estar presente.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) importante."
    },
    "Comunicação Interatrial (CIA) (Grave)": {
        "valvas": "Possíveis insuficiências funcionais secundárias, conforme remodelamento avançado.",
        "camaras": "Repercussão hemodinâmica grave provável em câmaras direitas.",
        "funcao": "Avaliar cuidadosamente função sistólica do VD e sinais indiretos de aumento de pressões.",
        "pericardio": "Ausência de efusão pericárdica.",
        "vasos": "Achados compatíveis com CIA. Considerar avaliação detalhada de hipertensão pulmonar e direção do shunt.",
        "ad_vd": "Repercussões avançadas em AD/VD podem estar presentes.",
        "conclusao": "Achados compatíveis com Comunicação Interatrial (CIA) grave."
    },
})


def inferir_layout(entry: dict, chave: str) -> str:
    # Normal sempre enxuto
    if chave == "Normal (Normal)":
        return "enxuto"

    # se já foi definido, respeita
    layout = (entry.get("layout") or "").strip().lower()
    if layout in ("enxuto", "detalhado"):
        return layout

    # heurística
    det = entry.get("det", {})
    det_tem_algo = any(
        (det.get(sec, {}).get(it, "") or "").strip()
        for sec, itens in QUALI_DET.items()
        for it in itens
    )

    txt_tem_algo = any(
        (entry.get(k, "") or "").strip()
        for k in ["valvas", "camaras", "vasos", "funcao", "pericardio", "ad_vd", "conclusao"]
    )

    if txt_tem_algo and not det_tem_algo:
        return "enxuto"
    return "detalhado"


def carregar_frases():
    if not os.path.exists(ARQUIVO_FRASES):
        with open(ARQUIVO_FRASES, "w", encoding="utf-8") as f:
            json.dump(FRASES_DEFAULT, f, indent=4, ensure_ascii=False)
        base = copy.deepcopy(FRASES_DEFAULT)
    else:
        try:
            with open(ARQUIVO_FRASES, "r", encoding="utf-8") as f:
                base = {**FRASES_DEFAULT, **json.load(f)}
        except:
            base = copy.deepcopy(FRASES_DEFAULT)

    # MIGRA / GARANTE 'det' EM TODAS AS FRASES + layout correto
    for k in list(base.keys()):
        entry = base[k]
        entry = garantir_schema_det_frase(entry)
        entry = migrar_txt_para_det(entry)
        entry["layout"] = inferir_layout(entry, k)
        base[k] = entry

    return base




# ==========================================
# 2. CLASSE PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        bg = MARCA_DAGUA_TEMP if os.path.exists(MARCA_DAGUA_TEMP) else ("logo.png" if os.path.exists("logo.png") else None)
        # Marca d'água: ligeiramente menor e mais alta para não conflitar com carimbo/assinatura.
        if bg: self.image(bg, x=55, y=65, w=100)
        if os.path.exists("logo.png"): self.image("logo.png", x=10, y=8, w=35)
        self.set_y(15); self.set_x(52)
        self.set_font("Arial", 'B', 16); self.set_text_color(0,0,0)
        self.cell(0, 10, "LAUDO ECOCARDIOGRÁFICO", ln=1, align='L')
        self.set_y(35) # Margem segurança

    def footer(self):
        self.set_y(-15); self.set_font("Arial", 'I', 9); self.set_text_color(100,100,100)
        self.cell(0, 10, "Fort Cordis Cardiologia Veterinária | Fortaleza-CE", align='C')

# ==========================================
# 3. LÓGICA
# ==========================================
def calcular_referencia_tabela(parametro, peso_kg, df=None):
    """Retorna a faixa de referência (min,max) e um texto "min - max".

    ✅ Importante: agora respeita o *df* passado (ex.: felinos) e aceita coluna de peso como
    "Peso (kg)" **ou** "Peso".
    """
    # Usa o df fornecido (ex.: tabela felina) ou cai no padrão canino
    if df is None:
        df = st.session_state.get('df_ref')
    if df is None:
        return None, ""

    # Trabalha em cópia para não alterar o df em sessão
    try:
        df = df.copy()
    except Exception:
        return None, ""

    # Normaliza peso
    try:
        peso_kg = float(str(peso_kg).replace(",", "."))
    except Exception:
        return None, ""

    # Normaliza coluna de peso (felinos vinha como "Peso")
    if "Peso (kg)" not in df.columns:
        if "Peso" in df.columns:
            df = df.rename(columns={"Peso": "Peso (kg)"})
        else:
            return None, ""

    # MAPA ATUALIZADO COM OS DADOS QUE VOCÊ PEDIU
    mapa = {
        "LVIDd": ("LVIDd_Min", "LVIDd_Max"), "Ao": ("Ao_Min", "Ao_Max"), "LA": ("LA_Min", "LA_Max"),
        "IVSd": ("IVSd_Min", "IVSd_Max"), "LVPWd": ("LVPWd_Min", "LVPWd_Max"),
        "LVIDs": ("LVIDs_Min", "LVIDs_Max"), "IVSs": ("IVSs_Min", "IVSs_Max"), "LVPWs": ("LVPWs_Min", "LVPWs_Max"),
        "EDV": ("EDV_Min", "EDV_Max"), "ESV": ("ESV_Min", "ESV_Max"), "SV": ("SV_Min", "SV_Max"),
        "Vmax_Ao": ("Vmax_Ao_Min", "Vmax_Ao_Max"), "Vmax_Pulm": ("Vmax_Pulm_Min", "Vmax_Pulm_Max"),
        "LA_Ao": ("LA_Ao_Min", "LA_Ao_Max"), "EF": ("EF_Min", "EF_Max"), "FS": ("FS_Min", "FS_Max"),
        "MV_E": ("MV_E_Min", "MV_E_Max"), "MV_A": ("MV_A_Min", "MV_A_Max"),
        "MV_E_A": ("MV_EA_Min", "MV_EA_Max"), "MV_DT": ("MV_DT_Min", "MV_DT_Max"), "MV_Slope": ("MV_Slope_Min", "MV_Slope_Max"),
        "IVRT": ("IVRT_Min", "IVRT_Max"), "E_IVRT": ("E_IVRT_Min", "E_IVRT_Max"),
        "TR_Vmax": ("TR_Vmax_Min", "TR_Vmax_Max"), "MR_Vmax": ("MR_Vmax_Min", "MR_Vmax_Max")
    }

    if parametro not in mapa:
        return None, ""

    col_min, col_max = mapa[parametro]
    if col_min not in df.columns or col_max not in df.columns:
        return (0.0, 0.0), "--"

    # Ordena e busca/interpola
    df = df.sort_values("Peso (kg)").reset_index(drop=True)

    # Garantir numérico (importações CSV podem vir como texto)
    df["Peso (kg)"] = pd.to_numeric(df["Peso (kg)"], errors="coerce")
    df[col_min] = pd.to_numeric(df[col_min], errors="coerce")
    df[col_max] = pd.to_numeric(df[col_max], errors="coerce")

    if peso_kg in set(df["Peso (kg)"].dropna().values.tolist()):
        row = df[df["Peso (kg)"] == peso_kg].iloc[0]
        min_val, max_val = row[col_min], row[col_max]
    else:
        # Insere linha e interpola
        row_new = {"Peso (kg)": peso_kg}
        for c in df.columns:
            if c != "Peso (kg)":
                row_new[c] = pd.NA
        df_temp = pd.concat([df, pd.DataFrame([row_new])], ignore_index=True)
        df_temp = df_temp.sort_values("Peso (kg)").reset_index(drop=True)

        # Converte tudo que dá para numérico; NA vira NaN
        df_temp = df_temp.apply(pd.to_numeric, errors="coerce")
        df_temp = df_temp.interpolate(method='linear', limit_direction='both')

        row = df_temp[(df_temp["Peso (kg)"] - peso_kg).abs() < 1e-9].iloc[0]
        min_val, max_val = row[col_min], row[col_max]

    if pd.isna(min_val) or pd.isna(max_val):
        return None, "--"
    if float(min_val) == 0.0 and float(max_val) == 0.0:
        return None, "--"
    return (float(min_val), float(max_val)), f"{float(min_val):.2f} - {float(max_val):.2f}"

def interpretar(valor, ref_tuple):
    if not ref_tuple or (ref_tuple[0] == 0 and ref_tuple[1] == 0): return ""
    min_v, max_v = ref_tuple
    if valor < min_v: return "Reduzido"
    if valor > max_v: return "Aumentado"
    return "Normal"


# Referência fixa para DIVEdN (DIVEd normalizado / LVIDdN)
# Observação: esta fórmula (peso^0,294) é a mais usada para cães; para felinos, o expoente e as referências diferem.
DIVEDN_REF_MIN = 1.27
DIVEDN_REF_MAX = 1.85
DIVEDN_REF_TXT = f"{DIVEDN_REF_MIN:.2f}-{DIVEDN_REF_MAX:.2f}"

def interpretar_divedn(divedn: float) -> str:
    """Interpretação prática para DIVEdN (LVIDdN) em cães.
    Mantém uma leitura clínica mais útil do que apenas 'Aumentado/Normal/Reduzido'.
    """
    try:
        v = float(divedn)
    except Exception:
        return ""
    if v <= 0:
        return ""
    if v < DIVEDN_REF_MIN:
        return "Abaixo do esperado"
    # Faixa considerada "normal"
    if v <= 1.70:
        return "Normal"
    # Zona limítrofe (acima do ponto de corte clínico mais usado, mas ainda dentro do teto de referência)
    if v <= DIVEDN_REF_MAX:
        return "Limítrofe"
    # Dilatação: gradação prática
    if v <= 2.00:
        return "Dilatação leve"
    if v <= 2.30:
        return "Dilatação moderada"
    return "Dilatação importante"

# Cérebro Clínico (Mantido)
def analisar_criterios_clinicos(dados, peso, patologia, grau_refluxo, tem_congestao, grau_geral):
    chave = montar_chave_frase(patologia, grau_refluxo, grau_geral)

    res_base = st.session_state['db_frases'].get(chave, {})
    if not res_base and patologia != "Normal":
        for k, v in st.session_state['db_frases'].items():
            if patologia in k:
                res_base = v.copy()
                break

    if not res_base:
        res_base = {'conclusao': f"{patologia}"}

    txt = res_base.copy()

    # ... (resto do seu código igual)


    if patologia == "Endocardiose Mitral":
        # pega o que veio do editor
        conclusao_editor = (txt.get("conclusao") or "").strip()

        try:
            r_lvidd = calcular_referencia_tabela("LVIDd", peso)[0]
            l_lvidd = r_lvidd[1] if r_lvidd[1] else 999

            r_laao = calcular_referencia_tabela("LA_Ao", peso)[0]
            l_laao = r_laao[1] if r_laao[1] else 1.6
        except:
            l_lvidd, l_laao = 999, 1.6

        val_laao, val_lvidd = dados.get('LA_Ao', 0), dados.get('LVIDd', 0)
        aum_ae, aum_ve = (val_laao >= l_laao), (val_lvidd > l_lvidd)

        # você pode manter valvas automático OU só se estiver vazio também
        if not (txt.get("valvas") or "").strip():
            txt['valvas'] = f"Valva mitral espessada. Insuficiência {grau_refluxo.lower()}."

        # ✅ só calcula e escreve a conclusão automática se o editor NÃO tiver conclusão
        if not conclusao_editor:
            if tem_congestao:
                txt['conclusao'] = f"Endocardiose Mitral Estágio C (ACVIM). Refluxo {grau_refluxo}. Sinais de ICC."
            elif aum_ae and aum_ve:
                txt['conclusao'] = f"Endocardiose Mitral Estágio B2 (ACVIM). Refluxo {grau_refluxo} com remodelamento."
            elif aum_ae:
                txt['conclusao'] = f"Endocardiose Mitral (Refluxo {grau_refluxo}) com aumento atrial esquerdo."
            else:
                txt['conclusao'] = f"Endocardiose Mitral Estágio B1 (ACVIM). Refluxo {grau_refluxo}."



    """
    Copia os textos corridos (txt_*) para os subcampos detalhados (q_*).
    Eu, particularmente, recomendo preencher só os campos mais prováveis
    e não “inventar” texto para válvulas/câmaras que não foram citadas.
    """

    """
    Complementa os campos qualitativos de valvas (q_valvas_*) com informação de regurgitação
    quando houver Vmax > 0 nas medidas.

    Observação (opinião técnica): Vmax NÃO classifica bem gravidade do refluxo sozinho.
    Então eu descrevo 'presente' + Vmax, e só uso o grau da mitral quando você já seleciona no sidebar.
    """
    dados = st.session_state.get("dados_atuais", {}) or {}

    mr = float(dados.get("MR_Vmax", 0.0) or 0.0)
    tr = float(dados.get("TR_Vmax", 0.0) or 0.0)
    ar = float(dados.get("AR_Vmax", 0.0) or 0.0)
    pr = float(dados.get("PR_Vmax", 0.0) or 0.0)

    def append_if_needed(key: str, extra: str):
        extra = (extra or "").strip()
        if not extra:
            return
        atual = (st.session_state.get(key, "") or "").strip()
        if extra.lower() in atual.lower():
            return
        st.session_state[key] = (atual + ("\n" if atual else "") + extra).strip()

    # Mitral
    if mr > 0:
        extra = f"Refluxo mitral presente ao Doppler (Vmax {mr:.2f} m/s)."
        append_if_needed("q_valvas_mitral", extra)

    # Se for Endocardiose Mitral, aí sim usa o grau escolhido
    if mr > 0 and patologia == "Endocardiose Mitral" and grau_refluxo:
        extra = f"Refluxo mitral {grau_refluxo.lower()} ao Doppler (Vmax {mr:.2f} m/s)."
        append_if_needed("q_valvas_mitral", extra)

    # Tricúspide
    if tr > 0:
        extra = f"Refluxo tricúspide presente ao Doppler (Vmax {tr:.2f} m/s)."
        append_if_needed("q_valvas_tricuspide", extra)

    # Aórtica
    if ar > 0:
        extra = f"Refluxo aórtico presente ao Doppler (Vmax {ar:.2f} m/s)."
        append_if_needed("q_valvas_aortica", extra)

    # Pulmonar
    if pr > 0:
        extra = f"Refluxo pulmonar presente ao Doppler (Vmax {pr:.2f} m/s)."
        append_if_needed("q_valvas_pulmonar", extra)



    def set_if_empty(key, value):
        value = (value or "").strip()
        if not value:
            return
        # só preenche se o campo ainda estiver vazio (pra não apagar o que você digitou)
        if not (st.session_state.get(key, "") or "").strip():
            st.session_state[key] = value

    txt_valvas = st.session_state.get("txt_valvas", "")
    txt_camaras = st.session_state.get("txt_camaras", "")
    txt_funcao = st.session_state.get("txt_funcao", "")
    txt_pericardio = st.session_state.get("txt_pericardio", "")
    txt_vasos = st.session_state.get("txt_vasos", "")
    txt_ad_vd = st.session_state.get("txt_ad_vd", "")

    # --- Valvas ---
    # Endocardiose mitral: joga a sugestão principalmente no campo Mitral
    if patologia == "Endocardiose Mitral":
        set_if_empty("q_valvas_mitral", txt_valvas)
    else:
        # outras patologias: coloca a sugestão em Mitral como “campo principal”
        set_if_empty("q_valvas_mitral", txt_valvas)

    # --- Câmaras ---
    # Texto corrido geralmente fala de câmaras esquerdas; joga em AE e VE
    set_if_empty("q_camaras_ae", txt_camaras)
    set_if_empty("q_camaras_ve", txt_camaras)

    # Texto subjetivo AD/VD joga para as câmaras direitas
    set_if_empty("q_camaras_ad", txt_ad_vd)
    set_if_empty("q_camaras_vd", txt_ad_vd)

    # --- Função ---
    # Texto corrido vai em “Sistólica VE” como principal
    set_if_empty("q_funcao_sistolica_ve", txt_funcao)

    # --- Pericárdio ---
    set_if_empty("q_pericardio_efusao", txt_pericardio)

    # --- Vasos ---
    set_if_empty("q_vasos_aorta", txt_vasos)
