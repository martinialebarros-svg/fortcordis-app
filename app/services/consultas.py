# Serviço de consultas: listar recentes, criar consulta
import sqlite3
from typing import Tuple, Optional

import pandas as pd

from app.config import DB_PATH


def listar_consultas_recentes(limite: int = 10) -> pd.DataFrame:
    """
    Retorna as consultas mais recentes com paciente, tutor e veterinário.
    Colunas: id, Data, Paciente, Tutor, Tipo, Diagnóstico, Veterinário.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql_query("""
            SELECT 
                c.id,
                c.data_consulta as 'Data',
                p.nome as 'Paciente',
                t.nome as 'Tutor',
                c.tipo_atendimento as 'Tipo',
                c.diagnostico_presuntivo as 'Diagnóstico',
                u.nome as 'Veterinário'
            FROM consultas c
            JOIN pacientes p ON c.paciente_id = p.id
            JOIN tutores t ON c.tutor_id = t.id
            JOIN usuarios u ON c.veterinario_id = u.id
            ORDER BY c.data_consulta DESC, c.id DESC
            LIMIT ?
        """, conn, params=(limite,))
        return df
    finally:
        conn.close()


def criar_consulta(
    paciente_id: int,
    tutor_id: int,
    veterinario_id: int,
    data_consulta: str,
    hora_consulta: str,
    tipo_atendimento: str,
    motivo_consulta: str,
    anamnese: str,
    historico_atual: str,
    alimentacao: str,
    ambiente: str,
    comportamento: str,
    peso_kg: float,
    temperatura_c: float,
    frequencia_cardiaca: int,
    frequencia_respiratoria: int,
    tpc: str,
    mucosas: str,
    hidratacao: str,
    linfonodos: str,
    auscultacao_cardiaca: str,
    auscultacao_respiratoria: str,
    palpacao_abdominal: str,
    exame_fisico_geral: str,
    diagnostico_presuntivo: str,
    diagnostico_diferencial: str,
    diagnostico_definitivo: str,
    conduta_terapeutica: str,
    exames_solicitados: str,
    procedimentos_realizados: str,
    orientacoes: str,
    prognostico: str,
    data_retorno: str,
    observacoes: str,
    atualizar_peso: bool = True,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Insere uma consulta no banco. Opcionalmente atualiza peso_kg do paciente.
    Retorna (consulta_id, None) em sucesso ou (None, mensagem_erro).
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consultas (
                paciente_id, tutor_id, data_consulta, hora_consulta, tipo_atendimento,
                motivo_consulta, anamnese, historico_atual, alimentacao, ambiente, comportamento,
                peso_kg, temperatura_c, frequencia_cardiaca, frequencia_respiratoria,
                tpc, mucosas, hidratacao, linfonodos, auscultacao_cardiaca, auscultacao_respiratoria,
                palpacao_abdominal, exame_fisico_geral,
                diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
                conduta_terapeutica, exames_solicitados, procedimentos_realizados, orientacoes,
                prognostico, data_retorno, observacoes,
                veterinario_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paciente_id, tutor_id, data_consulta, hora_consulta, tipo_atendimento,
            motivo_consulta, anamnese, historico_atual or anamnese, alimentacao, ambiente, comportamento,
            peso_kg, temperatura_c, frequencia_cardiaca, frequencia_respiratoria,
            tpc, mucosas, hidratacao, linfonodos, auscultacao_cardiaca, auscultacao_respiratoria,
            palpacao_abdominal, exame_fisico_geral,
            diagnostico_presuntivo, diagnostico_diferencial, diagnostico_definitivo,
            conduta_terapeutica, exames_solicitados, procedimentos_realizados, orientacoes,
            prognostico, data_retorno, observacoes,
            veterinario_id, "finalizado"
        ))
        consulta_id = cursor.lastrowid
        if atualizar_peso and peso_kg and peso_kg > 0:
            try:
                cursor.execute("UPDATE pacientes SET peso_kg = ? WHERE id = ?", (peso_kg, paciente_id))
            except Exception:
                pass
        conn.commit()
        return (consulta_id, None)
    except Exception as e:
        return (None, str(e))
    finally:
        conn.close()
