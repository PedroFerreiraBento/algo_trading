# **Imports of Libraries and Dependencies**

# **Test Framework**
import pytest

# **Date and Time Manipulation**
from datetime import datetime, timezone, timedelta

# **Data Structures for Candle Manipulation**
import pandas as pd

# **MetaTrader 5 Model Imports**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_POSITION_TYPE,  # Types of Positions (BUY and SELL)
    ENUM_SYMBOL_CALC_MODE,  # Calculation Modes (FOREX, CFDs, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Account Mode (DEMO, REAL)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Stop Out Mode
    ENUM_ACCOUNT_MARGIN_MODE,  # Margin Calculation Mode
    ENUM_SYMBOL_SWAP_MODE,
    MqlAccountInfo,  # Account Information Structure
)

# **Backtest Imports**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_check_stop_loss_reached,  # Stop Loss Verification Function
    __backtest_position_open,  # Position Opening Function during Backtest
)

# **Account Class Import**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account Data Manipulation Class


# **Account Fixture for Tests**
@pytest.fixture
def account():
    """
    Fixture that creates an account instance for tests.
    Simulates login to a live account and reinitializes the account in backtest mode.
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


# **Test 1: Position `BUY` Reaches Stop Loss**
def test_buy_position_stop_loss_hit(account: Account):
    """
    Tests if a `BUY` position is closed correctly when the candle's `low` price reaches the stop loss.
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
            {"open": 1.12, "high": 1.14, "low": 1.09, "close": 1.10},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `BUY` position with stop loss at 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.09,
        comment="Test Buy Position",
    )

    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The position should be open."

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position was closed
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "The `BUY` position should have been closed by the stop loss."


# **Test 2: Position `SELL` Reaches Stop Loss**
def test_sell_position_stop_loss_hit(account: Account):
    """
    Tests if a `SELL` position is closed correctly when the candle's `high` price reaches the stop loss.
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
            {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.14},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `SELL` position with stop loss at 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        stop_price=1.15,
        comment="Test Sell Position",
    )

    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The `SELL` position should be open."

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position was closed
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "The `SELL` position should have been closed by the stop loss."


# **Test 3: Position `BUY` Does Not Reach Stop Loss**
def test_buy_position_no_stop_loss(account: Account):
    """
    Tests if a `BUY` position is not closed when the candle's `low` price does not reach the stop loss.
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
            {"open": 1.12, "high": 1.14, "low": 1.11, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `BUY` position with stop loss at 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.10,
        comment="Test Buy Position",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position remains open
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The `BUY` position should not have been closed."


# **Test 4: Position `SELL` Does Not Reach Stop Loss**
def test_sell_position_no_stop_loss(account: Account):
    """
    Tests if a `SELL` position is not closed when the candle's `high` price does not reach the stop loss.
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
            {"open": 1.12, "high": 1.13, "low": 1.11, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `SELL` position with stop loss at 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        stop_price=1.14,
        comment="Test Sell Position",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position remains open
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The `SELL` position should not have been closed."


# **Test 5: Position Without Stop Loss Configured**
def test_position_without_stop_loss(account: Account):
    """
    Tests if a position is not closed when there is no stop loss configured.
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
            {"open": 1.12, "high": 1.13, "low": 1.11, "close": 1.12},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `BUY` position without stop loss
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=0.0,  # Sem stop loss
        comment="Test Buy Position Without SL",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position remains open
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The position should not have been closed, as there is no stop loss configured."


# **Test 6: Position `BUY` with Stop Loss Reached Exactly at `low`**
def test_buy_position_stop_loss_exact_low(account: Account):
    """
    Tests if a `BUY` position is closed correctly when the candle's `low` price is exactly equal to the stop loss.
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
            {"open": 1.12, "high": 1.14, "low": 1.10, "close": 1.11},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `BUY` position with stop loss at 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.10,
        comment="Test Buy Position Exact SL",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position was closed
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "The `BUY` position should have been closed by the stop loss."


# **Test 7: Position `SELL` with Stop Loss Reached Exactly at `high`**
def test_sell_position_stop_loss_exact_high(account: Account):
    """
    Tests if a `SELL` position is closed correctly when the candle's `high` price is exactly equal to the stop loss.
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `SELL` position with stop loss at 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        stop_price=1.14,
        comment="Test Sell Position Exact SL",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position was closed
    assert (
        len(operation_handler.account_data.positions) == 0
    ), "The `SELL` position should have been closed by the stop loss."


# **Test 8: Position `BUY` with Stop Loss Not Hit (`low` Above the SL)**
def test_buy_position_stop_loss_not_hit(account: Account):
    """
    Tests if a `BUY` position remains open when the candle's `low` price is above the stop loss.
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
            {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `BUY` position with stop loss at 1.10
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.10,
        comment="Test Buy Position SL Not Hit",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position remains open
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The `BUY` position should not have been closed."


# **Test 9: Position `SELL` with Stop Loss Not Hit (`high` Below the SL)**
def test_sell_position_stop_loss_not_hit(account: Account):
    """
    Tests if a `SELL` position remains open when the candle's `high` price is below the stop loss.
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens a `SELL` position with stop loss at 1.14
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        stop_price=1.14,
        comment="Test Sell Position SL Not Hit",
    )

    # Verifies if the stop loss was reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if the position remains open
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The `SELL` position should not have been closed."


# **Test 10: Multiple Positions with Stop Loss**
def test_multiple_positions_stop_loss(account: Account):
    """
    Tests the behavior with multiple positions open with different stop losses.
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
            {"open": 1.12, "high": 1.15, "low": 1.09, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Opens multiple positions with different stop losses
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.10,
        comment="Test Buy Position SL 1",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,
        volume=1,
        stop_price=1.14,
        comment="Test Sell Position SL 2",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        volume=1,
        stop_price=1.08,  # Should not be reached
        comment="Test Buy Position SL 3",
    )

    # Verifies if the stop losses were reached
    __backtest_position_check_stop_loss_reached(operation_handler)

    # Verifies if only the positions with stop loss reached were closed
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "Only the `Test Buy Position SL 3` position should remain open."
