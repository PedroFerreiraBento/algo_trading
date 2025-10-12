# **Importation of libraries and dependencies**
import pytest  # Framework for tests

# **Imports related to MetaTrader5 (models and enums)**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum for order types (buy, sell, limit, etc.)
    ENUM_DEAL_TYPE,  # Enum for deal types (DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_POSITION_TYPE,  # Enum for position types (buy or sell)
    ENUM_DEAL_ENTRY,  # Enum for deal entry type (entry, exit, reversal)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for trade mode of the account (real, demo, hedge)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stopout type
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for margin mode of the account
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    MqlPositionInfo,  # Model that represents open position information
    MqlAccountInfo,  # Model that represents MetaTrader5 account information
)

# Imports of backtest functions (internal functions that perform calculations and simulation logic)
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __get_deal_type,  # Function to determine the type of deal based on the order type
    __get_entry,  # Function to determine the type of entry based on the order type and position
    __backtest_get_profit,  # Function to calculate the profit or loss of a position in backtest
    __validate_operation_handler_attributes_for_symbol,  # Function to verify if there are missing attributes
)

# **Imports for date and time manipulation**
from datetime import (
    datetime,
    timezone,
)  # For creating and manipulating datetime objects with timezone

# **Importation of the Account class (account management for backtesting)**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class for login and management of account information

# **Library for data manipulation**
import pandas as pd  # Utilized for creating and manipulating DataFrames and Series, which simulate candles and tick data


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
    )  # Initializes the account with a balance of $5.000 and leverage 1:100.

    return account


def test_get_deal_type():
    """
    Tests the `__get_deal_type` function, which determines the type of deal based on the order type.

    This test verifies:
    1. If the function returns `DEAL_TYPE_BUY` for buy order types.
    2. If the function returns `DEAL_TYPE_SELL` for sell order types.
    3. If the function raises a `TypeError` for invalid order types.
    """
    # Test of buy order types
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_BUY) == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    )
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP)
        == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    )

    # Test of sell order types
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_SELL)
        == ENUM_DEAL_TYPE.DEAL_TYPE_SELL
    )
    assert (
        __get_deal_type(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT)
        == ENUM_DEAL_TYPE.DEAL_TYPE_SELL
    )

    # Invalid order type
    with pytest.raises(TypeError, match="Invalid order type"):
        __get_deal_type("INVALID_ORDER_TYPE")


def test_get_entry():
    """
    Tests the `__get_entry` function, which determines the type of deal entry based on the current position and order type.

    This test verifies:
    1. If the function returns `DEAL_ENTRY_IN` for new entries in the same direction.
    2. If the function returns `DEAL_ENTRY_OUT` for partial or total closing of a position.
    3. If the function returns `DEAL_ENTRY_INOUT` for position reversals.
    """
    # Mock of position BUY with volume of 1.0
    position_buy = MqlPositionInfo(
        ticket=12345,
        time=datetime.now(timezone.utc),  # Corrected
        time_msc=datetime.now(timezone.utc),  # Corrected
        time_update=datetime.now(timezone.utc),  # Corrected
        time_update_msc=datetime.now(timezone.utc),  # Corrected
        type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        magic=42,
        identifier=999,
        reason=0,
        volume=1.0,
        price_open=1.2345,
        sl=1.2000,
        tp=1.2500,
        price_current=1.2400,
        swap=0.0,
        profit=100.0,
        symbol="EURUSD",
        comment="Test position",
        external_id="external_12345",
    )

    # Test of new entry (IN)
    assert (
        __get_entry(0.5, ENUM_ORDER_TYPE.ORDER_TYPE_BUY, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_IN
    )

    # Test of partial or total closing of a position (OUT)
    assert (
        __get_entry(1.0, ENUM_ORDER_TYPE.ORDER_TYPE_SELL, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT
    )

    # Test of position reversal (INOUT)
    assert (
        __get_entry(2.0, ENUM_ORDER_TYPE.ORDER_TYPE_SELL, position_buy)
        == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT
    )


def test_backtest_get_profit(account: Account):
    """
    Tests the `__backtest_get_profit` function, which calculates the profit or loss of a backtest position.

    This test verifies:
    1. If the profit is calculated correctly for buy and sell positions.
    2. If the return is zero for equal opening and closing prices.

    Args:
        account (Account): Fixture that provides a pre-configured backtest account.
    """

    # Configuration of the backtest account:
    # Define the initial balance, leverage, and enables backtest mode.
    account.login_backtest(balance=5000, leverage=100)

    # Define the simulated spread for the currency pair (4 points)
    account.backtest_account_data.simulated_spread = 4

    # Obtains the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation
    operation_handler.account_data.currency = "USD"

    # Currency pair and initial position configuration
    symbol: str = "EURUSD"
    initial_price = 1.12345  # Opening price of the position
    initial_volume = 1.0  # Initial position volume (in lots)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Mock of candle for market simulation
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Simulated tick volume simulating market liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define the new symbol data as a dictionary
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Case 1: Buy position with profit**
    # Opening price: 1.1200 | Closing price: 1.1250 | Expected profit: 500 units in the base currency (USD)
    profit_buy = __backtest_get_profit(
        operation_class=operation_handler,
        symbol=symbol,
        price_open=1.1200,  # Price at the time of opening
        price_close=1.1250,  # Price at the time of closing
        price_volume=initial_volume,  # Volume negociated (1 lot)
        position_type=ENUM_POSITION_TYPE.POSITION_TYPE_BUY,  # Position type (buy)
    )
    assert profit_buy == 500, "The profit of the buy position should be 500 USD."

    # **Case 2: Sell position with loss**
    # Opening price: 1.1300 | Closing price: 1.1350 | Expected loss: -500 units in the base currency (USD)
    profit_sell = __backtest_get_profit(
        operation_class=operation_handler,
        symbol=symbol,
        price_open=1.1300,
        price_close=1.1350,
        price_volume=1.0,
        position_type=ENUM_POSITION_TYPE.POSITION_TYPE_SELL,  # Position type (sell)
    )
    assert profit_sell == -500, "The loss of the sell position should be -500 USD."

    # **Case 3: No profit or loss**
    # Opening and closing prices are equal (1.1200)
    assert (
        __backtest_get_profit(
            operation_handler,
            symbol,
            1.1200,
            1.1200,
            1.0,
            ENUM_POSITION_TYPE.POSITION_TYPE_BUY,
        )
        == 0
    ), "The profit should be zero when the opening and closing prices are equal."


def test_validate_operation_handler_attributes_success(account: Account):
    """
    Tests if the function does not raise errors when all required attributes are present.
    """
    symbol = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time

    # Mock of candle for market simulation
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": 1.12,
        "tick_volume": 100,  # Simulated tick volume simulating market liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define the new symbol data as a dictionary
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Call without error
    __validate_operation_handler_attributes_for_symbol(operation_handler, symbol)


def test_validate_operation_handler_missing_last_candle(account: Account):
    """
    Tests if an exception is raised when the `last_candle` data is missing.
    """
    symbol = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    # Mock of candle for market simulation

    # Define the new symbol data as a dictionary
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

    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    with pytest.raises(
        ValueError,
        match=f"The data for the symbol '{symbol}' contains null or missing values in the following columns: last_candle.",
    ):
        __validate_operation_handler_attributes_for_symbol(operation_handler, symbol)


def test_validate_operation_handler_missing_symbol(account: Account):
    """
    Tests if an exception is raised when the symbol is not present in the attributes.
    """
    symbol_missing = "USDJPY"
    symbol_present = "EURUSD"
    operation_handler = account.backtest_account_data.operation
    # Mock of candle for market simulation
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": 1.12,
        "tick_volume": 100,  # Simulated tick volume simulating market liquidity
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define the new symbol data as a dictionary
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol_present])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    with pytest.raises(
        ValueError,
        match=f"The data for the symbol '{symbol_missing}' is missing in the DataFrame.",
    ):
        __validate_operation_handler_attributes_for_symbol(
            operation_handler, symbol_missing
        )
