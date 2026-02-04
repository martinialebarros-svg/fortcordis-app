# Construção centralizada do namespace deps para a página Laudos (Fase B)
# build_laudos_deps() importa dos módulos app e monta o SimpleNamespace.
# O app principal pode chamar build_laudos_deps() sem argumentos.
from types import SimpleNamespace

from app.config import PASTA_LAUDOS, ARQUIVO_REF, ARQUIVO_REF_FELINOS
from app.laudos_refs import (
    PARAMS,
    get_grupos_por_especie,
    normalizar_especie_label,
    especie_is_felina,
    gerar_tabela_padrao,
    gerar_tabela_padrao_felinos,
    limpar_e_converter_tabela,
    limpar_e_converter_tabela_felinos,
    carregar_tabela_referencia_cached,
    carregar_tabela_referencia_felinos_cached,
    listar_registros_arquivados_cached,
    calcular_referencia_tabela,
    interpretar,
    interpretar_divedn,
    DIVEDN_REF_TXT,
)
from app.laudos_pdf import (
    montar_nome_base_arquivo,
    _caminho_marca_dagua,
    obter_imagens_para_pdf,
    _normalizar_data_str,
)
from app.laudos_banco import salvar_laudo_no_banco
from app.laudos_helpers import (
    montar_qualitativa,
    montar_chave_frase,
    carregar_frases as _carregar_frases_impl,
    ARQUIVO_FRASES,
)


def _carregar_frases():
    """Wrapper sem argumentos para uso em deps (usa ARQUIVO_FRASES e dict vazio)."""
    return _carregar_frases_impl(ARQUIVO_FRASES, {})


# Chaves que a página Laudos espera em deps (para documentação e validação futura)
LAUDOS_DEPS_KEYS = [
    "PASTA_LAUDOS", "ARQUIVO_REF", "ARQUIVO_REF_FELINOS", "PARAMS",
    "get_grupos_por_especie", "normalizar_especie_label", "montar_nome_base_arquivo",
    "calcular_referencia_tabela", "interpretar", "interpretar_divedn", "DIVEDN_REF_TXT",
    "listar_registros_arquivados_cached", "salvar_laudo_no_banco", "obter_imagens_para_pdf",
    "montar_qualitativa", "_caminho_marca_dagua", "montar_chave_frase", "carregar_frases",
    "gerar_tabela_padrao", "gerar_tabela_padrao_felinos",
    "limpar_e_converter_tabela", "limpar_e_converter_tabela_felinos",
    "carregar_tabela_referencia_cached", "carregar_tabela_referencia_felinos_cached",
    "_normalizar_data_str", "especie_is_felina", "calcular_valor_final", "gerar_numero_os",
]


def build_laudos_deps(**kwargs):
    """
    Monta o namespace passado para render_laudos(deps).
    Se nenhum kwargs for passado, importa dos módulos app e fortcordis_modules.
    O caller pode passar overrides (ex.: PASTA_LAUDOS) para sobrescrever.
    """
    if not kwargs:
        from fortcordis_modules.database import calcular_valor_final, gerar_numero_os
        return SimpleNamespace(
            PASTA_LAUDOS=PASTA_LAUDOS,
            ARQUIVO_REF=ARQUIVO_REF,
            ARQUIVO_REF_FELINOS=ARQUIVO_REF_FELINOS,
            PARAMS=PARAMS,
            get_grupos_por_especie=get_grupos_por_especie,
            normalizar_especie_label=normalizar_especie_label,
            montar_nome_base_arquivo=montar_nome_base_arquivo,
            calcular_referencia_tabela=calcular_referencia_tabela,
            interpretar=interpretar,
            interpretar_divedn=interpretar_divedn,
            DIVEDN_REF_TXT=DIVEDN_REF_TXT,
            listar_registros_arquivados_cached=listar_registros_arquivados_cached,
            salvar_laudo_no_banco=salvar_laudo_no_banco,
            obter_imagens_para_pdf=obter_imagens_para_pdf,
            montar_qualitativa=montar_qualitativa,
            _caminho_marca_dagua=_caminho_marca_dagua,
            montar_chave_frase=montar_chave_frase,
            carregar_frases=_carregar_frases,
            gerar_tabela_padrao=gerar_tabela_padrao,
            gerar_tabela_padrao_felinos=gerar_tabela_padrao_felinos,
            limpar_e_converter_tabela=limpar_e_converter_tabela,
            limpar_e_converter_tabela_felinos=limpar_e_converter_tabela_felinos,
            carregar_tabela_referencia_cached=carregar_tabela_referencia_cached,
            carregar_tabela_referencia_felinos_cached=carregar_tabela_referencia_felinos_cached,
            _normalizar_data_str=_normalizar_data_str,
            especie_is_felina=especie_is_felina,
            calcular_valor_final=calcular_valor_final,
            gerar_numero_os=gerar_numero_os,
        )
    return SimpleNamespace(**kwargs)
