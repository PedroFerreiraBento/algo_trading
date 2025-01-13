# Importações de bibliotecas externas necessárias
import pytest
from datetime import datetime, timezone  # Manipulação de datas e fuso horário
import pandas as pd  # Biblioteca para manipulação de dados em formato de séries e tabelas

# Importações de classes e enums do modelo de metatrader (definições relacionadas ao mercado financeiro)
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Classe que contém as informações da conta no MetaTrader 5
    ENUM_SYMBOL_SWAP_MODE,  # Enum que define os modos de cálculo de swap
    ENUM_ACCOUNT_TRADE_MODE,  # Enum que define os modos de negociação da conta
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum que define os modos de stop out da conta
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum que define os modos de margem da conta
    ENUM_ORDER_TYPE_MARKET,  # Enum que define os tipos de ordens de mercado
    ENUM_SYMBOL_CALC_MODE,  # Enum que define os modos de cálculo do contrato de mercado
)

# Importações das funções de backtest
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_apply_swap_to_positions,  # Função que aplica o swap às posições abertas
    __backtest_position_open,  # Função que realiza a abertura de posições durante o backtest
)

# Importação da classe `Account` responsável por login e gerenciamento de informações da conta
from algo_trading.sources.MetaTrader5_source.account.account import Account


@pytest.fixture
def account():
    """Fixture que cria uma instância de conta para os testes.

    Simula o login em uma conta ao vivo.

    Returns:
        Account: Instância de conta com dados configurados.
    """
    account = Account()

    # Simula login na conta ao vivo antes do backtest
    account.live_account_data = MqlAccountInfo(
        login=123456,
        trade_mode=ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO,
        leverage=100,
        limit_orders=200,
        margin_so_mode=ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT,
        trade_allowed=True,
        trade_expert=True,
        margin_mode=ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        currency_digits=2,
        fifo_close=False,
        balance=10000.0,
        credit=0.0,
        profit=0.0,
        equity=10000.0,
        margin=0.0,
        margin_free=10000.0,
        margin_level=0.0,
        margin_so_call=50.0,
        margin_so_so=30.0,
        margin_initial=0.0,
        margin_maintenance=0.0,
        assets=0.0,
        liabilities=0.0,
        commission_blocked=0.0,
        name="Demo Account",
        server="demo.server.com",
        currency="USD",
        company="MetaTrader Company",
    )

    return account


def test_apply_swap_to_multiple_positions(account: Account):
    """
    Testa a aplicação de swaps em múltiplas posições abertas para o par EURUSD.

    Objetivo:
    - Verificar se os swaps são aplicados corretamente às posições abertas com base nas configurações.
    - Avaliar se os valores de swap diferem entre posições de compra e venda.
    - Considerar o rollover triplo na quarta-feira.

    Configurações:
    - Swap por pontos (SYMBOL_SWAP_MODE_POINTS).
    - Swap triplo aplicado na quarta-feira (3 dias).
    - Posição de compra com swap -1.0 por lote.
    - Posição de venda com swap -0.5 por lote.
    """
    # Login na conta de backtest com saldo inicial e alavancagem configurados
    account.login_backtest(balance=10000, leverage=100)
    account.backtest_account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )

    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Configuração de datas
    last_swap_date = datetime(
        2025, 1, 8, 20, 0, tzinfo=timezone.utc
    )  # Quarta-feira 20h
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira 23h
    operation_handler.account_data.backtest_last_swap_date = last_swap_date

    # Última vela (candle) de preço para EURUSD
    last_candle = {
        "open": 1.12,
        "high": 1.15,
        "low": 1.11,
        "close": 1.13,
    }
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_swap_date
    )

    # Abertura de uma posição de compra e uma de venda
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Posição de compra
        volume=1,  # 1 lote
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Posição de venda
        volume=2,  # 2 lotes
        comment="Position 2 (Sell)",
    )

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_candle_time
    )

    # Aplicação dos swaps às posições abertas
    __backtest_position_apply_swap_to_positions(operation_handler)

    # Obtenção das posições para verificação
    positions = account.backtest_account_data.positions

    # Assertivas para garantir que as posições estão corretas
    assert len(positions) == 2, "O número de posições não corresponde ao esperado."

    # Verificação dos valores de swap
    buy_swap = -5.0
    sell_swap = -5.0

    assert (
        positions[0].swap == buy_swap
    ), f"Swap da posição de compra está incorreto. Esperado: {buy_swap}, obtido: {positions[0].swap}"
    assert (
        positions[1].swap == sell_swap
    ), f"Swap da posição de venda está incorreto. Esperado: {sell_swap}, obtido: {positions[1].swap}"


def test_apply_triple_rollover_on_wednesday_night(account: Account):
    """
    Tests that the triple rollover swap is applied correctly on Wednesday night.
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Wednesday 21h -> Thursday 01h (next day)
    last_swap_date = datetime(2025, 1, 8, 20, 0, tzinfo=timezone.utc)  # Wednesday 20h
    last_candle_time = datetime(2025, 1, 9, 1, 0, tzinfo=timezone.utc)  # Thursday 01h
    operation_handler.account_data.backtest_last_swap_date = last_swap_date
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_swap_date,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Posição de compra
        volume=1,  # 1 lote
        comment="Position 1 (Buy)",  # Comentário identificando a posição
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Posição de venda
        volume=2,  # 2 lotes
        comment="Position 2 (Sell)",  # Comentário identificando a posição
    )
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == -3.0
    ), "Triple rollover swap for buy position was not applied correctly."
    assert (
        positions[1].swap == -3.0
    ), "Triple rollover swap for sell position was not applied correctly."


def test_apply_single_rollover_on_thursday_night(account: Account):
    """
    Tests that a single swap is applied correctly on Thursday night after 22h UTC.
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 9, 21, 0, tzinfo=timezone.utc
    )  # Thursday 21h
    last_candle_time = datetime(2025, 1, 9, 23, 0, tzinfo=timezone.utc)  # Thursday 23h

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=operation_handler.account_data.backtest_last_swap_date,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol="EURUSD",
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol="EURUSD",
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=2,
        comment="Position 2 (Sell)",
    )
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == -1.0
    ), "Single swap for buy position was not applied correctly after 22h on Thursday."
    assert (
        positions[1].swap == -1.0
    ), "Single swap for sell position was not applied correctly after 22h on Thursday."


def test_no_swap_applied_before_market_closing(account: Account):
    """
    Tests that no swap is applied before the market closes (before 22h UTC).
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 9, 15, 0, tzinfo=timezone.utc
    )  # Thursday 15h
    last_candle_time = datetime(
        2025, 1, 9, 18, 0, tzinfo=timezone.utc
    )  # Thursday 18h (before market closes)

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=2,
        comment="Position 2 (Sell)",
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == 0.0
    ), "Swap was incorrectly applied before market closing time."
    assert (
        positions[1].swap == 0.0
    ), "Swap was incorrectly applied before market closing time."


def test_apply_triple_rollover_on_sell_position(account: Account):
    """
    Tests that the triple rollover swap is applied correctly for a sell position (2 lots) on Wednesday night.
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 8, 21, 0, tzinfo=timezone.utc
    )  # Wednesday 21h
    last_candle_time = datetime(
        2025, 1, 9, 1, 0, tzinfo=timezone.utc
    )  # Thursday 01h (after Wednesday night)

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=operation_handler.account_data.backtest_last_swap_date,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=2,
        comment="Position 2 (Sell)",
    )
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == -3.0
    ), "Triple rollover swap for sell position was not applied correctly (2 lots)."


def test_no_swap_applied_during_weekend(account: Account):
    """
    Tests that no swap is applied during the weekend when the market is closed.
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Friday 23h
    last_candle_time = datetime(
        2025, 1, 11, 12, 0, tzinfo=timezone.utc
    )  # Saturday 12h (market closed)

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert positions[0].swap == 0.0, "Swap should not be applied during the weekend."


def test_no_swap_on_first_day_before_close(account: Account):
    """
    Tests that no swap is applied on the first day of trading before 22h UTC.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    # Complete configuration
    # Define os dados do novo símbolo como um dicionário
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = (
        None  # Sem histórico de swap
    )
    last_candle_time = datetime(
        2025, 1, 3, 18, 0, tzinfo=timezone.utc
    )  # Sexta-feira 18h

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == 0.0
    ), "Swap should not be applied on the first day before market closing time."


def test_no_duplicate_swap_on_friday(account: Account):
    """
    Tests that no duplicate swap is applied on Friday after 22h UTC.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.7,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatena o novo registro ao DataFrame existente
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Friday after market close
    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 17, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira 23h
    last_candle_time = datetime(
        2025, 1, 19, 12, 0, tzinfo=timezone.utc
    )  # Domingo 12h (ainda fechado)

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time,
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    __backtest_position_apply_swap_to_positions(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].swap == 0.0
    ), "Swap should not be reapplied after 22h on Friday until the next market open."


def test_swap_applied_only_after_positions_opened(account: Account):
    """
    Tests that swaps are applied only for candles after the positions have been opened.

    Scenario:
    - Last swap date: Monday.
    - Last candle before opening: Thursday 23h.
    - Last candle after opening: Friday 23h.
    - Expected: Only 1 swap (from Friday) should be applied.
    """
    account.login_backtest(balance=10000, leverage=100)

    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    # Complete configuration
    new_data = {
        "tick_size": 1e-05,
        "contract_size": 100_000,
        "trade_calc_mode": ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
        "swap_mode": ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS,
        "swap_long": -1,
        "swap_short": -0.5,
        "swap_rollover3days": 3,
        "volume_min": 0.01,
        "volume_max": 500,
        "volume_step": 0.01,
        "volume_limit": 0,
        "last_candle": None,
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Configuração de datas
    last_swap_date = datetime(
        2025, 1, 6, 22, 0, tzinfo=timezone.utc
    )  # Segunda-feira 22h
    last_candle_before_open = datetime(
        2025, 1, 9, 23, 0, tzinfo=timezone.utc
    )  # Quinta-feira 23h
    last_candle_after_open = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira 23h

    # Define a última data de swap na conta
    operation_handler.account_data.backtest_last_swap_date = last_swap_date

    # Adiciona o último candle antes de abrir a posição
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_before_open,
    )

    # Abre posições após o candle de quinta-feira
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=2,
        comment="Position 2 (Sell)",
    )

    # Atualiza o último candle para sexta-feira
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.13, "high": 1.16, "low": 1.12, "close": 1.14},
        name=last_candle_after_open,
    )

    # Aplica os swaps às posições abertas
    __backtest_position_apply_swap_to_positions(operation_handler)

    # Obtenção das posições para verificação
    positions = account.backtest_account_data.positions

    # Verifica se há exatamente 2 posições abertas
    assert (
        len(positions) == 2
    ), "O número de posições abertas não corresponde ao esperado."

    # Verifica o swap aplicado nas posições
    buy_swap = -1.0  # 1 lote, swap_long = -1.0
    sell_swap = -1.0  # 2 lotes, swap_short = -0.5 * 2 = -1.0

    assert (
        positions[0].swap == buy_swap
    ), f"Swap da posição de compra está incorreto. Esperado: {buy_swap}, obtido: {positions[0].swap}"
    assert (
        positions[1].swap == sell_swap
    ), f"Swap da posição de venda está incorreto. Esperado: {sell_swap}, obtido: {positions[1].swap}"
