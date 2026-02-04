# Camada de serviços: lógica reutilizável (consultas, pacientes, etc.)
from app.services.consultas import listar_consultas_recentes, criar_consulta
from app.services.pacientes import (
    listar_pacientes_com_tutor,
    listar_pacientes_tabela,
    buscar_pacientes,
    atualizar_peso_paciente,
)

__all__ = [
    "listar_consultas_recentes",
    "criar_consulta",
    "listar_pacientes_com_tutor",
    "listar_pacientes_tabela",
    "buscar_pacientes",
    "atualizar_peso_paciente",
]
