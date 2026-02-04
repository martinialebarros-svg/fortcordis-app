# Helpers para o módulo Laudos: frases (QUALI_DET, schema, migração), listagem e obter laudos do banco
import json
import copy
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

import streamlit as st

from app.config import DB_PATH
from app.utils import _norm_key
from app.laudos_refs import calcular_referencia_tabela

# Constantes para editor de frases
QUALI_DET = {
    "valvas": ["mitral", "tricuspide", "aortica", "pulmonar"],
    "camaras": ["ae", "ad", "ve", "vd"],
    "vasos": ["aorta", "art_pulmonar", "veias_pulmonares", "cava_hepaticas"],
    "funcao": ["sistolica_ve", "sistolica_vd", "diastolica", "sincronia"],
    "pericardio": ["efusao", "espessamento", "tamponamento"],
}

ROTULOS = {
    "mitral": "Mitral", "tricuspide": "Tricúspide", "aortica": "Aórtica", "pulmonar": "Pulmonar",
    "ae": "Átrio esquerdo", "ad": "Átrio direito", "ve": "Ventrículo esquerdo", "vd": "Ventrículo direito",
    "aorta": "Aorta", "art_pulmonar": "Artéria pulmonar", "veias_pulmonares": "Veias pulmonares", "cava_hepaticas": "Cava/Hepáticas",
    "sistolica_ve": "Sistólica VE", "sistolica_vd": "Sistólica VD", "diastolica": "Diastólica", "sincronia": "Sincronia",
    "efusao": "Efusão", "espessamento": "Espessamento", "tamponamento": "Sinais de tamponamento",
}

ARQUIVO_FRASES = str(Path.home() / "FortCordis" / "frases_personalizadas.json")


def garantir_schema_det_frase(entry: dict) -> dict:
    """Garante que entry tenha o formato com 'det' (detalhado) completo."""
    if "det" not in entry or not isinstance(entry["det"], dict):
        entry["det"] = {}
    for sec, itens in QUALI_DET.items():
        if sec not in entry["det"] or not isinstance(entry["det"][sec], dict):
            entry["det"][sec] = {}
        for it in itens:
            entry["det"][sec].setdefault(it, "")
    for c in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
        entry.setdefault(c, "")
    entry.setdefault("layout", "detalhado")
    return entry


def migrar_txt_para_det(entry: dict) -> dict:
    """Se a frase veio do modelo antigo, joga texto para subcampos do 'det'."""
    entry = garantir_schema_det_frase(entry)
    det = entry.get("det", {})

    def bloco_vazio(sec: str) -> bool:
        return not any((det.get(sec, {}).get(it, "") or "").strip() for it in QUALI_DET[sec])

    if bloco_vazio("valvas"):
        txt = (entry.get("valvas", "") or "").strip()
        if txt:
            det["valvas"]["mitral"] = txt
    if bloco_vazio("camaras"):
        txt = (entry.get("camaras", "") or "").strip()
        if txt:
            det["camaras"]["ae"] = txt
            det["camaras"]["ve"] = txt
    if bloco_vazio("vasos"):
        txt = (entry.get("vasos", "") or "").strip()
        if txt:
            det["vasos"]["aorta"] = txt
    if bloco_vazio("funcao"):
        txt = (entry.get("funcao", "") or "").strip()
        if txt:
            det["funcao"]["sistolica_ve"] = txt
    if bloco_vazio("pericardio"):
        txt = (entry.get("pericardio", "") or "").strip()
        if txt:
            det["pericardio"]["efusao"] = txt
    entry["det"] = det
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (det.get(sec, {}).get(it, "") or "")
    return entry


def det_para_txt(det: dict) -> dict:
    """Converte det{sec:{it:txt}} em txt_{sec}."""
    out = {}
    for sec, itens in QUALI_DET.items():
        linhas = []
        bloco = det.get(sec, {}) if isinstance(det, dict) else {}
        for it in itens:
            v = (bloco.get(it, "") or "").strip()
            if v:
                linhas.append(f"{ROTULOS.get(it, it)}: {v}")
        out[sec] = "\n".join(linhas).strip()
    return out


def frase_det(
    *,
    valvas=None, camaras=None, vasos=None, funcao=None, pericardio=None,
    resumo=None, ad_vd="", conclusao=""
):
    """Cria uma entrada de frase compatível com campos antigos e subcampos det."""
    valvas = valvas or {}
    camaras = camaras or {}
    vasos = vasos or {}
    funcao = funcao or {}
    pericardio = pericardio or {}
    resumo = resumo or {}
    entry = {
        "layout": "detalhado",
        "valvas": resumo.get("valvas", ""),
        "camaras": resumo.get("camaras", ""),
        "vasos": resumo.get("vasos", ""),
        "funcao": resumo.get("funcao", ""),
        "pericardio": resumo.get("pericardio", ""),
        "ad_vd": ad_vd or "",
        "conclusao": conclusao or "",
        "det": {
            "valvas": {k: "" for k in QUALI_DET["valvas"]},
            "camaras": {k: "" for k in QUALI_DET["camaras"]},
            "vasos": {k: "" for k in QUALI_DET["vasos"]},
            "funcao": {k: "" for k in QUALI_DET["funcao"]},
            "pericardio": {k: "" for k in QUALI_DET["pericardio"]},
        }
    }
    for k, v in valvas.items():
        entry["det"]["valvas"][k] = v
    for k, v in camaras.items():
        entry["det"]["camaras"][k] = v
    for k, v in vasos.items():
        entry["det"]["vasos"][k] = v
    for k, v in funcao.items():
        entry["det"]["funcao"][k] = v
    for k, v in pericardio.items():
        entry["det"]["pericardio"][k] = v
    for sec, itens in QUALI_DET.items():
        for it in itens:
            entry[f"q_{sec}_{it}"] = (entry["det"][sec].get(it, "") or "")
    return entry


def aplicar_frase_det_na_tela(frase: dict):
    """Joga os subcampos q_... da frase para o session_state."""
    if not isinstance(frase, dict):
        return
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
    txts = det_para_txt(det)
    for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos"]:
        if txts.get(sec):
            st.session_state[f"txt_{sec}"] = txts[sec]
    return True


def inferir_layout(entry: dict, chave: str) -> str:
    if chave == "Normal (Normal)":
        return "enxuto"
    layout = (entry.get("layout") or "").strip().lower()
    if layout in ("enxuto", "detalhado"):
        return layout
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


def _split_pat_grau(chave: str):
    """Quebra 'Patologia (Grau)' em (base, grau)."""
    s = (chave or "").strip()
    if s.endswith(")") and " (" in s:
        base, resto = s.rsplit(" (", 1)
        grau = resto[:-1].strip()
        return base.strip(), grau
    return s, ""


def _variantes_grau(grau: str) -> list:
    """Variações de grau para match robusto (Moderado/Moderada, etc.)."""
    g = (grau or "").strip()
    if not g:
        return [g]
    trocas = {
        "Moderada": ["Moderado"],
        "Moderado": ["Moderada"],
        "Severa": ["Severo", "Grave"],
        "Severo": ["Severa", "Grave"],
        "Grave": ["Severa", "Severo"],
    }
    return [g] + trocas.get(g, [])


def montar_chave_frase(patologia: str, grau_refluxo: str, grau_geral: str) -> str:
    if patologia == "Normal":
        return "Normal (Normal)"
    if patologia == "Endocardiose Mitral":
        return f"{patologia} ({grau_refluxo})"
    return f"{patologia} ({grau_geral})"


def obter_entry_frase(db: dict, chave: str):
    """Obtém a entry do banco tentando (1) exato, (2) normalizado e (3) variações de grau."""
    if not isinstance(db, dict):
        return None
    chave = (chave or "").strip()
    if not chave:
        return None
    if chave in db:
        return db.get(chave)
    base, grau = _split_pat_grau(chave)
    for g in _variantes_grau(grau):
        alt = f"{base} ({g})" if g else base
        if alt in db:
            return db.get(alt)
    alvo = _norm_key(chave)
    for k in db.keys():
        if _norm_key(k) == alvo:
            return db.get(k)
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
        for sec, itens in QUALI_DET.items():
            for it in itens:
                st.session_state[f"q_{sec}_{it}"] = ""
        for k in ["valvas", "camaras", "funcao", "pericardio", "vasos", "ad_vd", "conclusao"]:
            st.session_state[f"txt_{k}"] = (entry.get(k, "") or "").strip()
        return
    det = entry.get("det", {}) if isinstance(entry.get("det"), dict) else {}
    for sec, itens in QUALI_DET.items():
        for it in itens:
            st.session_state[f"q_{sec}_{it}"] = ""
    for sec, itens in QUALI_DET.items():
        bloco = det.get(sec, {}) if isinstance(det.get(sec), dict) else {}
        for it in itens:
            st.session_state[f"q_{sec}_{it}"] = (bloco.get(it, "") or "").strip()
    st.session_state["txt_conclusao"] = (entry.get("conclusao", "") or "").strip()
    txts = det_para_txt(det)
    for sec in ["valvas", "camaras", "funcao", "pericardio", "vasos"]:
        st.session_state[f"txt_{sec}"] = (txts.get(sec, "") or "").strip()


def complementar_regurgitacoes_nas_valvas(patologia: str = "", grau_mitral: str | None = None):
    """Complementa q_valvas_* com informação de regurgitação quando Vmax > 0 nas medidas."""
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


def analisar_criterios_clinicos(dados, peso, patologia, grau_refluxo, tem_congestao, grau_geral):
    """Gera texto qualitativo automático a partir de patologia/grau e medidas; preenche session_state."""
    chave = montar_chave_frase(patologia, grau_refluxo, grau_geral)
    db_frases = st.session_state.get("db_frases") or {}
    res_base = db_frases.get(chave, {})
    if not res_base and patologia != "Normal":
        for k, v in db_frases.items():
            if patologia in k:
                res_base = v.copy()
                break
    if not res_base:
        res_base = {"conclusao": f"{patologia}"}
    txt = res_base.copy()

    if patologia == "Endocardiose Mitral":
        conclusao_editor = (txt.get("conclusao") or "").strip()
        try:
            r_lvidd = calcular_referencia_tabela("LVIDd", peso)[0]
            l_lvidd = r_lvidd[1] if r_lvidd[1] else 999
            r_laao = calcular_referencia_tabela("LA_Ao", peso)[0]
            l_laao = r_laao[1] if r_laao[1] else 1.6
        except Exception:
            l_lvidd, l_laao = 999, 1.6
        val_laao, val_lvidd = dados.get("LA_Ao", 0), dados.get("LVIDd", 0)
        aum_ae, aum_ve = (val_laao >= l_laao), (val_lvidd > l_lvidd)
        if not (txt.get("valvas") or "").strip():
            txt["valvas"] = f"Valva mitral espessada. Insuficiência {grau_refluxo.lower()}."
        if not conclusao_editor:
            if tem_congestao:
                txt["conclusao"] = f"Endocardiose Mitral Estágio C (ACVIM). Refluxo {grau_refluxo}. Sinais de ICC."
            elif aum_ae and aum_ve:
                txt["conclusao"] = f"Endocardiose Mitral Estágio B2 (ACVIM). Refluxo {grau_refluxo} com remodelamento."
            elif aum_ae:
                txt["conclusao"] = f"Endocardiose Mitral (Refluxo {grau_refluxo}) com aumento atrial esquerdo."
            else:
                txt["conclusao"] = f"Endocardiose Mitral Estágio B1 (ACVIM). Refluxo {grau_refluxo}."

    dados_atual = st.session_state.get("dados_atuais", {}) or {}
    mr = float(dados_atual.get("MR_Vmax", 0.0) or 0.0)
    tr = float(dados_atual.get("TR_Vmax", 0.0) or 0.0)
    ar = float(dados_atual.get("AR_Vmax", 0.0) or 0.0)
    pr = float(dados_atual.get("PR_Vmax", 0.0) or 0.0)

    def append_if_needed(key: str, extra: str):
        extra = (extra or "").strip()
        if not extra:
            return
        atual = (st.session_state.get(key, "") or "").strip()
        if extra.lower() in atual.lower():
            return
        st.session_state[key] = (atual + ("\n" if atual else "") + extra).strip()

    if mr > 0:
        append_if_needed("q_valvas_mitral", f"Refluxo mitral presente ao Doppler (Vmax {mr:.2f} m/s).")
    if mr > 0 and patologia == "Endocardiose Mitral" and grau_refluxo:
        append_if_needed("q_valvas_mitral", f"Refluxo mitral {grau_refluxo.lower()} ao Doppler (Vmax {mr:.2f} m/s).")
    if tr > 0:
        append_if_needed("q_valvas_tricuspide", f"Refluxo tricúspide presente ao Doppler (Vmax {tr:.2f} m/s).")
    if ar > 0:
        append_if_needed("q_valvas_aortica", f"Refluxo aórtico presente ao Doppler (Vmax {ar:.2f} m/s).")
    if pr > 0:
        append_if_needed("q_valvas_pulmonar", f"Refluxo pulmonar presente ao Doppler (Vmax {pr:.2f} m/s).")

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
    set_if_empty("q_valvas_mitral", txt_valvas)
    set_if_empty("q_camaras_ae", txt_camaras)
    set_if_empty("q_camaras_ve", txt_camaras)
    set_if_empty("q_camaras_ad", txt_ad_vd)
    set_if_empty("q_camaras_vd", txt_ad_vd)
    set_if_empty("q_funcao_sistolica_ve", txt_funcao)
    set_if_empty("q_pericardio_efusao", txt_pericardio)
    set_if_empty("q_vasos_aorta", txt_vasos)


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
        if not bloco:
            bloco = (st.session_state.get(f"txt_{sec}", "") or "").strip()
        saida[sec] = bloco
    return saida


def carregar_frases(arquivo_frases: str, frases_default: dict):
    """Carrega frases do JSON; usa frases_default como base e merge do arquivo."""
    if not os.path.exists(arquivo_frases):
        Path(arquivo_frases).parent.mkdir(parents=True, exist_ok=True)
        with open(arquivo_frases, "w", encoding="utf-8") as f:
            json.dump(frases_default, f, indent=4, ensure_ascii=False)
        base = copy.deepcopy(frases_default)
    else:
        try:
            with open(arquivo_frases, "r", encoding="utf-8") as f:
                base = {**frases_default, **json.load(f)}
        except Exception:
            base = copy.deepcopy(frases_default)
    for k in list(base.keys()):
        entry = base[k]
        entry = garantir_schema_det_frase(entry)
        entry = migrar_txt_para_det(entry)
        entry["layout"] = inferir_layout(entry, k)
        base[k] = entry
    return base


def contar_laudos_do_banco():
    """Total de laudos em todas as tabelas (eco, eletro, pressão)."""
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
    """Preenche nome_paciente, nome_clinica, nome_tutor nos laudos a partir das tabelas vinculadas."""
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
    """Lista exames (laudos) do banco com tutor e clínica."""
    try:
        _backfill_nomes_laudos()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        out = []
        for tabela in ("laudos_ecocardiograma", "laudos_eletrocardiograma", "laudos_pressao_arterial"):
            try:
                cur.execute(f"PRAGMA table_info({tabela})")
                cols = [r[1] for r in cur.fetchall()]
                col_arquivo = "arquivo_json" if "arquivo_json" in cols else "arquivo_xml"
                sel_clinica = "COALESCE(c.nome, cp.nome, l.nome_clinica, '') AS clinica" if "nome_clinica" in cols else "COALESCE(c.nome, cp.nome, '') AS clinica"
                sel_tutor = "COALESCE(t.nome, l.nome_tutor, '') AS tutor" if "nome_tutor" in cols else "COALESCE(t.nome, '') AS tutor"
                query = f"""
                    SELECT l.id, l.tipo_exame,
                        COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '') AS animal,
                        l.data_exame AS data, {sel_clinica}, {sel_tutor},
                        l.{col_arquivo} AS arquivo_json, l.arquivo_pdf AS arquivo_pdf
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
                        params.extend([f"%{clinica_filtro.strip()}%", f"%{clinica_filtro.strip()}%", f"%{clinica_filtro.strip()}%"])
                    else:
                        query += " AND (UPPER(COALESCE(c.nome, '')) LIKE UPPER(?) OR UPPER(COALESCE(cp.nome, '')) LIKE UPPER(?))"
                        params.extend([f"%{clinica_filtro.strip()}%", f"%{clinica_filtro.strip()}%"])
                if animal_filtro and str(animal_filtro).strip():
                    query += " AND UPPER(COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '')) LIKE UPPER(?)"
                    params.append(f"%{animal_filtro.strip()}%")
                if busca_livre and str(busca_livre).strip():
                    termo = f"%{busca_livre.strip()}%"
                    parte_clinica = "COALESCE(c.nome, cp.nome, l.nome_clinica, '')" if "nome_clinica" in cols else "COALESCE(c.nome, cp.nome, '')"
                    parte_tutor = "COALESCE(t.nome, l.nome_tutor, '')" if "nome_tutor" in cols else "COALESCE(t.nome, '')"
                    query += f" AND (UPPER(COALESCE(NULLIF(TRIM(l.nome_paciente), ''), p.nome, '')) LIKE UPPER(?) OR UPPER({parte_tutor}) LIKE UPPER(?) OR UPPER({parte_clinica}) LIKE UPPER(?))"
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


def listar_laudos_arquivos_do_banco(tutor_filtro=None, clinica_filtro=None, animal_filtro=None, busca_livre=None):
    """Lista exames da tabela laudos_arquivos."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laudos_arquivos'")
        if not cur.fetchone():
            conn.close()
            return []
        query = """
            SELECT id, data_exame AS data, nome_clinica AS clinica, nome_animal AS animal,
                   nome_tutor AS tutor, tipo_exame, nome_base
            FROM laudos_arquivos WHERE 1=1
        """
        params = []
        if tutor_filtro and str(tutor_filtro).strip():
            query += " AND UPPER(COALESCE(nome_tutor,'')) LIKE UPPER(?)"
            params.append(f"%{tutor_filtro.strip()}%")
        if clinica_filtro and str(clinica_filtro).strip():
            query += " AND UPPER(COALESCE(nome_clinica,'')) LIKE UPPER(?)"
            params.append(f"%{clinica_filtro.strip()}%")
        if animal_filtro and str(animal_filtro).strip():
            query += " AND UPPER(COALESCE(nome_animal,'')) LIKE UPPER(?)"
            params.append(f"%{animal_filtro.strip()}%")
        if busca_livre and str(busca_livre).strip():
            termo = f"%{busca_livre.strip()}%"
            query += " AND (UPPER(COALESCE(nome_animal,'')) LIKE UPPER(?) OR UPPER(COALESCE(nome_tutor,'')) LIKE UPPER(?) OR UPPER(COALESCE(nome_clinica,'')) LIKE UPPER(?))"
            params.extend([termo, termo, termo])
        query += " ORDER BY data_exame DESC, id DESC"
        cur.execute(query, params)
        out = [dict(row) for row in cur.fetchall()]
        for r in out:
            r["id_laudo_arquivo"] = r["id"]
            r["tipo_exame"] = r.get("tipo_exame") or "ecocardiograma"
        conn.close()
        return out
    except Exception:
        return []


def contar_laudos_arquivos_do_banco():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM laudos_arquivos")
        n = cur.fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def obter_laudo_arquivo_por_id(laudo_arquivo_id):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nome_base, conteudo_json, conteudo_pdf FROM laudos_arquivos WHERE id=?",
            (laudo_arquivo_id,),
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def obter_imagens_laudo_arquivo(laudo_arquivo_id):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "SELECT nome_arquivo, conteudo FROM laudos_arquivos_imagens WHERE laudo_arquivo_id=? ORDER BY ordem, id",
            (laudo_arquivo_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [{"nome_arquivo": r[0] or f"imagem_{i}.jpg", "conteudo": r[1] or b""} for i, r in enumerate(rows)]
    except Exception:
        return []
