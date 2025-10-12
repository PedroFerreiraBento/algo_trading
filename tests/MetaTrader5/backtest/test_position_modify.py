# **Test Libraries**
import pytest  # Library for creating and executing unit tests.

# **Date and Time Libraries**
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # Used to define timestamps with UTC timezone and date/time manipulation.

# **MetaTrader5 Models and Enums**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Model containing trading account information (e.g., balance, margin, account name).
    ENUM_ACCOUNT_TRADE_MODE,  # Enum defining the trading account mode (e.g., demo, real).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum defining the stop-out mode (e.g., percent or fixed value).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum defining the type of margin of the account (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum that defines the types of market orders (e.g., BUY/SELL).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)

# **Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_open,  # Function that simulates opening positions in backtest mode.
    __backtest_position_modify,  # Function that simulates modifying positions in backtest mode.
)

# **Custom Exceptions**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
)  # Custom exception raised when a position cannot be selected.

# **Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class used for login and management of trading account information.

# **Data Manipulation Library**
import pandas as pd  # Library used to create and manipulate `Series` objects that simulate market candles.


@pytest.fixture
def account():
    """Fixture that creates an account instance for tests.

    Simulates login to a live account before backtest.

    Returns:
        Account: Instance of account with configured data.
    """
    account = Account()

    # Simulates login to a live account before backtest
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


def test_backtest_modify_position_single_position(account: Account):
    """
    Tests the `__backtest_modify_position` function when there is only one open position.

    Verifies:
    1. If the position is automatically selected when no `ticket` is passed.
    2. If the attributes `stop_price`, `profit_price` and `comment` are modified correctly.

    Args:
        account (Account): Fixture that provides a backtest account pre-configured.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Starts the account with a balance of $5.000 and leverage 1:100.
    account.backtest_account_data.magic_number = (
        654321  # Defines the magic number of the account to identify operations.
    )

    # **Initial Position Configuration**
    symbol = "EURUSD"  # Currency pair being traded.
    initial_volume = 1.0  # Initial position volume (1 lot = 100,000 units).
    initial_price = 1.12345  # Initial position opening price.
    initial_stop_price = 1.1200  # Stop-loss price.
    initial_profit_price = 1.1300  # Take-profit price.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time.

    # **Mock Candle for Market Simulation**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume of ticks to simulate liquidity.
    }
    mock_time_index = pd.to_datetime(position_time)
    mock_series = pd.Series(mock_series_data, name=mock_time_index)

    # Define the last candle for the currency pair.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Gets the operation handler.
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

    # **Initial Position Opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Market buy order.
        volume=initial_volume,
        stop_price=initial_stop_price,
        profit_price=initial_profit_price,
        comment="Initial position",  # Initial position comment.
    )
    position = account.backtest_account_data.positions[0]  # Gets the opened position.

    # **Modification Parameters**
    new_stop_price = 1.1180  # New stop-loss price.
    new_profit_price = 1.1350  # New take-profit price.
    new_comment = "Modified position"  # New comment.

    # **Position Modification**
    __backtest_position_modify(
        operation_class=operation_handler,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        comment=new_comment,
    )

    # **Verifications**
    assert position.sl == new_stop_price, "The stop-loss was not updated correctly."
    assert (
        position.tp == new_profit_price
    ), "The take-profit was not updated correctly."
    assert (
        position.comment == new_comment
    ), "The comment was not updated correctly."


def test_backtest_modify_position_no_position_found(account: Account):
    """
    Tests the `__backtest_modify_position` function when there are no open positions or
    when the provided `ticket` does not correspond to any position.

    Verifies:
    1. If an exception `CouldNotSelectPosition` is raised when there are no positions.
    2. If an exception is raised when the provided `ticket` is invalid.

    Args:
        account (Account): Fixture that provides a backtest account pre-configured.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Starts the account with a balance of $5.000 and leverage 1:100.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Gets the operation handler.
    symbol = "EURUSD"  # Currency pair being traded.
    initial_price = 1.12345  # Initial position opening price.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time.

    # **Mock Candle for Market Simulation**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume of ticks to simulate liquidity.
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

    # **Test: No open position**
    with pytest.raises(CouldNotSelectPosition, match="Could not select the position"):
        __backtest_position_modify(
            operation_class=operation_handler,
            stop_price=1.1200,
            profit_price=1.1300,
            comment="Attempt to modify non-existent position",
        )

    # **Initial Position Opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1200,
        profit_price=1.1300,
        comment="Position 1",
    )

    # **Test: Wrong ticket**
    with pytest.raises(CouldNotSelectPosition, match=r"Could not select the position"):
        __backtest_position_modify(
            operation_class=operation_handler,
            position=999999,  # Invalid ticket (does not correspond to any position).
            stop_price=1.1190,
            profit_price=1.1380,
            comment="Attempt to modify with wrong ticket",
        )


def test_backtest_modify_position_specific_ticket(account: Account):
    """
    Tests the `__backtest_modify_position` function when there are multiple open positions and
    a specific `ticket` is provided.

    Verifies:
    1. If the correct position is selected by the `ticket`.
    2. If the attributes `stop_price`, `profit_price` and `comment` are modified correctly.

    Args:
        account (Account): Fixture that provides a backtest account pre-configured.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Starts the account with a balance of $5.000 and leverage 1:100.
    symbol = "EURUSD"  # Currency pair being traded.
    operation_handler = (
        account.backtest_account_data.operation
    )  # Gets the operation handler.
    initial_price = 1.12345  # Initial position opening price.
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle time.

    # **Mock Candle for Market Simulation**
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,  # Volume of ticks to simulate liquidity.
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

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Initial Position Opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1200,
        profit_price=1.1300,
        comment="Position 1",
    )

    # **Timestamp Update to Ensure Difference between Orders**
    updated_time = operation_handler.backtest_symbols_data.loc[
        symbol
    ].last_candle.name + timedelta(days=2)
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        mock_series_data, name=pd.to_datetime(updated_time)
    )

    # **Second Position Opening with Different Timestamp**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1.0,
        stop_price=1.1220,
        profit_price=1.1350,
        comment="Position 2",
    )

    # **Selects the Position to be Modified**
    position_to_modify = account.backtest_account_data.positions[
        1
    ]  # Selects the second position.

    # **Modification Parameters**
    new_stop_price = 1.1190  # New stop-loss.
    new_profit_price = 1.1380  # New take-profit.
    new_comment = "Updated Position 2"  # New comment.

    # **Position Modification**
    __backtest_position_modify(
        operation_class=operation_handler,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        position=position_to_modify.ticket,  # Provides the specific `ticket`.
        comment=new_comment,
    )

    # **Verifications**
    assert (
        position_to_modify.sl == new_stop_price
    ), "The stop-loss was not updated correctly."
    assert (
        position_to_modify.tp == new_profit_price
    ), "The take-profit was not updated correctly."
    assert (
        position_to_modify.comment == new_comment
    ), "The comment was not updated correctly."
