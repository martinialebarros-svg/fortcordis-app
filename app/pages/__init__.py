# Páginas do menu principal (cada uma expõe render_*)
# Páginas já extraídas para módulos:
from app.pages.dashboard import render_dashboard
from app.pages.agendamentos import render_agendamentos
from app.pages.laudos import render_laudos

# As demais (Prontuário, Prescrições, Financeiro, Cadastros, Configurações)
# ainda rodam no fortcordis_app.py; quando forem extraídas, adicione aqui.

__all__ = [
    "render_dashboard",
    "render_agendamentos",
    "render_laudos",
]
