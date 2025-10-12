# **Python Standard Libraries**
import pytest  # Framework for automated test creation and execution
from datetime import (
    datetime,
    timezone,
    timedelta,
    time,
)  # Date and time manipulation
import pandas as pd  # DataFrames and time series manipulation

# **Import Enums and MetaTrader 5 Classes**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_PENDING,  # Types of pending orders (`BUY_LIMIT`, `SELL_STOP`, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for trading mode (`DEMO`, `LIVE`, etc.)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stop out mode (`PERCENT`, `MONEY`, etc.)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for margin type (`RETAIL_HEDGING`, `NETTING`, etc.)
    ENUM_SYMBOL_CALC_MODE,  # Enum for calculation mode (`FOREX`, `CFD`, `FUTURES`, etc.)
    ENUM_SYMBOL_SWAP_MODE,
    MqlAccountInfo,  # Class for account information (balance, margin, trading mode, etc.)
)

# **Import Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_check_expiration,  # Function to check and remove expired pending orders
    __backtest_pending_order_open,  # Function to create pending orders in backtest mode
)

# **Import Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Class representing the trading account


# **Account Fixture for Tests**
@pytest.fixture
def account():
    """
    Fixture that creates an account instance for testing.
    Simulates login to a live account before backtesting.
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

    return account


# **Test 1: Order expiration at exact time**
def test_order_expiration_specified_time(account: Account):
    """
    Tests the expiration of pending orders with type `ORDER_TIME_SPECIFIED`.

    Verifies if the order expires at the exact specified time.
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

    # Create a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Order expiration after opening time
    order_expiration_time = last_candle_time + timedelta(minutes=1)

    # Create pending order
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.11,
        expiration=order_expiration_time,
        comment="Order 1",
    )

    # Update the last candle after expiration
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.13, "low": 1.09, "close": 1.11},
        name=order_expiration_time + timedelta(seconds=1),
    )

    # Execute expiration check
    __backtest_pending_order_check_expiration(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have expired and been removed."


# **Test 2: Order expiration at the end of the day (`ORDER_TIME_SPECIFIED_DAY`)**
def test_order_expiration_specified_day(account: Account):
    """
    Tests the expiration of pending orders with type `ORDER_TIME_SPECIFIED_DAY`.

    Verifies if the order expires at the end of the specified day (23:59:59).
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

    # Create a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Expiration at the end of the day (23:59:59 UTC)
    order_expiration_datetime = datetime.combine(
        last_candle_time.date(), datetime.min.time(), tzinfo=timezone.utc
    )
    expiration_end_of_day = order_expiration_datetime.replace(
        hour=23, minute=59, second=59
    )

    # Create pending order with expiration at the end of the day
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
        volume=1,
        price=1.11,
        expiration=expiration_end_of_day,
        comment="Order 2",
    )

    # Update the last candle to 23:59:59 of the same day
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.14, "low": 1.10, "close": 1.13},
        name=expiration_end_of_day,
    )

    # Execute expiration check
    __backtest_pending_order_check_expiration(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have expired and been removed."


# **Test 3: Order without expiration (should not be removed)**
def test_order_no_expiration(account: Account):
    """
    Tests pending orders without `time_expiration`.

    Verifies if the order is not removed when `time_expiration` is `None`.
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

    # Create a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Create pending order without expiration
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.12,
        expiration=None,
        comment="Order 3",
    )

    # Update the last candle to a later time
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_time + timedelta(minutes=10),
    )

    # Execute expiration check
    __backtest_pending_order_check_expiration(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The order should not have expired."


# **Test 4: Multiple orders with different expiration types**
def test_multiple_orders_with_different_expirations(account: Account):
    """
    Tests the behavior with multiple pending orders with different expiration types.

    Verifies if each order is handled correctly based on its expiration type.
    """
    # **Account initialization in backtest mode**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    symbol = "EURUSD"
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # **Simulation of the last candle at the time of order opening**
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

    # Create a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Create multiple orders with different expiration types**

    # 1. Order that should expire after 5 minutes
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.11,
        expiration=last_candle_time + timedelta(minutes=5),  # Expira às 12:05
        comment="Order 4",  # Should expire
    )

    # 2. Order that should expire at the end of the day (23:59:59)
    expiration_date = datetime.combine(
        last_candle_time.date(), time(23, 59, 59), tzinfo=timezone.utc
    )
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
        volume=1,
        price=1.10,
        expiration=expiration_date,  # Expires at the end of the day
        comment="Order 5",  # Should expire
    )

    # 3. Order without expiration
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.12,
        expiration=None,  # Does not expire
        comment="Order 6",  # Should not expire
    )

    # Update the last candle to 10 minutes after order creation (12:10)
    updated_candle_time = last_candle_time + timedelta(minutes=10)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.10, "close": 1.14},
        name=updated_candle_time,
    )

    # Execute expiration check
    __backtest_pending_order_check_expiration(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 2
    ), "Only orders without expiration and not expired should remain."
    assert (
        operation_handler.account_data.orders[0].comment == "Order 5"
    ), "Order `Order 5` should remain."
    assert (
        operation_handler.account_data.orders[1].comment == "Order 6"
    ), "Order `Order 6` should remain."
