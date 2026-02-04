# Páginas do menu principal (cada uma expõe render_*)
# Páginas já extraídas para módulos:
from app.pages.dashboard import render_dashboard
from app.pages.agendamentos import render_agendamentos
from app.pages.laudos import render_laudos
from app.pages.prontuario import render_prontuario
from app.pages.prescricoes import render_prescricoes
from app.pages.financeiro import render_financeiro
from app.pages.cadastros import render_cadastros
from app.pages.configuracoes import render_configuracoes

__all__ = [
    "render_dashboard",
    "render_agendamentos",
    "render_laudos",
    "render_prontuario",
    "render_prescricoes",
    "render_financeiro",
    "render_cadastros",
    "render_configuracoes",
]
