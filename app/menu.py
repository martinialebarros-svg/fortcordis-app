# Registro central do menu principal — facilita adicionar/remover/reordenar páginas
# Cada item: (rótulo na sidebar, módulo Python, nome da função de render, handler especial ou None)
# Handler especial "laudos" = app principal monta laudos_deps e chama render_laudos(laudos_deps)

MENU_ITEMS = [
    ("🏠 Dashboard", "app.pages.dashboard", "render_dashboard", None),
    ("📅 Agendamentos", "app.pages.agendamentos", "render_agendamentos", None),
    ("📋 Prontuário", "app.pages.prontuario", "render_prontuario", None),
    ("🩺 Laudos e Exames", "app.pages.laudos", "render_laudos", "laudos"),
    ("💊 Prescrições", "app.pages.prescricoes", "render_prescricoes", None),
    ("💰 Financeiro", "app.pages.financeiro", "render_financeiro", None),
    ("🏢 Cadastros", "app.pages.cadastros", "render_cadastros", None),
    ("⚙️ Configurações", "app.pages.configuracoes", "render_configuracoes", None),
]


def get_menu_labels():
    """Lista de rótulos na ordem do menu (para st.sidebar.radio)."""
    return [item[0] for item in MENU_ITEMS]
