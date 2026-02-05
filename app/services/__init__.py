# Camada de serviços: lógica reutilizável (consultas, pacientes, financeiro, etc.)
from app.services.consultas import listar_consultas_recentes, criar_consulta
from app.services.pacientes import (
    listar_pacientes_com_tutor,
    listar_pacientes_tabela,
    buscar_pacientes,
    atualizar_peso_paciente,
)
from app.services.financeiro import (
    fluxo_caixa_periodo,
    demonstrativo_mensal,
    lucro_realizado,
    clientes_em_debito,
    creditos_clientes,
    consumo_clinicas,
    desempenho_colaboradores,
)

__all__ = [
    "listar_consultas_recentes",
    "criar_consulta",
    "listar_pacientes_com_tutor",
    "listar_pacientes_tabela",
    "buscar_pacientes",
    "atualizar_peso_paciente",
    "fluxo_caixa_periodo",
    "demonstrativo_mensal",
    "lucro_realizado",
    "clientes_em_debito",
    "creditos_clientes",
    "consumo_clinicas",
    "desempenho_colaboradores",
]
