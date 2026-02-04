# Referências e tabelas para laudos ecocardiográficos (caninos/felinos)
# Fase B: extraído do fortcordis_app.py
import os
from pathlib import Path
import pandas as pd
import streamlit as st

from app.config import PASTA_DB, ARQUIVO_REF, ARQUIVO_REF_FELINOS
from app.utils import nome_proprio_ptbr

_PATH_REF_CANINOS = PASTA_DB / ARQUIVO_REF if hasattr(PASTA_DB, "__truediv__") else Path(str(PASTA_DB)) / ARQUIVO_REF
_PATH_REF_FELINOS = PASTA_DB / ARQUIVO_REF_FELINOS if hasattr(PASTA_DB, "__truediv__") else Path(str(PASTA_DB)) / ARQUIVO_REF_FELINOS

PARAMS = {
    "Ao":      ("Aorta", "mm", "Ao"),
    "LA":      ("Átrio esquerdo", "mm", "LA"),
    "LA_Ao":   ("AE/Ao (Átrio esquerdo/Aorta)", "", "LA_Ao"),
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
    "Grad_Ao":   ("Gradiente aorta", "mmHg", None),
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
    s = str(especie_txt or "").strip()
    if not s:
        return ""
    sl = s.lower()
    if especie_is_felina(sl):
        return "Felina"
    if any(x in sl for x in ["can", "cao", "cão", "dog", "canine"]):
        return "Canina"
    return nome_proprio_ptbr(s)

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
    df = pd.DataFrame(TABELA_REF_FELINOS_DEFAULT)
    cols_num = [c for c in df.columns if c != "Peso"]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Peso"] = pd.to_numeric(df["Peso"], errors="coerce")
    df = df.dropna(subset=["Peso"]).sort_values("Peso").reset_index(drop=True)
    return df

def limpar_e_converter_tabela_felinos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "Peso" not in df.columns:
        for alt in ["Peso (kg)", "Peso_kg", "peso", "PESO"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "Peso"})
                break
    colunas_esperadas = [
        "Peso", "IVSd_Min", "IVSd_Max", "LVIDd_Min", "LVIDd_Max", "LVPWd_Min", "LVPWd_Max",
        "IVSs_Min", "IVSs_Max", "LVIDs_Min", "LVIDs_Max", "LVPWs_Min", "LVPWs_Max",
        "FS_Min", "FS_Max", "EF_Min", "EF_Max", "LA_Min", "LA_Max", "Ao_Min", "Ao_Max",
        "LA_Ao_Min", "LA_Ao_Max",
    ]
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = float("nan")
    for col in colunas_esperadas:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Peso"]).sort_values("Peso").reset_index(drop=True)
    return df[colunas_esperadas]

@st.cache_data(show_spinner=False, max_entries=3, ttl=3600)
def carregar_tabela_referencia_felinos_cached() -> pd.DataFrame:
    path = _PATH_REF_FELINOS
    if path.exists():
        try:
            df = pd.read_csv(path)
            df = limpar_e_converter_tabela_felinos(df)
            return df
        except Exception:
            df = gerar_tabela_padrao_felinos()
            try:
                df.to_csv(path, index=False)
            except Exception:
                pass
            return df
    df = gerar_tabela_padrao_felinos()
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass
    return df

def limpar_e_converter_tabela(df):
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df

def carregar_tabela_referencia():
    path = _PATH_REF_CANINOS
    if path.exists():
        try:
            df = pd.read_csv(path)
            df = limpar_e_converter_tabela(df)
            cols_check = ["LVIDd_Min", "MV_Slope_Max", "TR_Vmax_Max", "EDV_Max", "IVSs_Max"]
            for c in cols_check:
                if c not in df.columns:
                    df[c] = 0.0
                    df[c.replace("_Max", "_Min")] = 0.0
            return df
        except Exception:
            return gerar_tabela_padrao()
    df = gerar_tabela_padrao()
    try:
        df.to_csv(path, index=False)
    except Exception:
        pass
    return df

@st.cache_data(show_spinner=False, max_entries=3, ttl=3600)
def carregar_tabela_referencia_cached():
    return carregar_tabela_referencia()

def calcular_referencia_tabela(parametro, peso_kg, df=None):
    if df is None:
        df = st.session_state.get("df_ref")
    if df is None:
        return None, ""
    try:
        df = df.copy()
    except Exception:
        return None, ""
    try:
        peso_kg = float(str(peso_kg).replace(",", "."))
    except Exception:
        return None, ""
    if "Peso (kg)" not in df.columns:
        if "Peso" in df.columns:
            df = df.rename(columns={"Peso": "Peso (kg)"})
        else:
            return None, ""
    mapa = {
        "LVIDd": ("LVIDd_Min", "LVIDd_Max"), "Ao": ("Ao_Min", "Ao_Max"), "LA": ("LA_Min", "LA_Max"),
        "IVSd": ("IVSd_Min", "IVSd_Max"), "LVPWd": ("LVPWd_Min", "LVPWd_Max"), "LVIDs": ("LVIDs_Min", "LVIDs_Max"),
        "IVSs": ("IVSs_Min", "IVSs_Max"), "LVPWs": ("LVPWs_Min", "LVPWs_Max"),
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
    df = df.sort_values("Peso (kg)").reset_index(drop=True)
    df["Peso (kg)"] = pd.to_numeric(df["Peso (kg)"], errors="coerce")
    df[col_min] = pd.to_numeric(df[col_min], errors="coerce")
    df[col_max] = pd.to_numeric(df[col_max], errors="coerce")
    if peso_kg in set(df["Peso (kg)"].dropna().values.tolist()):
        row = df[df["Peso (kg)"] == peso_kg].iloc[0]
        min_val, max_val = row[col_min], row[col_max]
    else:
        row_new = {"Peso (kg)": peso_kg}
        for c in df.columns:
            if c != "Peso (kg)":
                row_new[c] = pd.NA
        df_temp = pd.concat([df, pd.DataFrame([row_new])], ignore_index=True)
        df_temp = df_temp.sort_values("Peso (kg)").reset_index(drop=True)
        df_temp = df_temp.apply(pd.to_numeric, errors="coerce")
        df_temp = df_temp.interpolate(method="linear", limit_direction="both")
        row = df_temp[(df_temp["Peso (kg)"] - peso_kg).abs() < 1e-9].iloc[0]
        min_val, max_val = row[col_min], row[col_max]
    if pd.isna(min_val) or pd.isna(max_val):
        return None, "--"
    if float(min_val) == 0.0 and float(max_val) == 0.0:
        return None, "--"
    return (float(min_val), float(max_val)), f"{float(min_val):.2f} - {float(max_val):.2f}"

def interpretar(valor, ref_tuple):
    if not ref_tuple or (ref_tuple[0] == 0 and ref_tuple[1] == 0):
        return ""
    min_v, max_v = ref_tuple
    if valor < min_v:
        return "Reduzido"
    if valor > max_v:
        return "Aumentado"
    return "Normal"

DIVEDN_REF_MIN = 1.27
DIVEDN_REF_MAX = 1.85
DIVEDN_REF_TXT = f"{DIVEDN_REF_MIN:.2f}-{DIVEDN_REF_MAX:.2f}"

def interpretar_divedn(divedn: float) -> str:
    try:
        v = float(divedn)
    except Exception:
        return ""
    if v <= 0:
        return ""
    if v < DIVEDN_REF_MIN:
        return "Abaixo do esperado"
    if v <= 1.70:
        return "Normal"
    if v <= DIVEDN_REF_MAX:
        return "Limítrofe"
    if v <= 2.00:
        return "Dilatação leve"
    if v <= 2.30:
        return "Dilatação moderada"
    return "Dilatação importante"
