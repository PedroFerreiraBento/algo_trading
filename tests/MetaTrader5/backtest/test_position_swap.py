# Imports of external libraries
import pytest
from datetime import datetime, timezone  # Data and time manipulation
import pandas as pd  # Library for data manipulation in series and tables format

# Imports of classes and enums from the metatrader model (definitions related to the financial market)
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Class that contains account information in MetaTrader 5
    ENUM_SYMBOL_SWAP_MODE,  # Enum that defines the swap calculation modes
    ENUM_ACCOUNT_TRADE_MODE,  # Enum that defines the account trading modes
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum that defines the account stop out modes
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum that defines the account margin modes
    ENUM_ORDER_TYPE_MARKET,  # Enum that defines the market order types
    ENUM_SYMBOL_CALC_MODE,  # Enum that defines the contract calculation modes
)

# Imports of backtest functions
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_apply_swap_to_positions,  # Function that applies swap to open positions
    __backtest_position_open,  # Function that opens positions during backtesting
)

# Import of the `Account` class responsible for login and account information management
from algo_trading.sources.MetaTrader5_source.account.account import Account


@pytest.fixture
def account():
    """Fixture that creates an account instance for testing.

    Simulates login to a live account before backtesting.

    Returns:
        Account: Account instance with configured data."
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


def test_apply_swap_to_multiple_positions(account: Account):
    """
    Tests the application of swaps to multiple open positions for the EURUSD pair.

    Objective:
    - Verify if swaps are applied correctly to open positions based on the configuration.
    - Evaluate if swap values differ between buy and sell positions.
    - Consider triple rollover on Wednesday.

    Configuration:
    - Swap by points (SYMBOL_SWAP_MODE_POINTS).
    - Triple rollover applied on Wednesday (3 days).
    - Buy position with swap -1.0 per lot.
    - Sell position with swap -0.5 per lot.
    """
    # Login to the backtest account with initial balance and leverage configured
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Configuration of dates
    last_swap_date = datetime(
        2025, 1, 8, 20, 0, tzinfo=timezone.utc
    )  # Wednesday 20h
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Friday 23h
    operation_handler.account_data.backtest_last_swap_date = last_swap_date

    # Last price candle for EURUSD
    last_candle = {
        "open": 1.12,
        "high": 1.15,
        "low": 1.11,
        "close": 1.13,
    }
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_swap_date
    )

    # Open a buy position and a sell position
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Buy position
        volume=1,  # 1 lot
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Sell position
        volume=2,  # 2 lots
        comment="Position 2 (Sell)",
    )

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_candle_time
    )

    # Application of swaps to open positions
    __backtest_position_apply_swap_to_positions(operation_handler)

    # Obtaining positions for verification
    positions = account.backtest_account_data.positions

    # Asserts to ensure that the positions are correct
    assert len(positions) == 2, "The number of positions does not match the expected value."

    # Verification of swap values
    buy_swap = -5.0
    sell_swap = -5.0

    assert (
        positions[0].swap == buy_swap
    ), f"Swap of the buy position is incorrect. Expected: {buy_swap}, obtained: {positions[0].swap}"
    assert (
        positions[1].swap == sell_swap
    ), f"Swap of the sell position is incorrect. Expected: {sell_swap}, obtained: {positions[1].swap}"


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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
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
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Buy position
        volume=1,  # 1 lot
        comment="Position 1 (Buy)",  # Comment identifying the position
    )

    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Sell position
        volume=2,  # 2 lots
        comment="Position 2 (Sell)",  # Comment identifying the position
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = None
    last_candle_time = datetime(
        2025, 1, 3, 18, 0, tzinfo=timezone.utc
    )  # Friday 18h

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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Friday after market close
    operation_handler.account_data.backtest_last_swap_date = datetime(
        2025, 1, 17, 23, 0, tzinfo=timezone.utc
    )  # Friday 23h
    last_candle_time = datetime(
        2025, 1, 19, 12, 0, tzinfo=timezone.utc
    )  # Sunday 12h (still closed)

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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Configuration of dates
    last_swap_date = datetime(
        2025, 1, 6, 22, 0, tzinfo=timezone.utc
    )  # Monday 22h
    last_candle_before_open = datetime(
        2025, 1, 9, 23, 0, tzinfo=timezone.utc
    )  # Thursday 23h
    last_candle_after_open = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Friday 23h

    # Sets the last swap date in the account
    operation_handler.account_data.backtest_last_swap_date = last_swap_date

    # Adds the last candle before opening the position
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": 1.13},
        name=last_candle_before_open,
    )

    # Opens positions after the Thursday candle
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

    # Updates the last candle for Friday
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.13, "high": 1.16, "low": 1.12, "close": 1.14},
        name=last_candle_after_open,
    )

    # Applies swaps to open positions
    __backtest_position_apply_swap_to_positions(operation_handler)

    # Obtains positions for verification
    positions = account.backtest_account_data.positions

    # Verifies if there are exactly 2 open positions
    assert (
        len(positions) == 2
    ), "The number of open positions does not match the expected value."

    # Verifies the swap applied to the positions
    buy_swap = -1.0  # 1 lot, swap_long = -1.0
    sell_swap = -1.0  # 2 lots, swap_short = -0.5 * 2 = -1.0

    assert (
        positions[0].swap == buy_swap
    ), f"Swap of the buy position is incorrect. Expected: {buy_swap}, obtained: {positions[0].swap}"
    assert (
        positions[1].swap == sell_swap
    ), f"Swap of the sell position is incorrect. Expected: {sell_swap}, obtained: {positions[1].swap}"
