# Exceções customizadas do app (prioridade média: tratamento de erros padronizado)


class AppError(Exception):
    """Base para erros do app."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class DBError(AppError):
    """Erro de banco de dados (conexão, query, integridade)."""
    pass


class LaudoNotFoundError(AppError):
    """Laudo não encontrado (id inválido ou registro inexistente)."""
    pass


class ConfigError(AppError):
    """Erro de configuração (path inexistente, valor inválido)."""
    pass
