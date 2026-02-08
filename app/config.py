# Configuração central: versão, caminhos, CSS, logging
import logging
from datetime import date, datetime
from pathlib import Path

VERSAO_DEPLOY = "2026-02-01"


def formatar_data_br(val):
    """
    Formata data para exibição no padrão brasileiro dd/mm/aaaa.
    Aceita: str (YYYY-MM-DD ou dd/mm/yyyy), date, datetime, None.
    Retorna string dd/mm/yyyy ou '—' se vazio/None.
    """
    if val is None or (isinstance(val, str) and not val.strip()):
        return "—"
    if isinstance(val, (date, datetime)):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()[:10]
    if not s:
        return "—"
    # Já está em dd/mm/yyyy (ex.: 31/01/2026)
    if "/" in s and len(s) >= 8:
        parts = s.split("/")
        if len(parts) == 3 and len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) == 4:
            return s[:10] if len(s) >= 10 else s
    # ISO YYYY-MM-DD
    if "-" in s and len(s) >= 10:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s

# Logging: nível INFO para módulos app.*; erros vão para stderr / Streamlit Cloud logs
def _setup_app_logging():
    log = logging.getLogger("app")
    if not log.handlers:
        log.setLevel(logging.INFO)
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
        log.addHandler(h)
        log.propagate = False  # evita duplicar no root
_setup_app_logging()
_ROOT = Path(__file__).resolve().parent.parent
PASTA_DB = _ROOT
DB_PATH = _ROOT / "fortcordis.db"

# Laudos: pastas e arquivos de referência (centralizado para Fase B)
PASTA_LAUDOS = Path.home() / "FortCordis" / "Laudos"
PASTA_LAUDOS.mkdir(parents=True, exist_ok=True)
ARQUIVO_REF = "tabela_referencia_caninos.csv"
ARQUIVO_REF_FELINOS = "tabela_referencia_felinos.csv"

CSS_GLOBAL = """
<style>
    :root {
        --fc-primary: #1d4ed8;
        --fc-primary-dark: #1e3a8a;
        --fc-bg: #f5f8ff;
        --fc-surface: #ffffff;
        --fc-border: #dbe7ff;
        --fc-text: #10213f;
        --fc-muted: #4b5f84;
    }

    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px;}
    .stApp { background: linear-gradient(180deg, #f5f8ff 0%, #eef3ff 100%); color: var(--fc-text); }

    h1, h2, h3 { letter-spacing: -0.01em; }
    h1 { font-size: 1.9rem !important; font-weight: 700 !important; color: var(--fc-primary-dark) !important; }
    h2 { font-size: 1.35rem !important; font-weight: 650 !important; color: #17356e !important; }
    h3 { font-size: 1.08rem !important; font-weight: 600 !important; color: #223555 !important; }

    [data-testid="stSidebar"] { background: linear-gradient(180deg, #16336b 0%, #1d4ed8 100%); border-right: 1px solid rgba(255,255,255,0.08); }
    [data-testid="stSidebar"] * { color: #f8fbff; }
    [data-testid="stSidebar"] .stCaptionContainer { color: rgba(248, 251, 255, 0.75); }

    [data-testid="stMetric"] {
        background: var(--fc-surface);
        border: 1px solid var(--fc-border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 24px rgba(17, 36, 79, 0.08);
    }

    .fc-card {
        background: var(--fc-surface);
        border: 1px solid var(--fc-border);
        border-radius: 14px;
        box-shadow: 0 12px 24px rgba(17, 36, 79, 0.08);
        padding: 1rem 1.15rem;
        margin-bottom: 1rem;
    }

    .stButton > button {
        border-radius: 12px;
        border: 1px solid #c8d8ff;
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--fc-primary) 0%, #2563eb 100%);
        border: 0;
        color: #fff;
    }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stDateInput input,
    .stNumberInput input {
        border-radius: 10px !important;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .35rem; }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        background: #ebf2ff;
        height: 2.3rem;
        padding-left: .9rem;
        padding-right: .9rem;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #dbe7ff;
        color: #0f2d66;
        font-weight: 600;
    }

    [data-testid="stAlert"] { border-radius: 10px; }
</style>
"""

