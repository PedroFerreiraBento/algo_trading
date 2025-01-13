from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_POSITION_TYPE,
    MqlTick,
    MqlSymbolInfo,
    MqlTradeOrder,
)
from algo_trading.sources.MetaTrader5_source.rates import Rates
from algo_trading.sources.MetaTrader5_source.utils.exceptions import PairNotAvailable
import datetime
import pandas as pd
from typing import List, TYPE_CHECKING
from collections import Counter

if TYPE_CHECKING:
    from algo_trading.sources.MetaTrader5_source.operation.operation import Operation


def find_pair(currency_1: str, currency_2: str) -> str:
    pairs = [
        name
        for name in Rates.get_symbols_names()
        if currency_1 in name and currency_2 in name
    ]

    # No pairs available
    if not pairs:
        raise PairNotAvailable(
            f"[ERROR]: Could not find a pair with currencies: {currency_1} and {currency_2}"
        )

    # More then one pair found - Atypical
    if len(pairs) > 1:
        pairs = [pair for pair in pairs if str.endswith(currency_2)]

    return pairs[0]


def identify_required_pairs(symbol: str, account_currency: str):
    usd_intermediary = "USD"
    base_currency, quote_currency = symbol[:3], symbol[3:]

    # Lista com os símbolos necessários
    required_symbols = [symbol]

    # Caso em que nem a base nem o quote são iguais à moeda da conta
    if account_currency not in (base_currency, quote_currency):
        # Exemplo: account_currency = "JPY", symbol = "EURGBP"
        # Precisamos montar a rota EUR -> USD -> JPY
        required_symbols.append(find_pair(quote_currency, usd_intermediary))
        if account_currency != usd_intermediary:
            required_symbols.append(find_pair(usd_intermediary, account_currency))

    # Remove duplicados
    required_symbols = list(set(required_symbols))

    return required_symbols


def convert_cross_currency_value(
    operation_class: "Operation",
    value: float,
    value_currency: str,
    target_currency: str,
    position_type: ENUM_POSITION_TYPE,
):
    # Direct currency convertion
    if target_currency == "USD" or value_currency == "USD":
        convert_pair = find_pair(currency_1=value_currency, currency_2=target_currency)

        convert_tick = operation_class.backtest_last_candle[convert_pair]
        tick_size = operation_class.backtest_tick_sizes[convert_tick]

        close_price = (
            tick_size.close
            + (tick_size * operation_class.account_data.simulated_spread)
            if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
            else tick_size.close
        )

        value_target = (
            value * close_price
            if convert_pair.endswith(target_currency)
            else value / close_price
        )

    # Cross conversion
    else:
        # Base convert to USD
        convert_base_pair = find_pair(currency_1=value_currency, currency_2="USD")

        convert_tick_base = operation_class.backtest_last_candle[convert_base_pair]
        tick_size = operation_class.backtest_tick_sizes[convert_base_pair]

        close_price = (
            convert_tick_base.close
            + (tick_size * operation_class.account_data.simulated_spread)
            if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
            else convert_tick_base.close
        )

        value_base = (
            value * close_price
            if convert_base_pair.endswith("USD")
            else value / close_price
        )

        # USD convert to target
        convert_target_pair = find_pair(currency_1="USD", currency_2=target_currency)

        convert_tick_target = operation_class.backtest_last_candle[convert_target_pair]
        tick_size = operation_class.backtest_tick_sizes[convert_tick_target]

        close_price = (
            convert_tick_target.close
            + (tick_size * operation_class.account_data.simulated_spread)
            if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
            else convert_tick_target.close
        )

        value_target = (
            value_base * close_price
            if convert_target_pair.endswith(target_currency)
            else value_base / close_price
        )

    return value_target


def compute_profit(
    operation_class: "Operation",
    price_open: float,
    price_close: float,
    price_volume: float,
    symbol: str,
    position_type: ENUM_POSITION_TYPE,
) -> float:
    """
    Calcula o lucro ou prejuízo de uma posição com base nos preços de abertura e fechamento,
    volume negociado e a moeda da conta.

    Args:
        operation_class (Operation): Classe de operação que contém os dados do contrato e de conversão de moeda.
        price_open (float): Preço de abertura da posição.
        price_close (float): Preço de fechamento da posição.
        price_volume (float): Volume da posição em lotes.
        symbol (str): Par de moedas (exemplo: "EURUSD").
        position_type (ENUM_POSITION_TYPE): Tipo de posição (compra ou venda).

    Returns:
        float: Lucro ou prejuízo da posição, arredondado para 5 casas decimais.
    """
    account_currency = operation_class.account_data.currency

    # Obtém o tamanho do contrato (exemplo: 100.000 unidades para 1 lote padrão)
    contract_size = operation_class.backtest_symbols_data.loc[symbol].contract_size

    # Calcula o lucro na moeda do par de negociação (target currency)
    # Exemplo: em uma negociação USDJPY, o lucro será em JPY.
    target_profit = contract_size * price_volume * (price_close - price_open)

    # Se for uma posição de venda, o lucro precisa ser revertido
    if position_type != ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        target_profit *= -1

    # Converte o lucro para a moeda da conta, se necessário
    simulated_spread: int = operation_class.account_data.simulated_spread

    # Se a moeda da conta for a base do par (exemplo: "USD" em "USDJPY")
    if symbol.startswith(account_currency):
        # Ajusta o lucro com base no preço de fechamento considerando o spread simulado
        target_profit /= (
            price_close + (contract_size * simulated_spread)
            if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
            else price_close
        )

    # Se for um par cruzado (a moeda da conta não está no par de moedas negociado)
    elif not symbol.endswith(account_currency):
        # Converte o lucro para a moeda da conta usando uma função de conversão de cross currency
        target_profit = convert_cross_currency_value(
            operation_class=operation_class,
            value=target_profit,
            value_currency=symbol[3:],  # Moeda de cotação (exemplo: "JPY" em "USDJPY")
            target_currency=account_currency,  # Moeda da conta
        )

    # Arredonda o lucro para evitar valores com muitas casas decimais
    profit = round(target_profit, 2)

    return profit


def get_last_tick(symbol: str, financial_data: pd.DataFrame) -> MqlTick:
    """Get last tick of the last DataFrame candle

    Args:
        symbol (str): Symbol pair
        financial_data (pd.DataFrame): Dataframe

    Returns:
        MqlTick: Last candle tick
    """

    # Get the two last candles
    time_candle_last1 = financial_data["Datetime"].iloc[-1]
    time_candle_last2 = financial_data["Datetime"].iloc[-2]
    time_candle_last3 = financial_data["Datetime"].iloc[-3]
    time_candle_last4 = financial_data["Datetime"].iloc[-4]

    # Compute time difference
    timediff1 = time_candle_last1 - time_candle_last2
    timediff2 = time_candle_last2 - time_candle_last3
    timediff3 = time_candle_last3 - time_candle_last4

    timediff = Counter([timediff1, timediff2, timediff3]).most_common(1)[0][0]

    # Get a 5 minutes tick interval
    interval = datetime.timedelta(minutes=5)

    # Get last tick date
    date_to = time_candle_last1 + timediff
    date_from = time_candle_last1
    # date_from = date_to - interval

    # Get last tick
    last_tick = Rates.get_ticks_range(symbol, date_from, date_to)[-1]

    return last_tick


def get_order(list_orders: List[MqlTradeOrder], ticket: int) -> MqlTradeOrder:
    # Find the order
    order: List[MqlTradeOrder] = [
        order for order in list_orders if order.ticket == ticket
    ]
    if not order:
        raise ValueError(f"[ERROR]: Order with ticket #{ticket} not found")

    return order[0]
