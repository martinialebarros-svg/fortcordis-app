# Configuração central: versão, caminhos, CSS
from pathlib import Path

VERSAO_DEPLOY = "2026-02-01"
_ROOT = Path(__file__).resolve().parent.parent
PASTA_DB = _ROOT
DB_PATH = _ROOT / "fortcordis.db"

CSS_GLOBAL = """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    h1 { font-size: 1.85rem !important; font-weight: 600 !important; color: #1e3a5f !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.35rem !important; font-weight: 600 !important; color: #2c5282 !important; }
    h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #2d3748 !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2c5282 100%); }
    [data-testid="stSidebar"] .stMarkdown { color: rgba(255,255,255,0.95); }
    [data-testid="stSidebar"] h1 { color: #fff !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: rgba(255,255,255,0.9) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }
    [data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.95) !important; }
    [data-testid="stSidebar"] .stRadio label div { color: inherit !important; }
    [data-testid="stMetric"] { background: #f7fafc; padding: 1rem 1.25rem; border-radius: 8px; border-left: 4px solid #2c5282; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    [data-testid="stMetric"] label { font-weight: 600 !important; color: #2d3748 !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%); font-weight: 600; border-radius: 6px; }
    .stButton > button[kind="primary"]:hover { box-shadow: 0 4px 12px rgba(44,82,130,0.35); }
    .streamlit-expanderHeader { background: #f7fafc; border-radius: 6px; }
    hr { margin: 1.25rem 0 !important; border-color: #e2e8f0 !important; }
    [data-testid="stAlert"] { border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px 6px 0 0; padding: 0.5rem 1rem; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #edf2f7; }
    [data-testid="stSidebar"] .stCaptionContainer { color: rgba(255,255,255,0.75); }
    [data-testid="stSidebar"] [data-testid="stAlert"] { background: rgba(255,255,255,0.12) !important; color: #fff !important; border: 1px solid rgba(255,255,255,0.25); }
    [data-testid="stSidebar"] [data-testid="stAlert"] p { color: #fff !important; }
    [data-testid="stSidebar"] [data-testid="stAlert"] a { color: #a5d6ff !important; }
</style>
"""
