import MetaTrader5 as mt5
from typing import Callable


def validate_connection_established() -> None:
    """Validate connection

    Validate if the connection with the server is already established

    Raises:
        ConnectionError: Connection is not established
    """

    # Check request success
    if not mt5.initialize() or mt5.account_info() is None:
        raise ConnectionError("[ERROR]: Connection is not established")


def decorator_validate_mt5_connection(server_function: Callable) -> Callable:
    """Validate MetaTrader Connection

    Args:
        server_function (Callable): Server operation function

    Returns:
        Callable: Server function
    """

    # Refresh before and after
    def validater_server_connection(*args, **kwargs) -> Callable:
        """Validate MetaTrader Connection

        Validate connection before execute server functions

        Returns:
            Callable: original function
        """

        # Validate connection
        validate_connection_established()

        return server_function(*args, **kwargs)

    return validater_server_connection


def validate_mt5_long_size(value: int) -> None:
    """Validate int size

    Args:
        value (int): Request int value

    Raises:
        ValueError: The count of candles must be higher
        ValueError: Python int too large to convert to C long
    """

    # Check language C long int size
    if value >= (2**63) or value <= -(2**63):
        raise ValueError(f"[ERROR]: Python int too large to convert MQL5 long")


def validate_mt5_ulong_size(value: int) -> None:
    """Validate int size

    Args:
        value (int): Request int value

    Raises:
        ValueError: The count of candles must be higher
        ValueError: Python int too large to convert to C ulong
    """

    # Check negative count
    if value < 0:
        raise ValueError(f"[ERROR]: The count must be equal or higher to zero")

    # Check language C long int size
    if value >= (2**64):
        raise ValueError(f"[ERROR]: Python int too large to convert MQL5 long")
