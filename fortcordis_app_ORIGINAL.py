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
import re

# ----------------------------
# Normalização de textos (cadastro)
# ----------------------------
_PREPS = {"da", "de", "do", "das", "dos", "e"}

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
st.set_page_config(page_title="Fort Cordis - Laudos", layout="wide")
st.sidebar.write("✅ CHECKPOINT 0: script começou")
st.write("✅ CHECKPOINT 0B: script começou (tela principal)")

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
# 🗄️ Banco local (SQLite) para cadastros (clínica/tutor/paciente)
# ==========================================================
PASTA_DB = Path.home() / "FortCordis" / "DB"
PASTA_DB.mkdir(parents=True, exist_ok=True)
DB_PATH = PASTA_DB / "fortcordis.db"

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
    ("VE - Modo M", ["LVIDd","DIVEdN","IVSd","LVPWd","LVIDs","IVSs","LVPWs","EDV","ESV","EF","FS"]),
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
st.sidebar.title("Auxiliar Clínico")
# ==========================================================
# ✅ Assinatura/Carimbo PERSISTENTE (não precisa reenviar)
# Salva em: C:\Users\<SeuUsuario>\FortCordis\assinatura.png  (Windows)
# ==========================================================
PASTA_FORTCORDIS = Path.home() / "FortCordis"
PASTA_FORTCORDIS.mkdir(parents=True, exist_ok=True)

ASSINATURA_PATH = str(PASTA_FORTCORDIS / "assinatura.png")

# Se já existir assinatura salva, usa automaticamente
if "assinatura_path" not in st.session_state:
    if os.path.exists(ASSINATURA_PATH):
        st.session_state["assinatura_path"] = ASSINATURA_PATH

st.sidebar.markdown("### 🖊️ Assinatura/Carimbo")

# Mostra status + preview se existir
assin_atual = st.session_state.get("assinatura_path")
if assin_atual and os.path.exists(assin_atual):
    st.sidebar.info("Assinatura carregada automaticamente.")
    try:
        st.sidebar.image(assin_atual, use_container_width=True)
    except:
        pass

# Botão para trocar assinatura (só abre uploader quando você pedir)
if "trocar_assinatura" not in st.session_state:
    st.session_state["trocar_assinatura"] = False

colA, colB = st.sidebar.columns(2)
with colA:
    if st.button("🔁 Trocar", use_container_width=True):
        st.session_state["trocar_assinatura"] = True
with colB:
    if st.button("🗑️ Remover", use_container_width=True):
        try:
            if os.path.exists(ASSINATURA_PATH):
                os.remove(ASSINATURA_PATH)
        except:
            pass
        st.session_state.pop("assinatura_path", None)
        st.session_state["trocar_assinatura"] = False
        st.rerun()

# Uploader só aparece quando você clicar em "Trocar"
if st.session_state["trocar_assinatura"]:
    up_assin = st.sidebar.file_uploader(
        "Envie a assinatura (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        key="up_assinatura"
    )
    if up_assin is not None:
        try:
            img = Image.open(up_assin)
            # salva como PNG (bom para transparência)
            img.save(ASSINATURA_PATH, format="PNG")
            st.session_state["assinatura_path"] = ASSINATURA_PATH
            st.session_state["trocar_assinatura"] = False
            st.sidebar.success("Assinatura salva para os próximos laudos.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erro ao salvar assinatura: {e}")


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

# --- Sidebar: Suspeita (base) + Grau ---
db_frases = st.session_state.get("db_frases", {}) or {}

op_patologias = ["Normal"] + _listar_patologias_base(db_frases)

# garante que o valor atual em session_state existe na lista (evita erro no front)
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
    # garante valor selecionado válido
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
    # pega os graus existentes no JSON para essa patologia;
    # se não existir, usa o padrão
    graus_existentes = _graus_da_patologia(db_frases, sb_patologia)
    if not graus_existentes:
        graus_existentes = ["Leve", "Moderada", "Importante", "Grave"]

    # garante valor selecionado válido
    if graus_existentes and st.session_state.get("sb_grau_geral") not in graus_existentes:
        st.session_state["sb_grau_geral"] = graus_existentes[0]

    # ✅ FIX: o select_slider quebra no front quando há apenas 1 opção (erro JS: min==max)
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

# ✅ UX: se for Normal, não mostra sliders
if sb_patologia == "Normal":
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

st.sidebar.markdown("---")
add_refluxo = st.sidebar.checkbox("Adicionar frase de refluxo valvar", value=False, key="add_refluxo")

sb_valva_refluxo = st.sidebar.selectbox(
    "Valva do refluxo:",
    options=["mitral", "tricuspide", "aortica", "pulmonar"],
    index=0,
    disabled=(not add_refluxo),
    key="sb_valva_refluxo"
)

sb_grau_refluxo_extra = st.sidebar.select_slider(
    "Grau do refluxo:",
    options=["Leve", "Moderada", "Importante", "Grave"],
    value="Leve",
    disabled=(not add_refluxo),
    key="sb_grau_refluxo_extra"
)


if st.sidebar.button("🔄 Gerar Texto"):
    # Primeiro: tenta carregar exatamente o que foi salvo no banco de frases
    chave = montar_chave_frase(sb_patologia, sb_grau_refluxo, sb_grau_geral)
    db_local = st.session_state.get("db_frases", {}) or {}

    # ✅ Busca robusta (evita falhas por acentos/caixa ou "Moderado" vs "Moderada")
    entry = obter_entry_frase(db_local, chave)

    if entry:
        # ✅ Quando existe no banco, aplica exatamente o que foi salvo (sem “ajustes automáticos”)
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

    # ==========================================================
    # Complementos opcionais
    # ==========================================================
    # Endocardiose Mitral: só aplica complemento automático quando NÃO houver entry salva.
    # (se tiver entry no banco, respeita o texto exatamente como foi salvo)
    if (not entry) and (sb_patologia == "Endocardiose Mitral"):
        complementar_regurgitacao_valvar("mitral", sb_grau_refluxo)

    # Qualquer patologia: se o usuário marcar o checkbox, aplica também
    if st.session_state.get("add_refluxo"):
        complementar_regurgitacao_valvar(
            st.session_state.get("sb_valva_refluxo"),
            st.session_state.get("sb_grau_refluxo_extra")
        )

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


st.sidebar.success("Texto aplicado!")




st.title("🫀 Fort Cordis - Laudo V.28.0")

# feedback quando um exame arquivado é carregado para edição
if st.session_state.pop("toast_carregar_exame", False):
    st.success("Exame arquivado carregado para edição. Ajuste o que precisar e gere um novo PDF/JSON.")

st.markdown("---")

uploaded_xml = st.file_uploader("1. XML Vivid IQ", type=['xml'])

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
        try: soup = BeautifulSoup(content, 'xml')
        except: soup = BeautifulSoup(content, 'lxml')
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



# ABAS
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    ["Cadastro", "Medidas", "Qualitativa", "📷 Imagens", "⚙️ Frases", "📏 Referências", "🔎 Buscar exames", "🩺 Pressão Arterial"]
)

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
    with st.expander("Cadastrar nova espécie"):
        nova_especie = st.text_input("Nova espécie (ex.: Lagomorfo)", key="nova_especie_txt")
        c_add1, c_add2 = st.columns([1, 3])
        if c_add1.button("Adicionar", key="btn_add_especie"):
            nova_especie = normalizar_especie_label(nova_especie)
            if nova_especie:
                if nova_especie not in st.session_state.get("lista_especies", []):
                    st.session_state["lista_especies"].append(nova_especie)
                st.session_state["cad_especie"] = nova_especie
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
    if "cad_clinica" not in st.session_state:

        st.session_state["cad_clinica"] = clinica

    clinica = st.text_input("Clínica", key="cad_clinica")
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

                        # mantém o widget sincronizado (key fixa)
                        st.session_state["DIVEdN_out"] = float(dados.get("DIVEdN", 0.0) or 0.0)
                        st.number_input(label, value=float(dados.get("DIVEdN", 0.0)), disabled=True, key="DIVEdN_out")

                    with col_interp:
                        ref_txt, interp_txt = _ref_interp_para_ui(k, float(dados.get(k, 0.0) or 0.0))
                        if ref_txt:
                            st.caption(f"Ref.: {ref_txt}")
                        if interp_txt:
                            st.caption(f"Interp.: {interp_txt}")

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
    st.caption(f"Pasta de arquivos: {PASTA_LAUDOS}")

    # varre apenas JSON (JavaScript Object Notation) e usa cache com TTL (Time To Live)
    registros = listar_registros_arquivados_cached(str(PASTA_LAUDOS))

    if not registros:
        st.warning("Nenhum exame arquivado ainda. Gere um PDF para o sistema arquivar e aparecer aqui.")
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
    o1, o2, o3 = st.columns(3)
    manguito = o1.text_input("Manguito", value=str(st.session_state.get("pa_manguito", "") or ""), key="pa_manguito", placeholder="Ex.: Manguito 02")
    membro = o2.text_input("Membro", value=str(st.session_state.get("pa_membro", "") or ""), key="pa_membro", placeholder="Ex.: Membro anterior esquerdo")
    decubito = o3.text_input("Decúbito", value=str(st.session_state.get("pa_decubito", "") or ""), key="pa_decubito", placeholder="Ex.: Decúbito lateral direito")

    obs_extra = st.text_area("Outras observações (opcional)", value=str(st.session_state.get("pa_obs_extra", "") or ""), key="pa_obs_extra", height=80)

    st.markdown("### Valores de referência (PAS - pressão arterial sistólica)")
    st.write("• Normal: 110 a 140 mmHg")
    st.write("• Levemente elevada: 141 a 159 mmHg (recomendado monitoramento e reavaliação periódica)")
    st.write("• Moderadamente elevada: 160 a 179 mmHg (potencial risco de lesão em órgãos-alvo)")
    st.write("• Severamente elevada: ≥180 mmHg")

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


    if st.button("🧾 Gerar PDF"):
        pdf_bytes = criar_pdf()
        st.session_state["pdf_bytes"] = pdf_bytes

        # arquiva PDF, JSON e imagens na pasta fixa (para busca)
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

            st.success(f"PDF gerado e arquivado em: {PASTA_LAUDOS}")
        except Exception as e:
            st.warning(f"PDF gerado, mas não consegui arquivar automaticamente: {e}")


    if "pdf_bytes" in st.session_state:
        st.download_button(
            "⬇️ Baixar PDF",
            data=st.session_state["pdf_bytes"],
            file_name=f"{nome_base}.pdf",
            mime="application/pdf"
        )