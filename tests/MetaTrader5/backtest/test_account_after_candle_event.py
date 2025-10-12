# **Imports of  required Libraries and Dependencies**
import pytest  # Framework of tests
from unittest.mock import patch  # Tool of mock to simulate function and method calls

# **Importation of the Account class (account management of MetaTrader 5)**
from algo_trading.sources.MetaTrader5_source.account.account import Account

# **Importation of classes, enums and functions of MetaTrader 5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Account information model (e.g. balance, leverage, profit)
    ENUM_ACCOUNT_TRADE_MODE,  # Enum for account operation mode (real/demo)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum for stopout mode (percent/fix value)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum for margin calculation mode (hedge/reduction)
)

# **Importation of backtest functions**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __process_account_after_candle_event,  # Main function to be tested
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

# **Test: Verification of the Order of Execution of Internal Functions in `__process_account_after_candle_event`**
def test_process_account_after_candle_event_execution_order(account: Account):
    """
    Tests the order of execution of internal functions in the `__process_account_after_candle_event` function.

    Objective:
    - Ensure that internal functions are called in the correct order:
      1. `__backtest_pending_order_check_triggered`
      2. `__backtest_pending_order_check_expiration`
      3. `__backtest_position_check_stop_loss_reached`
      4. `__backtest_position_check_take_profit_reached`
    """
    account.login_backtest(balance=10000, leverage=100)  # Initializes the account with balance and leverage
    operation_handler = account.backtest_account_data.operation

    # **Mock of internal functions**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_triggered", autospec=True) as mock_triggered, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_expiration", autospec=True) as mock_expiration, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_stop_loss_reached", autospec=True) as mock_stop_loss, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_take_profit_reached", autospec=True) as mock_take_profit:

        # **Avoid real execution**
        mock_triggered.side_effect = None
        mock_expiration.side_effect = None
        mock_stop_loss.side_effect = None
        mock_take_profit.side_effect = None

        # **Call of the main function**
        __process_account_after_candle_event(operation_handler)

        # **Verification of the order of execution of internal functions**
        calls = [
            mock_triggered.mock_calls[0],
            mock_expiration.mock_calls[0],
            mock_stop_loss.mock_calls[0],
            mock_take_profit.mock_calls[0],
        ]

        # **Confirmation if functions were called in the correct order**
        assert calls == sorted(calls, key=lambda x: x[1]), "Functions were not called in the expected order."


# **Test: Verification of Function Activation**
def test_process_account_after_candle_event_functions_called(account: Account):
    """
    Tests if all internal functions are called in the `__process_account_after_candle_event` function.

    Objective:
    - Ensure that each internal function is called at least once.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Mock of internal functions**
    with patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_triggered", autospec=True) as mock_triggered, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_pending_order_check_expiration", autospec=True) as mock_expiration, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_stop_loss_reached", autospec=True) as mock_stop_loss, \
         patch("algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_check_take_profit_reached", autospec=True) as mock_take_profit:

        # **Call of the main function**
        __process_account_after_candle_event(operation_handler)

        # **Verification of calls**
        mock_triggered.assert_called_once(), "The function `__backtest_pending_order_check_triggered` was not called."
        mock_expiration.assert_called_once(), "The function `__backtest_pending_order_check_expiration` was not called."
        mock_stop_loss.assert_called_once(), "The function `__backtest_position_check_stop_loss_reached` was not called."
        mock_take_profit.assert_called_once(), "The function `__backtest_position_check_take_profit_reached` was not called."


