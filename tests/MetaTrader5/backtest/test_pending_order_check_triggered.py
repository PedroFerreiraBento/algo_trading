# **Imports of Libraries and Dependencies**
import pytest  # Framework for automated test creation and execution
from datetime import datetime, timezone, timedelta  # Date and time manipulation
import pandas as pd  # DataFrames and time series manipulation

# **Import Enums and MetaTrader 5 Classes**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_PENDING,  # Types of pending orders (BUY_LIMIT, SELL_LIMIT, BUY_STOP, etc.)
    ENUM_ORDER_TYPE,  # Types of orders (buy and sell)
    ENUM_SYMBOL_CALC_MODE,  # Calculation mode (Forex, CFD, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Account operation modes (DEMO, REAL)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Stop out mode (percent or monetary value)
    ENUM_ACCOUNT_MARGIN_MODE,  # Margin calculation mode (Hedging or Netting)
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_POSITION_TYPE,
    MqlAccountInfo,  # Account information structure (balance, margin, etc.)
)

# **Import Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_check_expiration,  # Function to check and remove expired pending orders
    __backtest_pending_order_check_triggered,  # Function to check if a pending order was triggered
    __backtest_pending_order_open,  # Function to create and register a pending order
)

# **Import Account Class for Tests**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class for manipulating account data during backtesting


# **Account Fixture for Tests**
@pytest.fixture
def account():
    """
    Fixture that creates an account instance for tests.
    Simulates login to a live account and reinitializes the account in backtest mode.
    """
    account = Account()

    # Simulate login to a live account before backtesting
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


# **Test 1: Buy Limit Order Triggered**
def test_buy_limit_triggered(account: Account):
    """
    Tests if a `BUY_LIMIT` order is triggered correctly when the `high` price of the candle reaches the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `BUY_LIMIT` order with price of 1.12 (equal to the `high` of the candle)
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
    ), "The order should be present before activation."

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have expired and been removed."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The corresponding position should have been opened."


# **Test 2: Sell Limit Order Triggered**
def test_sell_limit_triggered(account: Account):
    """
    Tests if a `SELL_LIMIT` order is triggered correctly when the `low` price of the candle reaches the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `SELL_LIMIT` order with price of 1.10 (equal to the `low` of the candle)
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
    ), "The order should be present before activation."

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have been triggered and removed."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The corresponding position should have been opened."


# **Test 3: Buy Limit Order Not Triggered**
def test_buy_limit_not_triggered(account: Account):
    """
    Tests if a `BUY_LIMIT` order is not triggered when the `high` price of the candle does not reach the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `BUY_LIMIT` order with price of 1.12 (above the `high` of the candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        volume=1,
        price=1.0,
        comment="Buy Limit Order",
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The order should not have been triggered."


# **Test 4: Sell Stop Order Not Triggered**
def test_sell_stop_not_triggered(account: Account):
    """
    Tests if a `SELL_STOP` order is not triggered when the `low` price of the candle does not reach the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `SELL_STOP` order with price of 1.10 (below the `low` of the candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
        volume=1,
        price=1.10,
        comment="Sell Stop Order",
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The order should not have been triggered."


# **Test 5: Buy Stop Order Triggered**
def test_buy_stop_triggered(account: Account):
    """
    Tests if a `BUY_STOP` order is triggered correctly when the `high` price of the candle reaches the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `BUY_STOP` order with price of 1.14 (equal to the `high` of the candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        volume=1,
        price=1.14,
        comment="Buy Stop Order",
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have been triggered and removed."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The corresponding position should have been opened."


# **Test 6: Sell Limit Order Triggered by `low`**
def test_sell_limit_triggered_low(account: Account):
    """
    Tests if a `SELL_LIMIT` order is triggered correctly when the `low` price of the candle reaches the order price.
    """
    # Resetting the account
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `SELL_LIMIT` order with price of 1.08 (equal to the `low` of the candle)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
        volume=1,
        price=1.12,
        comment="Sell Limit Order",
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The order should have been triggered and removed."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The corresponding position should have been opened."


# **Test 7: Buy Stop Limit Order Triggers and Checks Limit**
def test_buy_stop_limit_triggers_and_checks_limit(account: Account):
    """
    Tests if a `BUY_STOP_LIMIT` order creates a `BUY_LIMIT` order correctly.
    Verifies:
    1. Case where the `LIMIT` order is not triggered after creation.
    2. Case where the `LIMIT` order is triggered on the same candle.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4

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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `BUY_STOP_LIMIT` order with initial price of 1.12 and limit price of 1.125
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
        volume=1,
        price=1.12,  # Initial price
        stop_limit=1.05,  # Limit price
        stop_price=1.0,
        profit_price=1.13,
        comment="Buy Stop Limit Order",
    )

    # Simulate the activation of the `STOP_LIMIT` order
    updated_candle_time = last_candle_time + timedelta(minutes=1)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.11, "high": 1.11996, "low": 1.10, "close": 1.11},
        name=updated_candle_time,
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify after expiration
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The `BUY_STOP_LIMIT` order should create a `BUY_LIMIT` pending order."

    # Verify the details of the created `BUY_LIMIT` order
    buy_limit_order = operation_handler.account_data.orders[0]
    assert (
        buy_limit_order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT
    ), "The created order should be of type `BUY_LIMIT`."
    assert buy_limit_order.price_open == 1.05, "The `BUY_LIMIT` price is incorrect."
    assert (
        buy_limit_order.volume_initial == 1
    ), "The volume of the `BUY_LIMIT` is incorrect."
    assert buy_limit_order.sl == 1.0, "The stop-loss of the `BUY_LIMIT` is incorrect."
    assert buy_limit_order.tp == 1.13, "The take-profit of the `BUY_LIMIT` is incorrect."

    # Simulate a scenario where the `LIMIT` order is not triggered
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.124, "low": 1.05, "close": 1.123},
        name=updated_candle_time + timedelta(minutes=1),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # The `LIMIT` order should still be pending
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The `BUY_LIMIT` order should not have been triggered yet."
    assert (
        operation_handler.account_data.positions == []
    ), "No position should have been opened."

    # Simulate a scenario where the `LIMIT` order is triggered on the next candle
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.125, "high": 1.13, "low": 1.04996, "close": 1.126},
        name=updated_candle_time + timedelta(minutes=2),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify if the `LIMIT` order was triggered
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The `BUY_LIMIT` order should have been triggered."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A corresponding position should have been opened."

    # Verify the details of the opened position
    position = operation_handler.account_data.positions[0]
    assert position.symbol == symbol, "The symbol of the position is incorrect."
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "The type of the position is incorrect."
    assert position.price_open == 1.05, "The opening price of the position is incorrect."
    assert position.volume == 1, "The volume of the position is incorrect."
    assert position.sl == 1.0, "The stop-loss of the position is incorrect."
    assert position.tp == 1.13, "The take-profit of the position is incorrect."


# **Test 8: Sell Stop Limit Order Triggers and Checks Limit**
def test_sell_stop_limit_triggers_and_checks_limit(account: Account):
    """
    Tests if a `SELL_STOP_LIMIT` order creates a `SELL_LIMIT` order correctly.
    Verifies:
    1. Case where the `LIMIT` order is not triggered after creation.
    2. Case where the `LIMIT` order is triggered on the same candle.
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
            {"open": 1.20, "high": 1.22, "low": 1.19, "close": 1.21},
            name=last_candle_time,
        ),
    }

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Open `SELL_STOP_LIMIT` order with initial price of 1.18 and limit price of 1.175
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT,
        volume=1,
        price=1.18,  # Initial price
        stop_limit=1.185,  # Limit price
        stop_price=1.19,
        profit_price=1.16,
        comment="Sell Stop Limit Order",
    )

    # Simulate the activation of the `STOP_LIMIT` order
    updated_candle_time = last_candle_time + timedelta(minutes=1)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.19, "high": 1.20, "low": 1.18, "close": 1.18},
        name=updated_candle_time,
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify if the `STOP_LIMIT` order was removed and `LIMIT` was created
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The `SELL_STOP_LIMIT` order should create a `SELL_LIMIT` pending order."

    # Verify the details of the created `SELL_LIMIT` order
    sell_limit_order = operation_handler.account_data.orders[0]
    assert (
        sell_limit_order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT
    ), "The created order should be of type `SELL_LIMIT`."
    assert (
        sell_limit_order.price_open == 1.185
    ), "The `SELL_LIMIT` price is incorrect."
    assert (
        sell_limit_order.volume_initial == 1
    ), "The volume of the `SELL_LIMIT` is incorrect."
    assert sell_limit_order.sl == 1.19, "The stop-loss of the `SELL_LIMIT` is incorrect."
    assert sell_limit_order.tp == 1.16, "The take-profit of the `SELL_LIMIT` is incorrect."

    # Simulate a scenario where the `LIMIT` order is not triggered
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.18, "high": 1.184, "low": 1.176, "close": 1.177},
        name=updated_candle_time + timedelta(minutes=1),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # The `LIMIT` order should still be pending
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The `SELL_LIMIT` order should not have been triggered yet."
    assert (
        operation_handler.account_data.positions == []
    ), "No position should have been opened."

    # Simulate a scenario where the `LIMIT` order is triggered on the next candle
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.175, "high": 1.185, "low": 1.174, "close": 1.175},
        name=updated_candle_time + timedelta(minutes=2),
    )
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify if the `LIMIT` order was triggered
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The `SELL_LIMIT` order should have been triggered."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "A position corresponding should have been opened."

    # Verify the details of the opened position
    position = operation_handler.account_data.positions[0]
    assert position.symbol == symbol, "The symbol of the position is incorrect."
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
    ), "The type of the position is incorrect."
    assert (
        position.price_open == 1.185
    ), "The opening price of the position is incorrect."
    assert position.volume == 1, "The volume of the position is incorrect."
    assert position.sl == 1.19, "The stop-loss of the position is incorrect."
    assert position.tp == 1.16, "The take-profit of the position is incorrect."


# **Test 9: Invalid Order Type**
def test_invalid_order_type(account: Account):
    """
    Tests if the system ignores orders with unknown types.
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Create an invalid order type (not mapped)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY,  # Invalid order type
        volume=1,
        price=1.14,
        comment="Invalid Order Type",
    )

    # Execute expiration check
    __backtest_pending_order_check_triggered(operation_handler)

    # Verify if the invalid order is still present
    assert (
        len(operation_handler.account_data.orders) == 1
    ), "The invalid order should not have been triggered."
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "No position should have been opened."


# **Test 10: Expired Order Should Not Be Triggered**
def test_expired_order_not_triggered(account: Account):
    """
    Tests if an expired order is not triggered even if the price is reached.
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

    # Create a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Expired order
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

    # Execute expiration check
    __backtest_pending_order_check_expiration(operation_class=operation_handler)
    __backtest_pending_order_check_triggered(operation_class=operation_handler)

    # Verify if the expired order is still present (should not be triggered)
    assert (
        len(operation_handler.account_data.orders) == 0
    ), "The expired order should not have been triggered."
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "No position should have been opened."
