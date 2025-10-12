# **Importations of libraries and dependencies**
import pytest  # Framework for tests
from unittest.mock import (
    patch,
)  # Tool for mocking function and method calls

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
    __process_account_update_data,  # Function to update account data in backtest
)


# **Account fixture for tests**
@pytest.fixture
def account():
    """
    Creates an account instance for testing.
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


# **Test: Verification of the Execution Order of Internal Functions**
def test_process_update_data_execution_order(account: Account):
    """
    Tests the execution order of internal functions in the `__process_update_data` function.

    Objective:
    - Ensure that internal functions are called in the correct order:
      1. `__backtest_position_apply_swap_to_positions`
      2. `__backtest_position_update_price_and_profit`
      3. `__backtest_account_update_margin`
      4. `__backtest_account_check_margin_call`
      5. `__backtest_account_process_stop_out`
    """
    account.login_backtest(
        balance=10000, leverage=100
    )  # Initializes the account with balance and leverage
    operation_handler = account.backtest_account_data.operation

    # **Mock of internal functions**
    with patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_apply_swap_to_positions",
        autospec=True,
    ) as mock_swap, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_position_update_price_and_profit",
        autospec=True,
    ) as mock_update_price, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_update_margin",
        autospec=True,
    ) as mock_update_margin, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_check_margin_call",
        autospec=True,
    ) as mock_check_margin_call, patch(
        "algo_trading.sources.MetaTrader5_source.backtest.backtest.__backtest_account_process_stop_out",
        autospec=True,
    ) as mock_process_stop_out:

        # **Avoid real execution**
        mock_swap.side_effect = None
        mock_update_price.side_effect = None
        mock_update_margin.side_effect = None
        mock_check_margin_call.side_effect = None
        mock_process_stop_out.side_effect = None

        # **Function call**
        __process_account_update_data(operation_handler)

        # **Verification of the execution order of internal functions**
        calls = [
            mock_swap.mock_calls[0],
            mock_update_price.mock_calls[0],
            mock_update_margin.mock_calls[0],
            mock_check_margin_call.mock_calls[0],
            mock_process_stop_out.mock_calls[0],
        ]

        # **Confirmation if functions were called in the correct order**
        assert calls == sorted(
            calls, key=lambda x: x[1]
        ), "Functions were not called in the expected order."
