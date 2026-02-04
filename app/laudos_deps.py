# Construção centralizada do namespace deps para a página Laudos (Fase B)
# O app principal chama build_laudos_deps(...) com os símbolos que ainda vivem lá;
# paths (PASTA_LAUDOS, ARQUIVO_REF, ARQUIVO_REF_FELINOS) vêm de app.config.
from types import SimpleNamespace


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
    Todos os argumentos nomeados são repassados ao SimpleNamespace.
    O caller (fortcordis_app) deve passar os símbolos; paths podem vir de app.config.
    """
    return SimpleNamespace(**kwargs)
