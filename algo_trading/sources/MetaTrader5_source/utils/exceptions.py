class NotExpectedParseType(Exception):
    pass

class PairNotAvailable(Exception):
    pass

class CouldNotSelectPosition(Exception):
    pass

class InsufficientMarginError(Exception):
    """Erro levantado quando não há margem suficiente para abrir uma posição."""
    pass