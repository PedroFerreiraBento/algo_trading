# **Test Libraries**
import pytest  # Library for creating and executing unit tests

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
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum defining the margin type of the account (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum defining the types of market orders (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum defining the types of pending orders (e.g., BUY LIMIT, SELL STOP).
    ENUM_ORDER_TYPE_TIME,  # Enum for order expiration types (e.g., GTC, specified time).
    MqlTradeOrder,  # Model representing a pending or executed trade order.
    ENUM_ORDER_STATE,  # Enum defining the state of the order (e.g., `ORDER_STATE_PLACED`, `ORDER_STATE_FILLED`).
    ENUM_ORDER_REASON,  # Enum indicating the reason for order creation (e.g., manual, expert).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_ORDER_TYPE,
)

# **Custom Exceptions**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
)  # Custom exception raised when it is not possible to select a position based on the ticket.

# **Backtest Functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_open,  # Function that simulates the opening of pending orders in backtest mode.
)


# **Account Class**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # The `Account` class is used for login and management of trading account information.

import pandas as pd


@pytest.fixture
def account():
    """Fixture that creates an account instance for tests.

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


def test_backtest_open_pending_order(account: Account):
    """
    Tests the `__backtest_open_pending_order` function to verify if a pending order is opened correctly.

    Verifies:
    1. If the pending order is added to the list of orders.
    2. If the important attributes of the order (symbol, order type, volume, price, etc.) are correct.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with a balance of $5.000 and leverage 1:100
    account.backtest_account_data.magic_number = 987654  # Defines the "magic number" of the account to identify automatic operations
    account.backtest_account_data.type_filling = (
        ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY
    )  # Order execution type
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
        "last_candle": pd.Series(
            {"open": 1.12, "high": 1.15, "low": 1.09, "close": 1.13},
            name=datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc),
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # **Pending Order Parameters**
    order_type = (
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT
    )  # Pending order type BUY LIMIT
    volume = 1.0  # Order volume in lots
    price = 1.1200  # Desired execution price (limit)
    stop_limit = 0.0  # Not used in this case
    stop_price = 1.1150  # Stop-loss
    profit_price = 1.1300  # Take-profit
    expiration = datetime.now(timezone.utc) + timedelta(
        days=2
    )  # Expiration of the pending order
    comment = "Pending order test"

    # **Pending Order Opening**
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=order_type,
        volume=volume,
        price=price,
        stop_limit=stop_limit,
        stop_price=stop_price,
        profit_price=profit_price,
        expiration=expiration,
        comment=comment,
    )

    # **Verifications**
    # Verifies if a new pending order was added to the list of orders
    assert (
        len(account.backtest_account_data.orders) == 1
    ), "The pending order was not added correctly."

    # Gets the created pending order
    pending_order: MqlTradeOrder = account.backtest_account_data.orders[-1]

    assert pending_order.symbol == symbol, "The symbol of the pending order is incorrect."
    assert pending_order.type == order_type, "The type of the pending order is incorrect."
    assert (
        pending_order.volume_initial == volume
    ), "The initial order volume is incorrect."
    assert (
        pending_order.price_open == price
    ), "The desired execution price is incorrect."
    assert pending_order.sl == stop_price, "The stop loss price is incorrect."
    assert pending_order.tp == profit_price, "The take profit price is incorrect."
    assert (
        pending_order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    ), "The expiration type of the pending order is incorrect."
    assert (
        pending_order.time_expiration == expiration
    ), "The expiration time of the pending order is incorrect."
    assert (
        pending_order.comment == comment
    ), "The comment of the pending order is incorrect."
    assert (
        pending_order.magic == 987654
    ), "The magic number of the pending order is incorrect."

    # Verifies if the state of the pending order is "ORDER_STATE_PLACED"
    assert (
        pending_order.state == ENUM_ORDER_STATE.ORDER_STATE_PLACED
    ), "The state of the pending order should be 'ORDER_STATE_PLACED'."
    assert (
        pending_order.reason == ENUM_ORDER_REASON.ORDER_REASON_EXPERT
    ), "The reason of the order should be 'ORDER_REASON_EXPERT'."


def test_validate_pending_order_prices_with_spread(account: Account):
    """
    Tests the `__backtest_pending_order_open` function to validate prices
    based on the spread and pending order type.

    Verifies:
    1. If the validations for pending order prices are performed correctly.
    2. If exceptions are raised for prices outside the allowed range.
    """
    # **Backtest Account Configuration**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Initializes the account with a balance of $5.000 and leverage 1:100
    account.backtest_account_data.magic_number = (
        987654  # Defines the "magic number" of the account
    )
    account.backtest_account_data.simulated_spread = (
        2  # Defines the simulated spread in points
    )
    symbol = "EURUSD"

    # **Recent candle configuration**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
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

    # Gets the current price and calculates the spread
    close_price = 1.13  # Closing price of the last candle
    tick_size = 1e-05
    spread = account.backtest_account_data.simulated_spread * tick_size

    # **Valid prices tests**
    valid_price_buy_limit = close_price - 0.005
    valid_price_sell_limit = close_price + 0.005

    # Ordem BUY_LIMIT válida
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
        volume=1.0,
        price=valid_price_buy_limit,
        stop_limit=0,
        stop_price=1.12,
        profit_price=1.14,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid BUY_LIMIT order",
    )

    # Valid SELL_LIMIT order
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
        volume=1.0,
        price=valid_price_sell_limit,
        stop_limit=0,
        stop_price=1.14,
        profit_price=1.12,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid SELL_LIMIT order",
    )

    # **Invalid prices tests**
    invalid_price_buy_limit = (
        close_price + 0.005
    )  # BUY_LIMIT cannot be greater than or equal to the current price
    invalid_price_sell_limit = (
        close_price - 0.005
    )  # SELL_LIMIT cannot be less than or equal to the current price
    invalid_price_buy_stop = (
        close_price - 0.005
    )  # BUY_STOP cannot be less than or equal to the current price with spread
    invalid_price_sell_stop = (
        close_price + spread + 0.005
    )  # SELL_STOP cannot be greater than or equal to the current price

    # Invalid BUY_LIMIT order
    with pytest.raises(ValueError, match="should be less than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
            volume=1.0,
            price=invalid_price_buy_limit,
            stop_limit=0,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_LIMIT order",
        )

    # Invalid SELL_LIMIT order
    with pytest.raises(ValueError, match="should be greater than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
            volume=1.0,
            price=invalid_price_sell_limit,
            stop_limit=0,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_LIMIT order",
        )

    # BUY_STOP invalid
    with pytest.raises(ValueError, match="should be greater than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
            volume=1.0,
            price=invalid_price_buy_stop,
            stop_limit=0,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP order",
        )

    # SELL_STOP invalid
    with pytest.raises(ValueError, match="should be less than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
            volume=1.0,
            price=invalid_price_sell_stop,
            stop_limit=0,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP order",
        )

    # **Valid prices for STOP_LIMIT tests**
    valid_price_buy_stop_limit = close_price + spread + 0.005
    valid_stop_limit_buy = (
        valid_price_buy_stop_limit - 0.002
    )  # Stop limit less than the initial price
    valid_price_sell_stop_limit = close_price - 0.005
    valid_stop_limit_sell = (
        valid_price_sell_stop_limit + 0.002
    )  # Stop limit greater than the initial price

    # BUY_STOP_LIMIT valid
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
        volume=1.0,
        price=valid_price_buy_stop_limit,
        stop_limit=valid_stop_limit_buy,
        stop_price=1.12,
        profit_price=1.14,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid BUY_STOP_LIMIT order",
    )

    # SELL_STOP_LIMIT valid
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
        volume=1.0,
        price=valid_price_sell_stop_limit,
        stop_limit=valid_stop_limit_sell,
        stop_price=1.14,
        profit_price=1.12,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid SELL_STOP_LIMIT order",
    )

    # **Invalid prices for STOP_LIMIT tests**
    invalid_price_buy_stop_limit = (
        close_price - 0.005
    )  # Initial price less than the current price
    invalid_stop_limit_buy = (
        invalid_price_buy_stop_limit + 0.002
    )  # Stop limit greater than the initial price
    invalid_price_sell_stop_limit = (
        close_price + spread + 0.005
    )  # Initial price greater than the current price
    invalid_stop_limit_sell = (
        invalid_price_sell_stop_limit - 0.002
    )  # Stop limit less than the initial price

    # BUY_STOP_LIMIT invalid
    with pytest.raises(ValueError, match="should be greater than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_buy_stop_limit,
            stop_limit=valid_stop_limit_buy,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP_LIMIT order",
        )

    # SELL_STOP_LIMIT invalid
    with pytest.raises(ValueError, match="should be less than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_sell_stop_limit,
            stop_limit=invalid_stop_limit_sell,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP_LIMIT order",
        )

    # **Invalid prices for BUY_STOP_LIMIT tests**
    invalid_price_buy_stop_limit = close_price + spread + 0.005  # Initial price valid
    invalid_stop_limit_buy = (
        invalid_price_buy_stop_limit + 0.002
    )  # Stop limit invalid (greater than the initial price)

    # BUY_STOP_LIMIT invalid
    with pytest.raises(ValueError, match="should be less than the initial price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_buy_stop_limit,
            stop_limit=invalid_stop_limit_buy,  # Stop limit inválido
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP_LIMIT order (stop_limit)",
        )

    # SELL_STOP_LIMIT invalid
    with pytest.raises(ValueError, match="should be less than the current price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_sell_stop_limit,
            stop_limit=valid_stop_limit_sell,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP_LIMIT order",
        )

    # **Invalid prices for SELL_STOP_LIMIT tests**
    valid_price_sell_stop_limit = (
        close_price - 0.005
    )  # Initial price valid (less than the current price)
    invalid_stop_limit_sell = (
        valid_price_sell_stop_limit - 0.002
    )  # Stop limit invalid (less than the initial price)

    # SELL_STOP_LIMIT invalid
    with pytest.raises(ValueError, match="should be greater than the initial price"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            volume=1.0,
            price=valid_price_sell_stop_limit,  # Initial price valid
            stop_limit=invalid_stop_limit_sell,  # Stop limit invalid
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP_LIMIT order (stop_limit)",
        )
