# **Test Libraries**
import pytest  # Library for creating and executing unit tests.

# **Date and Time Libraries**
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # Utilized to define timestamps with UTC timezone and date and time manipulation.

# **MetaTrader5 Models and Enums**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Model that contains trading account information (e.g., balance, margin, account name).
    MqlTradeOrder,  # Model that represents a pending or executed trade order.
    ENUM_ACCOUNT_TRADE_MODE,  # Enum that defines the trading account mode (e.g., demo, real).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stop-out mode (e.g., percentage or fixed value).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for defining the type of margin of the account (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum that defines market order types (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum that defines pending order types (e.g., BUY LIMIT, SELL STOP).
    ENUM_ORDER_TYPE_TIME,  # Enum for order expiration types (e.g., GTC, specified time).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_ORDER_TYPE,
)

# **Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_open,  # Function that simulates the opening of pending orders in backtest mode.
    __backtest_pending_order_modify,  # Function that simulates the modification of pending orders in backtest mode.
)

# **Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # The `Account` class is used for login and management of trading account information.

import pandas as pd


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


def test_backtest_modify_pending_order(account: Account):
    """
    Tests the `__backtest_modify_pending_order` function to verify if a pending order is modified correctly.

    Verifies:
    1. If the pending order is selected and modified successfully.
    2. If the main attributes of the order (entry price, stop-loss, take-profit, expiration, comment) are updated.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with a balance of $5.000 and leverage 1:100
    account.backtest_account_data.magic_number = 123456  # Defines the "magic number" of the account to identify automatic operations
    account.backtest_account_data.type_filling = (
        ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY
    )  # Order execution type
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
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # **Initial Pending Order Parameters**
    initial_order_type = (
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT
    )  # Pending order type SELL LIMIT
    initial_volume = 1.0  # Order volume in lots
    initial_price = 1.1300  # Desired execution price
    initial_stop_price = 1.1350  # Initial stop-loss
    initial_profit_price = 1.1250  # Initial take-profit
    initial_expiration = last_candle_time + timedelta(
        days=2
    )  # Expiration of the initial pending order
    initial_comment = "Initial pending order"

    # **Initial Pending Order Opening**
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=initial_order_type,
        volume=initial_volume,
        price=initial_price,
        stop_price=initial_stop_price,
        profit_price=initial_profit_price,
        expiration=initial_expiration,
        comment=initial_comment,
    )

    # **Get the created pending order**
    pending_order: MqlTradeOrder = account.backtest_account_data.orders[-1]
    ticket = pending_order.ticket  # ID of the pending order

    # **New parameters to modify the order**
    new_price = 1.14  # New execution price
    new_stop_price = 1.1530  # New stop-loss
    new_profit_price = 0.9  # New take-profit
    new_expiration = last_candle_time + timedelta(days=3)  # New expiration date
    new_comment = "Modified pending order"

    # **Modify the pending order**
    __backtest_pending_order_modify(
        operation_class=account.backtest_account_data.operation,
        ticket=ticket,
        price=new_price,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        expiration=new_expiration,
        comment=new_comment,
    )

    # **Verification of the modification**
    assert (
        pending_order.price_open == new_price
    ), "The execution price was not updated correctly."
    assert (
        pending_order.sl == new_stop_price
    ), "The stop-loss was not updated correctly."
    assert (
        pending_order.tp == new_profit_price
    ), "The take-profit was not updated correctly."
    assert (
        pending_order.time_expiration == new_expiration
    ), "The expiration date was not updated correctly."
    assert (
        pending_order.comment == new_comment
    ), "The order comment was not updated correctly."
    assert (
        pending_order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    ), "The order time type was not updated correctly to 'ORDER_TIME_SPECIFIED'."
    assert (
        pending_order.magic == account.backtest_account_data.magic_number
    ), "The magic number of the order was not maintained correctly."


def test_validate_prices_buy_and_sell(account: Account):
    """
    Tests if the prices, stop loss (sl) and take profit (tp) are validated correctly
    for buy (BUY) and sell (SELL) orders.
    """
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with a balance of $5.000 and leverage 1:100
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
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Initial configuration
    price = 1.1300
    sl_buy = 1.1200
    tp_buy = 1.1400
    sl_sell = 1.1400
    tp_sell = 1.1200

    # Buy order
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        volume=1.0,
        price=price,
        stop_price=sl_buy,
        profit_price=tp_buy,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Buy order test",
    )

    # Sell order
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        volume=1.0,
        price=price,
        stop_price=sl_sell,
        profit_price=tp_sell,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Sell order test",
    )

    # Get the created pending orders
    buy_order = account.backtest_account_data.orders[-2]
    sell_order = account.backtest_account_data.orders[-1]

    # Validate the prices of the buy and sell orders
    assert buy_order.sl == sl_buy, "Stop loss of the buy order is incorrect."
    assert buy_order.tp == tp_buy, "Take profit of the buy order is incorrect."
    assert sell_order.sl == sl_sell, "Stop loss of the sell order is incorrect."
    assert sell_order.tp == tp_sell, "Take profit of the sell order is incorrect."


def test_validate_invalid_prices(account: Account):
    """
    Tests if the validation raises exceptions for invalid price configurations,
    including stop loss (sl) and take profit (tp).
    """
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with a balance of $5.000 and leverage 1:100
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
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Invalid configurations for testing
    invalid_price = 1.1300

    # Buy order with invalid stop loss (greater than the price)
    with pytest.raises(ValueError, match="Invalid stop loss"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1400,  # Stop loss inválido
            profit_price=1.1400,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid buy order (SL)",
        )

    # Buy order with invalid take profit (less than the price)
    with pytest.raises(ValueError, match="Invalid take profit"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1200,
            profit_price=1.1200,  # Take profit inválido
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid buy order (TP)",
        )

    # Sell order with invalid stop loss (less than the price)
    with pytest.raises(ValueError, match="Invalid stop loss"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1200,  # Stop loss inválido
            profit_price=1.1200,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid sell order (SL)",
        )

    # Sell order with invalid take profit (greater than the price)
    with pytest.raises(ValueError, match="Invalid take profit"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1400,
            profit_price=1.1400,  # Take profit inválido
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid sell order (TP)",
        )
