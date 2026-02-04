# Helpers para PDF e imagens de laudos: marca d'água, imagens do exame, nome de arquivo e data
# Fase B: extraído do fortcordis_app.py
import os
import re
import tempfile
import unicodedata
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from PIL import Image

# Marca d'água em pasta gravável (Streamlit Cloud pode ter app dir read-only)
MARCA_DAGUA_TEMP = str(Path(tempfile.gettempdir()) / "fortcordis_watermark_faded.png")


def criar_imagem_esmaecida(input_path, output_path, opacidade=0.10):
    """Gera versão esmaecida do logo para marca d'água."""
    try:
        img = Image.open(input_path).convert("RGBA")
        dados = list(img.getdata())
        novos_dados = []
        for item in dados:
            novo_alpha = int(item[3] * opacidade)
            novos_dados.append((item[0], item[1], item[2], novo_alpha))
        img.putdata(novos_dados)
        img.save(output_path, "PNG")
        return True
    except Exception:
        return False


def _caminho_marca_dagua():
    """Retorna caminho da marca d'água; cria na primeira geração (lazy) para não gastar no Cloud."""
    if os.path.exists("logo.png") and not os.path.exists(MARCA_DAGUA_TEMP):
        try:
            criar_imagem_esmaecida("logo.png", MARCA_DAGUA_TEMP, opacidade=0.05)
        except Exception:
            pass
    if os.path.exists(MARCA_DAGUA_TEMP):
        return MARCA_DAGUA_TEMP
    if os.path.exists("logo.png"):
        return "logo.png"
    return None


def _img_ext_from_name(nome: str) -> str:
    try:
        ext = (Path(nome).suffix or "").lower()
    except Exception:
        ext = ""
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"
    return ext


def obter_imagens_para_pdf():
    """Retorna lista de imagens do exame (bytes) para preview e PDF."""
    imgs = []

    carregadas = st.session_state.get("imagens_carregadas", []) or []
    for it in carregadas:
        if isinstance(it, dict) and it.get("bytes"):
            imgs.append({
                "name": str(it.get("name") or "imagem"),
                "bytes": bytes(it.get("bytes")),
                "ext": _img_ext_from_name(it.get("name") or "")
            })

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


def _limpar_texto_filename(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "SEM_DADO"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    return s[:60] if len(s) > 60 else s


def _normalizar_data_str(data_exame: str) -> str:
    """
    Aceita formatos comuns: YYYYMMDD, YYYY-MM-DD, DD/MM/YYYY.
    Retorna 'YYYY-MM-DD'.
    """
    s = (data_exame or "").strip()
    if not s:
        return date.today().strftime("%Y-%m-%d")

    if re.fullmatch(r"\d{8}", s):
        try:
            dt = datetime.strptime(s, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
        try:
            dt = datetime.strptime(s, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    nums = re.sub(r"\D", "", s)
    if len(nums) >= 8:
        try:
            dt = datetime.strptime(nums[:8], "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return date.today().strftime("%Y-%m-%d")


def montar_nome_base_arquivo(*, data_exame: str, animal: str, tutor: str, clinica: str) -> str:
    d = _normalizar_data_str(data_exame)
    a = _limpar_texto_filename(animal)
    t = _limpar_texto_filename(tutor)
    c = _limpar_texto_filename(clinica)
    return f"{d}__{a}__{t}__{c}"
