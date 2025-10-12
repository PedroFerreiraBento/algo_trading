# **Test Framework**
import pytest

# **Date and Time Manipulation**
from datetime import (
    datetime,
    timezone,
)

# **MetaTrader5 Models and Enums**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum for order types (e.g., BUY, SELL)
    MqlTradeDeal,  # Model representing a trade deal
    MqlAccountInfo,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_ORDER_TYPE_MARKET,
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)

# **Custom Exceptions**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
)

# **Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_position_close,  # Function to close positions in backtest mode
    __backtest_position_open,  # Function to open positions in backtest mode
)

# **Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Account class for login and management of account information

# **Data Libraries**
import pandas as pd  # Library used for date manipulation and series creation


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


def test_backtest_close_position_success(account: Account):
    """
    Tests the `__backtest_close_position` function to ensure that a position is closed correctly in backtest mode.

    Verifies:
    1. If the position with the specified `ticket` is closed correctly.
    2. If the closing deal is created and added to the history of deals.
    3. If the position is removed from the list of open positions after closing.
    """
    # **Backtest Account Configuration**
    account.login_backtest(balance=5000, leverage=100)
    account.backtest_account_data.simulated_spread = 4
    account.backtest_account_data.magic_number = 123456

    # **Initial Position Configuration**
    symbol = "EURUSD"
    initial_volume = 1.0  # Volume of 1 lot
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)

    # **Mock Candle for Market State Simulation**
    mock_candle = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": 1.12496,  # Closing price (to simulate BID)
        "tick_volume": 200,
    }
    mock_time_index = pd.to_datetime(position_time)
    last_candle = pd.Series(mock_candle, name=mock_time_index)

    # **Operation Handler Configuration**
    operation_handler = account.backtest_account_data.operation
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
        "last_candle": last_candle,
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Hedge Mode Configuration**
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )  # Allows multiple positions on the same asset

    # **Initial Position Opening**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Market buy order
        volume=initial_volume,  # Volume of 1 lot
        stop_price=1.12,  # Stop-loss price
        profit_price=1.13,  # Take-profit price
        comment="Test Hedge Mode",
    )
    position = account.backtest_account_data.positions[-1]

    operation_handler.backtest_symbols_data.loc[symbol].last_candle.close = 1.1300

    # **Position Closing**
    __backtest_position_close(
        operation_class=operation_handler,
        position_ticket=position.ticket,
        commission=5.0,  # Fake commission
        fee=1.0,  # Fake fee
        comment="Close position test",
    )

    # **Verifications**
    assert (
        len(account.backtest_account_data.positions) == 0
    ), "The position should have been removed after closing."
    assert (
        len(account.backtest_account_data.history_deals) == 3
    ), "There should be a deal in the history after closing."

    deal: MqlTradeDeal = account.backtest_account_data.history_deals[-1]

    assert deal.symbol == symbol, "The deal symbol is incorrect."
    assert (
        deal.type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL
    ), "The order type should be SELL."
    assert (
        deal.volume == initial_volume
    ), "The deal volume should be equal to the position volume."
    assert deal.comment == "Close position test", "The deal comment is incorrect."
    assert (
        deal.profit == 500
    ), "The profit should be positive, since the position was closed with profit."


def test_backtest_close_position_not_found(account: Account):
    """
    Tests if the `__backtest_close_position` function raises an exception when trying to close a non-existent position.
    """
    # **Backtest Account Configuration**
    account.login_backtest(balance=5000, leverage=100)

    # Tries to close a position with an non-existent `ticket`
    with pytest.raises(CouldNotSelectPosition, match=r"Could not select the position"):
        __backtest_position_close(
            operation_class=account.backtest_account_data.operation,
            position_ticket=99999,  # Non-existent ticket
            comment="Close non-existent position",
        )
