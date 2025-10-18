# **Type Checking and Date Manipulation Libraries**
from typing import (
    Callable,
    List,
    TYPE_CHECKING,
)

# **Date Manipulation Libraries**
from datetime import (
    datetime,
    timezone,
    time,
    timedelta,
)

# **Random Ticket Generation**
import time as time_rand

# **Random Ticket Generation**
import random

# **Models and Enums from MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlPositionInfo,  # Model with information about an open position
    MqlTradeDeal,  # Model with information about a trade deal (execution result)
    MqlTradeOrder,  # Model with information about a pending or executed trade order
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for account margin modes (e.g., netting, hedging)
    ENUM_DEAL_TYPE,  # Enum for deal types (e.g., DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_DEAL_ENTRY,  # Enum for types of market entry (IN - entry, OUT - exit, INOUT - reversal)
    ENUM_DEAL_REASON,  # Enum for reasons of deal execution (e.g., expert, manual)
    ENUM_ORDER_TYPE,  # Enum for order types (buy, sell, limit, stop, etc.)
    ENUM_ORDER_REASON,  # Enum for reasons of order execution (e.g., robot, user, stop-out)
    ENUM_ORDER_TYPE_MARKET,  # Enum for market order types (buy market, sell market)
    ENUM_ORDER_TYPE_PENDING,  # Enum for pending order types (buy limit, sell stop)
    ENUM_ORDER_STATE,  # Enum for order states (pending, completed, canceled, etc.)
    ENUM_POSITION_REASON,  # Enum for reasons of position opening (e.g., expert advisor)
    ENUM_POSITION_TYPE,  # Enum for types of open positions (e.g.: buy/sell)
    ENUM_ORDER_TYPE_TIME,  # Enum for order types based on time (e.g.: Good Till Canceled - GTC)
    ENUM_SYMBOL_CALC_MODE,  # Enum for profit and margin calculation mode
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    validate_prices,
)


# **Date Functions, Trades and Exceptions Utilities**
from algo_trading.sources.MetaTrader5_source.utils.dates import (
    get_timestamp_ms,
)  # Function that returns timestamp in milliseconds
from algo_trading.sources.MetaTrader5_source.utils.trades import (
    compute_profit,  # Function that calculates the profit or loss of a position based on prices and volumes
    get_order,  # Function that searches for a specific order based on its `ticket`
)
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
    InsufficientMarginError,
)  # Custom exception for when a position cannot be selected

# **Logging Configuration**
import logging  # Logging library for registering information during execution

import pandas as pd
from decimal import Decimal


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)  # Logging configuration for format and level of logs

# **Importation Conditional for Type Checking**
# Imports `Operation` only at static analysis time to avoid circular dependencies.
if TYPE_CHECKING:
    from algo_trading.sources.MetaTrader5_source.operation.operation import (
        Operation,
    )  # Class responsible for managing operations


# Auxiliary Function ------------------------------------------------------------------------------
def __get_deal_type(
    order_type: ENUM_ORDER_TYPE,
) -> ENUM_DEAL_TYPE:
    """
    Determines the type of deal based on the order type (buy or sell).

    Args:
        order_type (ENUM_ORDER_TYPE): Order type (buy, sell, limit, stop, etc.).

    Raises:
        TypeError: Raises if the order type is invalid or not recognized.

    Returns:
        ENUM_DEAL_TYPE: Deal type corresponding to:
            - `DEAL_TYPE_BUY`: Represents a buy operation.
            - `DEAL_TYPE_SELL`: Represents a sell operation.
    """

    # Verify if the order type is a buy operation (buy)
    if order_type in (
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Order of buy market.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,  # Order of buy limit.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,  # Order of buy stop.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,  # Order of buy stop limit.
    ):
        return ENUM_DEAL_TYPE.DEAL_TYPE_BUY  # Returns the deal type "BUY".

    # Verify if the order type is a sell operation (sell)
    if order_type in (
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL,  # Order of sell market.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,  # Order of sell limit.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,  # Order of sell stop.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,  # Order of sell stop limit.
    ):
        return ENUM_DEAL_TYPE.DEAL_TYPE_SELL  # Returns the deal type "SELL".

    # Raises an error if the order type is invalid or not recognized
    raise TypeError("Invalid order type")


def __get_entry(
    volume: float,
    order_type: ENUM_ORDER_TYPE,
    position: MqlPositionInfo,
) -> ENUM_DEAL_ENTRY:
    """
    Determines the type of deal entry based on the order volume, order type,
    and direction of the open position.

    Args:
        volume (float): Deal volume (lot).
        order_type (ENUM_ORDER_TYPE): Order type (buy, sell, limit, stop, etc.).
        position (MqlPositionInfo): Position information, including type and volume.

    Returns:
        ENUM_DEAL_ENTRY: Deal entry type:
            - `DEAL_ENTRY_IN`: New entry (opening position in the same direction).
            - `DEAL_ENTRY_OUT`: Partial or total closing of the existing position.
            - `DEAL_ENTRY_INOUT`: Reversion (closing and opening position opposite).
    """

    # **Verification of opposite directions:**
    # - Case 1: The current position is "BUY" (buy) and the order is "SELL" (sell).
    # - Case 2: The current position is "SELL" (sell) and the order is "BUY" (buy).
    if (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
        and order_type
        in (
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
        )
    ) or (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
        and order_type
        in (
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
        )
    ):
        # **Case 1: Partial or total closing of the existing position:**
        if volume <= position.volume:
            return (
                ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT
            )  # Entry "OUT" (closes the position).

        # **Case 2: Reversion of position:**
        # - When the volume of the new order is greater than the volume of the current position.
        return ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT  # Entry "INOUT" (reverses the position).

    # **Case 3: New entry (position in the same direction):**
    # Returns "IN" if the current position and the new order have the same direction.
    return ENUM_DEAL_ENTRY.DEAL_ENTRY_IN


def __backtest_get_profit(
    operation_class: "Operation",
    symbol: str,
    price_open: float,
    price_close: float,
    price_volume: float,
    position_type: ENUM_POSITION_TYPE,
) -> float:
    """
    Calculates the profit or loss of a backtest position based on the opening and closing prices,
    trading volume, and account base currency.

    Args:
        operation_class (Operation): Operation class with conversion data and trading parameters.
        symbol (str): Currency pair (e.g., "EURUSD").
        price_open (float): Opening price of the position.
        price_close (float): Closing price of the position.
        price_volume (float): Position volume in lots.
        position_type (ENUM_POSITION_TYPE): Position type (buy or sell).

    Returns:
        float: Profit or loss calculated from the position.
    """

    # Calculate the profit of the position using the `compute_profit` function.
    profit: float = compute_profit(
        operation_class=operation_class,
        position_type=position_type,
        price_open=price_open,
        price_close=price_close,
        price_volume=price_volume,
        symbol=symbol,
    )

    return profit


def __validate_operation_handler_attributes_for_symbol(
    operation_class: "Operation",  # Object that manages operation data and account information
    symbol: str,  # Currency pair (e.g., "EURUSD")
):
    """
    Validates the necessary attributes for the specified symbol in the context of operations
    of backtest. Verifies the existence of required data in a DataFrame indexed by symbol.
    """
    # DataFrame with backtest data
    symbols_data = operation_class.backtest_symbols_data

    # Verifies if the symbol index exists in the DataFrame
    if symbol not in symbols_data.index:
        raise ValueError(
            f"The data for the symbol '{symbol}' is missing in the DataFrame."
        )

    # Extraction of the data row corresponding to the symbol
    symbol_data = symbols_data.loc[symbol]

    # List of required columns for validation
    required_columns = [
        "tick_size",  # Tick size (float)
        "contract_size",  # Contract size (int)
        "trade_calc_mode",  # Enum for calculation mode (int)
        "swap_mode",  # Enum for swap mode (int)
        "swap_long",  # Swap long rate (float)
        "swap_short",  # Swap short rate (float)
        "swap_rollover3days",  # Rollover day (int)
        "last_candle",  # Last candle (Series or equivalent)
    ]

    # Verify if all required columns are present
    missing_columns = [
        col for col in required_columns if col not in symbols_data.columns
    ]
    if missing_columns:
        raise ValueError(
            f"The data for the symbol '{symbol}' is missing the following required columns: {', '.join(missing_columns)}."
        )

    # Validation of null or missing values for the specific symbol
    if symbol_data.isnull().any():
        raise ValueError(
            f"The data for the symbol '{symbol}' contains null or missing values in the following columns: "
            f"{', '.join(symbol_data[symbol_data.isnull()].index)}."
        )

    # Critical value validation for the symbol
    if symbol_data["tick_size"] <= 0:
        raise ValueError(
            f"The 'tick_size' should be greater than zero for the symbol '{symbol}'."
        )
    if symbol_data["contract_size"] <= 0:
        raise ValueError(
            f"The 'contract_size' should be greater than zero for the symbol '{symbol}'."
        )

    # Validation of the 'last_candle' column
    if (
        not isinstance(symbol_data["last_candle"], pd.Series)
        or symbol_data["last_candle"].empty
    ):
        raise ValueError(
            f"The 'last_candle' column for the symbol '{symbol}' is invalid or empty."
        )

    # Validation successful
    return True


def __generate_unique_ticket():
    """
    Generates a unique ticket by combining the current timestamp in milliseconds and a random number.

    Returns:
        int: Unique ticket.
    """
    # Current timestamp in milliseconds
    timestamp_ms = int(time_rand.time() * 1000)

    # Random large number to add more randomness (7 digits)
    random_part = random.randint(1000000, 9999999)

    # Combine both to form the ticket
    ticket = int(f"{timestamp_ms}{random_part}")

    return ticket


def __convert_order_to_position_type(order_type: ENUM_ORDER_TYPE) -> ENUM_POSITION_TYPE:
    """
    Converts the type of pending order to the corresponding position type (`BUY` or `SELL`).

    Args:
        order_type (ENUM_ORDER_TYPE): Type of pending order.

    Returns:
        ENUM_POSITION_TYPE: Type of position corresponding.
    """
    if order_type in {
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
    }:
        return ENUM_POSITION_TYPE.POSITION_TYPE_BUY

    if order_type in {
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
    }:
        return ENUM_POSITION_TYPE.POSITION_TYPE_SELL

    raise ValueError(f"Unknown order type: {order_type}")


def __validate_order_price(
    operation_class: "Operation", 
    symbol: str,
    order_type: ENUM_ORDER_TYPE, 
    price: float,
    stop_limit: float = 0
):
    last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle
    
    spread = (operation_class.account_data.simulated_spread * operation_class.backtest_symbols_data.loc[symbol].tick_size)
    # **Specific validations by order type**
    if order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT:
        if price > last_candle["close"] + spread:
            raise ValueError(
                f"Price {price} for BUY_LIMIT should be less than the current price ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT:
        if price < last_candle["close"]:
            raise ValueError(
                f"Price {price} for SELL_LIMIT should be greater than the current price ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP:
        if price < last_candle["close"] + spread:
            raise ValueError(
                f"Price {price} for BUY_STOP should be greater than the current price ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP:
        if price > last_candle["close"]:
            raise ValueError(
                f"Price {price} for SELL_STOP should be less than the current price ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT:
        if price < last_candle["close"] + spread:
            raise ValueError(
                f"Initial price {price} for BUY_STOP_LIMIT should be greater than the current price ({last_candle['close']})"
            )
        if stop_limit > price:
            raise ValueError(
                f"Stop limit price {stop_limit} for BUY_STOP_LIMIT should be less than the initial price ({price})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT:
        if price > last_candle["close"]:
            raise ValueError(
                f"Initial price {price} for SELL_STOP_LIMIT should be less than the current price ({last_candle['close']})"
            )
        if stop_limit < price:
            raise ValueError(
                f"Stop limit price {stop_limit} for SELL_STOP_LIMIT should be greater than the initial price ({price})"
            )


def __validate_order_volume(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_PENDING,
    volume: float,
):
    """
    Validates the volume of a pending order based on the symbol's volume restrictions, considering pending orders and open positions.

    Args:
        operation_class (Operation): Class of operation with conversion data and account information.
        symbol (str): Currency pair (example: "EURUSD").
        order_type (ENUM_ORDER_TYPE_PENDING): Type of pending order (BUY_LIMIT, SELL_STOP).
        volume (float): Volume of the pending order.

    Raises:
        ValueError: If the volume does not meet the defined restrictions.
    """
    symbol_data = operation_class.backtest_symbols_data.loc[symbol]

    volume_min = symbol_data.volume_min
    volume_max = symbol_data.volume_max
    volume_step = symbol_data.volume_step
    volume_limit = symbol_data.volume_limit

    # Verify if the volume is below the minimum allowed volume
    if volume < volume_min:
        raise ValueError(
            f"Volume {volume} below the minimum allowed ({volume_min}) for {symbol}."
        )

    # Verify if the volume is above the maximum allowed volume
    if volume > volume_max:
        raise ValueError(
            f"Volume {volume} above the maximum allowed ({volume_max}) for {symbol}."
        )

    # Verify if the volume is a multiple of the minimum increment (volume_step)
    if Decimal(str(volume)) % Decimal(str(volume_step)) != 0:
        raise ValueError(
            f"Volume {volume} is not a multiple of the minimum increment ({volume_step}) for {symbol}."
        )

    # Determine the direction based on the order type (buy/sell)
    is_buy_order = order_type in {
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
    }

    # Calculate the aggregated volume in the same direction (pending orders + open positions)
    total_volume_in_direction = sum(
        order.volume_current
        for order in operation_class.account_data.orders
        if order.symbol == symbol
        and (order.type in {
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
        }
        if is_buy_order else
        order.type in {
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT,
        })
    ) + sum(
        position.volume
        for position in operation_class.account_data.positions
        if position.symbol == symbol
        and ((position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY) if is_buy_order else (position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL))
    )

    # Verify if the aggregated volume exceeds the defined limit
    if volume_limit > 0 and total_volume_in_direction + volume > volume_limit:
        raise ValueError(
            f"The aggregated volume in the direction {'BUY' if is_buy_order else 'SELL'} ({total_volume_in_direction + volume}) exceeds the limit allowed ({volume_limit}) for {symbol}."
        )


def __validate_position_volume(
    operation_class: "Operation",
    symbol: str,
    position_type: ENUM_POSITION_TYPE,
    volume: float,
):
    """
    Validates the volume of a position based on the symbol's volume restrictions.

    Args:
        operation_class (Operation): Class of operation with conversion data and account information.
        symbol (str): Currency pair (example: "EURUSD").
        position_type (ENUM_POSITION_TYPE): Type of market order (BUY, SELL).
        volume (float): Position volume.

    Raises:
        ValueError: If the volume does not meet the defined restrictions.
    """
    symbol_data = operation_class.backtest_symbols_data.loc[symbol]

    volume_min = symbol_data.volume_min
    volume_max = symbol_data.volume_max
    volume_step = symbol_data.volume_step
    volume_limit = symbol_data.volume_limit

    # Verify if the volume is below the minimum allowed volume
    if volume < volume_min:
        raise ValueError(
            f"Volume {volume} below the minimum allowed ({volume_min}) for {symbol}."
        )

    # Verify if the volume is above the maximum allowed volume
    if volume > volume_max:
        raise ValueError(
            f"Volume {volume} above the maximum allowed ({volume_max}) for {symbol}."
        )

    # Verify if the volume is a multiple of the minimum increment (volume_step)
    if Decimal(str(volume)) % Decimal(str(volume_step)) != 0:
        raise ValueError(
            f"Volume {volume} is not a multiple of the minimum increment ({volume_step}) for {symbol}."
        )

    # Calculate the aggregated volume in the direction of the order (considering open positions and pending orders)
    total_volume_in_direction = sum(
        pos.volume
        for pos in operation_class.account_data.positions
        if pos.symbol == symbol and pos.type == position_type
    )

    # Verify if the aggregated volume does not exceed the defined limit
    if volume_limit > 0 and total_volume_in_direction + volume > volume_limit:
        raise ValueError(
            f"The aggregated volume in the direction {position_type.name} ({total_volume_in_direction + volume}) "
            f"exceeds the limit allowed ({volume_limit}) for {symbol}."
        )


def __validate_sl_tp_prices(
    *,
    price: float,
    sl: float,
    tp: float,
    order_type,
) -> None:
    """
    Shared SL/TP validation wrapper. Calls `validate_prices` only when SL/TP are provided.

    Args:
        price (float): Reference price used to validate SL/TP (execution/current price or pending open price).
        sl (float): Stop-loss price.
        tp (float): Take-profit price.
        order_type: Directional order type (BUY/SELL or their pending equivalents) used by `validate_prices`.
    """
    if sl or tp:
        validate_prices(price=price, sl=sl, tp=tp, order_type=order_type)

# Create Deal -------------------------------------------------------------------------------------
def __backtest_create_a_deal(
    operation_class: "Operation",
    symbol: str,
    deal_time: datetime,
    order_type: ENUM_ORDER_TYPE,
    volume: float,
    price: float,
    position: MqlPositionInfo,
    fee: float = 0,
    commission: float = 0,
    order: int = None,
    comment: str = "",
    reason: ENUM_DEAL_REASON = ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
) -> MqlTradeDeal:
    """
    Creates a deal during the backtest and updates the account data if it is a closing or reversal of a position.

    Args:
        operation_class (Operation): Class of operation with conversion data and account information.
        symbol (str): Currency pair (example: "EURUSD").
        deal_time (datetime): Deal time.
        order_type (ENUM_ORDER_TYPE): Order type (buy, sell, limit, etc.).
        volume (float): Order volume in lots.
        price (float): Execution price of the deal.
        position (MqlPositionInfo): Information of the open position (type, volume, opening price, etc.).
        fee (float, optional): Fee applied to the order. Default: 0.
        commission (float, optional): Commission applied to the order. Default: 0.
        order (int, optional): ID of the order. If `None`, will be generated automatically.
        comment (str, optional): Comment about the deal. Default: "".

    Returns:
        MqlTradeDeal: Object containing the deal details.
    """
    # **1. Deal ticket generation**
    random_ticket = __generate_unique_ticket()

    # **2. Definition of the order ID**
    order_id = (
        order if order is not None else get_timestamp_ms(datetime.now(timezone.utc))
    )

    # **3. Determination of the deal type (BUY/SELL)**
    deal_type = __get_deal_type(order_type=order_type)

    # **4. Determination of the entry type (IN, OUT, INOUT)**
    entry = __get_entry(order_type=order_type, volume=volume, position=position)

    # **5. Profit Calculation for the Deal**
    if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_IN:
        close_volume = (
            volume if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT else position.volume
        )

        profit = __backtest_get_profit(
            operation_class=operation_class,
            symbol=symbol,
            position_type=position.type,
            price_open=position.price_open,
            price_close=price,
            price_volume=close_volume,
        )
    else:
        profit = 0  # Entries do not have profit immediately

    # **6. Swap Proportional to Deal Calculation**
    if volume <= position.volume:
        # Partial or total closing: calculates the proportional swap
        swap_deal = position.swap * (volume / position.volume) if position.swap else 0
        position.swap -= swap_deal  # Updates the remaining swap of the position
    else:
        # Reversal: applies the remaining swap of the position and starts with swap zero for the additional volume
        swap_deal = position.swap  # Applies the remaining swap of the position
        position.swap = 0  # Sets the swap to zero for the additional volume
        volume_excedente = volume - position.volume  # Volume that reversed the direction
        logging.info(
            f"[REVERSAL] Reversion detected - Excedent volume: {volume_excedente} lots"
        )

    # **7. Adjust the account profit for exits and reversals**
    if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_IN:
        # Reduces the total profit of open positions
        operation_class.account_data.profit -= position.profit

        # Updates the account balance with the profit/loss from the closing
        operation_class.account_data.balance = round(
            operation_class.account_data.balance + profit + swap_deal, 2
        )

        # Recalculates the margin after closing/reversal
        __backtest_account_update_margin(operation_class=operation_class)

    # **8. Deal Object Creation**
    deal = MqlTradeDeal(
        symbol=symbol,
        ticket=random_ticket,
        order=order_id,
        time=deal_time.replace(microsecond=0),
        time_msc=deal_time,
        type=deal_type,
        entry=entry,
        position_id=position.ticket,
        volume=volume,
        price=price,
        commission=commission,
        swap=round(swap_deal, 2),  # Swap applied to the deal
        profit=profit,
        fee=fee,
        comment=comment,
        magic=operation_class.account_data.magic_number,
        reason=reason,
        external_id=None,
    )

    # **9. Deal Log**
    logging.info(
        f"[DEAL] {symbol} - Ticket: {random_ticket} | Type: {'BUY' if deal_type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY else 'SELL'} "
        f"| Volume: {volume} | Price: {price:.5f} | Profit: {profit:.2f} | Swap Applied: {swap_deal:.2f} "
        f"| Updated Balance: {operation_class.account_data.balance:.2f}"
    )

    return deal


# Open Position -----------------------------------------------------------------------------------
def __hedge_create_position_and_deal(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    position_time: datetime,
    price: float,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> None:
    """
    Creates a new position and a corresponding deal in a backtest account with hedge enabled.

    Args:
        operation_class (Operation): Operation class containing account data and auxiliary methods.
        symbol (str): Currency pair being traded (e.g., "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Type of market order (BUY/SELL).
        position_time (datetime): Position creation time.
        price (float): Execution price of the order.
        volume (float): Order volume in lots.
        stop_price (float, optional): Stop-loss price. Defaults to 0.
        profit_price (float, optional): Take-profit price. Defaults to 0.
        commission (float, optional): Commission applied to the deal. Defaults to 0.
        fee (float, optional): Additional fee applied to the deal. Defaults to 0.
        comment (str, optional): Optional comment about the operation. Defaults to "".

    Returns:
        None: The function does not return anything, but updates the position and deal history.
    """
    # Converts the type of market order (BUY/SELL) to the corresponding position type.
    position_type = __convert_order_to_position_type(order_type)

    # Creation of the `MqlPositionInfo` object representing the opened position.
    position = MqlPositionInfo(
        ticket=__generate_unique_ticket(),  # Unique ticket generated with timestamp.
        time=position_time,  # Position creation time.
        time_msc=position_time,  # Time with millisecond precision.
        time_update=position_time,  # Last update time (initially equal to the opening time).
        time_update_msc=position_time,  # Time with millisecond precision.
        type=position_type,  # Position type (buy/sell).
        magic=operation_class.account_data.magic_number,  # Robot/expert identifier.
        identifier=__generate_unique_ticket(),  # Unique position identifier.
        reason=ENUM_POSITION_REASON.POSITION_REASON_EXPERT,  # Reason for opening (expert advisor).
        volume=volume,  # Position volume in lots.
        price_open=price,  # Opening price of the position.
        price_current=price,  # Current price of the position (initially equal to the opening price).
        sl=stop_price,  # Stop-loss price.
        tp=profit_price,  # Take-profit price.
        swap=0,  # Swap (not applicable in backtest).
        profit=0,  # Profit (initially zero).
        symbol=symbol,  # Currency pair (currency pair).
        comment=comment,  # Optional comment.
        external_id=None,  # External ID (not used in backtest).
    )

    # Creation of a `MqlTradeDeal` corresponding to the new position.
    deal = __backtest_create_a_deal(
        operation_class=operation_class,  # Operation class associated.
        position=position,  # Position for which the deal will be created.
        symbol=symbol,  # Currency pair of the deal.
        order_type=order_type,  # Type of order associated with the deal (BUY/SELL).
        deal_time=position.time,  # Deal time.
        price=position.price_current,  # Execution price of the deal.
        volume=volume,  # Deal volume in lots.
        fee=fee,  # Additional fee applied to the deal.
        commission=commission,  # Commission applied to the deal.
        order=None,  # Order ID (None means that a new ID will be automatically generated).
        comment=comment,  # Optional comment about the deal.
    )

    # Adds the new position to the set of open positions.
    operation_class.account_data.positions.append(position)

    # Adds the deal to the history of deals.
    operation_class.account_data.history_deals.append(deal)


def __netting_create_position_and_deal(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    position_time: datetime,
    price: float,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> None:
    """
    Creates or updates a position in a backtest account with netting enabled.

    In netting accounts, only one aggregated position is maintained per symbol.
    Depending on the type of operation (buy/sell) and the volume, partial, total, or position reversal may occur.

    Args:
        operation_class (Operation): Operation class containing account data and auxiliary methods.
        symbol (str): Currency pair being traded (e.g., "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Type of market order (BUY/SELL).
        position_time (datetime): Position creation time.
        price (float): Execution price of the order.
        volume (float): Order volume in lots.
        stop_price (float, optional): Stop-loss price. Defaults to 0.
        profit_price (float, optional): Take-profit price. Defaults to 0.
        commission (float, optional): Commission applied to the deal. Defaults to 0.
        fee (float, optional): Additional fee applied to the deal. Defaults to 0.
        comment (str, optional): Optional comment about the operation. Defaults to "".

    Returns:
        None: The function does not return anything, but updates the position and deal history.
    """
    # Converts the type of market order (BUY/SELL) to the corresponding position type.
    position_type = __convert_order_to_position_type(order_type)

    # Creation of the `MqlPositionInfo` object representing the opened position.
    position = MqlPositionInfo(
        ticket=__generate_unique_ticket(),  # Unique ticket generated with timestamp.
        time=position_time,  # Position opening time.
        time_msc=position_time,  # Time with millisecond precision.
        time_update=position_time,  # Last update time (initially equal to the opening time).
        time_update_msc=position_time,  # Time with millisecond precision.
        type=position_type,  # Position type (buy/sell).
        magic=operation_class.account_data.magic_number,  # Robo/expert identifier.
        identifier=__generate_unique_ticket(),  # Unique position identifier.
        reason=ENUM_POSITION_REASON.POSITION_REASON_EXPERT,  # Reason for opening (expert advisor).
        volume=volume,  # Position volume in lots.
        price_open=price,  # Opening price of the position.
        price_current=price,  # Current price of the position (initially equal to the opening price).
        sl=stop_price,  # Stop-loss price.
        tp=profit_price,  # Take-profit price.
        swap=0,  # Swap (not applicable in backtest).
        profit=0,  # Profit (initially zero).
        symbol=symbol,  # Symbol (currency pair).
        comment=comment,  # Optional comment.
        external_id=None,  # External ID (not used in backtest).
    )

    # Verify if there is an open position for the symbol.
    if operation_class.account_data.positions:
        opened_position = operation_class.account_data.positions[0]

        # The updated position receives the identifier and information from the opened position.
        position.time = opened_position.time
        position.time_msc = opened_position.time_msc
        position.identifier = opened_position.identifier
        position.volume = opened_position.volume
        position.type = opened_position.type

        # Case the opened position is in the opposite direction to the current order.
        if opened_position.type != position_type:
            # Total closing: the volumes are equal.
            if opened_position.volume == volume:
                deal = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Removes the closed position from the list of positions.
                del operation_class.account_data.positions[0]
                operation_class.account_data.history_deals.append(deal)

            # Partial closing: the open position volume is greater.
            elif opened_position.volume > volume:
                deal = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Updates the remaining volume of the position after partial closing.
                position.volume = round(position.volume - volume, 2)
                operation_class.account_data.positions[0] = position
                operation_class.account_data.history_deals.append(deal)

            # Reversion of position: volume of the new order is greater.
            elif opened_position.volume < volume:
                # Generates a new identifier for the reversed position.
                position.identifier = __generate_unique_ticket()

                # Creates a deal to close the open position.
                deal_close = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Calculates the new volume and updates the position type.
                position.volume = round(abs(position.volume - volume), 2)
                if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                    position.type = ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                else:
                    position.type = ENUM_POSITION_TYPE.POSITION_TYPE_BUY

                # Updates the opening price with the current price.
                position.price_open = position.price_current

                operation_class.account_data.positions[0] = position
                operation_class.account_data.history_deals.append(deal_close)

        # Case the new order is in the same direction as the open position.
        else:
            deal = __backtest_create_a_deal(
                deal_time=position.time,
                position=position,
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=position.price_current,
                operation_class=operation_class,
                fee=fee,
                commission=commission,
                order=None,
                comment=comment,
            )

            # Calculates the new total volume and weighted average price.
            total_volume = round(position.volume + volume, 2)
            mean_price = (
                (opened_position.price_open * opened_position.volume)
                + (position.price_open * volume)
            ) / total_volume

            # Updates the volume, opening price, and current price.
            position.volume = total_volume
            position.price_open = mean_price
            position.price_current = price

            # Replaces the existing position with the new aggregated position.
            operation_class.account_data.positions[0] = position
            operation_class.account_data.history_deals.append(deal)
    else:
        # Creates a new position if there is no open position.
        deal = __backtest_create_a_deal(
            operation_class=operation_class,
            position=position,
            symbol=symbol,
            order_type=order_type,
            deal_time=position.time,
            price=position.price_current,
            volume=volume,
            fee=fee,
            commission=commission,
            order=None,
            comment=comment,
        )
        operation_class.account_data.positions.append(position)
        operation_class.account_data.history_deals.append(deal)


def __backtest_position_open(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> bool:
    """
    Opens a position in a backtest account.

    This function simulates the opening of a market position in a backtest environment,
    using candlestick data and simulated spreads to replicate realistic conditions.

    Args:
        operation_class (Operation): Operation class with account data and backtest context.
        symbol (str): Currency pair or asset to trade (ex.: "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Market order type (ex.: BUY or SELL).
        volume (float): Position volume (lot size).
        stop_price (float, optional): Stop-loss price. Default: 0 (no stop-loss).
        profit_price (float, optional): Take-profit price. Default: 0 (no take-profit).
        commission (float, optional): Commission applied to the operation. Default: 0.
        fee (float, optional): Additional fee applied to the operation. Default: 0.
        comment (str, optional): Optional comment about the operation. Default: "".

    Returns:
        bool: True, indicating that the order was processed successfully in the simulation.

    Raises:
        ValueError: If the volume or margin data is invalid.
    """
    __validate_operation_handler_attributes_for_symbol(
        operation_class=operation_class, symbol=symbol
    )

    # Validates the position volume
    __validate_position_volume(operation_class, symbol, order_type, volume)

    # Retrieves the most recent candle to simulate the current market state.
    last_candle = operation_class.backtest_symbols_data.loc[symbol, "last_candle"]

    # Define the timestamp of the candle as the time of the position.
    position_time = last_candle.name

    # Retrieves the simulated spread and tick size for the currency pair.
    simulated_spread: int = operation_class.account_data.simulated_spread
    trade_tick_size: float = operation_class.backtest_symbols_data.loc[symbol].tick_size

    # Define the entry price based on the order type (buy or sell).
    if order_type == ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY:
        # Buy order: uses the closing price of the candle + spread (to simulate the ASK price).
        price = last_candle.close + (trade_tick_size * simulated_spread)
    else:
        # Sell order: uses the closing price of the candle directly (to simulate the BID price).
        price = last_candle.close

    # Validate SL/TP relative to execution price and direction
    mapped_order_type = (
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY
        if order_type == ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY
        else ENUM_ORDER_TYPE.ORDER_TYPE_SELL
    )
    __validate_sl_tp_prices(
        price=price,
        sl=stop_price,
        tp=profit_price,
        order_type=mapped_order_type,
    )

    # Calculates the margin required (to open the position)
    contract_size = operation_class.backtest_symbols_data.loc[symbol, "contract_size"]
    leverage = operation_class.account_data.leverage
    margin_required = (volume * contract_size * price) / leverage

    # Verifies the available margin
    if operation_class.account_data.margin_free < margin_required:
        raise InsufficientMarginError(
            f"Insufficient margin to open position of {volume} lot(s) in '{symbol}'. "
            f"Required margin: {margin_required:.2f}, Free margin: {operation_class.account_data.margin_free:.2f}"
        )

    # Verifies the account type and applies the corresponding logic:
    # - Hedge: allows multiple positions in the same direction or opposite directions.
    # - Netting: allows only one aggregated position per symbol.
    if (
        operation_class.account_data.margin_mode
        == ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    ):
        # Creates a new position and deal for hedge accounts.
        __hedge_create_position_and_deal(
            operation_class=operation_class,
            symbol=symbol,
            order_type=order_type,
            position_time=position_time,
            price=price,
            stop_price=stop_price,
            profit_price=profit_price,
            volume=volume,
            commission=commission,
            fee=fee,
            comment=comment,
        )
    else:
        # Creates or updates the aggregated position for netting accounts.
        __netting_create_position_and_deal(
            operation_class=operation_class,
            symbol=symbol,
            order_type=order_type,
            position_time=position_time,
            price=price,
            stop_price=stop_price,
            profit_price=profit_price,
            volume=volume,
            commission=commission,
            fee=fee,
            comment=comment,
        )

    # Update data after execution
    __process_account_update_data(operation_class=operation_class)

    # Returns True to indicate that the operation was successfully executed in the simulation.
    return True

# Open Pending Order ------------------------------------------------------------------------------
def __backtest_pending_order_open(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_PENDING,
    volume: float,
    price: float,
    stop_limit: float = 0,
    stop_price: float = 0,
    profit_price: float = 0,
    expiration: datetime = None,
    comment: str = "",
):
    """
    Opens a pending order in a backtest account with volume and price validation.
    """
    __validate_operation_handler_attributes_for_symbol(
        operation_class=operation_class, symbol=symbol
    )

    # Validate the order volume
    __validate_order_volume(
        operation_class=operation_class, symbol=symbol, order_type=order_type, volume=volume
    )

    # Retrieve the most recent candle to simulate the current market state.
    last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle

    # Define the timestamp of the candle as the time of the position.
    position_time = last_candle.name
    order_time = position_time
    current_time_ms = get_timestamp_ms(order_time)

    type_time = (
        ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
        if expiration
        else ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC
    )

    __validate_order_price(
        operation_class=operation_class,
        symbol=symbol,
        price=price,
        order_type=order_type,
        stop_limit=stop_limit,
    )

    # Validate SL/TP for pending orders (relative to pending price and direction)
    __validate_sl_tp_prices(
        price=price,
        sl=stop_price,
        tp=profit_price,
        order_type=order_type,
    )

    order = MqlTradeOrder(
        ticket=current_time_ms,
        symbol=symbol,
        type=order_type,
        time_setup=order_time.replace(microsecond=0),
        time_setup_msc=order_time,
        volume_initial=volume,
        volume_current=volume,
        price_stoplimit=stop_limit,
        price_open=price,
        price_current=price,
        tp=profit_price,
        sl=stop_price,
        type_time=type_time,
        time_expiration=expiration,
        state=ENUM_ORDER_STATE.ORDER_STATE_PLACED,
        reason=ENUM_ORDER_REASON.ORDER_REASON_EXPERT,
        magic=operation_class.account_data.magic_number,
        type_filling=operation_class.account_data.type_filling,
        comment=comment,
    )

    operation_class.account_data.orders.append(order)


def __backtest_pending_order_modify(
    operation_class: "Operation",
    ticket: int,
    price: float,
    stop_price: float = 0,
    profit_price: float = 0,
    expiration: datetime = None,
    comment: str = "",
):
    # Select the order
    order: MqlTradeOrder = get_order(
        list_orders=operation_class.account_data.orders, ticket=ticket
    )

    if expiration:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    else:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC

        # Check if stop or take profit is defined
    
    if stop_price or profit_price:
        # Validate SL/TP
        __validate_sl_tp_prices(price=price, sl=stop_price, tp=profit_price, order_type=order.type)

    __validate_order_price(
        operation_class=operation_class,
        symbol=order.symbol,
        price=price,
        order_type=order.type,
        stop_limit=order.price_stoplimit,
    )

    # Change the order attributes
    order.update(
        price_open=price,
        sl=stop_price,
        tp=profit_price,
        comment=comment,
        type_filling=operation_class.account_data.type_filling,
        magic=operation_class.account_data.magic_number,
        time_expiration=expiration,
        type_time=type_time,
    )


def __backtest_position_modify(
    operation_class: "Operation",
    stop_price: float = 0,
    profit_price: float = 0,
    position: int = None,
    comment: str = "",
):
    position_not_found_error = CouldNotSelectPosition("Could not select the position.")

    # If position not received, try to get it
    if position is None:
        # If there is only one position opened, get it
        if len(operation_class.account_data.positions) == 1:
            position = operation_class.account_data.positions[0].ticket
        else:
            raise position_not_found_error

    # Get the position from account positions
    position_selected: List[MqlPositionInfo] = [
        mqlposition
        for mqlposition in operation_class.account_data.positions
        if mqlposition.ticket == position
    ]

    # Check if the position exists
    if len(position_selected) != 1:
        raise position_not_found_error

    # Select the position object
    position_selected: MqlPositionInfo = position_selected[0]
    
    # Check if stop or take profit is defined
    if stop_price or profit_price:
        price = position_selected.price_current
        order_type = (
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY
            if position_selected.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
            else ENUM_ORDER_TYPE.ORDER_TYPE_SELL
        )
        # Validate SL/TP
        __validate_sl_tp_prices(price=price, sl=stop_price, tp=profit_price, order_type=order_type)

    position_selected.update(
        sl=stop_price,
        tp=profit_price,
        comment=comment,
    )

    # Update data after execution
    __process_account_update_data(operation_class=operation_class)


def __backtest_position_close(
    operation_class: "Operation",  # Operation class containing account data and auxiliary methods.
    position_ticket: int,  # Ticket of the position to be closed.
    commission: float = 0,  # Commission applied to the closing of the position.
    fee: float = 0,  # Additional fee applied to the operation.
    comment: str = "",  # Optional comment about the position closing.
    deal_reason: ENUM_DEAL_REASON | None = None,
):
    """
    Closes a position in backtest mode.

    Args:
        operation_class (Operation): Operation class containing account data and auxiliary methods.
        position_ticket (int): ID of the position to be closed.
        commission (float, optional): Commission charged for the closing operation. Default: 0.
        fee (float, optional): Additional fee applied to the operation. Default: 0.
        comment (str, optional): Optional comment about the position closing.

    Raises:
        CouldNotSelectPosition: Exception raised if the position with the specified `ticket` is not found.
    """

    # **1. Position Selection**
    position_selected: List[MqlPositionInfo] = [
        position
        for position in operation_class.account_data.positions
        if position.ticket == position_ticket
    ]

    # **2. Verification of the Position's Existence**
    if len(position_selected) != 1:
        raise CouldNotSelectPosition("[ERROR]: Could not select the position.")

    # **3. Retrieve the Position and Required Attributes**
    position_selected = position_selected[0]
    symbol = position_selected.symbol
    last_candle = operation_class.backtest_symbols_data.loc[
        symbol
    ].last_candle  # Last available candle
    deal_time = last_candle.name  # Define the timestamp of the candle as the deal time

    # **4. Determine execution price and inverse order type**
    if position_selected.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        price = last_candle.close  # Closing price for sell orders
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_SELL  # Sell order
    else:
        price = last_candle.close + (
            operation_class.backtest_symbols_data.loc[symbol].tick_size
            * operation_class.account_data.simulated_spread
        )
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY  # Buy order

    # **5. Create and Register the Deal**
    deal = __backtest_create_a_deal(
        deal_time=deal_time,
        position=position_selected,
        symbol=symbol,
        order_type=order_type,
        volume=position_selected.volume,
        price=price,
        fee=fee,
        commission=commission,
        order=None,
        comment=comment,
        reason=deal_reason or ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
        operation_class=operation_class,
    )
    operation_class.account_data.history_deals.append(deal)

    # **6. Update balance and equity based on deal profit**
    __backtest_account_update_equity(operation_class=operation_class)

    # **7. Remove the Position from the List**
    operation_class.account_data.positions.remove(position_selected)

    # **8. Log the Closure**
    logging.info(
        f"[CLOSE POSITION] Position {position_selected.ticket} closed in {symbol} | Profit: {deal.profit:.2f} | "
        f"Current Balance: {operation_class.account_data.balance:.2f} | Equity: {operation_class.account_data.equity:.2f}"
    )

    # **9. Update data after execution**
    __process_account_update_data(operation_class=operation_class)


# Pending Orders Management -----------------------------------------------------------------------
def __backtest_pending_order_check_triggered(operation_class: "Operation") -> None:
    """
    Checks if any pending order was triggered based on the `high` and `low` price of the last candle.
    For `STOP_LIMIT` orders, checks the activation of the initial price and, if necessary,
    creates a `LIMIT` order. For `LIMIT` and `STOP` orders, opens positions directly.

    Args:
        operation_class (Operation): Operation class with account and pending orders information.

    Returns:
        None: The function does not return anything, but opens positions or creates `LIMIT` orders as needed.
    """
    # **Iteration over all pending orders**
    spread_points = operation_class.account_data.simulated_spread
    for order in operation_class.account_data.orders[:]:  # Copy of the list to avoid errors when modifying
        symbol = order.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle
        order_triggered = False  # Variable to control if the order was triggered
        spread = spread_points * operation_class.backtest_symbols_data.loc[symbol].tick_size

        # **Verification of prices by order type**
        if order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT:
            # `BUY_LIMIT`: Market price (`low`) should be less than or equal to the order price
            if last_candle.low + spread <= order.price_open:
                logging.info(
                    f"[INFO] Order `BUY_LIMIT` {order.ticket} reached in {symbol} at {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT:
            # `SELL_LIMIT`: Market price (`high`) should be greater than or equal to the order price
            if last_candle.high >= order.price_open:
                logging.info(
                    f"[INFO] Order `SELL_LIMIT` {order.ticket} reached in {symbol} at {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP:
            # `BUY_STOP`: Market price (`high`) should be greater than or equal to the order price
            if last_candle.high + spread >= order.price_open:
                logging.info(
                    f"[INFO] Order `BUY_STOP` {order.ticket} reached in {symbol} at {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP:
            # `SELL_STOP`: Market price (`low`) should be less than or equal to the order price
            if last_candle.low <= order.price_open:
                logging.info(
                    f"[INFO] Order `SELL_STOP` {order.ticket} reached in {symbol} at {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT:
            # `BUY_STOP_LIMIT`: Market price (`high`) should be greater than or equal to the initial price
            if last_candle.high + spread >= order.price_open:
                logging.info(
                    f"[INFO] Order `BUY_STOP_LIMIT` {order.ticket} reached in {symbol}."
                )
                # Create a pending `LIMIT` order
                __backtest_pending_order_open(
                    operation_class=operation_class,
                    expiration=order.time_expiration,
                    order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
                    price=order.price_stoplimit,
                    symbol=symbol,
                    volume=order.volume_initial,
                    profit_price=order.tp,
                    stop_price=order.sl,
                    stop_limit=0,
                    comment=f"Created LIMIT order from STOP_LIMIT #{order.ticket}",
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT:
            # `SELL_STOP_LIMIT`: Market price (`low`) should be less than or equal to the initial price
            if last_candle.low <= order.price_open:
                logging.info(
                    f"[INFO] Order `SELL_STOP_LIMIT` {order.ticket} reached in {symbol}."
                )
                # Create a pending `LIMIT` order
                __backtest_pending_order_open(
                    operation_class=operation_class,
                    expiration=order.time_expiration,
                    order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
                    price=order.price_stoplimit,
                    symbol=symbol,
                    volume=order.volume_initial,
                    profit_price=order.tp,
                    stop_price=order.sl,
                    stop_limit=0,
                    comment=f"Created LIMIT order from STOP_LIMIT {order.ticket}",
                )
                order_triggered = True

        else:
            logging.warning(f"[WARNING] Order type {order.type} not recognized.")
            continue  # Ignore unknown order types
            
        # **Open position only if the order was triggered**
        if order_triggered:
            original_close = (
                last_candle.close
            )  # Save the original close value of the candle

            # Temporarily adjust the close to the order price
            try:
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ] = last_candle.copy()
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ]["close"] = order.price_open

                if order.type not in (ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT, ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT):
                    # **Open position with order price**
                    try:
                        # **Open position with order price**
                        __backtest_position_open(
                            operation_class=operation_class,
                            symbol=symbol,
                            order_type=order.type,
                            volume=order.volume_current,
                            stop_price=order.sl,
                            profit_price=order.tp,
                            commission=0,
                            fee=0,
                            comment=f"Activated pending order {order.ticket}",
                        )
                    except Exception as e:
                        # Log the error and continue execution
                        logging.error(
                            f"Error opening position for order {order.ticket} in symbol {symbol} (The order will not be activated, but will be removed): {str(e)}"
                        )

                # Remove the order after activation
                operation_class.account_data.orders.remove(order)
                logging.info(f"[INFO] Order {order.ticket} removed after activation.")

            finally:
                # **Restores the original close value of the candle**   
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ]["close"] = original_close
         

def __backtest_pending_order_check_expiration(operation_class: "Operation") -> None:
    """
    Verify if any pending order expired based on the current date/time and remove expired orders.

    Args:
        operation_class (Operation): Operation class containing account and pending orders data.

    Returns:
        None: The function does not return anything, but removes expired orders from the `orders` attribute of `account_data`.
    """
    # Validate attributes for each symbol present in pending orders
    symbols = set([order.symbol for order in operation_class.account_data.orders])
    for symbol in symbols:
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

    # Filter expired orders
    expired_orders = []
    for order in operation_class.account_data.orders:
        last_candle_time = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle.name

        if order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED:
            # `ORDER_TIME_SPECIFIED`: Order expires at the exact specified time
            if (
                order.time_expiration is not None
                and order.time_expiration <= last_candle_time
            ):
                expired_orders.append(order)

        elif order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY:
            # `ORDER_TIME_SPECIFIED_DAY`: Expires at 23:59:59 of the specified day
            if order.time_expiration is not None:
                expiration_day_end = datetime.combine(
                    order.time_expiration.date(), time(23, 59, 59), tzinfo=timezone.utc
                )
                if expiration_day_end <= last_candle_time:
                    expired_orders.append(order)

    # Remove the expired orders
    for expired_order in expired_orders:
        operation_class.account_data.orders.remove(expired_order)
        logging.info(
            f"Order {expired_order.ticket} for {expired_order.symbol} was removed due to expiration."
        )


# Positions Management ----------------------------------------------------------------------------
def __backtest_position_check_stop_loss_reached(operation_class: "Operation") -> None:
    """
    Verify if the stop loss was reached for open positions based on the `high` and `low` of the last candle.
    If the stop loss is reached, the position is automatically closed at the stop loss price.

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but closes positions that reached the stop loss.
    """
    for position in operation_class.account_data.positions[
        :
    ]:  # Copy of the list to avoid errors
        symbol = position.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle  # Last available candle
        logging.info(f"Last candle for {symbol}: {last_candle}")

        if position.sl > 0:  # Verify if there is a stop loss configured
            stop_loss_reached = (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
                and last_candle.low <= position.sl
            ) or (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                and last_candle.high >= position.sl
            )

            if stop_loss_reached:
                logging.warning(
                    f"[STOP LOSS] Position {position.ticket} in {symbol} reached stop loss at {position.sl}"
                )

                # Store the original `close` of the candle
                original_close = last_candle.close


                try:
                    # Adjust temporarily the stored last_candle to the stop loss price
                    lc_copy = last_candle.copy()
                    lc_copy["close"] = position.sl
                    lc_copy.name = last_candle.name  # ensure timestamp is preserved
                    operation_class.backtest_symbols_data.at[symbol, "last_candle"] = lc_copy

                    # Close the position using the adjusted close so the deal gets the SL price
                    __backtest_position_close(
                        operation_class=operation_class,
                        position_ticket=position.ticket,
                        comment="Stop loss reached",
                        deal_reason=ENUM_DEAL_REASON.DEAL_REASON_SL,
                    )

                finally:
                    # Restore the original `close` of the candle
                    operation_class.backtest_symbols_data.at[symbol, "last_candle"]["close"] = original_close


def __backtest_position_check_take_profit_reached(operation_class: "Operation") -> None:
    """
    Verify if the take profit was reached for open positions based on the `high` and `low` of the last candle.
    If the take profit is reached, the position is automatically closed at the take profit price.

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but closes positions that reached the take profit.
    """
    for position in operation_class.account_data.positions[
        :
    ]:  # Copy of the list to avoid errors
        symbol = position.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle  # Last available candle

        if position.tp > 0:  # Verify if there is a take profit configured
            take_profit_reached = (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
                and last_candle.high >= position.tp
            ) or (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                and last_candle.low <= position.tp
            )

            if take_profit_reached:
                logging.info(
                    f"[TAKE PROFIT] Position {position.ticket} in {symbol} reached take profit at {position.tp}"
                )

                # Store the original `close` of the candle
                original_close = last_candle.close

                try:
                    # Adjust temporarily the stored last_candle to the take profit price
                    lc_copy = last_candle.copy()
                    lc_copy["close"] = position.tp
                    lc_copy.name = last_candle.name  # ensure timestamp is preserved
                    operation_class.backtest_symbols_data.at[symbol, "last_candle"] = lc_copy

                    # Close the position using the adjusted close so the deal gets the TP price
                    __backtest_position_close(
                        operation_class=operation_class,
                        position_ticket=position.ticket,
                        comment="Take profit reached",
                        deal_reason=ENUM_DEAL_REASON.DEAL_REASON_TP,
                    )

                finally:
                    # Restore the original `close` of the candle
                    operation_class.backtest_symbols_data.at[symbol, "last_candle"]["close"] = original_close


def __backtest_position_update_price_and_profit(operation_class: "Operation") -> None:
    """
    Updates the current price and profit/loss of open positions based on the last available price.

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but updates the price and profit/loss of open positions.
    """
    # Reset the total profit of the account before calculating the profit of the positions
    operation_class.account_data.profit = 0

    # Iteration over all open positions
    for position in operation_class.account_data.positions:
        symbol = position.symbol

        # Validate essential attributes for the symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        # Get the last candle for the symbol
        last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle

        # Uses the closing price (`close`) of the candle as the current price
        if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
            last_price = last_candle.close  # Closing price for sell orders
        else:
            last_price = last_candle.close + (
                operation_class.backtest_symbols_data.loc[symbol].tick_size
                * operation_class.account_data.simulated_spread
            )

        # Update current price of the position
        position.price_current = round(last_price, 5)

        # Calculate profit/loss based on the current price
        profit = __backtest_get_profit(
            operation_class=operation_class,
            symbol=symbol,
            price_open=position.price_open,  # Opening price of the position
            price_close=position.price_current,  # Current price
            price_volume=position.volume,  # Position volume
            position_type=position.type,  # Position type (buy/sell)
        )

        # Update profit/loss in the position
        position.profit = profit

        # Accumulate total profit/loss of the account
        operation_class.account_data.profit = round(
            operation_class.account_data.profit + profit + position.swap, 2
        )

        # Log update
        logging.info(
            f"[UPDATE] Position {position.ticket} ({'BUY' if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY else 'SELL'}) "
            f"in {symbol}: Current Price: {last_price:.5f} | Profit/Loss: {profit:.2f} {operation_class.account_data.currency}"
        )


# Account Management ------------------------------------------------------------------------------
def __backtest_account_update_equity(operation_class: "Operation") -> None:
    """
    Updates the equity of the account based on the current balance and the profit/loss of open positions.

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but updates the `equity` attribute of the account.
    """
    account_data = operation_class.account_data

    # Update equity
    account_data.equity = round(account_data.balance + account_data.profit, 2)

    # Log equity update
    message = (
        f"[EQUITY UPDATE] Balance: {account_data.balance:.2f}, "
        f"Profit/Loss Open: {account_data.profit:.2f}, "
        f"Equity: {account_data.equity:.2f}"
    )
    if getattr(account_data, "_last_equity_log", None) != message:
        logging.info(message)
        setattr(account_data, "_last_equity_log", message)


def __backtest_account_update_margin(operation_class: "Operation") -> None:
    """
    Updates the margin values of the account based on the margin calculation mode.

    This function calculates only dynamic values that change with open positions:
    - `margin`: Total margin used by open positions.
    - `margin_free`: Free margin of the account (`equity - margin`).
    - `margin_level`: Margin level (percentage between `equity` and `margin`).

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but updates the margin attributes in the `account_data`.
    """
    account_data = operation_class.account_data

    # Update equity before calculating margin
    __backtest_account_update_equity(operation_class)

    # Initialize total margin used
    total_margin_used = 0.0

    # Iteration over all open positions to calculate used margin
    for position in account_data.positions:
        symbol = position.symbol
        trade_calc_mode = operation_class.backtest_symbols_data.loc[
            symbol
        ].trade_calc_mode
        position_open_price = position.price_open

        # Get symbol information
        contract_size = operation_class.backtest_symbols_data.loc[symbol].contract_size
        leverage = account_data.leverage

        # Margin calculation based on symbol calculation mode
        if trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_CFDLEVERAGE,
        ]:
            margin = (position.volume * contract_size * position_open_price) / leverage

        elif (
            trade_calc_mode == ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE
        ):
            margin = position.volume * contract_size * position_open_price

        elif trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FUTURES,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_FUTURES,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
        ]:
            margin = position.volume * operation_class.initial_margin.get(symbol, 0)

        elif trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_STOCKS,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_CFD,
        ]:
            margin = position.volume * contract_size * position_open_price

        elif trade_calc_mode == ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            margin = 0  # Non-tradable assets do not consume margin

        else:
            logging.warning(f"Unknown calculation mode for symbol: {symbol}")
            margin = 0

        # Add the calculated margin to the total used margin
        total_margin_used += margin

    # Update margin attributes in the account
    account_data.margin = round(total_margin_used, 2)  # Total used margin
    account_data.margin_free = round(
        account_data.equity - total_margin_used, 2
    )  # Free margin

    # Margin level
    if total_margin_used > 0:
        account_data.margin_level = round(
            (account_data.equity / total_margin_used) * 100, 3
        )
    else:
        account_data.margin_level = float(
            "inf"
        )  # When there's no margin used, the margin level is infinite

    # Margin information logs
    margin_message = (
        f"[UPDATED MARGIN] Used Margin: {account_data.margin:.2f}, Free Margin: {account_data.margin_free:.2f}, "
        f"Margin Level: {account_data.margin_level:.2f}%"
    )
    if getattr(account_data, "_last_margin_log", None) != margin_message:
        logging.info(margin_message)
        setattr(account_data, "_last_margin_log", margin_message)


def __backtest_account_check_margin_call(operation_class: "Operation") -> None:
    """
    Verify if the margin level of the account reached the defined limit (`margin_so_call`) and,
    if necessary, emits a margin call alert.

    Args:
        operation_class (Operation): Class of operation containing account data.

    Returns:
        None: The function does not return anything, but may emit warning logs if the margin level is critical.
    """
    account_data = operation_class.account_data

    # Verify margin calculation mode
    if (
        account_data.margin_so_mode
        == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    ):
        # Margin level based on percentage
        if account_data.margin_level <= account_data.margin_so_call:
            logging.warning(
                f"[MARGIN CALL] Margin level below the limit ({account_data.margin_level:.2f}%). "
                f"Minimum margin allowed: {account_data.margin_so_call}%."
            )

    elif (
        account_data.margin_so_mode
        == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_MONEY
    ):
        # Margin level based on monetary value
        if account_data.margin_free <= account_data.margin_so_call:
            logging.warning(
                f"[MARGIN CALL] Free margin below the limit ({account_data.margin_free:.2f} {account_data.currency}). "
                f"Minimum margin allowed: {account_data.margin_so_call} {account_data.currency}."
            )


def __backtest_account_process_stop_out(operation_class: "Operation") -> None:
    """
    Process the stop out event, closing open positions if the margin level falls below the limit
    established by the broker. Positions are closed in the order defined by the `fifo_close` parameter:
    - If `True`: positions are closed in FIFO order.
    - If `False`: positions are closed by the largest loss not realized.

    At the end, the account margin is updated.

    Args:
        operation_class (Operation): Operation class containing account and position data.

    Returns:
        None: The function does not return anything, but closes positions and updates account data.
    """
    account_data = operation_class.account_data

    # Verify if the margin level is below the stop out level.
    if account_data.margin_level > 0:
        if (
            account_data.margin_so_mode
            == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
        ):
            stop_out_triggered = account_data.margin_level <= account_data.margin_so_so
        else:
            stop_out_triggered = account_data.equity <= account_data.margin_so_so
    else:
        # If the margin level is 0 or negative, trigger stop out directly
        stop_out_triggered = True

    # **If stop out was not triggered, return without actions**
    if not stop_out_triggered:
        return

    logging.warning(
        "[STOP OUT] Margin level reached! Starting position closing..."
    )

    # **Position sorting**
    if account_data.fifo_close:
        # FIFO sorting: Closes positions in the order of opening (oldest first)
        positions_to_close = sorted(
            account_data.positions, key=lambda pos: pos.time_msc
        )
    else:
        # Close positions with the highest loss first
        positions_to_close = sorted(account_data.positions, key=lambda pos: pos.profit)

    # **Close positions until margin is restored**
    for position in positions_to_close:
        __backtest_position_close(
            operation_class=operation_class,
            position_ticket=position.ticket,
            comment="Stop out triggered",
            deal_reason=ENUM_DEAL_REASON.DEAL_REASON_SO,
        )

        # Update margin data after each closing
        __backtest_position_update_price_and_profit(operation_class=operation_class)
        __backtest_account_update_margin(operation_class=operation_class)

        # Verify if the margin level has returned to above the limit after closing positions
        if account_data.margin_level > account_data.margin_so_so:
            logging.info(
                "[STOP OUT] Margin level restored after position closing."
            )
            break

    # **Final log after stop out process**
    logging.info(
        f"[STOP OUT FINISHED] Balance: {account_data.balance:.2f} | Equity: {account_data.equity:.2f} | "
        f"Margin Level: {account_data.margin_level:.2f}%"
    )


# Swap Management ---------------------------------------------------------------------------------
def __backtest_position_apply_swap_to_positions(operation_class: "Operation") -> None:
    """
    Applies swaps to open positions based on `last_candle` and the `backtest_last_swap_date` history.
    Verifies if passed the closing time of NY (22:00 UTC) and applies cumulative swaps correctly.

    Args:
        operation_class (Operation): Class containing open positions information and account parameters.
    """
    last_swap_date = operation_class.account_data.backtest_last_swap_date
    # Some symbols may not have a last_candle yet (None). Filter them out.
    _last_candles_col = operation_class.backtest_symbols_data["last_candle"]
    _available_candles = [c for c in _last_candles_col if c is not None]
    # If no candles are available yet, there is nothing to apply
    if not _available_candles:
        return
    last_candle_time = max(c.name for c in _available_candles)

    # **Special case: first swap application**
    if last_swap_date is None:
        if not operation_class.account_data.positions:
            # No open positions, so only update the last swap date
            operation_class.account_data.backtest_last_swap_date = last_candle_time
        else:
            # Update the last swap date to the time of the oldest position
            oldest_position_time = min(
                position.time for position in operation_class.account_data.positions
            )
            operation_class.account_data.backtest_last_swap_date = oldest_position_time
        return

    # **Calculate the difference in days between the last swap and the last candle**
    days_diff = (last_candle_time.date() - last_swap_date.date()).days

    # **Avoid reprocessing if the last swap was already applied after 22h of the same day**
    last_close_time = last_swap_date.replace(hour=22, minute=0, second=0, microsecond=0)
    if (
        last_swap_date >= last_close_time
        and last_swap_date.date() == last_candle_time.date()
    ):
        return

    # **Iterate over the pending days to apply swaps**
    for i in range(days_diff + 1):
        current_date = last_swap_date + timedelta(days=i)  # Current date in the loop
        close_time_current = current_date.replace(
            hour=22, minute=0, second=0, microsecond=0
        )  # Closing time

        # **If the last swap was applied after 22h, ignore this day**
        if (
            last_swap_date.date() == current_date.date()
            and close_time_current < last_swap_date
        ):
            continue

        # **If the last swap was applied after 22h, ignore this day**
        if (
            current_date.date() == last_candle_time.date()
            and last_candle_time < close_time_current
        ):
            continue

        # **Ignore Saturday and Sunday (market closed)**
        weekday = (current_date.weekday() + 1) % 7  # Adjusts Sunday to be 0
        if weekday in (0, 6):
            continue

        # **Avoid reaplying swap on the same day after 22h**
        if (
            last_swap_date >= close_time_current
            and current_date == last_swap_date.date()
        ):
            continue

        # **Apply swap to open positions**
        for position in operation_class.account_data.positions:
            # **Ignore positions opened after the current date**
            if position.time > close_time_current:
                continue

            symbol = position.symbol
            rollover_day = operation_class.backtest_symbols_data.loc[
                symbol, "swap_rollover3days"
            ]  # Default rollover day for triple is Wednesday

            # **Calculate swap multiplier (triple on Wednesday, normal on other days)**
            swap_multiplier = 3 if weekday == rollover_day else 1
            swap_value = __backtest_position_calculate_swap(
                operation_class, position, swap_multiplier
            )
            position.swap += swap_value

            # **Log informative with swap details applied**
            logging.info(
                f"[SWAP] {position.symbol} | Date: {current_date.strftime('%Y-%m-%d')} | "
                f"Swap applied: {swap_value:.2f} | Multiplier: {swap_multiplier}x | Swap Total: {position.swap:.2f} | "
                f"Position Time: {position.time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    # **Update the last swap date to the time of the last candle**
    operation_class.account_data.backtest_last_swap_date = last_candle_time


def __backtest_position_calculate_swap(
    operation_class: "Operation", position: "MqlPositionInfo", multiplier: int
) -> float:
    """
    Calculates the swap value for a position based on the swap type and multiplier.

    Args:
        operation_class (Operation): Class containing account and market information.
        position (MqlPositionInfo): Open position for which the swap will be calculated.
        multiplier (int): Swap multiplier (1 for normal days, 3 for Wednesday in Forex).

    Returns:
        float: Calculated swap value.
    """
    symbol = position.symbol
    swap_mode = operation_class.backtest_symbols_data.loc[symbol].swap_mode
    trade_contract_size = operation_class.backtest_symbols_data.loc[
        symbol
    ].contract_size
    volume = position.volume
    last_price = operation_class.backtest_symbols_data.loc[symbol].last_candle.close

    if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        swap_rate = operation_class.backtest_symbols_data.loc[symbol].swap_long
    else:
        swap_rate = operation_class.backtest_symbols_data.loc[symbol].swap_short

    # **Calculate swap based on mode**
    if swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS:
        swap_value = swap_rate * multiplier * volume
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_SYMBOL:
        swap_value = swap_rate * multiplier * volume * trade_contract_size * last_price
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_MARGIN:
        swap_value = swap_rate * multiplier * volume
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT:
        swap_value = swap_rate * multiplier * volume * trade_contract_size
    else:
        swap_value = 0  # No swap for disabled or unsupported modes

    return round(swap_value, 2)


# New Candle --------------------------------------------------------------------------------------
def __process_account_update_data(operation_class: "Operation"):
    """
    Updates operation data after generating a new candle.

    Objectives:
    - Apply swaps to open positions.
    - Update the current price and profit/loss of positions.
    - Update account margin data (used margin, free margin, and margin level).
    - Check if a `margin call` alert needs to be issued.
    - Check if a `stop out` needs to be processed and positions need to be closed.

    Args:
        operation_class (Operation): Operation class containing account and position data.
    """
    # **Apply swaps**
    __backtest_position_apply_swap_to_positions(operation_class=operation_class)

    # **Update price and profit/loss**
    __backtest_position_update_price_and_profit(operation_class=operation_class)

    # **Update margin data**
    __backtest_account_update_margin(operation_class=operation_class)

    # **Check `margin call`**
    __backtest_account_check_margin_call(operation_class=operation_class)

    # **Process `stop out` if necessary**
    __backtest_account_process_stop_out(operation_class=operation_class)


def __process_account_after_candle_event(operation_class: "Operation"):
    """
    Process events related to pending orders and positions after generating a new candle.

    Objectives:
    - Verify if pending orders were triggered by the current price.
    - Verify if pending orders expired due to time.
    - Verify if open positions reached the `stop loss` and need to be closed.
    - Verify if open positions reached the `take profit` and need to be closed.

    Args:
        operation_class (Operation): Operation class containing account and position data.
    """
    # **Verification of pending order activation**
    __backtest_pending_order_check_triggered(operation_class=operation_class)

    # **Verification of pending orders expired**
    __backtest_pending_order_check_expiration(operation_class=operation_class)

    # **Verification of positions that reached the `stop loss`**
    __backtest_position_check_stop_loss_reached(operation_class=operation_class)

    # **Verification of positions that reached the `take profit`**
    __backtest_position_check_take_profit_reached(operation_class=operation_class)


def __process_account_new_candle_event(operation_class: "Operation"):
    """
    Process events related to generating a new candle.

    Objectives:
    - Execute verifications after the candle close to update orders and positions.
    - Update open positions and account data, such as margin, profit, and risk alerts.

    Args:
        operation_class (Operation): Operation class containing account and position data.
    """
    # Log snapshot of last candles per symbol
    try:
        last_candles_series = operation_class.backtest_symbols_data["last_candle"]
        candles_log = {}
        for symbol, candle in last_candles_series.items():
            if candle is None:
                candles_log[symbol] = None
                continue
            candles_log[symbol] = {
                "time": str(getattr(candle, "name", None)),
                "o": float(candle.get("open")) if "open" in candle else None,
                "h": float(candle.get("high")) if "high" in candle else None,
                "l": float(candle.get("low")) if "low" in candle else None,
                "c": float(candle.get("close")) if "close" in candle else None,
            }
        logging.debug(f"[NEW CANDLE] last_candles snapshot: {candles_log}")
    except Exception as e:
        logging.debug(f"[NEW CANDLE] Unable to log last_candles: {e}")

    # **Process events after candle close to update orders and positions**
    __process_account_after_candle_event(operation_class=operation_class)

    # **Update data after a new candle**
    __process_account_update_data(operation_class=operation_class)


# Decorators --------------------------------------------------------------------------------------
def decorator_backtest_position_open(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_open(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_pending_order_open(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_pending_order_open(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_position_modify(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_modify(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_pending_order_modify(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_pending_order_modify(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_position_close(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_close(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_update_candles(func: Callable):
    def execute_process_account_new_candle_event(*args, **kwargs):
        func_return = func(*args, **kwargs)
        __process_account_new_candle_event(operation_class=args[0])
        return func_return

    return execute_process_account_new_candle_event
