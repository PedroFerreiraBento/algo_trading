# **Bibliotecas de Teste**
import pytest  # Biblioteca de testes unitários.
from unittest.mock import patch  # Utilizado para criar patches nos testes.

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo que representa informações sobre a conta de trading.
    ENUM_ACCOUNT_TRADE_MODE,  # Enum que indica o modo de operação da conta (real, demo, etc.).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum que indica o modo de stop-out (percentual ou valor fixo).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum que define o tipo de margem da conta (hedge, netting, etc.).
    ENUM_ORDER_TYPE_MARKET,  # Enum para ordens de mercado (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum para ordens pendentes (e.g., BUY LIMIT, SELL STOP).
)

# **Classe de Conta**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe `Account` para login e gerenciamento de informações da conta de trading.

# **Decorators e Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    decorator_backtest_position_open,  # Decorator que redireciona a função para `__backtest_position_open` no modo de backtest.
    decorator_backtest_pending_order_open,  # Decorator que redireciona a função para `__backtest_pending_order_open`.
    decorator_backtest_position_modify,  # Decorator que redireciona para `__backtest_position_modify`.
    decorator_backtest_pending_order_modify,  # Decorator que redireciona para `__backtest_pending_order_modify`.
    decorator_backtest_position_close,  # Decorator que redireciona para `__backtest_close_position`.
)


# **Fixture da Conta**
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
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100.

    return account


# **Função Simulada**
def dummy_func(*args, **kwargs):
    return "Function executed in live account"


# **Testes para Decorators**
def test_decorator_backtest_position_open(account):
    """
    Testa o decorator `decorator_backtest_position_open`.

    Verifica:
    1. Se `__backtest_position_open` é chamado em contas de backtest sem executar sua lógica interna.
    """
    decorated_func = decorator_backtest_position_open(dummy_func)

    # Modo Backtest
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_open",
        return_value=None,
    ) as mock_position_open:
        decorated_func(
            account.backtest_account_data.operation,
            "EURUSD",
            ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
            1.0,
        )
        mock_position_open.assert_called_once()

    # Modo Live
    account.live_account_data.is_backtest_account = False
    result = decorated_func(
        account.live_account_data.operation,
        "EURUSD",
        ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        1.0,
    )
    assert result == "Function executed in live account"


def test_decorator_backtest_pending_order_open(account):
    """
    Testa o decorator `decorator_backtest_pending_order_open`.

    Verifica se `__backtest_pending_order_open` é chamado corretamente.
    """
    decorated_func = decorator_backtest_pending_order_open(dummy_func)

    # Modo Backtest
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_open",
        return_value=None,
    ) as mock_pending_order_open:
        decorated_func(
            account.backtest_account_data.operation,
            "EURUSD",
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
            1.0,
            1.1200,
        )
        mock_pending_order_open.assert_called_once()

    # Modo Live
    account.live_account_data.is_backtest_account = False
    result = decorated_func(
        account.live_account_data.operation,
        "EURUSD",
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        1.0,
        1.1200,
    )
    assert result == "Function executed in live account"


def test_decorator_backtest_position_modify(account):
    """
    Testa o decorator `decorator_backtest_position_modify`.

    Verifica se `__backtest_position_modify` é chamado corretamente.
    """
    decorated_func = decorator_backtest_position_modify(dummy_func)

    # Modo Backtest
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_modify",
        return_value=None,
    ) as mock_position_modify:
        decorated_func(
            account.backtest_account_data.operation,
            stop_price=1.1190,
            profit_price=1.1300,
        )
        mock_position_modify.assert_called_once()

    # Modo Live
    account.live_account_data.is_backtest_account = False
    result = decorated_func(
        account.live_account_data.operation, stop_price=1.1190, profit_price=1.1300
    )
    assert result == "Function executed in live account"


def test_decorator_backtest_pending_order_modify(account):
    """
    Testa o decorator `decorator_backtest_pending_order_modify`.

    Verifica se `__backtest_pending_order_modify` é chamado corretamente.
    """
    decorated_func = decorator_backtest_pending_order_modify(dummy_func)

    # Modo Backtest
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_modify",
        return_value=None,
    ) as mock_pending_order_modify:
        decorated_func(
            account.backtest_account_data.operation,
            ticket=12345,
            price=1.1250,
            stop_price=1.1200,
            profit_price=1.1300,
        )
        mock_pending_order_modify.assert_called_once()

    # Modo Live
    account.live_account_data.is_backtest_account = False
    result = decorated_func(
        account.live_account_data.operation,
        ticket=12345,
        price=1.1250,
        stop_price=1.1200,
        profit_price=1.1300,
    )
    assert result == "Function executed in live account"


def test_decorator_backtest_position_close(account):
    """
    Testa o decorator `decorator_backtest_position_close`.

    Verifica se `__backtest_position_close` é chamado corretamente.
    """
    decorated_func = decorator_backtest_position_close(dummy_func)

    # Modo Backtest
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_close",
        return_value=None,
    ) as mock_close_position:
        decorated_func(account.backtest_account_data.operation, position_ticket=12345)
        mock_close_position.assert_called_once()

    # Modo Live
    account.live_account_data.is_backtest_account = False
    result = decorated_func(account.live_account_data.operation, position_ticket=12345)
    assert result == "Function executed in live account"
