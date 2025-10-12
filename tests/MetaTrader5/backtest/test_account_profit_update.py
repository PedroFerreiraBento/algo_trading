# **Importation of libraries and dependencies**

# **Importation of standard libraries**
import pytest  # Framework for tests
from datetime import datetime, timezone  # Date and time manipulation
import pandas as pd  # Data manipulation library

# **Importation of classes, enums and functions of MetaTrader 5**

# Models and enums for MetaTrader 5 operations
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Account information model
    ENUM_ORDER_TYPE_MARKET,  # Enum for types of market orders (buy/sell)
    ENUM_SYMBOL_CALC_MODE,  # Enum for symbol calculation modes (Forex, CFDs, etc.)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for account trading modes
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for account stop-out modes
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for account margin modes
    ENUM_SYMBOL_SWAP_MODE,  # Enum for symbol swap modes
)

# Backtest functions of MetaTrader 5
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_update_price_and_profit,  # Function to update position price and profit
    __backtest_position_open,  # Function to open market positions during backtesting
    __backtest_position_apply_swap_to_positions,  # Function to apply swaps to open positions
)

# Account management class
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class for login and account data management


# **Account fixture for tests**
@pytest.fixture
def account():
    """
    Creates an account instance with simulated data for testing.
    """
    account = Account()
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


# **Test 1: Update of price and profit for a buy position**
def test_update_buy_position_price_and_profit(account: Account):
    """
    Tests the update of the current price and profit calculation for a buy position.

    Objective:
    - Verify if the position opening price is calculated correctly considering the spread.
    - Validate if the position current price is updated based on the last closing price.
    - Ensure that the profit is calculated accurately based on the price difference.
    """
    # Initializes the account in backtest mode with initial balance and leverage
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Market parameters configuration**
    symbol = "EURUSD"
    contract_size = 100_000  # 1 lot = 100.000 units
    tick_size = 0.00001  # 1 pip = 0.00001

    # Define the new symbol data as a dictionary
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_candle_price = 1.14  # Closing price of the candle
    last_candle = {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_candle_price}

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
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Creates a DataFrame for the new symbol data with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new symbol data to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Last price candle**
    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Buy position opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,
        comment="Position 1 (Buy)",
    )

    # **Position price and profit update**
    __backtest_position_update_price_and_profit(operation_handler)
    positions = account.backtest_account_data.positions

    # **Verification of opening and current price**
    assert (
        positions[0].price_open == open_position_price
    ), "The opening price of the position does not match the expected value."
    assert (
        positions[0].price_current == close_candle_price
    ), "The current price of the position was not updated correctly."

    # **Verification of expected profit**
    expected_profit = round(
        (close_candle_price - open_position_price) * contract_size, 2
    )
    assert (
        positions[0].profit == expected_profit
    ), f"Profit is incorrect. Expected: {expected_profit}, obtained: {positions[0].profit}"


# **Test 2: Update of price and loss for a sell position**
def test_update_sell_position_price_and_profit(account: Account):
    """
    Tests the update of the current price and loss calculation for a sell position.

    Objective:
    - Verify if the opening price of the position is calculated correctly considering the spread.
    - Validate if the current price of the position is updated based on the last closing price.
    - Ensure that the profit/loss is calculated accurately based on the price difference.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    symbol = "EURUSD"
    contract_size = 100_000
    tick_size = 0.00001
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_candle_price = 1.14
    last_candle = {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_candle_price}

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
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Creates a DataFrame for the new symbol data with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new symbol data to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    position_price_current = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Sell position opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=1,
        comment="Position 2 (Sell)",
    )

    # **Price and loss update**
    __backtest_position_update_price_and_profit(operation_handler)
    positions = account.backtest_account_data.positions

    assert (
        positions[0].price_open == close_candle_price
    ), "The opening price of the position does not match the expected value."
    assert (
        positions[0].price_current == position_price_current
    ), "The current price of the position was not updated correctly."

    expected_profit = round(
        (position_price_current - close_candle_price) * contract_size * -1, 2
    )
    assert (
        positions[0].profit == expected_profit
    ), f"Profit is incorrect. Expected: {expected_profit}, obtained: {positions[0].profit}"


# **Test 3: Profit zero if the price does not change**
def test_update_position_no_price_change(account: Account):
    """
    Tests the update of the current price and profit calculation with unchanged price.

    Objective:
    - Ensure that the opening price of the buy position is calculated correctly considering the spread.
    - Maintain the same closing price in `last_candle` after opening the position.
    - Verify that the profit remains zero when the price does not change.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Market parameters configuration**
    symbol = "EURUSD"  # Currency pair
    contract_size = 100_000  # 1 lot = 100.000 units of the base currency
    tick_size = 0.00001  # Price precision (1 pip = 0.00001)

    # **Last candle before opening the position**
    last_candle_time_before = datetime(
        2025, 1, 10, 12, 0, tzinfo=timezone.utc
    )  # Time of the last candle before opening the position
    close_candle_price = 1.12  # Closing price
    last_candle_before = {
        "open": close_candle_price,
        "high": 1.15,
        "low": 1.11,
        "close": close_candle_price,
    }

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
        "last_candle": pd.Series(last_candle_before, name=last_candle_time_before),
    }

    # Creates a DataFrame for the new symbol data with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new symbol data to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Price calculation adjusted by spread**
    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )

    # **Buy position opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Order type: buy
        volume=1,  # Volume of 1 lot
        comment="Position 1 (Buy)",  # Comment identifying the position
    )

    # **Last candle after opening the position (same closing price)**
    last_candle_time_after = datetime(
        2025, 1, 10, 12, 5, tzinfo=timezone.utc
    )  # Time after opening the position
    last_candle_after = {
        "open": close_candle_price,
        "high": 1.15,
        "low": 1.11,
        "close": open_position_price,
    }

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle_after, name=last_candle_time_after
    )

    # **Price and profit update**
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Updates the current price and profit of the position
    positions = account.backtest_account_data.positions  # Gets the open positions

    # **Verification of the opening and current price**
    assert (
        positions[0].price_open == open_position_price
    ), f"The opening price of the position is incorrect. Expected: {open_position_price}, obtained: {positions[0].price_open}"
    assert (
        positions[0].price_current == open_position_price
    ), f"The current price was not updated correctly. Expected: {open_position_price}, obtained: {positions[0].price_current}"

    # **Verification of expected profit**
    expected_profit = 0.0  # The expected profit should be zero because the price did not change
    assert (
        positions[0].profit == expected_profit
    ), f"Profit is incorrect. Expected: {expected_profit}, obtained: {positions[0].profit}"


# **Test 4: Negative profit for a buy position with swap applied**
def test_account_profit_with_buy_position_and_swap(account: Account):
    """
    Tests the calculation of the `profit` total of the account considering a buy position with negative profit
    due to `swap` and spread application.

    Objective:
    - Verify if the opening price of the position is calculated correctly considering the spread.
    - Validate if the `swap` is applied correctly after closing time (22:00 UTC).
    - Verify that the total profit of the account is updated correctly with the `swap`.
    """
    account.login_backtest(
        balance=10000, leverage=100
    )  # Initializes the account with initial balance and leverage
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Market parameters configuration**
    symbol = "EURUSD"  # Currency pair
    tick_size = 0.00001  # Price precision (1 pip = 0.00001)

    # **Last candle before closing time**
    last_candle_time = datetime(
        2025, 1, 10, 12, 0, tzinfo=timezone.utc
    )  # Friday, 12h UTC
    close_candle_price = 1.15  # Closing price of the last candle

    # **Prices of the candle before opening the position**
    last_candle = {"open": 1.12, "high": 1.16, "low": 1.11, "close": close_candle_price}

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
        "last_candle": pd.Series(last_candle, name=last_candle_time),
    }

    # Creates a DataFrame for the new symbol data with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new symbol data to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = last_candle_time

    open_position_price = round(
        close_candle_price
        + (operation_handler.account_data.simulated_spread * tick_size),
        5,
    )  # Opening price with spread

    # **Buy position opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Order type: buy
        volume=1,  # 1 lote
        comment="Position 1 (Buy)",  # Comment to identify the position
    )

    # **Candle after closing time to activate the `swap`**
    last_candle_time_swap = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Friday, 23h UTC

    # Updates the last candle to validate the swap
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        last_candle, name=last_candle_time_swap
    )

    # **Swap application to open positions**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Applies the `swap` after closing time (22h UTC)

    # **Price and profit update**
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Updates the current price and profit with the `swap`
    positions = account.backtest_account_data.positions  # Gets the open positions

    # **Verification of the opening price, `swap` and expected profit**
    assert (
        positions[0].price_open == open_position_price
    ), f"The opening price is incorrect. Expected: {open_position_price}, obtained: {positions[0].price_open}"
    assert (
        positions[0].swap == -1.0
    ), f"The `swap` value is incorrect. Expected: -1.0, obtained: {positions[0].swap}"
    assert (
        positions[0].profit == -4.0
    ), f"The position profit is incorrect. Expected: -4.0, obtained: {positions[0].profit}"

    # **Total profit calculation**
    total_profit_with_swap = round(positions[0].swap + positions[0].profit, 2)
    assert (
        account.backtest_account_data.profit == total_profit_with_swap
    ), f"The total profit of the account is incorrect. Expected: {total_profit_with_swap}, obtained: {account.backtest_account_data.profit}"
