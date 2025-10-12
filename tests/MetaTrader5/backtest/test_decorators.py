# **Test Libraries**
import pytest  # Unit testing library.
from unittest.mock import patch  # Used to create patches in tests.

# **MetaTrader5 Models and Enums**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Model representing trading account information.
    ENUM_ACCOUNT_TRADE_MODE,  # Enum indicating the trading account mode (live, demo, etc.).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum indicating the stop-out mode (percent or fixed value).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum defining the type of margin of the account (hedge, netting, etc.).
    ENUM_ORDER_TYPE_MARKET,  # Enum for market orders (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum for pending orders (e.g., BUY LIMIT, SELL STOP).
)

# **Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Class `Account` for login and management of trading account information.

# **Decorators and Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    decorator_backtest_position_open,  # Decorator that redirects to `__backtest_position_open` in backtest mode.
    decorator_backtest_pending_order_open,  # Decorator that redirects to `__backtest_pending_order_open`.
    decorator_backtest_position_modify,  # Decorator that redirects to `__backtest_position_modify`.
    decorator_backtest_pending_order_modify,  # Decorator that redirects to `__backtest_pending_order_modify`.
    decorator_backtest_position_close,  # Decorator that redirects to `__backtest_close_position`.
)


# **Account Fixture**
@pytest.fixture
def account():
    """Fixture that creates an account instance for testing.

    Simulates login to a live account before backtesting.

    Returns:
        Account: Account instance with configured data.
    """
    account = Account()

    # Simulates login to a live account before backtesting
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
    )  # Initializes the account with $5,000 balance and 1:100 leverage.

    return account


# **Simulated Function**
def dummy_func(*args, **kwargs):
    return "Function executed in live account"


# **Tests for Decorators**
def test_decorator_backtest_position_open(account):
    """
    Tests the `decorator_backtest_position_open` decorator.

    Verifies:
    1. If `__backtest_position_open` is called in backtest accounts without executing its internal logic.
    """
    decorated_func = decorator_backtest_position_open(dummy_func)

    # Backtest Mode
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

    # Live Mode
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
    Tests the `decorator_backtest_pending_order_open` decorator.

    Verifies if `__backtest_pending_order_open` is called correctly.
    """
    decorated_func = decorator_backtest_pending_order_open(dummy_func)

    # Backtest Mode
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

    # Live Mode
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
    Tests the `decorator_backtest_position_modify` decorator.

    Verifies if `__backtest_position_modify` is called correctly.
    """
    decorated_func = decorator_backtest_position_modify(dummy_func)

    # Backtest Mode
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

    # Live Mode
    account.live_account_data.is_backtest_account = False
    result = decorated_func(
        account.live_account_data.operation, stop_price=1.1190, profit_price=1.1300
    )
    assert result == "Function executed in live account"


def test_decorator_backtest_pending_order_modify(account):
    """
    Tests the `decorator_backtest_pending_order_modify` decorator.

    Verifies if `__backtest_pending_order_modify` is called correctly.
    """
    decorated_func = decorator_backtest_pending_order_modify(dummy_func)

    # Backtest Mode
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

    # Live Mode
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
    Tests the `decorator_backtest_position_close` decorator.

    Verifies if `__backtest_position_close` is called correctly.
    """
    decorated_func = decorator_backtest_position_close(dummy_func)

    # Backtest Mode
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_close",
        return_value=None,
    ) as mock_close_position:
        decorated_func(account.backtest_account_data.operation, position_ticket=12345)
        mock_close_position.assert_called_once()

    # Live Mode
    account.live_account_data.is_backtest_account = False
    result = decorated_func(account.live_account_data.operation, position_ticket=12345)
    assert result == "Function executed in live account"
