# **Bibliotecas Padrão do Python**
import pytest  # Framework de testes para facilitar a criação e execução de testes automatizados
from datetime import (
    datetime,
    timezone,
    timedelta,
    time,
)  # Manipulação de datas e fusos horários
import pandas as pd  # Biblioteca para manipulação de séries temporais e DataFrames

# **Importações de Enums e Classes Relacionadas ao MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_PENDING,  # Tipos de ordens pendentes (`BUY_LIMIT`, `SELL_STOP`, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum de modo de negociação (`DEMO`, `LIVE`, etc.)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para tipo de `stop out` (`PERCENT`, `MONEY`, etc.)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para tipo de margem (`RETAIL_HEDGING`, `NETTING`, etc.)
    ENUM_SYMBOL_CALC_MODE,  # Enum para modo de cálculo (`FOREX`, `CFD`, `FUTURES`, etc.)
    ENUM_SYMBOL_SWAP_MODE,
    MqlAccountInfo,  # Classe de informações da conta (saldo, margem, modo de operação, etc.)
)

# **Importações das Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_check_expiration,  # Função que verifica e remove ordens pendentes expiradas
    __backtest_pending_order_open,  # Função que cria ordens pendentes no modo backtest
)

# **Importação da Classe Account**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe que representa a conta de negociação


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


# **Teste 1: Expiração de ordem no horário exato**
def test_order_expiration_specified_time(account: Account):
    """
    Testa a expiração de ordens pendentes com tipo `ORDER_TIME_SPECIFIED`.

    Verifica se a ordem expira no horário exato especificado.
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
            {"open": 1.10, "high": 1.12, "low": 1.08, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Expiração da ordem após o horário de abertura
    order_expiration_time = last_candle_time + timedelta(minutes=1)

    # Criação da ordem pendente
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.11,
        expiration=order_expiration_time,
        comment="Order 1",
    )

    # Atualização do último candle para após a expiração
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.13, "low": 1.09, "close": 1.11},
        name=order_expiration_time + timedelta(seconds=1),
    )

    # Executa a verificação de expiração
    __backtest_pending_order_check_expiration(operation_handler)

    # Verificação após expiração
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter expirado e sido removida."


# **Teste 2: Expiração de ordem ao final do dia (`ORDER_TIME_SPECIFIED_DAY`)**
def test_order_expiration_specified_day(account: Account):
    """
    Testa a expiração de ordens pendentes com tipo `ORDER_TIME_SPECIFIED_DAY`.

    Verifica se a ordem expira ao final do dia especificado (23:59:59).
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc)

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

    # Expiração ao final do dia (23:59:59 UTC)
    order_expiration_datetime = datetime.combine(
        last_candle_time.date(), datetime.min.time(), tzinfo=timezone.utc
    )
    expiration_end_of_day = order_expiration_datetime.replace(
        hour=23, minute=59, second=59
    )

    # Criação de ordem pendente com expiração ao final do dia
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
        volume=1,
        price=1.11,
        expiration=expiration_end_of_day,
        comment="Order 2",
    )

    # Atualização do último candle para 23:59:59 do mesmo dia
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.14, "low": 1.10, "close": 1.13},
        name=expiration_end_of_day,
    )

    # Executa a verificação de expiração
    __backtest_pending_order_check_expiration(operation_handler)

    # Verificação após expiração
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "A ordem deveria ter expirado e sido removida."


# **Teste 3: Ordem sem expiração (não deve ser removida)**
def test_order_no_expiration(account: Account):
    """
    Testa ordens pendentes sem `time_expiration`.

    Verifica se a ordem não é removida quando `time_expiration` é `None`.
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
            {"open": 1.10, "high": 1.12, "low": 1.08, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Criação de ordem pendente sem expiração
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.12,
        expiration=None,
        comment="Order 3",
    )

    # Atualização do último candle para um horário posterior
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time + timedelta(minutes=10),
    )

    # Executa a verificação de expiração
    __backtest_pending_order_check_expiration(operation_handler)

    # Verificação após execução
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "A ordem não deveria ter expirado."


# **Teste 4: Várias ordens pendentes com diferentes tipos de expiração**
def test_multiple_orders_with_different_expirations(account: Account):
    """
    Testa o comportamento com múltiplas ordens pendentes com diferentes tipos de expiração.

    Verifica se cada ordem é tratada corretamente com base em seu tipo de expiração.
    """
    # **Inicialização da conta em modo de backtest**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # **Simulação do último candle no momento da abertura das ordens**
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

    # **Criação de múltiplas ordens com diferentes tipos de expiração**

    # 1. Ordem que deve expirar após 5 minutos
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.11,
        expiration=last_candle_time + timedelta(minutes=5),  # Expira às 12:05
        comment="Order 4",  # Deve expirar
    )

    # 2. Ordem que deve expirar ao final do dia (23:59:59)
    expiration_date = datetime.combine(
        last_candle_time.date(), time(23, 59, 59), tzinfo=timezone.utc
    )
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
        volume=1,
        price=1.10,
        expiration=expiration_date,  # Expira ao final do dia
        comment="Order 5",  # Deve expirar
    )

    # 3. Ordem sem expiração
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.12,
        expiration=None,  # Não expira
        comment="Order 6",  # Não deve expirar
    )

    # **Atualização do último candle para 10 minutos após a criação das ordens (12:10)**
    updated_candle_time = last_candle_time + timedelta(minutes=10)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.10, "close": 1.14},
        name=updated_candle_time,
    )

    # **Executa a verificação de expiração**
    __backtest_pending_order_check_expiration(operation_handler)

    # **Verificações após execução**
    assert (
        len(operation_handler.account_data.orders) == 2
    ), "Apenas as ordens sem expiração e não expiradas deveriam permanecer."
    assert (
        operation_handler.account_data.orders[0].comment == "Order 5"
    ), "A ordem `Order 5` deveria ser remanescente."
    assert (
        operation_handler.account_data.orders[1].comment == "Order 6"
    ), "A ordem `Order 6` deveria ser remanescente."
