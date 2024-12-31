import pytest
import MetaTrader5 as mt5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (  
    ENUM_TRADE_REQUEST_ACTIONS,
    ENUM_POSITION_TYPE,
    ENUM_POSITION_REASON,
    ENUM_DEAL_TYPE,
    ENUM_DEAL_ENTRY,
    ENUM_DEAL_REASON,
    ENUM_ORDER_REASON,
    ENUM_ORDER_TYPE,
    ENUM_ORDER_TYPE_MARKET,
    ENUM_ORDER_TYPE_PENDING,
    ENUM_ORDER_TYPE_FILLING,
    ENUM_ORDER_TYPE_TIME,
    ENUM_ORDER_STATE,
    ENUM_TRADE_RETCODE,
    ENUM_TIMEFRAME,
    ENUM_CHECK_CODE,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
)


# Test for ENUM_TRADE_REQUEST_ACTIONS
def test_enum_trade_request_actions():
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL == mt5.TRADE_ACTION_DEAL
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING == mt5.TRADE_ACTION_PENDING
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_SLTP == mt5.TRADE_ACTION_SLTP
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_MODIFY == mt5.TRADE_ACTION_MODIFY
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_REMOVE == mt5.TRADE_ACTION_REMOVE
    assert ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_CLOSE_BY == mt5.TRADE_ACTION_CLOSE_BY


# Test for ENUM_POSITION_TYPE
def test_enum_position_type():
    assert ENUM_POSITION_TYPE.POSITION_TYPE_BUY == mt5.POSITION_TYPE_BUY
    assert ENUM_POSITION_TYPE.POSITION_TYPE_SELL == mt5.POSITION_TYPE_SELL


# Test for ENUM_POSITION_REASON
def test_enum_position_reason():
    assert ENUM_POSITION_REASON.POSITION_REASON_CLIENT == mt5.POSITION_REASON_CLIENT
    assert ENUM_POSITION_REASON.POSITION_REASON_EXPERT == mt5.POSITION_REASON_EXPERT
    assert ENUM_POSITION_REASON.POSITION_REASON_MOBILE == mt5.POSITION_REASON_MOBILE
    assert ENUM_POSITION_REASON.POSITION_REASON_WEB == mt5.POSITION_REASON_WEB


# Test for ENUM_DEAL_TYPE
def test_enum_deal_type():
    assert ENUM_DEAL_TYPE.DEAL_TYPE_BUY == mt5.DEAL_TYPE_BUY
    assert ENUM_DEAL_TYPE.DEAL_TYPE_SELL == mt5.DEAL_TYPE_SELL
    assert ENUM_DEAL_TYPE.DEAL_TYPE_BALANCE == mt5.DEAL_TYPE_BALANCE
    assert ENUM_DEAL_TYPE.DEAL_TYPE_CREDIT == mt5.DEAL_TYPE_CREDIT
    assert ENUM_DEAL_TYPE.DEAL_TYPE_CHARGE == mt5.DEAL_TYPE_CHARGE
    assert ENUM_DEAL_TYPE.DEAL_TYPE_CORRECTION == mt5.DEAL_TYPE_CORRECTION
    assert ENUM_DEAL_TYPE.DEAL_TYPE_BONUS == mt5.DEAL_TYPE_BONUS
    assert ENUM_DEAL_TYPE.DEAL_TYPE_COMMISSION == mt5.DEAL_TYPE_COMMISSION
    assert ENUM_DEAL_TYPE.DEAL_TYPE_COMMISSION_DAILY == mt5.DEAL_TYPE_COMMISSION_DAILY
    assert ENUM_DEAL_TYPE.DEAL_TYPE_COMMISSION_MONTHLY == mt5.DEAL_TYPE_COMMISSION_MONTHLY
    assert ENUM_DEAL_TYPE.DEAL_TYPE_COMMISSION_AGENT_DAILY == mt5.DEAL_TYPE_COMMISSION_AGENT_DAILY
    assert ENUM_DEAL_TYPE.DEAL_TYPE_COMMISSION_AGENT_MONTHLY == mt5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY
    assert ENUM_DEAL_TYPE.DEAL_TYPE_INTEREST == mt5.DEAL_TYPE_INTEREST
    assert ENUM_DEAL_TYPE.DEAL_TYPE_BUY_CANCELED == mt5.DEAL_TYPE_BUY_CANCELED
    assert ENUM_DEAL_TYPE.DEAL_TYPE_SELL_CANCELED == mt5.DEAL_TYPE_SELL_CANCELED
    assert ENUM_DEAL_TYPE.DEAL_DIVIDEND == mt5.DEAL_DIVIDEND
    assert ENUM_DEAL_TYPE.DEAL_DIVIDEND_FRANKED == mt5.DEAL_DIVIDEND_FRANKED
    assert ENUM_DEAL_TYPE.DEAL_TAX == mt5.DEAL_TAX


# Test for ENUM_DEAL_ENTRY
def test_enum_deal_entry():
    assert ENUM_DEAL_ENTRY.DEAL_ENTRY_IN == mt5.DEAL_ENTRY_IN
    assert ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT == mt5.DEAL_ENTRY_OUT
    assert ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT == mt5.DEAL_ENTRY_INOUT
    assert ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT_BY == mt5.DEAL_ENTRY_OUT_BY


# Test for ENUM_DEAL_REASON
def test_enum_deal_reason():
    assert ENUM_DEAL_REASON.DEAL_REASON_CLIENT == mt5.DEAL_REASON_CLIENT
    assert ENUM_DEAL_REASON.DEAL_REASON_MOBILE == mt5.DEAL_REASON_MOBILE
    assert ENUM_DEAL_REASON.DEAL_REASON_WEB == mt5.DEAL_REASON_WEB
    assert ENUM_DEAL_REASON.DEAL_REASON_EXPERT == mt5.DEAL_REASON_EXPERT
    assert ENUM_DEAL_REASON.DEAL_REASON_SL == mt5.DEAL_REASON_SL
    assert ENUM_DEAL_REASON.DEAL_REASON_TP == mt5.DEAL_REASON_TP
    assert ENUM_DEAL_REASON.DEAL_REASON_SO == mt5.DEAL_REASON_SO
    assert ENUM_DEAL_REASON.DEAL_REASON_ROLLOVER == mt5.DEAL_REASON_ROLLOVER
    assert ENUM_DEAL_REASON.DEAL_REASON_VMARGIN == mt5.DEAL_REASON_VMARGIN
    assert ENUM_DEAL_REASON.DEAL_REASON_SPLIT == mt5.DEAL_REASON_SPLIT


# Test for ENUM_ORDER_REASON
def test_enum_order_reason():
    assert ENUM_ORDER_REASON.ORDER_REASON_CLIENT == mt5.ORDER_REASON_CLIENT
    assert ENUM_ORDER_REASON.ORDER_REASON_MOBILE == mt5.ORDER_REASON_MOBILE
    assert ENUM_ORDER_REASON.ORDER_REASON_WEB == mt5.ORDER_REASON_WEB
    assert ENUM_ORDER_REASON.ORDER_REASON_EXPERT == mt5.ORDER_REASON_EXPERT
    assert ENUM_ORDER_REASON.ORDER_REASON_SL == mt5.ORDER_REASON_SL
    assert ENUM_ORDER_REASON.ORDER_REASON_TP == mt5.ORDER_REASON_TP
    assert ENUM_ORDER_REASON.ORDER_REASON_SO == mt5.ORDER_REASON_SO


# Test for ENUM_ORDER_TYPE
def test_enum_order_type():
    assert ENUM_ORDER_TYPE.ORDER_TYPE_BUY == mt5.ORDER_TYPE_BUY
    assert ENUM_ORDER_TYPE.ORDER_TYPE_SELL == mt5.ORDER_TYPE_SELL
    assert ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT == mt5.ORDER_TYPE_BUY_LIMIT
    assert ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT == mt5.ORDER_TYPE_SELL_LIMIT
    assert ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP == mt5.ORDER_TYPE_BUY_STOP
    assert ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP == mt5.ORDER_TYPE_SELL_STOP
    assert ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT == mt5.ORDER_TYPE_BUY_STOP_LIMIT
    assert ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT == mt5.ORDER_TYPE_SELL_STOP_LIMIT
    assert ENUM_ORDER_TYPE.ORDER_TYPE_CLOSE_BY == mt5.ORDER_TYPE_CLOSE_BY
    # Teste o método `get_order_name`
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_BUY") == "BUY"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_SELL") == "SELL"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_BUY_LIMIT") == "BUY_LIMIT"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_SELL_LIMIT") == "SELL_LIMIT"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_BUY_STOP") == "BUY_STOP"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_SELL_STOP") == "SELL_STOP"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_BUY_STOP_LIMIT") == "BUY_STOP_LIMIT"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_SELL_STOP_LIMIT") == "SELL_STOP_LIMIT"
    assert ENUM_ORDER_TYPE.get_order_name("ORDER_TYPE_CLOSE_BY") == "CLOSE_BY"


# Test for ENUM_ORDER_TYPE_MARKET
def test_enum_order_type_market():
    assert ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY == ENUM_ORDER_TYPE.ORDER_TYPE_BUY
    assert ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL == ENUM_ORDER_TYPE.ORDER_TYPE_SELL


# Test for ENUM_ORDER_TYPE_PENDING
def test_enum_order_type_pending():
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP
    assert ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT


# Test for ENUM_ORDER_TYPE_FILLING
def test_enum_order_type_filling():
    assert ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_FOK == mt5.ORDER_FILLING_FOK
    assert ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_IOC == mt5.ORDER_FILLING_IOC
    assert ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_BOC == mt5.ORDER_FILLING_BOC
    assert ENUM_ORDER_TYPE_FILLING.ORDER_FILLING_RETURN == mt5.ORDER_FILLING_RETURN


# Test for ENUM_ORDER_TYPE_TIME
def test_enum_order_type_time():
    assert ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC == mt5.ORDER_TIME_GTC
    assert ENUM_ORDER_TYPE_TIME.ORDER_TIME_DAY == mt5.ORDER_TIME_DAY
    assert ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED == mt5.ORDER_TIME_SPECIFIED
    assert ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY == mt5.ORDER_TIME_SPECIFIED_DAY


# Test for ENUM_ORDER_STATE
def test_enum_order_type_state():
    assert ENUM_ORDER_STATE.ORDER_STATE_STARTED == mt5.ORDER_STATE_STARTED
    assert ENUM_ORDER_STATE.ORDER_STATE_PLACED == mt5.ORDER_STATE_PLACED
    assert ENUM_ORDER_STATE.ORDER_STATE_CANCELED == mt5.ORDER_STATE_CANCELED
    assert ENUM_ORDER_STATE.ORDER_STATE_PARTIAL == mt5.ORDER_STATE_PARTIAL
    assert ENUM_ORDER_STATE.ORDER_STATE_FILLED == mt5.ORDER_STATE_FILLED
    assert ENUM_ORDER_STATE.ORDER_STATE_REJECTED == mt5.ORDER_STATE_REJECTED
    assert ENUM_ORDER_STATE.ORDER_STATE_EXPIRED == mt5.ORDER_STATE_EXPIRED
    assert ENUM_ORDER_STATE.ORDER_STATE_REQUEST_ADD == mt5.ORDER_STATE_REQUEST_ADD
    assert ENUM_ORDER_STATE.ORDER_STATE_REQUEST_MODIFY == mt5.ORDER_STATE_REQUEST_MODIFY
    assert ENUM_ORDER_STATE.ORDER_STATE_REQUEST_CANCEL == mt5.ORDER_STATE_REQUEST_CANCEL


# Test for ENUM_TRADE_RETCODE
def test_enum_trade_retcode():
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_REQUOTE == mt5.TRADE_RETCODE_REQUOTE
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_REJECT == mt5.TRADE_RETCODE_REJECT
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_CANCEL == mt5.TRADE_RETCODE_CANCEL
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_PLACED == mt5.TRADE_RETCODE_PLACED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE == mt5.TRADE_RETCODE_DONE
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_DONE_PARTIAL == mt5.TRADE_RETCODE_DONE_PARTIAL
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_ERROR == mt5.TRADE_RETCODE_ERROR
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_TIMEOUT == mt5.TRADE_RETCODE_TIMEOUT
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID == mt5.TRADE_RETCODE_INVALID
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_VOLUME == mt5.TRADE_RETCODE_INVALID_VOLUME
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_PRICE == mt5.TRADE_RETCODE_INVALID_PRICE
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_STOPS == mt5.TRADE_RETCODE_INVALID_STOPS
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_TRADE_DISABLED == mt5.TRADE_RETCODE_TRADE_DISABLED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_MARKET_CLOSED == mt5.TRADE_RETCODE_MARKET_CLOSED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_NO_MONEY == mt5.TRADE_RETCODE_NO_MONEY
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_PRICE_CHANGED == mt5.TRADE_RETCODE_PRICE_CHANGED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_PRICE_OFF == mt5.TRADE_RETCODE_PRICE_OFF
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_EXPIRATION == mt5.TRADE_RETCODE_INVALID_EXPIRATION
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_ORDER_CHANGED == mt5.TRADE_RETCODE_ORDER_CHANGED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_TOO_MANY_REQUESTS == mt5.TRADE_RETCODE_TOO_MANY_REQUESTS
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_NO_CHANGES == mt5.TRADE_RETCODE_NO_CHANGES
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_SERVER_DISABLES_AT == mt5.TRADE_RETCODE_SERVER_DISABLES_AT
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_CLIENT_DISABLES_AT == mt5.TRADE_RETCODE_CLIENT_DISABLES_AT
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_LOCKED == mt5.TRADE_RETCODE_LOCKED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_FROZEN == mt5.TRADE_RETCODE_FROZEN
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_FILL == mt5.TRADE_RETCODE_INVALID_FILL
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_CONNECTION == mt5.TRADE_RETCODE_CONNECTION
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_ONLY_REAL == mt5.TRADE_RETCODE_ONLY_REAL
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_LIMIT_ORDERS == mt5.TRADE_RETCODE_LIMIT_ORDERS
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_LIMIT_VOLUME == mt5.TRADE_RETCODE_LIMIT_VOLUME
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_ORDER == mt5.TRADE_RETCODE_INVALID_ORDER
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_POSITION_CLOSED == mt5.TRADE_RETCODE_POSITION_CLOSED
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_INVALID_CLOSE_VOLUME == mt5.TRADE_RETCODE_INVALID_CLOSE_VOLUME
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_CLOSE_ORDER_EXIST == mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_LIMIT_POSITIONS == mt5.TRADE_RETCODE_LIMIT_POSITIONS
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_REJECT_CANCEL == mt5.TRADE_RETCODE_REJECT_CANCEL
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_LONG_ONLY == mt5.TRADE_RETCODE_LONG_ONLY
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_SHORT_ONLY == mt5.TRADE_RETCODE_SHORT_ONLY
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_CLOSE_ONLY == mt5.TRADE_RETCODE_CLOSE_ONLY
    assert ENUM_TRADE_RETCODE.TRADE_RETCODE_FIFO_CLOSE == mt5.TRADE_RETCODE_FIFO_CLOSE


# Test for ENUM_TIMEFRAME
def test_enum_timeframe():
    assert ENUM_TIMEFRAME.TIMEFRAME_M1 == mt5.TIMEFRAME_M1
    assert ENUM_TIMEFRAME.TIMEFRAME_M2 == mt5.TIMEFRAME_M2
    assert ENUM_TIMEFRAME.TIMEFRAME_M3 == mt5.TIMEFRAME_M3
    assert ENUM_TIMEFRAME.TIMEFRAME_M4 == mt5.TIMEFRAME_M4
    assert ENUM_TIMEFRAME.TIMEFRAME_M5 == mt5.TIMEFRAME_M5
    assert ENUM_TIMEFRAME.TIMEFRAME_M6 == mt5.TIMEFRAME_M6
    assert ENUM_TIMEFRAME.TIMEFRAME_M10 == mt5.TIMEFRAME_M10
    assert ENUM_TIMEFRAME.TIMEFRAME_M15 == mt5.TIMEFRAME_M15
    assert ENUM_TIMEFRAME.TIMEFRAME_M20 == mt5.TIMEFRAME_M20
    assert ENUM_TIMEFRAME.TIMEFRAME_M30 == mt5.TIMEFRAME_M30
    assert ENUM_TIMEFRAME.TIMEFRAME_H1 == mt5.TIMEFRAME_H1
    assert ENUM_TIMEFRAME.TIMEFRAME_H2 == mt5.TIMEFRAME_H2
    assert ENUM_TIMEFRAME.TIMEFRAME_H3 == mt5.TIMEFRAME_H3
    assert ENUM_TIMEFRAME.TIMEFRAME_H4 == mt5.TIMEFRAME_H4
    assert ENUM_TIMEFRAME.TIMEFRAME_H6 == mt5.TIMEFRAME_H6
    assert ENUM_TIMEFRAME.TIMEFRAME_H8 == mt5.TIMEFRAME_H8
    assert ENUM_TIMEFRAME.TIMEFRAME_H12 == mt5.TIMEFRAME_H12
    assert ENUM_TIMEFRAME.TIMEFRAME_D1 == mt5.TIMEFRAME_D1
    assert ENUM_TIMEFRAME.TIMEFRAME_MN1 == mt5.TIMEFRAME_MN1


# Test for ENUM_CHECK_CODE
def test_enum_check_code():
    assert ENUM_CHECK_CODE.CHECK_RETCODE_OK == 1
    assert ENUM_CHECK_CODE.CHECK_RETCODE_ERROR == 2
    assert ENUM_CHECK_CODE.CHECK_RETCODE_RETRY == 3


# Test for ENUM_ACCOUNT_TRADE_MODE
def test_enum_account_trade_mode():
    assert ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO == mt5.ACCOUNT_TRADE_MODE_DEMO
    assert ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_CONTEST == mt5.ACCOUNT_TRADE_MODE_CONTEST
    assert ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_REAL == mt5.ACCOUNT_TRADE_MODE_REAL


# Test for ENUM_ACCOUNT_MARGIN_MODE
def test_enum_account_margin_mode():
    assert ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_NETTING == mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING
    assert ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_EXCHANGE == mt5.ACCOUNT_MARGIN_MODE_EXCHANGE
    assert ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING


# Test for ENUM_ACCOUNT_STOPOUT_MODE
def test_enum_account_stopout_mode():
    assert ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT == mt5.ACCOUNT_STOPOUT_MODE_PERCENT
    assert ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_MONEY == mt5.ACCOUNT_STOPOUT_MODE_MONEY

