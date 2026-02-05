# Validação de identificadores SQL para prevenir SQL injection
# Todos os nomes de tabelas e colunas usados em f-strings DEVEM ser validados aqui

from __future__ import annotations


# Tabelas permitidas no sistema (whitelist)
TABELAS_PERMITIDAS: frozenset[str] = frozenset({
    # Cadastros principais
    "clinicas",
    "clinicas_parceiras",
    "tutores",
    "pacientes",
    # Laudos
    "laudos_ecocardiograma",
    "laudos_eletrocardiograma",
    "laudos_pressao_arterial",
    "laudos_arquivos",
    "laudos_arquivos_imagens",
    # Prontuario
    "consultas",
    # Auth / RBAC
    "usuarios",
    "papeis",
    "usuario_papel",
    "permissoes",
    "papel_permissao",
    "usuario_permissao",
    "sessoes",
    "sessoes_persistentes",
    "login_tokens",
    "reset_senha_tokens",
    # Financeiro
    "financeiro",
    "servicos",
    # Agendamentos
    "agendamentos",
    # Prescricoes
    "prescricoes",
    "prescricao_itens",
    # Medicamentos
    "medicamentos",
})


# Colunas permitidas em ALTER TABLE / UPDATE dinâmico
COLUNAS_PERMITIDAS: frozenset[str] = frozenset({
    # Pacientes
    "ativo", "peso_kg", "microchip", "observacoes", "chip",
    # Tutores
    "whatsapp",
    # Laudos (colunas adicionadas por migração)
    "nome_clinica", "nome_tutor", "nome_paciente",
    "arquivo_json", "arquivo_pdf",
    # Genéricas
    "nome", "telefone", "raca", "sexo", "nascimento",
    "email", "endereco", "bairro", "cidade", "cnpj",
    "inscricao_estadual", "responsavel_veterinario", "crmv_responsavel",
    "data_cadastro",
})


def validar_tabela(tabela: str) -> str:
    """Valida que o nome da tabela está na whitelist. Retorna o nome ou levanta ValueError."""
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError(f"Nome de tabela não permitido: {tabela!r}")
    return tabela


def validar_coluna(coluna: str) -> str:
    """Valida que o nome da coluna está na whitelist. Retorna o nome ou levanta ValueError."""
    if coluna not in COLUNAS_PERMITIDAS:
        raise ValueError(f"Nome de coluna não permitido: {coluna!r}")
    return coluna
