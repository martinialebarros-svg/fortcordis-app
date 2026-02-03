# Páginas do menu principal (cada uma expõe render_*)
# Páginas já extraídas para módulos:
from app.pages.dashboard import render_dashboard
from app.pages.agendamentos import render_agendamentos

# As demais (Prontuário, Laudos, Prescrições, Financeiro, Cadastros, Configurações)
# ainda rodam no fortcordis_app.py; quando forem extraídas, adicione aqui:
# from app.pages.prontuario import render_prontuario
# from app.pages.laudos import render_laudos
# etc.

__all__ = [
    "render_dashboard",
    "render_agendamentos",
]
