# **Importações de Bibliotecas e Dependências Necessárias**
import pytest  # Framework de testes
from datetime import datetime, timezone, timedelta  # Manipulação de datas e horários
import pandas as pd  # Estruturas de dados (DataFrame e Series) para simulação de candles

# **Importações de Enums e Classes do MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_PENDING,  # Tipos de ordens pendentes (BUY_LIMIT, SELL_LIMIT, BUY_STOP, etc.)
    ENUM_ORDER_TYPE,  # Tipos de ordens (compra e venda)
    ENUM_SYMBOL_CALC_MODE,  # Modo de cálculo de margem (Forex, CFD, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Modos de operação da conta (DEMO, REAL)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Modo de stop out (percentual ou valor monetário)
    ENUM_ACCOUNT_MARGIN_MODE,  # Modo de cálculo de margem (Hedging ou Netting)
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_POSITION_TYPE,
    MqlAccountInfo,  # Estrutura com informações da conta (saldo, margem, etc.)
)

# **Importações de Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_check_expiration,  # Função que verifica a expiração de ordens pendentes
    __backtest_pending_order_check_triggered,  # Função que verifica se uma ordem pendente foi acionada
    __backtest_pending_order_open,  # Função que cria e registra uma ordem pendente
)

# **Importação da Classe de Conta para Testes**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe Account para manipulação dos dados da conta durante o backtest


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


# **Teste 1: Ordem de Compra (`BUY_LIMIT`) Acionada pelo `high`**
def test_buy_limit_triggered(account: Account):
    """
    Testa se uma ordem `BUY_LIMIT` é acionada corretamente quando o preço `high` do candle atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `BUY_LIMIT` com preço de 1.12 (igual ao `high` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.1,
        comment="Buy Limit Order",
    )

    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem deveria estar presente antes do acionamento."

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem foi ativada e removida
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter sido acionada e removida."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição correspondente deveria ter sido aberta."


# **Teste 2: Ordem de Venda (`SELL_LIMIT`) Acionada pelo `low`**
def test_sell_limit_triggered(account: Account):
    """
    Testa se uma ordem `SELL_LIMIT` é acionada corretamente quando o preço `low` do candle atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.11, "high": 1.14, "low": 1.10, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `SELL_LIMIT` com preço de 1.10 (igual ao `low` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
        volume=1,
        price=1.14,
        comment="Sell Limit Order",
    )

    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem deveria estar presente antes do acionamento."

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem foi ativada e removida
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter sido acionada e removida."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição correspondente deveria ter sido aberta."


# **Teste 3: Ordem de Compra (`BUY_LIMIT`) Não Acionada**
def test_buy_limit_not_triggered(account: Account):
    """
    Testa se uma ordem `BUY_LIMIT` não é acionada quando o preço `high` do candle não atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.10, "high": 1.11, "low": 1.09, "close": 1.10},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `BUY_LIMIT` com preço de 1.12 (acima do `high` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.0,
        comment="Buy Limit Order",
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem não foi ativada
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem não deveria ter sido acionada."


# **Teste 4: Ordem de Venda (`SELL_STOP`) Não Acionada**
def test_sell_stop_not_triggered(account: Account):
    """
    Testa se uma ordem `SELL_STOP` não é acionada quando o preço `low` do candle não atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.13, "high": 1.14, "low": 1.11, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `SELL_STOP` com preço de 1.10 (abaixo do `low` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
        volume=1,
        price=1.10,
        comment="Sell Stop Order",
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem não foi ativada
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem não deveria ter sido acionada."


# **Teste 5: Ordem `BUY_STOP` Acionada pelo `high`**
def test_buy_stop_triggered(account: Account):
    """
    Testa se uma ordem `BUY_STOP` é acionada corretamente quando o preço `high` do candle atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.10, "high": 1.15, "low": 1.09, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `BUY_STOP` com preço de 1.14 (igual ao `high` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.14,
        comment="Buy Stop Order",
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem foi ativada e removida
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter sido acionada e removida."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição correspondente deveria ter sido aberta."


# **Teste 6: Ordem `SELL_LIMIT` Acionada pelo `low`**
def test_sell_limit_triggered_low(account: Account):
    """
    Testa se uma ordem `SELL_LIMIT` é acionada corretamente quando o preço `low` do candle atinge o preço da ordem.
    """
    # Resetando a conta
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.12, "high": 1.14, "low": 1.08, "close": 1.10},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `SELL_LIMIT` com preço de 1.08 (igual ao `low` do candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
        volume=1,
        price=1.12,
        comment="Sell Limit Order",
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem foi ativada e removida
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter sido acionada e removida."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A posição correspondente deveria ter sido aberta."


# **Teste 7: Ordem `BUY_STOP_LIMIT` Acionada pelo `high`**
def test_buy_stop_limit_triggers_and_checks_limit(account: Account):
    """
    Testa se uma ordem `BUY_STOP_LIMIT` cria corretamente uma ordem `BUY_LIMIT`.
    Verifica:
    1. Caso em que a ordem `LIMIT` não é acionada após a criação.
    2. Caso em que a ordem `LIMIT` é acionada no mesmo candle.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # Configuração do candle mais recente
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
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `BUY_STOP_LIMIT` com preço inicial 1.12 e preço limite 1.125
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
        volume=1,
        price=1.12,  # Preço inicial
        stop_limit=1.05,  # Preço limite
        stop_price=1.0,
        profit_price=1.13,
        comment="Buy Stop Limit Order",
    )

    # Simula o acionamento da ordem `STOP_LIMIT`
    updated_candle_time = last_candle_time + timedelta(minutes=1)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.11, "high": 1.11996, "low": 1.10, "close": 1.11},
        name=updated_candle_time,
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem `STOP_LIMIT` foi removida e `LIMIT` foi criada
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem `BUY_STOP_LIMIT` deveria criar uma `BUY_LIMIT` pendente."

    # Verifica os detalhes da ordem `BUY_LIMIT` criada
    buy_limit_order = operation_handler.account_data.orders[0]
    assert (
        buy_limit_order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT
    ), "A ordem criada deveria ser do tipo `BUY_LIMIT`."
    assert buy_limit_order.price_open == 1.05, "O preço da `BUY_LIMIT` está incorreto."
    assert (
        buy_limit_order.volume_initial == 1
    ), "O volume da `BUY_LIMIT` está incorreto."
    assert buy_limit_order.sl == 1.0, "O stop-loss da `BUY_LIMIT` está incorreto."
    assert buy_limit_order.tp == 1.13, "O take-profit da `BUY_LIMIT` está incorreto."

    # Simula um cenário onde a ordem `LIMIT` não é acionada
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.124, "low": 1.05, "close": 1.123},
        name=updated_candle_time + timedelta(minutes=1),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # A ordem `LIMIT` ainda deve estar pendente
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem `BUY_LIMIT` não deveria ter sido acionada ainda."
    assert (
        operation_handler.account_data.positions == []
    ), "Nenhuma posição deveria ter sido aberta."

    # Simula um cenário onde a ordem `LIMIT` é acionada no próximo candle
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.125, "high": 1.13, "low": 1.04996, "close": 1.126},
        name=updated_candle_time + timedelta(minutes=2),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem `LIMIT` foi acionada
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem `BUY_LIMIT` deveria ter sido acionada."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "Uma posição correspondente deveria ter sido aberta."

    # Verifica os detalhes da posição aberta
    position = operation_handler.account_data.positions[0]
    assert position.symbol == symbol, "O símbolo da posição está incorreto."
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "O tipo da posição está incorreto."
    assert position.price_open == 1.05, "O preço de abertura da posição está incorreto."
    assert position.volume == 1, "O volume da posição está incorreto."
    assert position.sl == 1.0, "O stop-loss da posição está incorreto."
    assert position.tp == 1.13, "O take-profit da posição está incorreto."


# **Teste 8: Ordem `SELL_STOP_LIMIT` Acionada pelo `low`**
def test_sell_stop_limit_triggers_and_checks_limit(account: Account):
    """
    Testa se uma ordem `SELL_STOP_LIMIT` cria corretamente uma ordem `SELL_LIMIT`.
    Verifica:
    1. Caso em que a ordem `LIMIT` não é acionada após a criação.
    2. Caso em que a ordem `LIMIT` é acionada no mesmo candle.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # Configuração do candle mais recente
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
            {"open": 1.20, "high": 1.22, "low": 1.19, "close": 1.21},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Ordem `SELL_STOP_LIMIT` com preço inicial 1.18 e preço limite 1.175
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT,
        volume=1,
        price=1.18,  # Preço inicial
        stop_limit=1.185,  # Preço limite
        stop_price=1.19,
        profit_price=1.16,
        comment="Sell Stop Limit Order",
    )

    # Simula o acionamento da ordem `STOP_LIMIT`
    updated_candle_time = last_candle_time + timedelta(minutes=1)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.19, "high": 1.20, "low": 1.18, "close": 1.18},
        name=updated_candle_time,
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem `STOP_LIMIT` foi removida e `LIMIT` foi criada
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem `SELL_STOP_LIMIT` deveria criar uma `SELL_LIMIT` pendente."

    # Verifica os detalhes da ordem `SELL_LIMIT` criada
    sell_limit_order = operation_handler.account_data.orders[0]
    assert (
        sell_limit_order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT
    ), "A ordem criada deveria ser do tipo `SELL_LIMIT`."
    assert (
        sell_limit_order.price_open == 1.185
    ), "O preço da `SELL_LIMIT` está incorreto."
    assert (
        sell_limit_order.volume_initial == 1
    ), "O volume da `SELL_LIMIT` está incorreto."
    assert sell_limit_order.sl == 1.19, "O stop-loss da `SELL_LIMIT` está incorreto."
    assert sell_limit_order.tp == 1.16, "O take-profit da `SELL_LIMIT` está incorreto."

    # Simula um cenário onde a ordem `LIMIT` não é acionada
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.18, "high": 1.184, "low": 1.176, "close": 1.177},
        name=updated_candle_time + timedelta(minutes=1),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # A ordem `LIMIT` ainda deve estar pendente
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem `SELL_LIMIT` não deveria ter sido acionada ainda."
    assert (
        operation_handler.account_data.positions == []
    ), "Nenhuma posição deveria ter sido aberta."

    # Simula um cenário onde a ordem `LIMIT` é acionada no próximo candle
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.175, "high": 1.185, "low": 1.174, "close": 1.175},
        name=updated_candle_time + timedelta(minutes=2),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem `LIMIT` foi acionada
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem `SELL_LIMIT` deveria ter sido acionada."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "Uma posição correspondente deveria ter sido aberta."

    # Verifica os detalhes da posição aberta
    position = operation_handler.account_data.positions[0]
    assert position.symbol == symbol, "O símbolo da posição está incorreto."
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
    ), "O tipo da posição está incorreto."
    assert (
        position.price_open == 1.185
    ), "O preço de abertura da posição está incorreto."
    assert position.volume == 1, "O volume da posição está incorreto."
    assert position.sl == 1.19, "O stop-loss da posição está incorreto."
    assert position.tp == 1.16, "O take-profit da posição está incorreto."


# **Teste 9: Ordem Inválida (Tipo Desconhecido)**
def test_invalid_order_type(account: Account):
    """
    Testa se o sistema ignora ordens com tipos não reconhecidos.
    """
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.10, "high": 1.15, "low": 1.09, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Criação de uma ordem com tipo inválido (não mapeado)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY,  # Tipo inválido
        volume=1,
        price=1.14,
        comment="Invalid Order Type",
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_triggered(operation_handler)

    # Verifica se a ordem ainda está presente
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem inválida não deveria ter sido acionada."
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "Nenhuma posição deveria ter sido aberta."


# **Teste 10: Ordem Expirada Não Deve Ser Acionada**
def test_expired_order_not_triggered(account: Account):
    """
    Testa se uma ordem expirada não é acionada mesmo que o preço seja atingido.
    """
    account.login_backtest(balance=10000, leverage=100)
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
            {"open": 1.10, "high": 1.15, "low": 1.09, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Ordem expirada
    expired_time = last_candle_time + timedelta(minutes=1)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.14,
        expiration=expired_time,
        comment="Expired Order",
    )
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.10, "high": 1.15, "low": 1.09, "close": 1.14},
        name=expired_time + timedelta(minutes=1),
    )

    # Executa a verificação de acionamento
    __backtest_pending_order_check_expiration(operation_class=operation_handler)
    __backtest_pending_order_check_triggered(operation_class=operation_handler)

    # Verifica se a ordem ainda está presente (não deve ser acionada)
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem expirada deveria ter sido descartada."
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "Nenhuma posição deveria ter sido aberta."
