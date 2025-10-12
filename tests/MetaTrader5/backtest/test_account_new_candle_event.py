# **Importations of Libraries and Dependencies**
import pytest  # Framework of tests
from unittest.mock import patch  # Tool for mocking function and method calls

# **Importation of Account class (MetaTrader 5 account management)**
from algo_trading.sources.MetaTrader5_source.account.account import Account

# **Importation of classes, enums and functions of MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Account information model (e.g.: balance, leverage, profit)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for account operation mode (real/demo)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stopout mode (percent/fix value)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for margin calculation mode (hedge/reduction)
)

# **Importation of backtest functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __process_account_new_candle_event,  # Main function to be tested
)

# **Account fixture for tests**
@pytest.fixture
def account():
    """
    Fixture that creates an account instance for testing.
    Simulates login to a live account and reinitializes the account in backtest mode.
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


# **Test 1: Verification of Function Execution Order**
def test_process_account_new_candle_event_execution_order(account: Account):
    """
    Tests the order of execution of internal functions in the `__process_account_new_candle_event` function.

    Objective:
    - Ensure that internal functions are called in the correct order:
      1. `__process_account_after_candle_event`
      2. `__process_account_update_data`
    """
    account.login_backtest(balance=10000, leverage=100)  # Initializes the account with balance and leverage
    operation_handler = account.backtest_account_data.operation

    # **Mock of internal functions**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_after_candle_event", autospec=True) as mock_after_candle_event, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_update_data", autospec=True) as mock_update_data:

        # **Avoid real execution**
        mock_after_candle_event.side_effect = None
        mock_update_data.side_effect = None

        # **Function call**
        __process_account_new_candle_event(operation_handler)

        # **Verification of function execution order**
        calls = [
            mock_after_candle_event.mock_calls[0],
            mock_update_data.mock_calls[0],
        ]

        # **Confirmation if functions were called in the correct order**
        assert calls == sorted(calls, key=lambda x: x[1]), "Functions were not called in the expected order."


# **Test 2: Verification of Function Calls**
def test_process_account_new_candle_event_functions_called(account: Account):
    """
    Tests if all internal functions are called in the `__process_account_new_candle_event` function.

    Objective:
    - Ensure that each internal function is called at least once.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Mock of internal functions**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_after_candle_event", autospec=True) as mock_after_candle_event, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__process_account_update_data", autospec=True) as mock_update_data:

        # **Function call**
        __process_account_new_candle_event(operation_handler)

        # **Verification of calls**
        mock_after_candle_event.assert_called_once(), "The function `__process_account_after_candle_event` was not called."
        mock_update_data.assert_called_once(), "The function `__process_account_update_data` was not called."

