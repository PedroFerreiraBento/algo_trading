# Test library
import pytest  # For unit testing

# MetaTrader5 account and information module
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class for managing accounts

# MetaTrader5 models and enums
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum for order types (buy, sell, limit, etc.)
    ENUM_DEAL_TYPE,  # Enum for deal types (DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_DEAL_ENTRY,  # Enum for deal entry type (IN, OUT, INOUT)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for account trade mode (real, demo, hedge)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stopout type
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for account margin mode
    ENUM_ORDER_TYPE_MARKET,  # Enum for market orders
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_SYMBOL_CALC_MODE,
    MqlAccountInfo,  # Model with detailed account information
)

# Auxiliary modules
from datetime import datetime, timezone  # For date and time manipulation
import pandas as pd  # For time series data manipulation (last candles)

# Functions for creating and manipulating deals and positions
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_create_a_deal,  # Internal function for creating deals in backtest
    __backtest_position_open,  # Internal function for opening positions in backtest mode
)


@pytest.fixture
def account():
    """Fixture that creates an account instance for testing.

    Simulates logging into a live account before backtesting.

    Returns:
        Account: An account instance with configured data."
    """
    account = Account()

    # Simulates logging into a live account before backtesting
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


def test_backtest_create_a_deal_buy_entry_in(account: Account):
    """
    Tests the `__backtest_create_a_deal` function with a BUY entry (`DEAL_ENTRY_IN`).

    Verifies:
    1. If the deal is created correctly.
    2. If the profit (`profit`) is 0 for a new buy entry.
    3. If the important deal attributes (symbol, order type, comment, magic number) are correct.

    Args:
        account (Account): Fixture that provides a pre-configured backtest account.
    """
    # **Backtest account configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with $5,000 balance and 1:100 leverage
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread for 4 points
    )
    account.backtest_account_data.magic_number = (
        123456  # Defines the magic number for the account to identify automatic operations
    )

    # **Initial position configuration**
    symbol = "EURUSD"  # Currency pair being traded
    initial_price = 1.12345  # Opening price of the position
    initial_volume = 1.0  # Initial volume in lots (1 lot = 100,000 units)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Gets the account operation handler
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Defines the account currency

    # **Mock of candle to simulate market state**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Defines the tick volume to simulate liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Defines the new symbol data as a dictionary
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
        "last_candle": mock_series,
    }

    # Creates a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new row to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Hedge mode configuration**
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )  # Allows multiple positions on the same asset

    # **Initial position opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Market buy order
        volume=initial_volume,  # Volume of 1 lot
        stop_price=1.12,  # Stop-loss price
        profit_price=1.13,  # Take-profit price
        comment="Test Hedge Mode",
    )

    # **Opened position mock**
    position = account.backtest_account_data.positions[
        0
    ]  # Gets the opened position after `__backtest_open_position`

    # **Deal creation**
    deal_time = datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc)  # Deal time
    volume = 1.0  # Volume of the new entry
    price = 1.1250  # Deal price
    comment = "Test Buy Entry"  # Deal comment

    # Calls the `__backtest_create_a_deal` function to create the buy deal
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        volume=volume,
        price=price,
        position=position,
        comment=comment,
    )

    # **Created Deal Verifications**
    assert deal.symbol == symbol, "The deal symbol is incorrect."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "The deal type should be BUY."
    assert (
        deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_IN
    ), "The deal entry should be IN."
    assert deal.profit == 0, "The profit should be 0 for a new buy entry."
    assert deal.comment == comment, "The deal comment is incorrect."
    assert deal.magic == 123456, "The magic number of the deal is incorrect."


def test_backtest_create_a_deal_sell_entry_out(account: Account):
    """
    Tests the `__backtest_create_a_deal` function with a partial sell entry (`DEAL_ENTRY_OUT`).

    Verifies:
    1. If the partial sell deal is created correctly.
    2. If the profit is positive when the position is closed with profit.
    3. If the important deal attributes (symbol, order type, volume, comment, profit) are correct.

    Args:
        account (Account): Fixture that provides a pre-configured backtest account.
    """
    # **Backtest account configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with $5,000 balance and 1:100 leverage
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread for 4 points
    )
    account.backtest_account_data.magic_number = 654321  # Defines the magic number

    # **Initial position configuration**
    symbol = "EURUSD"  # Currency pair being traded
    initial_price = 1.1300  # Opening price of the position (for SELL)
    initial_volume = 1.0  # Initial volume in lots (1 lot = 100,000 units)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Gets the account operation handler
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Defines the account currency

    # **Mock of candle to simulate market state**
    mock_series_data = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": initial_price,
        "tick_volume": 200,  # Volume of ticks to simulate liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Defines the new symbol data as a dictionary
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
        "last_candle": mock_series,
    }

    # Creates a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new row to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Hedge mode configuration**
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )

    # **Initial position opening of SELL**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Market sell order
        volume=initial_volume,  # Volume of 1 lot
        stop_price=1.1350,  # Stop-loss price
        profit_price=1.1200,  # Take-profit price
        comment="Test SELL Position",
    )

    # **Mock of opened position**
    position = account.backtest_account_data.positions[
        0
    ]  # Gets the opened position after `__backtest_open_position`

    # **Partial close deal parameters**
    deal_time = datetime(2025, 1, 3, 13, 0, tzinfo=timezone.utc)  # Deal time
    partial_volume = 0.5  # Partial close of 0.5 lots
    close_price = 1.1250  # Close price
    comment = "Test Partial Close"

    # **Partial close deal creation**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Market buy order to close part of the SELL position
        volume=partial_volume,
        price=close_price,
        position=position,
        comment=comment,
    )

    # **Created Deal Verifications**
    assert deal.symbol == symbol, "The deal symbol is incorrect."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "The deal type should be BUY."
    assert (
        deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT
    ), "The deal entry should be OUT."
    assert (
        deal.volume == partial_volume
    ), "The deal volume should be equal to the partial close volume."
    assert (
        deal.position_id == position.ticket
    ), "The position ID in the deal is incorrect."
    assert (
        deal.profit == 250
    ), "The profit should be positive for a partial close with a favorable price."
    assert deal.comment == comment, "The deal comment is incorrect."
    assert deal.magic == 654321, "The magic number of the deal is incorrect."


def test_backtest_create_a_deal_inout_reversal(account: Account):
    """
    Tests the `__backtest_create_a_deal` function with a reversal (`DEAL_ENTRY_INOUT`).

    Verifies:
    1. If the reversal deal is created correctly.
    2. If the profit of the reversal is calculated correctly.
    3. If the important deal attributes (symbol, order type, volume, comment, profit) are correct.

    Args:
        account (Account): Fixture that provides a pre-configured backtest account.
    """
    # **Backtest account configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with $5,000 balance and 1:100 leverage
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread for 4 points
    )
    account.backtest_account_data.magic_number = 789012  # Defines the magic number

    # **Initial position configuration**
    symbol = "EURUSD"  # Currency pair being traded
    initial_price = 1.1300  # Opening price of the position (for SELL)
    initial_volume = 1.0  # Initial volume in lots (1 lot = 100,000 units)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Gets the account operation handler
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Defines the account currency

    # **Mock of candle to simulate market state**
    mock_series_data = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": initial_price,
        "tick_volume": 200,  # Volume of ticks to simulate liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Defines the new symbol data as a dictionary
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
        "last_candle": mock_series,
    }

    # Creates a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new row to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Hedge mode configuration**
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )

    # **Initial position opening of SELL**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Market sell order
        volume=initial_volume,  # Volume of 1 lot
        stop_price=1.1350,  # Stop-loss price
        profit_price=1.1200,  # Take-profit price
        comment="Test SELL Position",
    )

    # **Mock of opened position**
    position = account.backtest_account_data.positions[
        0
    ]  # Gets the opened position after `__backtest_open_position`

    # **Reversal deal parameters**
    deal_time = datetime(2025, 1, 3, 14, 0, tzinfo=timezone.utc)  # Deal time
    reversal_volume = 2.0  # Volume to reverse the position
    close_price = 1.1250  # Close price to reverse the position
    comment = "Test Reversal"

    # **Reversal deal creation**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Market buy order to reverse the SELL position
        volume=reversal_volume,
        price=close_price,
        position=position,
        comment=comment,
    )

    # **Expected Profit Calculation**
    contract_size = operation_handler.backtest_symbols_data.loc[symbol].contract_size
    expected_profit = round(
        (initial_price - close_price) * contract_size * position.volume, 2
    )  # (1.1300 - 1.1250) * 100.000 * 1 lot

    # **Created Deal Verifications**
    assert deal.symbol == symbol, "The deal symbol is incorrect."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "The deal type should be BUY."
    assert (
        deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT
    ), "The deal entry should be INOUT (reversal)."
    assert (
        deal.volume == reversal_volume
    ), "The deal volume should be equal to the reversal volume."
    assert (
        deal.position_id == position.ticket
    ), "The position ID in the deal is incorrect."
    assert (
        deal.profit == expected_profit
    ), f"The profit should be {expected_profit} USD for a profitable reversal."
    assert deal.comment == comment, "The deal comment is incorrect."
    assert deal.magic == 789012, "The magic number of the deal is incorrect."


def test_backtest_create_a_deal_no_order_id(account: Account):
    """
    Tests the `__backtest_create_a_deal` function with `order` as `None`.

    Verifies:
    1. If a random ID is generated automatically when `order` is not provided.
    2. If the important deal attributes (symbol, order type, volume, comment, order ID) are correct.

    Args:
        account (Account): Fixture that provides a pre-configured backtest account.
    """
    # **Backtest account configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with $5,000 balance and 1:100 leverage
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread for 4 points
    )
    account.backtest_account_data.magic_number = 123456  # Defines the magic number

    # **Initial position configuration**
    symbol = "EURUSD"  # Currency pair being traded
    initial_price = 1.1200  # Opening price of the position
    initial_volume = 1.0  # Initial volume in lots (1 lot = 100,000 units)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Gets the account operation handler
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"  # Defines the account currency

    # **Mock of candle to simulate market state**
    mock_series_data = {
        "open": 1.1195,
        "high": 1.1210,
        "low": 1.1185,
        "close": initial_price,
        "tick_volume": 150,  # Volume of ticks to simulate liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Defines the new symbol data as a dictionary
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
        "last_candle": mock_series,
    }

    # Creates a DataFrame for the new symbol with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new row to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Hedge mode configuration**
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )

    # **Initial position opening of BUY**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Market buy order
        volume=initial_volume,  # Volume of 1 lot
        stop_price=1.1150,  # Stop-loss price
        profit_price=1.1300,  # Take-profit price
        comment="Test BUY Position",
    )

    # **Mock of opened position**
    position = account.backtest_account_data.positions[
        0
    ]  # Gets the opened position after `__backtest_open_position`

    # **Deal parameters without order ID**
    deal_time = datetime(2025, 1, 3, 15, 0, tzinfo=timezone.utc)  # Deal time
    volume = 1.0  # Volume of the new entry
    price = 1.1250  # Deal price
    comment = "Test No Order ID"  # Deal comment

    # **Deal creation without order ID**
    deal = __backtest_create_a_deal(
        operation_class=operation_handler,
        symbol=symbol,
        deal_time=deal_time,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Market buy order
        volume=volume,
        price=price,
        position=position,
        order=None,  # ID of order not provided
        comment=comment,
    )

    # **Created Deal Verifications**
    assert deal.symbol == symbol, "The deal symbol is incorrect."
    assert deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY, "The deal type should be BUY."
    assert (
        deal.volume == volume
    ), "The deal volume should be equal to the order volume."
    assert deal.comment == comment, "The deal comment is incorrect."
    assert deal.magic == 123456, "The magic number of the deal is incorrect."
    assert deal.order is not None, "The order ID should not be None."
    assert isinstance(deal.order, int), "The order ID should be an integer."
