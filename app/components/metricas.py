# Componente: linha de métricas (dashboard-style)
from typing import List, Tuple, Union

import streamlit as st


def metricas_linha(
    metricas: List[Tuple[str, Union[str, int, float], Union[str, int, float, None]]],
) -> None:
    """
    Exibe uma linha de st.metric, uma por coluna.
    Cada item de metricas é (label, value, delta) ou (label, value) (delta será None).
    Ex.: metricas_linha([("Agendamentos Hoje", 5, None), ("Contas a Receber", "R$ 1.200,00", None)])
    """
    if not metricas:
        return
    cols = st.columns(len(metricas))
    for col, item in zip(cols, metricas):
        with col:
            if len(item) >= 3:
                label, value, delta = item[0], item[1], item[2]
                st.metric(label, value, delta)
            else:
                label, value = item[0], item[1]
                st.metric(label, value)
