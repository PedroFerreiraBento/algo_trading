# Imports for external libraries
import pytest  # Library for creating unit tests
from datetime import (
    datetime,
    timezone,
)

# Classes for date and time manipulation
import pandas as pd  # Library for DataFrame manipulation

# Imports of enums, classes and models related to MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE_MARKET,  # Enum for market order types
    ENUM_POSITION_TYPE,  # Enum for position types
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for account margin modes
    MqlAccountInfo,  # Model of MetaTrader5 account information
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for account operation modes
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for account stopout modes
    ENUM_DEAL_TYPE,  # Enum for deal types (e.g., order execution)
    ENUM_DEAL_ENTRY,  # Enum for deal entries (entry, exit)
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_SYMBOL_CALC_MODE,
)

# Imports of specific functions related to backtesting
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __hedge_create_position_and_deal,  # Internal function to create position and deal in hedge mode
    __netting_create_position_and_deal,  # Internal function to create position and deal in netting mode
    __backtest_position_open,  # Internal function to open position during backtesting
)

# Import of the Account module (account management)
from algo_trading.sources.MetaTrader5_source.account.account import Account

from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    InsufficientMarginError,
)


@pytest.fixture
def account():
    """Fixture that creates an account instance for tests.

    Simulates logging into a live account before backtesting.

    Returns:
        Account: Account instance with configured data.
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


def test_hedge_create_position_and_deal(account):
    """Tests the `__hedge_create_position_and_deal` function.

    This test verifies the behavior of the function when creating a position and registering a deal
    in a backtest account configured in hedge mode.

    The hedge mode allows multiple positions to be opened on the same currency pair,
    allowing simultaneous buy and sell positions without aggregation.

    Test steps:
    1. Initial configuration of the backtest account with balance and spread.
    2. Execution of the `__hedge_create_position_and_deal` function with specific parameters.
    3. Verification of open positions and deal history to ensure correct behavior.

    Args:
        account (Account): Fixture providing a pre-configured backtest account.
    """

    # Configuration of the backtest account:
    # Sets the initial balance and leverage and activates the backtest mode.
    account.login_backtest(balance=5000, leverage=100)

    # Simulates the spread for the currency pair (4 points)
    account.backtest_account_data.simulated_spread = 4

    # Gets the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation

    # Parameters for position creation
    symbol = "EURUSD"  # Currency pair to be traded
    order_type = ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY  # Order type (buy)
    position_time = datetime(
        2023, 12, 31, tzinfo=timezone.utc
    )  # Date and time of the operation
    price = 1.12345  # Opening price
    volume = 1.0  # Position volume (in lots)

    # Executes the function to create position and register deal
    __hedge_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=order_type,
        position_time=position_time,
        price=price,
        volume=volume,
        stop_price=1.12000,  # Stop-loss configured
        profit_price=1.13000,  # Take-profit configured
    )

    # Verification 1: There should be exactly one open position after execution
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The position was not created correctly."

    # Verification 2: The deal history should have exactly two entries:
    # - 1º: Deal of account initialization (initial deposit).
    # - 2º: Deal corresponding to the new position opening.
    assert (
        len(operation_handler.account_data.history_deals) == 2
    ), "The deal history was not updated correctly."

    # Access the open position and the last deal to validate its information
    position = operation_handler.account_data.positions[0]  # Open position
    deal = operation_handler.account_data.history_deals[-1]  # Last registered deal

    # Verification 3: Validate the open position information
    assert (
        position.symbol == symbol
    ), "The symbol of the position does not match the expected value."
    assert position.volume == volume, "The volume of the position is incorrect."
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "The position type should be buy."
    assert (
        deal.price == price
    ), "The price of the deal does not match the expected value."


def test_netting_create_position_and_deal_partial_close(account):
    """
    Tests the partial closing of a position in a backtest account with netting.

    This test verifies if, when partially closing a position, the operation is
    performed correctly and the position and deal history data are updated.

    Args:
        account: Fixture providing a pre-configured backtest account with initial values.
    """

    # Configures the backtest account with an initial balance and simulated spread.
    account.login_backtest(balance=5000, leverage=100)
    account.backtest_account_data.simulated_spread = 4  # Simulates a spread of 4 points.

    # Gets the operation handler from the backtest account.
    operation_handler = account.backtest_account_data.operation
    # Define the new symbol data as a dictionary
    symbol = "EURUSD"  # Currency pair to be traded.
    position_time = datetime(2023, 12, 31, tzinfo=timezone.utc)  # Position time.
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
    # Step 1: Creates a **buy (BUY)** position.
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Order type (buy).
        position_time=position_time,
        price=1.12345,  # Opening price.
        volume=1.0,  # Position volume (1 lot).
    )

    # Step 2: Partially closes the position with a **sell (SELL)**.
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Order type (sell).
        position_time=position_time,
        price=1.12,  # Closing price.
        volume=0.5,  # Closes half of the volume (0.5 lots).
    )

    # Verifications: Confirms if the position and deal history values were updated correctly.

    # The remaining position should have a volume of 0.5 lots.
    assert operation_handler.account_data.positions[0].volume == 0.5

    # The position direction should remain as BUY (since it was a partial sell).
    assert (
        operation_handler.account_data.positions[0].type
        == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    )

    # There should be exactly 3 deals in the history:
    # 1º: Deal of account initialization (initial deposit).
    # 2º: Opening of the buy position (BUY).
    # 3º: Partial closing of the position with sell (SELL).
    assert len(operation_handler.account_data.history_deals) == 3

    # Verifies if the operation profit was calculated correctly.
    # Expected calculation:
    # - Price difference: (1.12345 - 1.12) = 0.00345 (points lost).
    # - Partial volume: 0.5 (lots).
    # - Contract size: 100_000 units of the base currency.
    # Profit: 100_000 * 0.5 * -0.00345 = -172.5.
    assert operation_handler.account_data.history_deals[-1].profit == -172.5


def test_netting_create_position_and_deal_reversal(account):
    """Tests the `__netting_create_position_and_deal` function with position reversal.

    This test simulates a reversal scenario in a netting-configured account,
    where an open position (SELL) is reversed with an opposite position (BUY).
    Verifies if the original position is closed and if the profit/loss is calculated correctly.

    Args:
        account (Account): Fixture providing a backtest account configured.
    """

    # Initial backtest account configuration
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the backtest with a balance of 5000 and leverage of 1:100
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread of 4 points
    )

    # Initial position parameters (SELL)
    symbol = "EURUSD"  # Currency pair to be traded
    position_time = datetime(2023, 12, 31, tzinfo=timezone.utc)  # Execution date and time
    initial_price = 1.12345  # Opening price of the SELL position
    initial_volume = 1.0  # Initial position volume (in lots)

    # Gets the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation
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
        "last_candle": None,
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # Creates the initial sell position
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        position_time=position_time,
        price=initial_price,
        volume=initial_volume,
    )

    # Verifications after opening the initial position:
    # There should be exactly one open position of type SELL
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The initial position was not created correctly."
    assert (
        operation_handler.account_data.positions[0].type
        == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
    ), "The initial position should be of type SELL."

    # Parameters for position reversal (buy volume greater than the initial sell volume)
    reversal_price = 1.12500  # Opening price of the BUY position (reversal)
    reversal_volume = 2.0  # Greater volume to force complete reversal

    # Creates the buy position to reverse the initial sell position
    __netting_create_position_and_deal(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        position_time=position_time,
        price=reversal_price,
        volume=reversal_volume,
    )

    # Verifications after reversal:
    # There should be only one open position and it should be of type BUY
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The position was not reversed correctly."
    position = operation_handler.account_data.positions[0]
    assert (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "The position should be of type BUY after reversal."
    assert position.volume == 1.0, "The position volume is incorrect after reversal."

    # Verifications in the deal history:
    # There should be exactly 3 deals: creation of the SELL position, closing of the SELL, and opening of the BUY
    assert (
        len(operation_handler.account_data.history_deals) == 3
    ), "The deal history was not updated correctly."

    # Verifies the profit/loss of the closing deal
    last_deal = operation_handler.account_data.history_deals[-1]
    expected_profit = (
        operation_handler.backtest_symbols_data.loc[symbol].contract_size
        * (initial_price - reversal_price)
        * initial_volume
    )
    assert last_deal.profit == round(
        expected_profit, 2
    ), f"The expected profit is {expected_profit}, but it was {last_deal.profit}."
    assert (
        last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    ), "The last deal type should be BUY after reversal."
    assert (
        last_deal.entry == ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT
    ), "The last deal entry should be of type INOUT after reversal."


def test_backtest_open_position_hedging(account):
    """
    Tests the __backtest_open_position function for the Hedge mode.

    Verifies if the function opens positions correctly in a backtest account configured for the Hedge mode,
    where multiple positions in the same or opposite directions are allowed.
    """

    # Initial backtest account configuration
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the backtest with a balance of 5000 and leverage of 1:100
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread of 4 points
    )

    # Initial position parameters
    symbol = "EURUSD"  # Currency pair to be traded
    initial_price = 1.12345  # Opening price of the position
    initial_volume = 1.0  # Initial position volume (in lots)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle execution time

    # Gets the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation

    # Mock of candle for simulation
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,
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

    # Configuration for Hedge mode
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    )

    # Execution of the test: opening a buy position in Hedge mode
    result = __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=initial_volume,
        stop_price=1.12,  # Preço de stop-loss
        profit_price=1.13,  # Preço de take-profit
        comment="Teste de Hedge Mode",
    )

    # Verifications of result
    assert result is True, "The function did not return True for Hedge mode."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The position was not created correctly in Hedge mode."
    assert (
        operation_handler.account_data.positions[0].type
        == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "The position should be of type BUY."
    assert (
        operation_handler.account_data.positions[0].symbol == symbol
    ), "The symbol of the position does not match the expected value."
    assert (
        operation_handler.account_data.positions[0].volume == initial_volume
    ), "The volume of the position is incorrect."

    # Verifications of deal history
    assert (
        len(operation_handler.account_data.history_deals) == 2
    ), "The deal history was not updated correctly."
    last_deal = operation_handler.account_data.history_deals[-1]
    assert (
        last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY
    ), "The last deal type should be BUY."
    assert (
        last_deal.symbol == symbol
    ), "The symbol of the last deal does not match the expected value."
    assert (
        last_deal.volume == initial_volume
    ), "The volume of the last deal does not match the expected value."


def test_backtest_open_position_netting(account):
    """
    Tests the __backtest_open_position function for the Netting mode.

    Verifies if the function opens and closes positions correctly in a backtest account configured for the Netting mode,
    where only one consolidated position per symbol is allowed.
    """

    # Initial backtest account configuration
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the backtest with a balance of 5000 and leverage of 1:100
    account.backtest_account_data.simulated_spread = (
        4  # Defines the simulated spread of 4 points
    )

    # Initial position parameters
    symbol = "EURUSD"  # Currency pair to be traded
    initial_price = 1.12345  # Opening price of the position
    initial_volume = 1.0  # Initial position volume (in lots)
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle execution time

    # Gets the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation

    # Mock of candle for simulation
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,
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

    # Configuration for Netting mode
    operation_handler.account_data.margin_mode = (
        ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_NETTING
    )

    # Execution of the test: opening a buy position in Netting mode
    result = __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=initial_volume,
        stop_price=1.12,  # Stop-loss price
        profit_price=1.13,  # Take-profit price
        comment="Teste de Netting Mode",
    )

    # Verifications of result
    assert result is True, "The function did not return True for Netting mode."
    assert (
        len(operation_handler.account_data.positions) == 1
    ), "The Netting mode allowed multiple positions in the same currency pair."
    assert (
        operation_handler.account_data.positions[0].type
        == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
    ), "The position should be of type BUY."
    assert (
        operation_handler.account_data.positions[0].symbol == symbol
    ), "The symbol of the position does not match the expected value."

    # Test of position reversal (sell in the same currency pair)
    result = __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=1.8,
        comment="Reversão de posição no Netting Mode",
    )

    assert result is True, "The function did not return True for position reversal in Netting mode."
    assert (
        operation_handler.account_data.positions[0].type
        == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
    ), "The position was not reversed to SELL correctly."
    assert (
        operation_handler.account_data.positions[0].volume == 0.8
    ), "The volume of the position is incorrect after reversal."

    # Verifications of deal history
    assert (
        len(operation_handler.account_data.history_deals) == 3
    ), "The deal history was not updated correctly after reversal."
    last_deal = operation_handler.account_data.history_deals[-1]
    assert (
        last_deal.type == ENUM_DEAL_TYPE.DEAL_TYPE_SELL
    ), "The last deal type should be SELL after reversal."
    assert (
        last_deal.symbol == symbol
    ), "The symbol of the last deal does not match the expected value."
    assert (
        last_deal.volume == 1.8
    ), "The volume of the last deal does not match the expected value."


def test_backtest_open_position_insufficient_margin(account):
    """
    Tests the __backtest_position_open function to verify the behavior in case of insufficient margin.

    Verifies if an exception is raised when there is insufficient margin
    to open a position in the backtest account.
    """
    # Initial backtest account configuration with low balance
    account.login_backtest(
        balance=100, leverage=100
    )  # $100 balance and 1:100 leverage
    account.backtest_account_data.simulated_spread = (
        4  # Simulated spread of 4 points
    )

    # Position parameters
    symbol = "EURUSD"
    initial_price = 1.12345  # Opening price of the position
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)  # Candle execution time
    volume = 10.0  # High volume to generate insufficient margin

    # Gets the operation handler from the backtest account
    operation_handler = account.backtest_account_data.operation

    # Mock of candle for simulation
    mock_series_data = {
        "open": 1.12340,
        "high": 1.12360,
        "low": 1.12320,
        "close": initial_price,
        "tick_volume": 100,
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

    # Verifications of insufficient margin (accepts PT/EN)
    with pytest.raises(
        InsufficientMarginError,
        match=r"(Insufficient margin to open position)",
    ):
        __backtest_position_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
            volume=volume,  # High volume to generate insufficient margin
            stop_price=1.12,  # Stop-loss price
            profit_price=1.13,  # Take-profit price
            comment="Test of insufficient margin",
        )
