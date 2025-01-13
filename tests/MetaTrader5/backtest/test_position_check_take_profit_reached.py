# **Importações de Bibliotecas e Dependências Necessárias**

# **Framework de Testes**
import pytest

# **Manipulação de Datas e Horários**
from datetime import datetime, timezone, timedelta

# **Estruturas de Dados para Manipulação de Candles**
import pandas as pd

# **Importações do Modelo MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_POSITION_TYPE,  # Tipos de Posições (BUY e SELL)
    ENUM_SYMBOL_CALC_MODE,  # Modos de Cálculo (FOREX, CFDs, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Modo da Conta (DEMO, REAL)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Modo de Stop Out
    ENUM_ACCOUNT_MARGIN_MODE,  # Modo de Cálculo de Margem
    ENUM_SYMBOL_SWAP_MODE,
    MqlAccountInfo,  # Estrutura com Informações da Conta
)

# **Importações do Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_check_take_profit_reached,  # Função de Verificação de Stop Loss
    __backtest_position_open,  # Função para Abrir Posições durante o Teste
)

# **Importação da Classe Account**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe para Manipulação de Dados da Conta


# **Fixture de Conta para os Testes**
@pytest.fixture
def account():
    """
    Fixture que cria uma instância de conta para os testes.
    Simula o login em uma conta ao vivo e reinicializa a conta em modo backtest.
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


# **Teste 1: Posição `BUY` Atinge Take Profit**
def test_buy_position_take_profit_hit(account: Account):
    """
    Testa se uma posição `BUY` é fechada corretamente quando o preço `high` do candle atinge o take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.15, "low": 1.10, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `BUY` com take profit em 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.14,
        comment="Test Buy Position TP",
    )

    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `BUY` deveria estar aberta."

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição foi fechada
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "A posição `BUY` deveria ter sido fechada pelo take profit."


# **Teste 2: Posição `SELL` Atinge Take Profit**
def test_sell_position_take_profit_hit(account: Account):
    """
    Testa se uma posição `SELL` é fechada corretamente quando o preço `low` do candle atinge o take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.14, "low": 1.09, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `SELL` com take profit em 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        profit_price=1.10,
        comment="Test Sell Position TP",
    )

    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `SELL` deveria estar aberta."

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição foi fechada
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "A posição `SELL` deveria ter sido fechada pelo take profit."


# **Teste 3: Posição `BUY` Não Atinge Take Profit**
def test_buy_position_no_take_profit(account: Account):
    """
    Testa se uma posição `BUY` permanece aberta quando o preço `high` do candle não atinge o take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.13, "low": 1.10, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `BUY` com take profit em 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.14,
        comment="Test Buy Position TP",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição permanece aberta
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `BUY` não deveria ter sido fechada."


# **Teste 4: Posição `SELL` Não Atinge Take Profit**
def test_sell_position_no_take_profit(account: Account):
    """
    Testa se uma posição `SELL` permanece aberta quando o preço `low` do candle não atinge o take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.11, "high": 1.14, "low": 1.11, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `SELL` com take profit em 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        profit_price=1.10,
        comment="Test Sell Position TP",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição permanece aberta
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `SELL` não deveria ter sido fechada."


# **Teste 5: Posição Sem Take Profit Configurado**
def test_position_without_take_profit(account: Account):
    """
    Testa se uma posição permanece aberta quando não há um take profit configurado.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.11, "high": 1.13, "low": 1.10, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `BUY` sem take profit
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=0.0,  # Sem take profit
        comment="Test Buy Position Without TP",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição permanece aberta
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `BUY` não deveria ser fechada, pois não há take profit configurado."


# **Teste 6: Posição `BUY` com Take Profit Atingido Exatamente no `high`**
def test_buy_position_take_profit_exact_high(account: Account):
    """
    Testa se uma posição `BUY` é fechada corretamente quando o preço `high` do candle é exatamente igual ao take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.14, "low": 1.11, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `BUY` com take profit em 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.14,
        comment="Test Buy Position Exact TP",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição foi fechada
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "A posição `BUY` deveria ter sido fechada pelo take profit."


# **Teste 7: Posição `SELL` com Take Profit Atingido Exatamente no `low`**
def test_sell_position_take_profit_exact_low(account: Account):
    """
    Testa se uma posição `SELL` é fechada corretamente quando o preço `low` do candle é exatamente igual ao take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.15, "low": 1.10, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `SELL` com take profit em 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        profit_price=1.10,
        comment="Test Sell Position Exact TP",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição foi fechada
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "A posição `SELL` deveria ter sido fechada pelo take profit."


# **Teste 8: Posição `BUY` com Take Profit Não Atingido (`high` Abaixo do TP)**
def test_buy_position_take_profit_not_hit(account: Account):
    """
    Testa se uma posição `BUY` permanece aberta quando o preço `high` do candle está abaixo do take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.10, "high": 1.12, "low": 1.08, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `BUY` com take profit em 1.13
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.13,
        comment="Test Buy Position TP Not Hit",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição permanece aberta
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `BUY` não deveria ter sido fechada."


# **Teste 9: Posição `SELL` com Take Profit Não Atingido (`low` Acima do TP)**
def test_sell_position_take_profit_not_hit(account: Account):
    """
    Testa se uma posição `SELL` permanece aberta quando o preço `low` do candle está acima do take profit.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.15, "low": 1.12, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de posição `SELL` com take profit em 1.11
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        profit_price=1.11,
        comment="Test Sell Position TP Not Hit",
    )

    # Verifica se o take profit foi atingido
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se a posição permanece aberta
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição `SELL` não deveria ter sido fechada."


# **Teste 10: Múltiplas Posições com Take Profit**
def test_multiple_positions_take_profit(account: Account):
    """
    Testa o comportamento com múltiplas posições abertas com diferentes take profits.
    """
    account.login_backtest(balance=10_000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.16, "low": 1.10, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Abertura de múltiplas posições com diferentes take profits
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.15,
        comment="Test Buy Position TP 1",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        profit_price=1.11,
        comment="Test Sell Position TP 2",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        profit_price=1.17,  # Não deve ser atingido
        comment="Test Buy Position TP 3",
    )

    # Verifica se os take profits foram atingidos
    __backtest_position_check_take_profit_reached(operation_handler)

    # Verifica se apenas as posições com take profit atingido foram fechadas
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "Apenas a posição `Test Buy Position TP 3` deveria permanecer aberta."
