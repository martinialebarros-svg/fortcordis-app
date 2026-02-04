import streamlit as st
import sys
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
# VERSÃO E CONFIG (app/config.py)
# ============================================================
from app.config import VERSAO_DEPLOY, DB_PATH, PASTA_DB, CSS_GLOBAL
try:
    from app.config import PASTA_LAUDOS, ARQUIVO_REF, ARQUIVO_REF_FELINOS
except ImportError:
    # Fallback para deploy com app.config antigo (sem paths de laudos)
    PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
    PASTA_LAUDOS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_REF = "tabela_referencia_caninos.csv"
    ARQUIVO_REF_FELINOS = "tabela_referencia_felinos.csv"

# Referências e tabelas de laudos (Fase B)
from app.laudos_refs import (
    PARAMS,
    get_grupos_por_especie,
    normalizar_especie_label,
    especie_is_felina,
    gerar_tabela_padrao,
    gerar_tabela_padrao_felinos,
    limpar_e_converter_tabela,
    limpar_e_converter_tabela_felinos,
    carregar_tabela_referencia_cached,
    carregar_tabela_referencia_felinos_cached,
    listar_registros_arquivados_cached,
    calcular_referencia_tabela,
    interpretar,
    interpretar_divedn,
    DIVEDN_REF_TXT,
)

# ============================================================
# CONFIGURAÇÃO DA PÁGINA E DESIGN (primeiro comando Streamlit)
# ============================================================
st.set_page_config(
    page_title="Fort Cordis - Sistema Integrado",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Captura erros não tratados para exibir na página (evita "Error running app" genérico)
import traceback as _traceback_mod
try:
    _original_excepthook = sys.excepthook
    def _fortcordis_excepthook(etype, value, tb):
        try:
            st.error("O aplicativo encontrou um erro. Abra **Detalhes do erro** e copie o texto para enviar ao suporte.")
            with st.expander("Detalhes do erro (copie e envie para diagnóstico)"):
                st.code("".join(_traceback_mod.format_exception(etype, value, tb)), language="text")
            st.stop()
        except Exception:
            pass
        _original_excepthook(etype, value, tb)
    sys.excepthook = _fortcordis_excepthook
except NameError:
    pass

# CSS global (app/config.py)
st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

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

if st.session_state.get("db_was_recovered"):
    st.warning(
        "O banco de dados foi reiniciado devido a um erro anterior (por exemplo, importação interrompida com 502). "
        "Os dados foram salvos em um arquivo `.corrupted`. Importe o backup novamente em **Configurações > Importar dados** se necessário."
    )
    st.session_state.pop("db_was_recovered", None)

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
_app_root = Path(__file__).resolve().parent
# Garantir que o app root está no path (Streamlit Cloud pode rodar de outro diretório)
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))
sys.path.append(str(_app_root / "fortcordis_modules"))

from fortcordis_modules.database import (
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

from fortcordis_modules.integrations import (
    whatsapp_link,
    mensagem_confirmacao_agendamento,
    exportar_agendamento_ics,
)

from fortcordis_modules.documentos import (
    gerar_receituario_pdf,
    gerar_atestado_saude_pdf,
    gerar_gta_pdf,
    calcular_posologia
)

from app.laudos_helpers import (
    ARQUIVO_FRASES,
    QUALI_DET,
    ROTULOS,
    garantir_schema_det_frase,
    migrar_txt_para_det,
    det_para_txt,
    frase_det,
    aplicar_frase_det_na_tela,
    aplicar_det_nos_subcampos,
    inferir_layout,
    carregar_frases as _carregar_frases_impl,
    _backfill_nomes_laudos,
    listar_laudos_do_banco,
    listar_laudos_arquivos_do_banco,
    obter_laudo_arquivo_por_id,
    obter_imagens_laudo_arquivo,
    contar_laudos_do_banco,
    contar_laudos_arquivos_do_banco,
)


def carregar_frases():
    """Wrapper sem argumentos para uso no app e em laudos_deps; usa ARQUIVO_FRASES e dict vazio como default."""
    return _carregar_frases_impl(ARQUIVO_FRASES, {})


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
# Marca d'água em pasta gravável (Streamlit Cloud pode ter app dir read-only)
MARCA_DAGUA_TEMP = str(Path(tempfile.gettempdir()) / "fortcordis_watermark_faded.png")
ARQUIVO_FRASES = str((Path.home() / "FortCordis" / "frases_personalizadas.json"))
Path(ARQUIVO_FRASES).parent.mkdir(parents=True, exist_ok=True)

# Arquivos de referência e pasta Laudos vêm de app.config (PASTA_LAUDOS, ARQUIVO_REF, ARQUIVO_REF_FELINOS)

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


# Banco: usar mesmo DB do app (fortcordis_modules.database)
if "database" in sys.modules:
    sys.modules["database"].DB_PATH = DB_PATH
# Conexão e upserts locais (clinicas/tutores/pacientes) em app/db.py
from app.db import _db_conn_safe, _db_conn, _db_init, db_upsert_clinica, db_upsert_tutor, db_upsert_paciente

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
from app.menu import MENU_ITEMS, get_menu_labels

st.sidebar.markdown("## 🏥 Fort Cordis")
st.sidebar.markdown("*Sistema Integrado de Gestão*")
st.sidebar.markdown("---")
menu_principal = st.sidebar.radio(
    "Navegação",
    get_menu_labels(),
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
    # 1) Carregamento a partir do banco (JSON + imagens já em memória)
    obj = st.session_state.pop("__carregar_exame_json_content", None)
    imagens_banco = st.session_state.pop("__carregar_exame_imagens", None)
    if obj is not None:
        if not isinstance(obj, dict):
            st.error("JSON inválido (estrutura inesperada).")
            return
        if imagens_banco:
            st.session_state["imagens_carregadas"] = [
                {"name": (it.get("name") or it.get("nome_arquivo") or f"imagem_{i}.jpg"), "bytes": it.get("bytes") or it.get("conteudo") or b""}
                for i, it in enumerate(imagens_banco)
            ]
        else:
            st.session_state["imagens_carregadas"] = []
        # segue para o bloco comum de preenchimento (pac, medidas, etc.) abaixo
    else:
        # 2) Carregamento a partir de arquivo (path)
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
        # carregamento por path não preenche imagens_carregadas (arquivos em disco)
        st.session_state["imagens_carregadas"] = []

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

# MARCA_DAGUA_TEMP já definido no início do arquivo (pasta temp + opacidade 0.05)
ARQUIVO_FRASES = str((Path.home() / "FortCordis" / "frases_personalizadas.json"))
Path(ARQUIVO_FRASES).parent.mkdir(parents=True, exist_ok=True)
# ARQUIVO_REF, ARQUIVO_REF_FELINOS, PASTA_LAUDOS vêm de app.config

import unicodedata
from datetime import datetime, date
from pathlib import Path

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
    try:
        mostrar_tela_login()
    except Exception as e:
        st.error("Erro na tela de login ou ao criar primeiro usuário.")
        with st.expander("Detalhes do erro (copie e envie para diagnóstico)"):
            st.code(_traceback_mod.format_exc(), language="text")
        st.stop()
    if not st.session_state.get("autenticado"):
        st.stop()

# Se chegou aqui, está logado!
# Mostra info do usuário na sidebar
try:
    mostrar_info_usuario()
except Exception as e:
    st.error("Erro ao carregar dados do usuário.")
    with st.expander("Detalhes do erro (copie e envie para diagnóstico)"):
        st.code(_traceback_mod.format_exc(), language="text")
    st.stop()

# Menu principal já definido no início do script (único radio, evita StreamlitDuplicateElementId)

# ============================================================================
# DISPATCH: renderiza a página escolhida (menu centralizado em app.menu)
# ============================================================================
import importlib

for label, module_path, function_name, special in MENU_ITEMS:
    if menu_principal != label:
        continue
    if special == "laudos":
        from app.laudos_deps import build_laudos_deps
        from app.pages.laudos import render_laudos
        laudos_deps = build_laudos_deps(
            PASTA_LAUDOS=PASTA_LAUDOS,
            ARQUIVO_REF=ARQUIVO_REF,
            ARQUIVO_REF_FELINOS=ARQUIVO_REF_FELINOS,
            PARAMS=PARAMS,
            get_grupos_por_especie=get_grupos_por_especie,
            normalizar_especie_label=normalizar_especie_label,
            montar_nome_base_arquivo=montar_nome_base_arquivo,
            calcular_referencia_tabela=calcular_referencia_tabela,
            interpretar=interpretar,
            interpretar_divedn=interpretar_divedn,
            DIVEDN_REF_TXT=DIVEDN_REF_TXT,
            listar_registros_arquivados_cached=listar_registros_arquivados_cached,
            salvar_laudo_no_banco=salvar_laudo_no_banco,
            obter_imagens_para_pdf=obter_imagens_para_pdf,
            montar_qualitativa=montar_qualitativa,
            _caminho_marca_dagua=_caminho_marca_dagua,
            montar_chave_frase=montar_chave_frase,
            carregar_frases=carregar_frases,
            gerar_tabela_padrao=gerar_tabela_padrao,
            gerar_tabela_padrao_felinos=gerar_tabela_padrao_felinos,
            limpar_e_converter_tabela=limpar_e_converter_tabela,
            limpar_e_converter_tabela_felinos=limpar_e_converter_tabela_felinos,
            carregar_tabela_referencia_cached=carregar_tabela_referencia_cached,
            carregar_tabela_referencia_felinos_cached=carregar_tabela_referencia_felinos_cached,
            _normalizar_data_str=_normalizar_data_str,
            especie_is_felina=especie_is_felina,
            calcular_valor_final=calcular_valor_final,
            gerar_numero_os=gerar_numero_os,
        )
        try:
            render_laudos(laudos_deps)
        except TypeError:
            st.error(
                "**Laudos: versão desatualizada no servidor.** O módulo Laudos no deploy não está alinhado com o app. "
                "Confirme que **app/pages/laudos.py** está commitado com a assinatura `def render_laudos(deps=None)`, "
                "faça **push** e aguarde o redeploy no Streamlit Cloud (ou use *Manage app* → *Reboot*)."
            )
    else:
        mod = importlib.import_module(module_path)
        getattr(mod, function_name)()
    break

