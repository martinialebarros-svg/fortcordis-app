# Componente: tabela de dados (dataframe) com opção de esconder colunas e caption
from typing import Optional, List, Union

import pandas as pd
import streamlit as st


def tabela_tabular(
    df: pd.DataFrame,
    caption: Optional[str] = None,
    drop_colunas: Optional[Union[str, List[str]]] = "id",
    empty_message: Optional[str] = None,
    **dataframe_kwargs,
) -> None:
    """
    Exibe um DataFrame como tabela Streamlit com layout padrão do app.
    - drop_colunas: coluna(s) a remover antes de exibir (ex.: "id" ou ["id", "created_at"]).
      Use None para não remover nenhuma.
    - caption: texto abaixo da tabela (ex.: "Total: 10 itens").
    - empty_message: se o df estiver vazio, exibe st.info(empty_message) em vez da tabela.
    - **dataframe_kwargs: repassados para st.dataframe (ex.: key=...).
    """
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        if empty_message:
            st.info(empty_message)
        return
    out = df.copy()
    if drop_colunas:
        cols = [drop_colunas] if isinstance(drop_colunas, str) else drop_colunas
        for c in cols:
            if c in out.columns:
                out = out.drop(columns=[c])
    kwargs = {"use_container_width": True, "hide_index": True, **dataframe_kwargs}
    st.dataframe(out, **kwargs)
    if caption:
        st.caption(caption)
