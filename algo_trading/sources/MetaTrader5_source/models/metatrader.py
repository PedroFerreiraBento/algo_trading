# Importações de bibliotecas padrão
from datetime import datetime, timezone, timedelta  # Manipulação de datas e fusos horários
import sys # Para checar o que já foi importado

# Importações de terceiros
import MetaTrader5 as mt5  # Biblioteca MetaTrader5 para integração com a plataforma
import numpy as np  # Operações numéricas e manipulação de arrays
import pandas as pd  # Manipulação e análise de dados em formato tabular
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field  # Validação e modelagem de dados com Pydantic

# Tipagem estática
from typing import Optional, List, TYPE_CHECKING, Type  # Tipos e suporte para forward references

# Enumeradores
from enum import IntEnum, auto  # Criação de enumeradores para constantes

# Importações locais (módulo interno)
from algo_trading.sources.MetaTrader5_source.utils.metatrader import validate_mt5_ulong_size  # Validador para dados do MetaTrader5
from algo_trading.sources.MetaTrader5_source.utils.exceptions import NotExpectedParseType  # Exceção personalizada para parsing
from algo_trading.sources.MetaTrader5_source.utils.dates import get_timestamp_ms  # Função utilitária para timestamps


    
if TYPE_CHECKING:
    from algo_trading.sources.MetaTrader5_source.rates.rates import Rates


class ENUM_COPY_TICKS(IntEnum):
    """Tick Copy Types

    COPY_TICKS defines the types of ticks that can be requested using the functions copy_ticks_from() and copy_ticks_range().

    Args:
        COPY_TICKS_ALL (int): All ticks.
        COPY_TICKS_INFO (int): Ticks containing changes in Bid and/or Ask prices.
        COPY_TICKS_TRADE (int): Ticks containing changes in Last price and/or Volume.
    """
    COPY_TICKS_ALL: int = mt5.COPY_TICKS_ALL
    COPY_TICKS_INFO: int = mt5.COPY_TICKS_INFO
    COPY_TICKS_TRADE: int = mt5.COPY_TICKS_TRADE

class ENUM_TICK_FLAGS(IntEnum):
    """Tick Flags

    TICK_FLAG defines possible flags for ticks. These flags are used to describe the ticks received by the functions copy_ticks_from() and copy_ticks_range().

    Args:
        TICK_FLAG_BID (int): Indicates a change in the Bid price.
        TICK_FLAG_ASK (int): Indicates a change in the Ask price.
        TICK_FLAG_LAST (int): Indicates a change in the Last price.
        TICK_FLAG_VOLUME (int): Indicates a change in Volume.
        TICK_FLAG_BUY (int): Indicates a change in the last Buy price.
        TICK_FLAG_SELL (int): Indicates a change in the last Sell price.
    """
    TICK_FLAG_BID: int = mt5.TICK_FLAG_BID
    TICK_FLAG_ASK: int = mt5.TICK_FLAG_ASK
    TICK_FLAG_LAST: int = mt5.TICK_FLAG_LAST
    TICK_FLAG_VOLUME: int = mt5.TICK_FLAG_VOLUME
    TICK_FLAG_BUY: int = mt5.TICK_FLAG_BUY
    TICK_FLAG_SELL: int = mt5.TICK_FLAG_SELL



class ENUM_TRADE_REQUEST_ACTIONS(IntEnum):
    """Trade actions

    Trading is done by sending orders to open positions using the OrderSend() function, as well as to place, modify or delete pending orders. Each trade order refers to the type of the requested operation.
        Trading operations are described in the ENUM_TRADE_REQUEST_ACTIONS enumeration.

    Args:
        TRADE_ACTION_DEAL (int): Place a trade order for an immediate execution with the specified parameters (market order).
        TRADE_ACTION_PENDING (int): Place a trade order for the execution under specified conditions (pending order).
        TRADE_ACTION_SLTP (int): Modify Stop Loss and Take Profit values of an opened position.
        TRADE_ACTION_MODIFY (int): Modify the parameters of the order placed previously.
        TRADE_ACTION_REMOVE (int): Delete the pending order placed previously.
        TRADE_ACTION_CLOSE_BY (int): Close a position by an opposite one.
    """

    TRADE_ACTION_DEAL: int = mt5.TRADE_ACTION_DEAL
    TRADE_ACTION_PENDING: int = mt5.TRADE_ACTION_PENDING
    TRADE_ACTION_SLTP: int = mt5.TRADE_ACTION_SLTP
    TRADE_ACTION_MODIFY: int = mt5.TRADE_ACTION_MODIFY
    TRADE_ACTION_REMOVE: int = mt5.TRADE_ACTION_REMOVE
    TRADE_ACTION_CLOSE_BY: int = mt5.TRADE_ACTION_CLOSE_BY


class ENUM_POSITION_TYPE(IntEnum):
    """Position types

    Direction of an open position (buy or sell)

    Args:
        POSITION_TYPE_BUY (int): Buy position.
        POSITION_TYPE_SELL (int): Sell position.
    """

    POSITION_TYPE_BUY: int = mt5.POSITION_TYPE_BUY
    POSITION_TYPE_SELL: int = mt5.POSITION_TYPE_SELL


class ENUM_POSITION_REASON(IntEnum):
    """Platform that the position was opened

    Args:
        POSITION_REASON_CLIENT (int): The position was opened as a result of activation of an order placed from a desktop terminal
        POSITION_REASON_EXPERT (int): The position was opened as a result of activation of an order placed from an MQL5 program, i.e. an Expert Advisor or a script
        POSITION_REASON_MOBILE (int): The position was opened as a result of activation of an order placed from a mobile application
        POSITION_REASON_WEB (int): The position was opened as a result of activation of an order placed from the web platform
    """

    POSITION_REASON_CLIENT: int = mt5.POSITION_REASON_CLIENT
    POSITION_REASON_EXPERT: int = mt5.POSITION_REASON_EXPERT
    POSITION_REASON_MOBILE: int = mt5.POSITION_REASON_MOBILE
    POSITION_REASON_WEB: int = mt5.POSITION_REASON_WEB


class ENUM_DEAL_TYPE(IntEnum):
    """Deal type

    Args:
        DEAL_TYPE_BUY (int): Buy.
        DEAL_TYPE_SELL (int): Sell.
        DEAL_TYPE_BALANCE (int): Balance.
        DEAL_TYPE_CREDIT (int): Credit.
        DEAL_TYPE_CHARGE (int): Additional charge.
        DEAL_TYPE_CORRECTION (int): Correction.
        DEAL_TYPE_BONUS (int): Bonus.
        DEAL_TYPE_COMMISSION (int): Additional commission.
        DEAL_TYPE_COMMISSION_DAILY (int): Daily commission.
        DEAL_TYPE_COMMISSION_MONTHLY (int): Monthly commission.
        DEAL_TYPE_COMMISSION_AGENT_DAILY (int): Daily agent commission.
        DEAL_TYPE_COMMISSION_AGENT_MONTHLY (int): Monthly agent commission.
        DEAL_TYPE_INTEREST (int): Interest rate.
        DEAL_TYPE_BUY_CANCELED (int): Canceled buy deal. There can be a situation when a previously executed buy deal is canceled. In this case, the type of the previously executed deal (DEAL_TYPE_BUY) is changed to DEAL_TYPE_BUY_CANCELED, and its profit/loss is zeroized. Previously obtained profit/loss is charged/withdrawn using a separated balance operation.
        DEAL_TYPE_SELL_CANCELED (int): Canceled sell deal. There can be a situation when a previously executed sell deal is canceled. In this case, the type of the previously executed deal (DEAL_TYPE_SELL) is changed to DEAL_TYPE_SELL_CANCELED, and its profit/loss is zeroized. Previously obtained profit/loss is charged/withdrawn using a separated balance operation.
        DEAL_DIVIDEND (int): Dividend operations.
        DEAL_DIVIDEND_FRANKED (int): Franked (non-taxable) dividend operations.
        DEAL_TAX (int): Tax charges.
    """

    DEAL_TYPE_BUY: int = mt5.DEAL_TYPE_BUY
    DEAL_TYPE_SELL: int = mt5.DEAL_TYPE_SELL
    DEAL_TYPE_BALANCE: int = mt5.DEAL_TYPE_BALANCE
    DEAL_TYPE_CREDIT: int = mt5.DEAL_TYPE_CREDIT
    DEAL_TYPE_CHARGE: int = mt5.DEAL_TYPE_CHARGE
    DEAL_TYPE_CORRECTION: int = mt5.DEAL_TYPE_CORRECTION
    DEAL_TYPE_BONUS: int = mt5.DEAL_TYPE_BONUS
    DEAL_TYPE_COMMISSION: int = mt5.DEAL_TYPE_COMMISSION
    DEAL_TYPE_COMMISSION_DAILY: int = mt5.DEAL_TYPE_COMMISSION_DAILY
    DEAL_TYPE_COMMISSION_MONTHLY: int = mt5.DEAL_TYPE_COMMISSION_MONTHLY
    DEAL_TYPE_COMMISSION_AGENT_DAILY: int = mt5.DEAL_TYPE_COMMISSION_AGENT_DAILY
    DEAL_TYPE_COMMISSION_AGENT_MONTHLY: int = mt5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY
    DEAL_TYPE_INTEREST: int = mt5.DEAL_TYPE_INTEREST
    DEAL_TYPE_BUY_CANCELED: int = mt5.DEAL_TYPE_BUY_CANCELED
    DEAL_TYPE_SELL_CANCELED: int = mt5.DEAL_TYPE_SELL_CANCELED
    DEAL_DIVIDEND: int = mt5.DEAL_DIVIDEND
    DEAL_DIVIDEND_FRANKED: int = mt5.DEAL_DIVIDEND_FRANKED
    DEAL_TAX: int = mt5.DEAL_TAX


class ENUM_DEAL_ENTRY(IntEnum):
    """Deal entry

    Args:
        DEAL_ENTRY_IN (int): Entry in.
        DEAL_ENTRY_OUT (int): Entry out.
        DEAL_ENTRY_INOUT (int): Reverse.
        DEAL_ENTRY_OUT_BY (int): Close a position by an opposite one.
    """

    DEAL_ENTRY_IN: int = mt5.DEAL_ENTRY_IN
    DEAL_ENTRY_OUT: int = mt5.DEAL_ENTRY_OUT
    DEAL_ENTRY_INOUT: int = mt5.DEAL_ENTRY_INOUT
    DEAL_ENTRY_OUT_BY: int = mt5.DEAL_ENTRY_OUT_BY


class ENUM_DEAL_REASON(IntEnum):
    """Deal Reason

    Args:
        DEAL_REASON_CLIENT (int): The deal was executed as a result of activation of an order placed from a desktop terminal.
        DEAL_REASON_MOBILE (int): The deal was executed as a result of activation of an order placed from a mobile application.
        DEAL_REASON_WEB (int): The deal was executed as a result of activation of an order placed from the web platform.
        DEAL_REASON_EXPERT (int): The deal was executed as a result of activation of an order placed from an MQL5 program, i.e. an Expert Advisor or a script.
        DEAL_REASON_SL (int): The deal was executed as a result of Stop Loss activation.
        DEAL_REASON_TP (int): The deal was executed as a result of Take Profit activation.
        DEAL_REASON_SO (int): The deal was executed as a result of the Stop Out event.
        DEAL_REASON_ROLLOVER (int): The deal was executed due to a rollover.
        DEAL_REASON_VMARGIN (int): The deal was executed after charging the variation margin.
        DEAL_REASON_SPLIT (int): The deal was executed after the split (price reduction) of an instrument, which had an open position during split announcement.
    """

    DEAL_REASON_CLIENT: int = mt5.DEAL_REASON_CLIENT
    DEAL_REASON_MOBILE: int = mt5.DEAL_REASON_MOBILE
    DEAL_REASON_WEB: int = mt5.DEAL_REASON_WEB
    DEAL_REASON_EXPERT: int = mt5.DEAL_REASON_EXPERT
    DEAL_REASON_SL: int = mt5.DEAL_REASON_SL
    DEAL_REASON_TP: int = mt5.DEAL_REASON_TP
    DEAL_REASON_SO: int = mt5.DEAL_REASON_SO
    DEAL_REASON_ROLLOVER: int = mt5.DEAL_REASON_ROLLOVER
    DEAL_REASON_VMARGIN: int = mt5.DEAL_REASON_VMARGIN
    DEAL_REASON_SPLIT: int = mt5.DEAL_REASON_SPLIT


class ENUM_ORDER_REASON(IntEnum):
    """The reason or source for placing an order

    Args:
        ORDER_REASON_CLIENT (int): The order was placed from a desktop terminal.
        ORDER_REASON_MOBILE (int): The order was placed from a mobile application.
        ORDER_REASON_WEB (int): The order was placed from a web platform.
        ORDER_REASON_EXPERT (int): The order was placed from an MQL5-program, i.e. by an Expert Advisor or a script.
        ORDER_REASON_SL (int): The order was placed as a result of Stop Loss activation.
        ORDER_REASON_TP (int): The order was placed as a result of Take Profit activation.
        ORDER_REASON_SO (int): The order was placed as a result of the Stop Out event.
    """

    ORDER_REASON_CLIENT: int = mt5.ORDER_REASON_CLIENT
    ORDER_REASON_MOBILE: int = mt5.ORDER_REASON_MOBILE
    ORDER_REASON_WEB: int = mt5.ORDER_REASON_WEB
    ORDER_REASON_EXPERT: int = mt5.ORDER_REASON_EXPERT
    ORDER_REASON_SL: int = mt5.ORDER_REASON_SL
    ORDER_REASON_TP: int = mt5.ORDER_REASON_TP
    ORDER_REASON_SO: int = mt5.ORDER_REASON_SO


class ENUM_ORDER_TYPE(IntEnum):
    """Order types

    When sending a trade request using the OrderSend() function, some operations require the indication of the order type.
        The order type is specified in the type field of the special structure MqlTradeRequest, and can accept values of the ENUM_ORDER_TYPE enumeration.

    Args:
        ORDER_TYPE_BUY (int): Market Buy order.
        ORDER_TYPE_SELL (int): Market Sell order.
        ORDER_TYPE_BUY_LIMIT (int): Buy Limit pending order.
        ORDER_TYPE_SELL_LIMIT (int): Sell Limit pending order.
        ORDER_TYPE_BUY_STOP (int): Buy Stop pending order.
        ORDER_TYPE_SELL_STOP (int): Sell Stop pending order.
        ORDER_TYPE_BUY_STOP_LIMIT (int): Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price.
        ORDER_TYPE_SELL_STOP_LIMIT (int): Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price.
        ORDER_TYPE_CLOSE_BY (int): Order to close a position by an opposite one.
    """

    ORDER_TYPE_BUY: int = mt5.ORDER_TYPE_BUY
    ORDER_TYPE_SELL: int = mt5.ORDER_TYPE_SELL
    ORDER_TYPE_BUY_LIMIT: int = mt5.ORDER_TYPE_BUY_LIMIT
    ORDER_TYPE_SELL_LIMIT: int = mt5.ORDER_TYPE_SELL_LIMIT
    ORDER_TYPE_BUY_STOP: int = mt5.ORDER_TYPE_BUY_STOP
    ORDER_TYPE_SELL_STOP: int = mt5.ORDER_TYPE_SELL_STOP
    ORDER_TYPE_BUY_STOP_LIMIT: int = mt5.ORDER_TYPE_BUY_STOP_LIMIT
    ORDER_TYPE_SELL_STOP_LIMIT: int = mt5.ORDER_TYPE_SELL_STOP_LIMIT
    ORDER_TYPE_CLOSE_BY: int = mt5.ORDER_TYPE_CLOSE_BY

    @classmethod
    def get_order_name(cls, name):
        return name.replace("ORDER_TYPE_", "")


class ENUM_ORDER_TYPE_MARKET(IntEnum):
    """Market order types

    Args:
        ORDER_TYPE_BUY (ENUM_ORDER_TYPE): Market Buy order.
        ORDER_TYPE_SELL (ENUM_ORDER_TYPE): Market Sell order.
    """

    ORDER_TYPE_BUY: ENUM_ORDER_TYPE = ENUM_ORDER_TYPE.ORDER_TYPE_BUY
    ORDER_TYPE_SELL: ENUM_ORDER_TYPE = ENUM_ORDER_TYPE.ORDER_TYPE_SELL


class ENUM_ORDER_TYPE_PENDING(IntEnum):
    """Pending order types

    When sending a trade request using the OrderSend() function, some operations require the indication of the order type.
        The order type is specified in the type field of the special structure MqlTradeRequest, and can accept values of the ENUM_ORDER_TYPE enumeration.

    Args:
        ORDER_TYPE_BUY_LIMIT (ENUM_ORDER_TYPE): Buy Limit pending order.
        ORDER_TYPE_BUY_STOP (ENUM_ORDER_TYPE): Buy Stop pending order.
        ORDER_TYPE_BUY_STOP_LIMIT (ENUM_ORDER_TYPE): Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price.
        ORDER_TYPE_SELL_LIMIT (ENUM_ORDER_TYPE): Sell Limit pending order.
        ORDER_TYPE_SELL_STOP (ENUM_ORDER_TYPE): Sell Stop pending order.
        ORDER_TYPE_SELL_STOP_LIMIT (ENUM_ORDER_TYPE): Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price.
    """

    ORDER_TYPE_BUY_LIMIT: ENUM_ORDER_TYPE = (ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,)
    ORDER_TYPE_BUY_STOP: ENUM_ORDER_TYPE = (ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,)
    ORDER_TYPE_BUY_STOP_LIMIT: ENUM_ORDER_TYPE = (
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
    )
    ORDER_TYPE_SELL_LIMIT: ENUM_ORDER_TYPE = (ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,)
    ORDER_TYPE_SELL_STOP: ENUM_ORDER_TYPE = (ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,)
    ORDER_TYPE_SELL_STOP_LIMIT: ENUM_ORDER_TYPE = (
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
    )


class ENUM_ORDER_TYPE_FILLING(IntEnum):
    """Volume filling policy

    Args:
        ORDER_FILLING_FOK (int): An order can be executed in the specified volume only.
        ORDER_FILLING_IOC (int): If the request cannot be filled completely, an order with the available volume will be executed, and the remaining volume will be canceled.
        ORDER_FILLING_BOC (int): The BoC order assumes that the order can only be placed in the Depth of Market and cannot be immediately executed. If the order can be executed immediately when placed, then it is canceled.
        ORDER_FILLING_RETURN (int): In case of partial filling, an order with remaining volume is not canceled but processed further.
    """

    ORDER_FILLING_FOK: int = mt5.ORDER_FILLING_FOK
    ORDER_FILLING_IOC: int = mt5.ORDER_FILLING_IOC
    ORDER_FILLING_BOC: int = mt5.ORDER_FILLING_BOC
    ORDER_FILLING_RETURN: int = mt5.ORDER_FILLING_RETURN


class ENUM_ORDER_TYPE_TIME(IntEnum):
    """Order validity period

    Args:
        ORDER_TIME_GTC (int): Good till cancel order
        ORDER_TIME_DAY (int): Good till current trade day order
        ORDER_TIME_SPECIFIED (int): Good till expired order
        ORDER_TIME_SPECIFIED_DAY (int): The order will be effective till 23:59:59 of the specified day.
    """

    ORDER_TIME_GTC: int = mt5.ORDER_TIME_GTC
    ORDER_TIME_DAY: int = mt5.ORDER_TIME_DAY
    ORDER_TIME_SPECIFIED: int = mt5.ORDER_TIME_SPECIFIED
    ORDER_TIME_SPECIFIED_DAY: int = mt5.ORDER_TIME_SPECIFIED_DAY


class ENUM_ORDER_STATE(IntEnum):
    """Order state

    Args:
        ORDER_STATE_STARTED (int): Order checked, but not yet accepted by broker.
        ORDER_STATE_PLACED (int): Order accepted.
        ORDER_STATE_CANCELED (int): Order canceled by client.
        ORDER_STATE_PARTIAL (int): Order partially executed.
        ORDER_STATE_FILLED (int): Order fully executed.
        ORDER_STATE_REJECTED (int): Order rejected.
        ORDER_STATE_EXPIRED (int): Order expired.
        ORDER_STATE_REQUEST_ADD (int): Order is being registered (placing to the trading system).
        ORDER_STATE_REQUEST_MODIFY (int): Order is being modified (changing its parameters).
        ORDER_STATE_REQUEST_CANCEL (int): Order is being deleted (deleting from the trading system).

    """

    ORDER_STATE_STARTED: int = mt5.ORDER_STATE_STARTED
    ORDER_STATE_PLACED: int = mt5.ORDER_STATE_PLACED
    ORDER_STATE_CANCELED: int = mt5.ORDER_STATE_CANCELED
    ORDER_STATE_PARTIAL: int = mt5.ORDER_STATE_PARTIAL
    ORDER_STATE_FILLED: int = mt5.ORDER_STATE_FILLED
    ORDER_STATE_REJECTED: int = mt5.ORDER_STATE_REJECTED
    ORDER_STATE_EXPIRED: int = mt5.ORDER_STATE_EXPIRED
    ORDER_STATE_REQUEST_ADD: int = mt5.ORDER_STATE_REQUEST_ADD
    ORDER_STATE_REQUEST_MODIFY: int = mt5.ORDER_STATE_REQUEST_MODIFY
    ORDER_STATE_REQUEST_CANCEL: int = mt5.ORDER_STATE_REQUEST_CANCEL


class ENUM_TRADE_RETCODE(IntEnum):
    """Order send result return codes

    Args:
        TRADE_RETCODE_REQUOTE (int): Requote.
        TRADE_RETCODE_REJECT (int): Request rejected.
        TRADE_RETCODE_CANCEL (int): Request canceled by trader.
        TRADE_RETCODE_PLACED (int): Order placed.
        TRADE_RETCODE_DONE (int): Request completed.
        TRADE_RETCODE_DONE_PARTIAL (int): Only part of the request was completed.
        TRADE_RETCODE_ERROR (int): Request processing error.
        TRADE_RETCODE_TIMEOUT (int): Request canceled by timeout.
        TRADE_RETCODE_INVALID (int): Invalid request.
        TRADE_RETCODE_INVALID_VOLUME (int): Invalid volume in the request.
        TRADE_RETCODE_INVALID_PRICE (int): Invalid price in the request.
        TRADE_RETCODE_INVALID_STOPS (int): Invalid stops in the request.
        TRADE_RETCODE_TRADE_DISABLED (int): Trade is disabled.
        TRADE_RETCODE_MARKET_CLOSED (int): Market is closed.
        TRADE_RETCODE_NO_MONEY (int): There is not enough money to complete the request.
        TRADE_RETCODE_PRICE_CHANGED (int): Prices changed.
        TRADE_RETCODE_PRICE_OFF (int): There are no quotes to process the request.
        TRADE_RETCODE_INVALID_EXPIRATION (int): Invalid order expiration date in the request.
        TRADE_RETCODE_ORDER_CHANGED (int): Order state changed.
        TRADE_RETCODE_TOO_MANY_REQUESTS (int): Too frequent requests.
        TRADE_RETCODE_NO_CHANGES (int): No changes in request.
        TRADE_RETCODE_SERVER_DISABLES_AT (int): Autotrading disabled by server.
        TRADE_RETCODE_CLIENT_DISABLES_AT (int): Autotrading disabled by client terminal.
        TRADE_RETCODE_LOCKED (int): Request locked for processing.
        TRADE_RETCODE_FROZEN (int): Order or position frozen.
        TRADE_RETCODE_INVALID_FILL (int): Invalid order filling type.
        TRADE_RETCODE_CONNECTION (int): No connection with the trade server.
        TRADE_RETCODE_ONLY_REAL (int): Operation is allowed only for live accounts.
        TRADE_RETCODE_LIMIT_ORDERS (int): The number of pending orders has reached the limit.
        TRADE_RETCODE_LIMIT_VOLUME (int): The volume of orders and positions for the symbol has reached the limit.
        TRADE_RETCODE_INVALID_ORDER (int): Incorrect or prohibited order type.
        TRADE_RETCODE_POSITION_CLOSED (int): Position with the specified POSITION_IDENTIFIER has already been closed.
        TRADE_RETCODE_INVALID_CLOSE_VOLUME (int): A close volume exceeds the current position volume.
        TRADE_RETCODE_CLOSE_ORDER_EXIST (int): A close order already exists for a specified position. This may happen when working in the hedging system:
            •when attempting to close a position with an opposite one, while close orders for the position already exist
            •when attempting to fully or partially close a position if the total volume of the already present close orders and the newly placed one exceeds the current position volume.
        TRADE_RETCODE_LIMIT_POSITIONS (int): The number of open positions simultaneously present on an account can be limited by the server settings. After a limit is reached, the server returns the TRADE_RETCODE_LIMIT_POSITIONS error when attempting to place an order. The limitation operates differently depending on the position accounting type:
            •Netting — number of open positions is considered. When a limit is reached, the platform does not let placing new orders whose execution may increase the number of open positions. In fact, the platform allows placing orders only for the symbols that already have open positions. The current pending orders are not considered since their execution may lead to changes in the current positions but it cannot increase their number.
            •Hedging — pending orders are considered together with open positions, since a pending order activation always leads to opening a new position. When a limit is reached, the platform does not allow placing both new market orders for opening positions and pending orders.
        TRADE_RETCODE_REJECT_CANCEL (int): The pending order activation request is rejected, the order is canceled.
        TRADE_RETCODE_LONG_ONLY (int): The request is rejected, because the "Only long positions are allowed" rule is set for the symbol (POSITION_TYPE_BUY).
        TRADE_RETCODE_SHORT_ONLY (int): The request is rejected, because the "Only short positions are allowed" rule is set for the symbol (POSITION_TYPE_SELL).
        TRADE_RETCODE_CLOSE_ONLY (int): The request is rejected, because the "Only position closing is allowed" rule is set for the symbol .
        TRADE_RETCODE_FIFO_CLOSE (int): The request is rejected, because "Position closing is allowed only by FIFO rule" flag is set for the trading account (ACCOUNT_FIFO_CLOSE=true).
        TRADE_RETCODE_HEDGE_PROHIBITED (int): The request is rejected, because the "Opposite positions on a single symbol are disabled" rule is set for the trading account. For example, if the account has a Buy position, then a user cannot open a Sell position or place a pending sell order. The rule is only applied to accounts with hedging accounting system (ACCOUNT_MARGIN_MODE=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING).
    """

    TRADE_RETCODE_REQUOTE: int = mt5.TRADE_RETCODE_REQUOTE
    TRADE_RETCODE_REJECT: int = mt5.TRADE_RETCODE_REJECT
    TRADE_RETCODE_CANCEL: int = mt5.TRADE_RETCODE_CANCEL
    TRADE_RETCODE_PLACED: int = mt5.TRADE_RETCODE_PLACED
    TRADE_RETCODE_DONE: int = mt5.TRADE_RETCODE_DONE
    TRADE_RETCODE_DONE_PARTIAL: int = mt5.TRADE_RETCODE_DONE_PARTIAL
    TRADE_RETCODE_ERROR: int = mt5.TRADE_RETCODE_ERROR
    TRADE_RETCODE_TIMEOUT: int = mt5.TRADE_RETCODE_TIMEOUT
    TRADE_RETCODE_INVALID: int = mt5.TRADE_RETCODE_INVALID
    TRADE_RETCODE_INVALID_VOLUME: int = mt5.TRADE_RETCODE_INVALID_VOLUME
    TRADE_RETCODE_INVALID_PRICE: int = mt5.TRADE_RETCODE_INVALID_PRICE
    TRADE_RETCODE_INVALID_STOPS: int = mt5.TRADE_RETCODE_INVALID_STOPS
    TRADE_RETCODE_TRADE_DISABLED: int = mt5.TRADE_RETCODE_TRADE_DISABLED
    TRADE_RETCODE_MARKET_CLOSED: int = mt5.TRADE_RETCODE_MARKET_CLOSED
    TRADE_RETCODE_NO_MONEY: int = mt5.TRADE_RETCODE_NO_MONEY
    TRADE_RETCODE_PRICE_CHANGED: int = mt5.TRADE_RETCODE_PRICE_CHANGED
    TRADE_RETCODE_PRICE_OFF: int = mt5.TRADE_RETCODE_PRICE_OFF
    TRADE_RETCODE_INVALID_EXPIRATION: int = mt5.TRADE_RETCODE_INVALID_EXPIRATION
    TRADE_RETCODE_ORDER_CHANGED: int = mt5.TRADE_RETCODE_ORDER_CHANGED
    TRADE_RETCODE_TOO_MANY_REQUESTS: int = mt5.TRADE_RETCODE_TOO_MANY_REQUESTS
    TRADE_RETCODE_NO_CHANGES: int = mt5.TRADE_RETCODE_NO_CHANGES
    TRADE_RETCODE_SERVER_DISABLES_AT: int = mt5.TRADE_RETCODE_SERVER_DISABLES_AT
    TRADE_RETCODE_CLIENT_DISABLES_AT: int = mt5.TRADE_RETCODE_CLIENT_DISABLES_AT
    TRADE_RETCODE_LOCKED: int = mt5.TRADE_RETCODE_LOCKED
    TRADE_RETCODE_FROZEN: int = mt5.TRADE_RETCODE_FROZEN
    TRADE_RETCODE_INVALID_FILL: int = mt5.TRADE_RETCODE_INVALID_FILL
    TRADE_RETCODE_CONNECTION: int = mt5.TRADE_RETCODE_CONNECTION
    TRADE_RETCODE_ONLY_REAL: int = mt5.TRADE_RETCODE_ONLY_REAL
    TRADE_RETCODE_LIMIT_ORDERS: int = mt5.TRADE_RETCODE_LIMIT_ORDERS
    TRADE_RETCODE_LIMIT_VOLUME: int = mt5.TRADE_RETCODE_LIMIT_VOLUME
    TRADE_RETCODE_INVALID_ORDER: int = mt5.TRADE_RETCODE_INVALID_ORDER
    TRADE_RETCODE_POSITION_CLOSED: int = mt5.TRADE_RETCODE_POSITION_CLOSED
    TRADE_RETCODE_INVALID_CLOSE_VOLUME: int = mt5.TRADE_RETCODE_INVALID_CLOSE_VOLUME
    TRADE_RETCODE_CLOSE_ORDER_EXIST: int = mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST
    TRADE_RETCODE_LIMIT_POSITIONS: int = mt5.TRADE_RETCODE_LIMIT_POSITIONS
    TRADE_RETCODE_REJECT_CANCEL: int = mt5.TRADE_RETCODE_REJECT_CANCEL
    TRADE_RETCODE_LONG_ONLY: int = mt5.TRADE_RETCODE_LONG_ONLY
    TRADE_RETCODE_SHORT_ONLY: int = mt5.TRADE_RETCODE_SHORT_ONLY
    TRADE_RETCODE_CLOSE_ONLY: int = mt5.TRADE_RETCODE_CLOSE_ONLY
    TRADE_RETCODE_FIFO_CLOSE: int = mt5.TRADE_RETCODE_FIFO_CLOSE


class ENUM_TIMEFRAME(IntEnum):
    """Chart timeframes

    Args:
        TIMEFRAME_M1 (int): 1 minute
        TIMEFRAME_M2 (int): 2 minutes
        TIMEFRAME_M3 (int): 3 minutes
        TIMEFRAME_M4 (int): 4 minutes
        TIMEFRAME_M5 (int): 5 minutes
        TIMEFRAME_M6 (int): 6 minutes
        TIMEFRAME_M10 (int): 10 minutes
        TIMEFRAME_M12 (int): 12 minutes
        TIMEFRAME_M15 (int): 15 minutes
        TIMEFRAME_M20 (int): 20 minutes
        TIMEFRAME_M30 (int): 30 minutes
        TIMEFRAME_H1 (int): 1 hour
        TIMEFRAME_H2 (int): 2 hour
        TIMEFRAME_H3 (int): 3 hour
        TIMEFRAME_H4 (int): 4 hour
        TIMEFRAME_H6 (int): 6 hour
        TIMEFRAME_H8 (int): 8 hour
        TIMEFRAME_H12 (int): 12 hour
        TIMEFRAME_D1 (int): 1 day
        TIMEFRAME_W1 (int): 1 week
        TIMEFRAME_MN1 (int): 1 month
    """

    TIMEFRAME_M1: int = mt5.TIMEFRAME_M1
    TIMEFRAME_M2: int = mt5.TIMEFRAME_M2
    TIMEFRAME_M3: int = mt5.TIMEFRAME_M3
    TIMEFRAME_M4: int = mt5.TIMEFRAME_M4
    TIMEFRAME_M5: int = mt5.TIMEFRAME_M5
    TIMEFRAME_M6: int = mt5.TIMEFRAME_M6
    TIMEFRAME_M10: int = mt5.TIMEFRAME_M10
    TIMEFRAME_M12: int = mt5.TIMEFRAME_M12
    TIMEFRAME_M15: int = mt5.TIMEFRAME_M15
    TIMEFRAME_M20: int = mt5.TIMEFRAME_M20
    TIMEFRAME_M30: int = mt5.TIMEFRAME_M30
    TIMEFRAME_H1: int = mt5.TIMEFRAME_H1
    TIMEFRAME_H2: int = mt5.TIMEFRAME_H2
    TIMEFRAME_H3: int = mt5.TIMEFRAME_H3
    TIMEFRAME_H4: int = mt5.TIMEFRAME_H4
    TIMEFRAME_H6: int = mt5.TIMEFRAME_H6
    TIMEFRAME_H8: int = mt5.TIMEFRAME_H8
    TIMEFRAME_H12: int = mt5.TIMEFRAME_H12
    TIMEFRAME_D1: int = mt5.TIMEFRAME_D1
    TIMEFRAME_W1: int = mt5.TIMEFRAME_W1
    TIMEFRAME_MN1: int = mt5.TIMEFRAME_MN1


class ENUM_CHECK_CODE(IntEnum):
    """Check return code

    Args:
        CHECK_RETCODE_OK (int): Successful request.
        CHECK_RETCODE_ERROR (int): Error request.
        CHECK_RETCODE_RETRY (int): Retry request.
    """

    CHECK_RETCODE_OK: int = auto()
    CHECK_RETCODE_ERROR: int = auto()
    CHECK_RETCODE_RETRY: int = auto()


class ENUM_ACCOUNT_TRADE_MODE(IntEnum):
    """Account Trade Mode

    Args:
        ACCOUNT_TRADE_MODE_DEMO (int): Demo account.
        ACCOUNT_TRADE_MODE_CONTEST (int): Contest account.
        ACCOUNT_TRADE_MODE_REAL (int): Real account.
    """

    ACCOUNT_TRADE_MODE_DEMO: int = mt5.ACCOUNT_TRADE_MODE_DEMO
    ACCOUNT_TRADE_MODE_CONTEST: int = mt5.ACCOUNT_TRADE_MODE_CONTEST
    ACCOUNT_TRADE_MODE_REAL: int = mt5.ACCOUNT_TRADE_MODE_REAL


class ENUM_ACCOUNT_MARGIN_MODE(IntEnum):
    """Account Margin Mode

    Args:
        ACCOUNT_MARGIN_MODE_RETAIL_NETTING (int): Used for the exchange markets where individual positions aren't possible.
        ACCOUNT_MARGIN_MODE_EXCHANGE (int): Used for the exchange markets.
        ACCOUNT_MARGIN_MODE_RETAIL_HEDGING (int): Used for the exchange markets where individual positions are possible.
    """

    ACCOUNT_MARGIN_MODE_RETAIL_NETTING: int = mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING
    ACCOUNT_MARGIN_MODE_EXCHANGE: int = mt5.ACCOUNT_MARGIN_MODE_EXCHANGE
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING: int = mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING


class ENUM_ACCOUNT_STOPOUT_MODE(IntEnum):
    """Account Margin Stop Out Mode

    Args:
        ACCOUNT_STOPOUT_MODE_PERCENT (int): Account stop out mode in percents.
        ACCOUNT_STOPOUT_MODE_MONEY (int): Account stop out mode in money.
    """

    ACCOUNT_STOPOUT_MODE_PERCENT: int = mt5.ACCOUNT_STOPOUT_MODE_PERCENT
    ACCOUNT_STOPOUT_MODE_MONEY: int = mt5.ACCOUNT_STOPOUT_MODE_MONEY


def validate_prices(
    price: float,
    order_type: ENUM_ORDER_TYPE,
    sl: float = None,
    tp: float = None,
    stoplimit: float = None,
) -> None:
    """Validate order prices

    Args:
        price (float): Order price
        order_type (ENUM_ORDER_TYPE): Order type
        sl (float, optional): Order stop loss. Defaults to None.
        tp (float, optional): Order take profit. Defaults to None.
        stoplimit (float, optional): Order stop limit. Defaults to None.

    Raises:
        ValueError: Invalid take profit
        ValueError: Invalid stop loss
        ValueError: Invalid stop limit
    """
    # Set buy order types
    buy_types = [
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
    ]

    # Set sell order types
    sell_types = [
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
    ]

    # Set stop-limit order types
    buy_stop_limit = ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT
    sell_stop_limit = ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT

    # Check the Stop Limit position
    if stoplimit and (
        # Buy stop limit
        (order_type == buy_stop_limit and stoplimit >= price)
        # Sell stop limit
        or (order_type == sell_stop_limit and stoplimit <= price)
    ):
        raise ValueError("Invalid stop limit")

    # Check the Stoploss position
    if sl and (
        # Invalid stop loss
        sl < 0
        # Buy orders
        or (order_type in buy_types and sl >= price)
        # Sell orders
        or (order_type in sell_types and sl <= price)
        # Buy stop limit
        or (order_type == buy_stop_limit and sl >= stoplimit)
        # Sell stop limit
        or (order_type == sell_stop_limit and sl <= stoplimit)
    ):
        raise ValueError("Invalid stop loss")

    # Check the Take Profit position
    if tp and (
        # Invalid take profit
        tp < 0
        # Buy orders
        or (order_type in buy_types and tp <= price)
        # Sell orders
        or (order_type in sell_types and tp >= price)
        # Buy stop limit
        or (order_type == buy_stop_limit and tp <= stoplimit)
        # Sell stop limit
        or (order_type == sell_stop_limit and tp >= stoplimit)
    ):
        raise ValueError("Invalid take profit")
    
    
class MqlSymbolInfo(BaseModel):
    """Symbol info parsed from MetaTrader5.SymbolInfo."""

    """Symbol info

    Args:
        time (datetime): Time of the last quote
        spread (int): Spread value in points
        digits (int): Digits after a decimal point
        ask (float): Ask - best buy offer
        bid (float): Bid - best sell offer
        volume_min (float): Minimal volume for a deal
        volume_max (float): Maximal volume for a deal
        volume_step (float): Minimal volume change step for deal execution
        trade_contract_size (float): Trade contract size
        trade_tick_size (float): Minimal price change
        trade_tick_value_profit (float): Calculated tick price for a profitable position
        trade_tick_value_loss (float): Calculated tick price for a losing position
        currency_base (str): Basic currency of a symbol
        currency_profit (str): Profit currency
        description (str): Symbol description
        name (str): Symbol name
    """

    time: Optional[datetime]
    spread: Optional[int] = 0
    digits: int
    ask: Optional[float] = 0
    bid: Optional[float] = 0
    volume_min: float
    volume_max: float
    volume_step: float
    trade_contract_size: float
    trade_tick_size: float
    trade_tick_value_profit: float
    trade_tick_value_loss: float
    currency_base: str
    currency_profit: str
    description: str
    name: str

    model_config = ConfigDict(validate_assignment=True)

    @classmethod
    def parse_symbol(cls, symbol: mt5.SymbolInfo) -> "MqlSymbolInfo":
        """Parse an mt5.SymbolInfo object to an MqlSymbolInfo instance."""
        required_attrs = [
            "time", "spread", "digits", "ask", "bid",
            "volume_min", "volume_max", "volume_step",
            "trade_tick_size", "trade_contract_size",
            "trade_tick_value_profit", "trade_tick_value_loss",
            "currency_base", "currency_profit", "description", "name"
        ]

        # Verifica se o objeto tem os atributos necessários
        if not all(hasattr(symbol, attr) for attr in required_attrs):
            raise NotExpectedParseType(
                f"{cls.__name__} expected an object with required attributes, got {type(symbol).__name__}"
            )

        dict_symbol = {
            "time": datetime.fromtimestamp(symbol.time, tz=timezone.utc) if symbol.time else None,
            "spread": symbol.spread,
            "digits": symbol.digits,
            "ask": symbol.ask,
            "bid": symbol.bid,
            "volume_min": symbol.volume_min,
            "volume_max": symbol.volume_max,
            "volume_step": symbol.volume_step,
            "trade_tick_size": symbol.trade_tick_size,
            "trade_contract_size": symbol.trade_contract_size,
            "trade_tick_value_profit": symbol.trade_tick_value_profit,
            "trade_tick_value_loss": symbol.trade_tick_value_loss,
            "currency_base": symbol.currency_base,
            "currency_profit": symbol.currency_profit,
            "description": symbol.description,
            "name": symbol.name,
        }
        
        return cls.model_validate(dict_symbol)
    
    @field_validator("bid", mode="after")
    def validate_bid(cls, value, info):
        """Ensure bid is less than or equal to ask."""
        if value > info.data["ask"]:  # Acesse o valor do campo 'ask'
            raise ValueError("bid must not exceed ask")
        return value

    @field_validator("spread", "ask", "bid", mode="before")
    def replace_none_with_zero(cls, value):
        """Replace None with 0 for numeric fields."""
        if value is None:
            return 0
        return value

    @model_validator(mode="after")
    def validate_volumes(cls, values):
        """Ensure volume_min and volume_max are valid together."""
        volume_min = getattr(values, "volume_min")
        volume_max = getattr(values, "volume_max")
        if volume_min is not None and volume_max is not None and volume_max <= volume_min:
            raise ValueError("volume_max must be greater than volume_min")
        return values
    
    @model_validator(mode="after")
    def validate_positive_values(cls, values):
        """Ensure all numeric fields are positive."""
        fields_to_validate = [
            "volume_min", "volume_max", "volume_step",
            "trade_tick_size", "trade_contract_size",
        ]

        for field in fields_to_validate:
            value = getattr(values, field)
            if value is not None and value <= 0:
                raise ValueError(f"The field {field} must be greater than 0.")
        
        return values


class MqlTradeRequest(BaseModel):
    """Interaction between the client terminal and a trade server.

    Interaction between the client terminal and a trade server for executing the order placing operation is performed by using trade requests.

    Args:
        action (ENUM_TRADE_REQUEST_ACTIONS): Trade operation type
        symbol (str): Trade symbol
        magic (int): Expert Advisor ID (magic number).
        order (int): Order ticket.
        volume (float): Requested volume for a deal in lots
        price (float): Price
        stoplimit (float): StopLimit level of the order
        sl (float): Stop Loss level of the order
        tp (float): Take Profit level of the order
        deviation (int): Maximal possible deviation from the requested price.
        type (ENUM_ORDER_TYPE): Order type
        type_filling (ENUM_ORDER_TYPE_FILLING): Order execution type
        type_time (EnumTradeRequestActions): Order expiration type
        expiration (EnumTradeRequestActions): Order expiration time (for the orders of ORDER_TIME_SPECIFIED type)
        comment (str): Order comment
        position (int): Position ticket
        position_by (int): The ticket of an opposite position

    Raises:
        ValidationError: magic, order, deviation, position, position_by
            must be equal or higher to zero
    """

    action: ENUM_TRADE_REQUEST_ACTIONS
    symbol: Optional[str] = None
    magic: Optional[int] = 0
    order: Optional[int] = None
    volume: Optional[float] = None
    price: Optional[float] = None
    stoplimit: Optional[float] = 0
    sl: Optional[float] = 0
    tp: Optional[float] = 0
    deviation: Optional[int] = 5
    type: Optional[ENUM_ORDER_TYPE] = None
    type_filling: Optional[
        ENUM_ORDER_TYPE_FILLING
    ] = ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_FOK
    type_time: Optional[ENUM_ORDER_TYPE_TIME] = ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC
    expiration: Optional[datetime] = None
    comment: Optional[str] = ""
    position: Optional[int] = None
    position_by: Optional[int] = None

    model_config = ConfigDict(validate_assignment=True)

    def prepare(self) -> dict:
        """Prepare request dict based on each trade action

        Returns:
            dict: Prepared request data
        """
        request = {}
        if self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "symbol": self.symbol,
                    "volume": self.volume,
                    "price": self.price,
                    "type": self.type,
                    # Optional fields
                    "deviation": self.deviation,
                    "type_filling": self.type_filling,
                }
            )

            if self.sl:
                request.update({"sl": self.sl})
            if self.tp:
                request.update({"tp": self.tp})
            if self.comment:
                request.update({"comment": self.comment})
            if self.magic:
                request.update({"magic": self.magic})

        elif self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "symbol": self.symbol,
                    "volume": self.volume,
                    "price": self.price,
                    "type": self.type,
                    # Optional fields
                    "type_filling": self.type_filling,
                    "deviation": self.deviation,
                    "type_time": self.type_time,
                }
            )

            if self.sl:
                request.update({"sl": self.sl})
            if self.tp:
                request.update({"tp": self.tp})
            if self.comment:
                request.update({"comment": self.comment})
            if self.magic:
                request.update({"magic": self.magic})

            # Set 'stoplimit'
            if self.type in [
                ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
                ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            ]:
                request.update({"stoplimit": self.stoplimit})

            # Set 'expiration'
            if self.expiration:
                request.update({"expiration": int(self.expiration.timestamp())})

        elif self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_SLTP:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "symbol": self.symbol,
                    "position": self.position,
                }
            )

            if self.sl:
                request.update({"sl": self.sl})
            if self.tp:
                request.update({"tp": self.tp})
            if self.comment:
                request.update({"comment": self.comment})
            if self.magic:
                request.update({"magic": self.magic})

        elif self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_MODIFY:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "order": self.order,
                    "price": self.price,
                    # Optional Field
                    "type_time": self.type_time,
                }
            )

            if self.sl:
                request.update({"sl": self.sl})
            if self.tp:
                request.update({"tp": self.tp})
            if self.expiration:
                request.update({"expiration": int(self.expiration.timestamp())})

        elif self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "order": self.order,
                    "type": self.type,
                }
            )

        elif self.action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY:
            request.update(
                {
                    # Required Fields
                    "action": self.action,
                    "type": self.type,
                    "position": self.position,
                    "position_by": self.position_by,
                }
            )

        return request
    
    @classmethod
    def parse_request(cls, request: "mt5.TradeRequest") -> "MqlTradeRequest":
        """Parse a mt5.TradeRequest to MqlTradeRequest"""
        if not hasattr(request, "action"):
            raise NotExpectedParseType(
                f"{cls.__name__} expected mt5.TradeRequest, got {type(request).__name__}"
            )

        dict_request = {
            "action": request.action,
            "symbol": request.symbol,
            "magic": request.magic,
            "order": request.order,
            "volume": request.volume,
            "price": request.price,
            "stoplimit": request.stoplimit,
            "sl": request.sl,
            "tp": request.tp,
            "deviation": request.deviation,
            "type": request.type,
            "type_time": request.type_time,
            "type_filling": request.type_filling,
            "comment": request.comment,
            "position": request.position,
            "position_by": request.position_by,
        }

        if request.expiration:
            dict_request["expiration"] = datetime.fromtimestamp(
                request.expiration, tz=timezone.utc
            )

        return cls.model_validate(dict_request)


    @field_validator("volume")
    def __validate_volume(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Volume must be greater than zero.")
        return value
    
    @field_validator("expiration", mode="before")
    def __validate_expiration(cls, value):
        if value is not None:
            if value.tzinfo is None:
                value = datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)

            if value <= datetime.now(timezone.utc):
                raise ValueError("Invalid expiration time: must be in the future.")
        return value
    
    @field_validator("magic", "order", "deviation", "position", "position_by", mode="before")
    def __validate_int_size(cls, value: int, values: dict) -> int:
        """Validate language C long integers

        Args:
            value (int): int value
            values (dict): previous values

        Returns:
            int: int value
        """
        if value is not None:
            # Validate int size
            validate_mt5_ulong_size(value)

        return value

    @model_validator(mode="after")
    def __validate_prices(cls, values: dict) -> dict:
        """Validate the stop loss and take profit positions

        Args:
            values (dict): class attributes

        Raises:
            ValueError: Invalid stop loss
            ValueError: Invalid take profit

        Returns:
            dict: class attributes
        """
        sl = getattr(values, "sl")
        tp = getattr(values, "tp")
        stoplimit = getattr(values, "stoplimit")


        # Validate Stop Loss, Take Profit, and Stop Limit
        if sl or tp or stoplimit:
            price = getattr(values, "price") or 0
            order_type = getattr(values, "type")
            validate_prices(
                price=price, 
                sl=sl, 
                tp=tp, 
                stoplimit=stoplimit, 
                order_type=order_type
            )

        return values
    
    @model_validator(mode="after")
    def __validate_order_types(cls, values: dict) -> dict:
        """Validate the order type

        Args:
            values (dict): class attributes

        Raises:
            ValueError: Invalid order type

        Returns:
            dict: class attributes
        """

        action = getattr(values, "action")
        order_type = getattr(values, "type")

        # Check if stop or take profit is defined
        if order_type:
            # Market order
            market = [
                ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
                ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            ]
            # Pending orders
            pending = [
                ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
                ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
                ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
                ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
                ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
                ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            ]

            # close by order
            close_by = [ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY]

            if (
                # Market orders
                (
                    action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL
                    and order_type not in market
                )
                # Pending orders
                or (
                    action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING
                    and order_type not in pending
                )
                # Close by orders
                or (
                    action == ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY
                    and order_type not in close_by
                )
            ):
                raise ValueError("Invalid order type")

        return values

    @model_validator(mode="after")
    def __validate_type_time(cls, values: dict) -> dict:
        """Validate type time

        Args:
            values (dict): class attributes

        Raises:
            ValueError: Invalid type time

        Returns:
            dict: class attributes
        """
        expiration = getattr(values, "expiration")
        type_time = getattr(values, "type_time")

        if type_time in [
            ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
            ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY,
        ] and not expiration:
            raise ValueError("Expiration must be provided for specified order time types.")
        
        if type_time not in [
            ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED,
            ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY,
        ] and expiration:
            raise ValueError("OrderTypeTime must be specified when the expiration is set.")

        return values

    @model_validator(mode="after")
    def __validate_general_consistency(cls, values: dict) -> dict:
        """General validation for consistency."""
        sl = getattr(values, "sl")
        tp = getattr(values, "tp")
        price = getattr(values, "price") or 0
        action = getattr(values, "action")

        # Validate prices
        if action in [
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL,
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING,
        ]:
            # Validate the price
            if price <= 0:
                raise ValueError("Price must be greater than 0.")
            validate_prices(
                price=price, sl=sl, tp=tp, stoplimit=getattr(values, "stoplimit"),
                order_type=getattr(values, "type")
            )

        return values

    @model_validator(mode="after")
    def __validate_required_fields(cls, values):
        action = getattr(values, "action")
        required_fields = {
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL: ["symbol", "volume", "price", "type"],
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING: ["symbol", "volume", "price", "type"],
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_SLTP: ["symbol", "position"],
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_MODIFY: ["order", "price"],
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE: ["order"],
            ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY: ["type", "position", "position_by"],
        }

        missing_fields = []
        for field in required_fields.get(action, []):
            if getattr(values, field, None) is None:
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required fields for action {action.name}: {', '.join(missing_fields)}")

        return values
    

class MqlTradeResult(BaseModel):
    """Result of a trade request

    A trade server returns data about the trade request processing result as a special predefined structure of MqlTradeResult type.

    Args:
        retcode (ENUM_TRADE_RETCODE): Operation return code
        deal (int): Deal ticket, if it is performed
        order (int): Order ticket, if it is placed
        volume (float): Deal volume, confirmed by broker
        price (float): Deal price, confirmed by broker
        bid (float): Current Bid price
        ask (float): Current Ask price
        comment (str): Broker comment to operation (by default it is filled by description of trade server return code)
        request_id (int): Request ID set by the terminal during the dispatch
        retcode_external (int): Return code of an external trading system
    """

    retcode: ENUM_TRADE_RETCODE
    deal: int
    order: int
    volume: float
    price: float
    bid: float
    ask: float
    comment: str
    request_id: int
    retcode_external: int

    model_config = ConfigDict(validate_assignment=True)

    @classmethod
    def parse_result(cls, result: "mt5.OrderSendResult") -> "MqlTradeResult":
        """Parse a mt5.OrderSendResult object to MqlTradeResult

        Args:
            result (mt5.OrderSendResult): mt5 result object

        Raises:
            NotExpectedParseType: Type not expected

        Returns:
            MqlTradeResult: object declared
        """
        required_attrs = [
            "retcode", "deal", "order", "volume", "price",
            "bid", "ask", "comment", "request_id", "retcode_external"
        ]

        # Ensure the result object has the necessary attributes
        if not all(hasattr(result, attr) for attr in required_attrs):
            raise ValueError(f"Expected an mt5.OrderSendResult object with all required attributes, got {type(result).__name__}")

        dict_result = {
            "retcode": result.retcode,
            "deal": result.deal,
            "order": result.order,
            "volume": result.volume,
            "price": result.price,
            "bid": result.bid,
            "ask": result.ask,
            "comment": result.comment,
            "request_id": result.request_id,
            "retcode_external": result.retcode_external,
        }

        return cls.model_validate(dict_result)

    @field_validator("volume")
    def __validate_volume(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Volume must be greater than zero.")
        return value

    @model_validator(mode="after")
    def __validate_bid(cls, values):
        """Ensure bid is less than or equal to ask."""
        ask = getattr(values, "ask")
        bid = getattr(values, "bid")
        if ask is not None and bid is not None and bid > ask:
            raise ValueError("Bid price must not exceed ask price")
        return values

    @model_validator(mode="after")
    def __validate_prices(cls, values):
        """Ensure price relationships are valid."""
        bid = getattr(values, "bid")
        ask = getattr(values, "ask")
        price = getattr(values, "price")
        if bid is not None and ask is not None and bid > ask:
            raise ValueError("Bid price cannot be greater than ask price")
        if price is not None and (bid is not None or ask is not None):
            if bid is not None and price < bid:
                raise ValueError("Price must be greater than or equal to bid")
            if ask is not None and price > ask:
                raise ValueError("Price must be less than or equal to ask")
        return values


class MqlPositionInfo(BaseModel):
    """Position info

    Args:
        ticket (int): Unique number assigned to each newly opened position.
        time (datetime): Position open time
        time_msc (datetime): Position opening time in milliseconds since 01.01.1970
        time_update (datetime): Position changing time
        time_update_msc (datetime): Position changing time in milliseconds since 01.01.1970
        type (ENUM_POSITION_TYPE): Position type
        magic (int): Position magic number
        identifier (int): Position identifier is a unique number assigned to each re-opened position.
            It does not change throughout its life cycle and corresponds to the ticket of an order used to open a position.
        reason (ENUM_POSITION_REASON): The reason for opening a position
        volume (float): Position volume
        price_open (float): Position open price
        sl (float): Stop Loss level of opened position
        tp (float): Take Profit level of opened position
        price_current (float): Current price of the position symbol
        swap (float): Cumulative swap
        profit (float): Current profit
        symbol (str): Symbol of the position
        comment (str): Position comment
        external_id (str): Position identifier in an external trading system (on the Exchange)
    """

    ticket: int
    time: datetime
    time_msc: datetime
    time_update: datetime
    time_update_msc: datetime
    type: ENUM_POSITION_TYPE
    magic: Optional[int] = None
    identifier: int
    reason: int
    volume: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    swap: float
    profit: float
    symbol: str
    comment: Optional[str] = None
    external_id: Optional[str] = None

    def update(self, **kwargs):
        """Atualiza os atributos do modelo após validação."""
        # Valida os dados existentes com os novos usando model_validate
        updated_data = self.model_validate(self.model_dump() | kwargs)
        # Atualiza o dicionário interno com os dados validados
        self.__dict__.update(updated_data.__dict__)

    @classmethod
    def parse_position(cls, position: "mt5.TradePosition") -> "MqlPositionInfo":
        """Parse an mt5.TradePosition object to MqlPositionInfo.

        Args:
            position (mt5.TradePosition): mt5 position object.

        Raises:
            ValueError: If the position object does not have the required attributes.

        Returns:
            MqlPositionInfo: Parsed position object.
        """
        required_attrs = [
            "ticket", "time", "time_msc", "time_update", "time_update_msc",
            "type", "magic", "identifier", "reason", "volume",
            "price_open", "sl", "tp", "price_current", "swap", "profit",
            "symbol", "comment", "external_id"
        ]

        if not all(hasattr(position, attr) for attr in required_attrs):
            raise ValueError(f"Expected an mt5.TradePosition object with all required attributes, got {type(position).__name__}")

        dict_position = {
            "ticket": position.ticket,
            "time": position.time,
            "time_msc": position.time_msc,
            "time_update": position.time_update,
            "time_update_msc": position.time_update_msc,
            "type": position.type,
            "magic": position.magic,
            "identifier": position.identifier,
            "reason": position.reason,
            "volume": position.volume,
            "price_open": position.price_open,
            "sl": position.sl,
            "tp": position.tp,
            "price_current": position.price_current,
            "swap": position.swap,
            "profit": position.profit,
            "symbol": position.symbol,
            "comment": position.comment,
            "external_id": position.external_id,
        }

        return cls.model_validate(dict_position)

    @field_validator("time", "time_update", mode="before")
    def __validate_datetimes(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="s", utc=True).to_pydatetime()

        return value

    @field_validator("time_msc", "time_update_msc", mode="before")
    def __validate_datetimes_msc(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="ms", utc=True).to_pydatetime()

        return value

    @field_validator("volume", mode="before")
    def __validate_volume(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Volume must be greater than zero.")
        return value
    
    @model_validator(mode="after")
    def __validate_prices(cls, values: dict) -> dict:
        """Validate the stop loss and take profit positions

        Args:
            values (dict): class attributes

        Returns:
            dict: class attributes
        """

        sl = getattr(values, "sl", 0)
        tp = getattr(values, "tp", 0)

        # Check if stop or take profit is defined
        if sl or tp:
            price = getattr(values, "price_current", 0)

            position_type = getattr(values, "type")
            if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                order_type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY
            else:
                order_type = ENUM_ORDER_TYPE.ORDER_TYPE_SELL

            # Validate the stoplimit, sl and tp
            validate_prices(price=price, sl=sl, tp=tp, order_type=order_type)
        return values


class MqlTradeOrder(BaseModel):
    """Order data

    Args:
        ticket (int): Order ticket. Unique number assigned to each order
        time_setup (datetime): Order setup time
        time_setup_msc (datetime): The time of placing an order for execution in milliseconds since 01.01.1970
        time_done (datetime): Order execution or cancellation time
        time_done_msc (datetime): Order execution/cancellation time in milliseconds since 01.01.1970
        time_expiration (datetime): Order execution/cancellation time in milliseconds since 01.01.1970
        type (ENUM_ORDER_TYPE): Order type
        type_time (ENUM_ORDER_TYPE_TIME): Order lifetime
        type_filling (ENUM_ORDER_TYPE_FILLING): Order filling type
        state (ENUM_ORDER_STATE): Order state
        magic (int): ID of an Expert Advisor that has placed the order (designed to ensure that each Expert Advisor places its own unique number)
        position_id (int): Position identifier that is set to an order as soon as it is executed.
        position_by_id (int): Identifier of an opposite position used for closing by order  ORDER_TYPE_CLOSE_BY
        reason (ENUM_ORDER_REASON): Position identifier that is set to an order as soon as it is executed.
        volume_initial (float): Order initial volume
        volume_current (float): Order current volume
        price_open (float): Price specified in the order
        sl (float): Stop Loss value
        tp (float): Take Profit value
        price_current (float): The current price of the order symbol
        price_stoplimit (float): The Limit order price for the StopLimit order
        symbol (str): Symbol of the order
        comment (str): Order comment
        external_id (str): Order identifier in an external trading system (on the Exchange)

    """

    ticket: int
    time_setup: datetime
    time_setup_msc: datetime
    time_done: Optional[datetime] = None
    time_done_msc: Optional[datetime] = None
    time_expiration: Optional[datetime] = None
    type: ENUM_ORDER_TYPE
    type_time: ENUM_ORDER_TYPE_TIME
    type_filling: ENUM_ORDER_TYPE_FILLING
    state: ENUM_ORDER_STATE
    magic: Optional[int] = None
    position_id: Optional[int] = None
    position_by_id: Optional[int] = None
    reason: ENUM_ORDER_REASON
    volume_initial: float
    volume_current: float
    price_open: float
    price_current: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    price_stoplimit: Optional[float] = None
    symbol: str
    comment: str
    external_id: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True)

    def update(self, **kwargs):
        """Atualiza os atributos do modelo após validação."""
        # Valida os dados existentes com os novos usando model_validate
        updated_data = self.model_validate(self.model_dump() | kwargs)
        # Atualiza o dicionário interno com os dados validados
        self.__dict__.update(updated_data.__dict__)

    @classmethod
    def parse_order(cls, order: "mt5.TradeOrder") -> "MqlTradeOrder":
        """Parse a mt5.TradeOrder object to MqlTradeOrder.

        Args:
            order (mt5.TradeOrder): mt5 order object.

        Raises:
            ValueError: If required attributes are missing.

        Returns:
            MqlTradeOrder: Parsed and validated MqlTradeOrder object.
        """
        required_attrs = [
            "ticket", "time_setup", "time_setup_msc", "time_done", "time_done_msc",
            "time_expiration", "type", "type_time", "type_filling", "state", "magic",
            "position_id", "position_by_id", "reason", "volume_initial", "volume_current",
            "price_open", "price_current", "sl", "tp", "price_stoplimit", "symbol",
            "comment", "external_id"
        ]

        # Ensure the order object has the necessary attributes
        if not all(hasattr(order, attr) for attr in required_attrs):
            raise ValueError(
                f"Expected an mt5.TradeOrder object with all required attributes, got {type(order).__name__}"
            )

        # Build the dictionary from the mt5.TradeOrder attributes
        dict_order = {
            "ticket": order.ticket,
            "time_setup": order.time_setup,
            "time_setup_msc": order.time_setup_msc,
            "time_done": order.time_done,
            "time_done_msc": order.time_done_msc,
            "time_expiration": order.time_expiration,
            "type": order.type,
            "type_time": order.type_time,
            "type_filling": order.type_filling,
            "state": order.state,
            "magic": order.magic,
            "position_id": order.position_id,
            "position_by_id": order.position_by_id,
            "reason": order.reason,
            "volume_initial": order.volume_initial,
            "volume_current": order.volume_current,
            "price_open": order.price_open,
            "price_current": order.price_current,
            "sl": order.sl,
            "tp": order.tp,
            "price_stoplimit": order.price_stoplimit,
            "symbol": order.symbol,
            "comment": order.comment,
            "external_id": order.external_id,
        }

        # Validate and return the model
        return cls.model_validate(dict_order)

    @field_validator("position_id", "position_by_id", "magic", "price_stoplimit", "sl", "tp", mode="before")
    def __validate_optional_values(cls, value: int):
        if value == 0:
            return None
        return value
    
    @field_validator("time_setup", "time_done", "time_expiration", mode="before")
    def __validate_datetimes(cls, value: int):
        if value == 0:
            return None

        if isinstance(value, int):
            value = pd.to_datetime(value, unit="s", utc=True).to_pydatetime()

        return value

    @field_validator("time_setup_msc", "time_done_msc", mode="before")
    def __validate_datetimes_msc(cls, value: int):
        if value == 0:
            return None

        if isinstance(value, int):
            value = pd.to_datetime(value, unit="ms", utc=True).to_pydatetime()

        return value
    
    @model_validator(mode="after")
    def __validate_expiration(cls, values):
        # Acessa os atributos da instância
        time_expiration = getattr(values, "time_expiration", None)
        time_setup = getattr(values, "time_setup", None)

        # Define time_expiration como None se for igual a 0
        if time_expiration == 0:
            values.time_expiration = None

        # Valida se time_setup existe
        if time_setup is None:
            raise ValueError("Invalid setup time: time_setup is required")

        # Valida se time_expiration é maior que time_setup
        if (
            values.time_expiration is not None
            and isinstance(values.time_expiration, datetime)
            and values.time_expiration <= time_setup
        ):
            raise ValueError("Invalid expiration time: time_expiration must be after time_setup")

        # Retorna a instância corrigida
        return values

    @model_validator(mode="after")
    def __validate_prices(cls, values: dict):
        """Validate the stop loss and take profit positions"""

        sl = getattr(values, "sl", 0)
        tp = getattr(values, "tp", 0)
        stoplimit = getattr(values, "price_stoplimit", 0)

        # Check if stop or take profit is defined
        if sl or tp or stoplimit:
            price = getattr(values, "price_open", 0)
            order_type = getattr(values, "type", None)

            # Valida os preços usando uma função externa
            validate_prices(
                price=price, sl=sl, tp=tp, stoplimit=stoplimit, order_type=order_type
            )

        return values


class MqlTradeDeal(BaseModel):
    """Trade Deal

    Args:
        ticket (int): Deal ticket. Unique number assigned to each deal.
        order (int): Deal order number
        time (datetime): Deal time
        time_msc (int): The time of a deal execution in milliseconds since 01.01.1970
        type (ENUM_DEAL_TYPE): Deal type
        entry (ENUM_DEAL_ENTRY): Deal entry - entry in, entry out, reverse
        magic (int): Deal magic number
        position_id (int): Identifier of a position, in the opening, modification or closing of which this deal took part.
        reason (ENUM_DEAL_REASON): The reason or source for deal execution
        volume (float): Deal volume
        price (float): Deal price
        commission (float): Deal commission
        swap (float): Cumulative swap on close
        profit (float): Deal profit
        fee (float): Fee for making a deal charged immediately after performing a deal
        symbol (str): Deal symbol
        comment (str): Deal comment
        external_id (str): Deal identifier in an external trading system (on the Exchange)
    """

    ticket: int
    order: int
    time: datetime
    time_msc: datetime
    type: ENUM_DEAL_TYPE
    entry: ENUM_DEAL_ENTRY
    magic: Optional[int] = None
    position_id: int
    reason: ENUM_DEAL_REASON
    volume: float
    price: float
    commission: float
    swap: float
    profit: float
    fee: float
    symbol: str
    comment: Optional[str] = ""
    external_id: Optional[str] = ""

    @classmethod
    def parse_deal(cls, deal: "mt5.TradeDeal") -> "MqlTradeDeal":
        """Parse an mt5.TradeDeal object to MqlTradeDeal.

        Args:
            deal (mt5.TradeDeal): mt5 deal object.

        Raises:
            ValueError: If required attributes are missing.

        Returns:
            MqlTradeDeal: Parsed and validated MqlTradeDeal object.
        """
        required_attrs = [
            "ticket", "order", "time", "time_msc", "type", "entry",
            "magic", "position_id", "reason", "volume", "price",
            "commission", "swap", "profit", "fee", "symbol", "comment", "external_id"
        ]

        # Ensure the deal object has the necessary attributes
        if not all(hasattr(deal, attr) for attr in required_attrs):
            raise ValueError(
                f"Expected an mt5.TradeDeal object with all required attributes, got {type(deal).__name__}"
            )

        # Build the dictionary from the mt5.TradeDeal attributes
        dict_deal = {
            "ticket": deal.ticket,
            "order": deal.order,
            "time": deal.time,
            "time_msc": deal.time_msc,  # Convert milliseconds to seconds
            "type": deal.type,
            "entry": deal.entry,
            "magic": deal.magic,
            "position_id": deal.position_id,
            "reason": deal.reason,
            "volume": deal.volume,
            "price": deal.price,
            "commission": deal.commission,
            "swap": deal.swap,
            "profit": deal.profit,
            "fee": deal.fee,
            "symbol": deal.symbol,
            "comment": deal.comment or "",
            "external_id": deal.external_id or "",
        }

        # Validate and return the model
        return cls.model_validate(dict_deal)

    @field_validator("time", mode="before")
    def __validate_datetimes(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="s", utc=True).to_pydatetime()

        return value

    @field_validator("time_msc", mode="before")
    def __validate_datetimes_ms(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="ms", utc=True).to_pydatetime()

        return value


class MqlTick(BaseModel):
    """Tick data

    Args:
        time (datetime): Time of the last prices update
        bid (float): Current Bid price
        ask (float): Current Ask price
        last (float): Price of the last deal (Last)
        volume (int): Volume for the current Last price
        time_msc (datetime): Time of a price last update in milliseconds
        flags (int): Tick flags
        volume_real (float): Volume for the current Last price with greater accuracy
    """

    time: datetime
    bid: float
    ask: float
    last: float
    volume: int
    time_msc: datetime
    flags: int
    volume_real: float

    @classmethod
    def parse_tick(cls, tick: np.void) -> "MqlTick":
        """Parse an mt5 tick object (np.void) to MqlTick.

        Args:
            tick (np.void): mt5 tick object.

        Raises:
            ValueError: If required attributes are missing or object type is incorrect.

        Returns:
            MqlTick: Parsed and validated MqlTick object.
        """
        required_attrs = [
            "time", "bid", "ask", "last", "volume", "time_msc", "flags", "volume_real"
        ]

        # Ensure the tick object has the necessary attributes
        if not isinstance(tick, np.void):
            raise ValueError(
                f"Expected an np.void object, got {type(tick).__name__}"
            )

        if not all(attr in tick.dtype.names for attr in required_attrs):
            raise ValueError(
                f"Expected an np.void object with all required attributes: {', '.join(required_attrs)}"
            )

        # Build the dictionary from the tick attributes
        dict_tick = {
            "time": tick["time"],
            "bid": tick["bid"],
            "ask": tick["ask"],
            "last": tick["last"],
            "volume": tick["volume"],
            "time_msc": tick["time_msc"],
            "flags": tick["flags"],
            "volume_real": tick["volume_real"],
        }

        # Validate and return the model
        return cls.model_validate(dict_tick)

    @field_validator("time", mode="before")
    def __validate_datetimes(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="s", utc=True).to_pydatetime()

        return value

    @field_validator("time_msc", mode="before")
    def __validate_datetimes_ms(cls, value: int, values: dict):
        if value == 0:
            return None

        if value is not None and type(value) == int:
            value = pd.to_datetime(value, unit="ms", utc=True).to_pydatetime()

        return value

def _create_rates() -> "Rates":
    """Cria uma instância de Rates para ser usada como valor padrão."""
    from algo_trading.sources.MetaTrader5_source.rates import Rates  # Importação tardia
    return Rates

def rebuild_model(cls):
    """Decorator to call model_rebuild on the class after its definition."""
    if 'algo_trading.sources.MetaTrader5_source.rates' not in sys.modules:
        # Importação tardia para evitar erro de circular import
        from algo_trading.sources.MetaTrader5_source.rates import Rates

        # Certifica-se de que `model_rebuild` seja chamado corretamente
        cls.model_rebuild()
    return cls

@rebuild_model
class MqlAccountInfo(BaseModel):
    """Account Info

    Args:
        login (int): Account login
        trade_mode (ENUM_ACCOUNT_TRADE_MODE): Account trade mode
        leverage (int): Account leverage
        limit_orders (int): Maximum allowed number of active pending orders
        margin_so_mode (ENUM_ACCOUNT_STOPOUT_MODE): Mode for setting the minimal allowed margin
        trade_allowed (bool): Allowed trade for the current account
        trade_expert (bool): Allowed trade for an Expert Advisor
        margin_mode (ENUM_ACCOUNT_TRADE_MODE): Margin calculation mode
        currency_digits (int): The number of decimal places in the account currency, which are required for an accurate display of trading results
        fifo_close (bool): An indication showing that positions can only be closed by FIFO rule.
            If the property value is set to true, then each symbol positions will be closed in the same order, in which they are opened, starting with the oldest one. In case of an attempt to close positions in a different order, the trader will receive an appropriate error.
        balance (float): Account balance in the deposit currency
        credit (float): Account credit in the deposit currency
        profit (float): Current profit of an account in the deposit currency
        equity (float): Account equity in the deposit currency
        margin (float): Account margin used in the deposit currency
        margin_free (float): Free margin of an account in the deposit currency
        margin_level (float): Account margin level in percents
        margin_so_call (float): Margin call level.
            Depending on the set ACCOUNT_MARGIN_SO_MODE is expressed in percents or in the deposit currency
        margin_so_so (float): Margin stop out level.
            Depending on the set ACCOUNT_MARGIN_SO_MODE is expressed in percents or in the deposit currency
        margin_initial (float): Initial margin.
            The amount reserved on an account to cover the margin of all pending orders
        margin_maintenance (float): Maintenance margin.
            The minimum equity reserved on an account to cover the minimum amount of all open positions
        assets (float): The current assets of an account
        liabilities (float): The current liabilities on an account
        commission_blocked (float): The current blocked commission amount on an account
        name (str): Client name
        server (str): Trade server name
        currency (str): Account currency
        company (str): Name of a company that serves the account
    """

    # Model attributes
    login: int
    trade_mode: ENUM_ACCOUNT_TRADE_MODE
    leverage: int
    limit_orders: int
    margin_so_mode: ENUM_ACCOUNT_STOPOUT_MODE
    trade_allowed: bool
    trade_expert: bool
    margin_mode: ENUM_ACCOUNT_MARGIN_MODE
    currency_digits: int
    fifo_close: bool
    balance: float
    credit: float
    profit: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    margin_so_call: float
    margin_so_so: float
    margin_initial: float
    margin_maintenance: float
    assets: float
    liabilities: float
    commission_blocked: float
    name: str
    server: str
    currency: str
    company: str
    # Utils attributes
    orders: Optional[List[MqlTradeOrder]] = []
    positions: Optional[List[MqlPositionInfo]] = []
    history_deals: Optional[List[MqlTradeDeal]] = []
    is_backtest_account: Optional[bool] = False
    rates_data: Optional[Type["Rates"]] = Field(default_factory=_create_rates)
    
    @classmethod
    def parse_account(cls, account: "mt5.AccountInfo") -> "MqlAccountInfo":
        """Parse a mt5.AccountInfo object to MqlAccountInfo.

        Args:
            account (mt5.AccountInfo): mt5 account object.

        Raises:
            NotExpectedParseType: Type not expected.

        Returns:
            MqlAccountInfo: Parsed and validated MqlAccountInfo object.
        """
        required_attrs = [
            "login", "trade_mode", "leverage", "limit_orders", "margin_so_mode",
            "trade_allowed", "trade_expert", "margin_mode", "currency_digits",
            "fifo_close", "balance", "credit", "profit", "equity", "margin",
            "margin_free", "margin_level", "margin_so_call", "margin_so_so",
            "margin_initial", "margin_maintenance", "assets", "liabilities",
            "commission_blocked", "name", "server", "currency", "company"
        ]

        # Ensure the account object has the necessary attributes
        if not all(hasattr(account, attr) for attr in required_attrs):
            raise ValueError(
                f"Expected an mt5.AccountInfo object with all required attributes, got {type(account).__name__}"
            )

        # Build the dictionary from the mt5.AccountInfo attributes
        dict_account = {attr: getattr(account, attr) for attr in required_attrs}

        # Add utility attributes specific to MqlAccountInfo
        dict_account.update(
            {
                "is_backtest_account": False,
                "orders": cls.__get_updated_orders(),
                "positions": cls.__get_updated_positions(),
                "history_deals": cls.__get_updated_history_deals(),
            }
        )

        # Validate and return the model
        return cls.model_validate(dict_account)

    # Updating ------------------------------------------------------------------------------------
    @classmethod
    def __get_updated_positions(cls):
        # Get open positions on MetaTrader5
        positions = [
            MqlPositionInfo.parse_position(position) for position in mt5.positions_get()
        ]

        return positions

    @classmethod
    def __get_updated_orders(cls):
        # Get positioned orders on MetaTrader5
        orders = [MqlTradeOrder.parse_order(orders) for orders in mt5.orders_get()]

        return orders

    @classmethod
    def __get_updated_history_deals(cls):
        deals = [
            MqlTradeDeal.parse_deal(deal)
            for deal in mt5.history_deals_get(
                datetime(1970, 1, 2, tzinfo=timezone.utc),
                # Cannot get the server time zone, so set the now() time to one day later
                datetime.now(timezone.utc) + timedelta(days=1),
            )
            if deal.type
            in (
                ENUM_DEAL_TYPE.DEAL_TYPE_BUY,
                ENUM_DEAL_TYPE.DEAL_TYPE_SELL,
                ENUM_DEAL_TYPE.DEAL_TYPE_BALANCE,
            )
        ]

        return deals

    def update_positions(self) -> None:
        # Get open positions on MetaTrader5
        self.positions = self.__get_updated_positions()

    def update_orders(self) -> None:
        # Get positioned orders on MetaTrader5
        self.orders = self.__get_updated_orders()

    def update_history_deals(self) -> None:
        # Get history deals on MetaTrader5
        self.history_deals = self.__get_updated_history_deals()

    # Validations ---------------------------------------------------------------------------------
    @model_validator(mode="after")
    def __validate_create_balance_deal(cls, values):
        if values.is_backtest_account:
            # Create initial balance deal
            initial_balance_time = datetime.now(tz=timezone.utc)
            initial_balance_time_ms = get_timestamp_ms(initial_balance_time)

            initial_balance_deal = MqlTradeDeal(
                symbol="",
                ticket=initial_balance_time_ms,
                order=0,
                time=initial_balance_time.replace(microsecond=0),
                time_msc=initial_balance_time,
                type=ENUM_DEAL_TYPE.DEAL_TYPE_BALANCE,
                entry=ENUM_DEAL_ENTRY.DEAL_ENTRY_IN,
                position_id=0,
                volume=0,
                price=0,
                commission=0,
                swap=0,
                profit=values.balance,
                fee=0,
                comment="",
                magic=0,
                reason=ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
                external_id=None,
            )
            

            # Append the deal to the history
            values.history_deals.append(initial_balance_deal)

        return values

    @model_validator(mode="after")
    def __validate_update_balance_value(cls, values):
        # Calcula o balance com base no histórico de deals
        balance = sum(deal.profit for deal in values.history_deals)
        values.balance = balance
        return values
    
