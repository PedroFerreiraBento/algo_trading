# Importations of libraries and dependencies
import pytest
from datetime import datetime, timezone
import pandas as pd

# Importations of classes, enums and functions of MetaTrader 5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,
    ENUM_ORDER_TYPE_MARKET,
    ENUM_SYMBOL_CALC_MODE,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
    ENUM_SYMBOL_SWAP_MODE,
)
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_account_update_equity,
    __backtest_account_update_margin,
    __backtest_position_open,
    __backtest_position_update_price_and_profit,
    __backtest_position_apply_swap_to_positions,
    __backtest_account_check_margin_call,
    __backtest_account_process_stop_out,
)
from algo_trading.sources.MetaTrader5_source.account.account import Account


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


# **Test 1: Update of Equity with Buy Position**
def test_update_equity_with_buy_position(account: Account):
    """
    Tests the update of the equity of the account with an open buy position.

    Objective:
    - Ensure that the equity of the account is updated correctly based on the balance and profit of the position.
    - Consider the `simulated_spread` and `swap` in the equity update.
    """
    # **Initializes the backtest account with initial balance and leverage**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Market parameters configuration**
    symbol = "EURUSD"  # Currency pair
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.14  # Last candle closing price
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
            {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Last price candle before update**
    operation_handler.account_data.backtest_last_swap_date = (
        last_candle_time  # Last swap date
    )

    # **Opening a buy position**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=1,  # Volume da posição (1 lote)
        comment="Position 1 (Buy)",
    )

    # **Updates the last price candle with a new time and the same price to apply the swap**
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Friday, 23h
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
        name=last_candle_time,
    )

    # **Swap, profit and equity update**
    __backtest_position_apply_swap_to_positions(operation_handler)
    __backtest_position_update_price_and_profit(operation_handler)
    __backtest_account_update_equity(operation_handler)

    # **Calculated equity**
    account_equity = account.backtest_account_data.equity

    # **Expected equity calculation**
    position = account.backtest_account_data.positions[0]  # Open buy position
    expected_equity = (
        account.backtest_account_data.balance + position.profit + position.swap
    )  # Expected equity

    # **Verification of equity**
    assert (
        account_equity == expected_equity
    ), f"Equity incorrect. Expected: {expected_equity}, obtained: {account_equity}"


# **Test 2: Update of Margin with Sell Position**
def test_update_account_margin_with_sell_position(account: Account):
    """
    Tests the update of margin with an open sell position.

    Objective:
    - Verify if the used margin, free margin and margin level are calculated correctly based on the price and leverage.
    """
    # **Initializes the backtest account with initial balance and leverage**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Market parameters configuration**
    symbol = "EURUSD"  # Currency pair
    contract_size = 100_000  # 1 lote = 100.000 units of the base currency

    # **Last price candle before update**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Last candle closing price
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
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # Creates a DataFrame for the new record with the same format as the existing DataFrame
    new_row = pd.DataFrame([new_data], index=[symbol])

    # Concatenates the new record to the existing DataFrame
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    operation_handler.account_data.backtest_last_swap_date = (
        last_candle_time  # Last swap date
    )

    # **Opening a sell position**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Order type: sell
        volume=1,  # Position volume (1 lot)
        comment="Position 2 (Sell)",  # Comment identifying the position
    )

    # **Updates the last price candle with a new time and the same price to apply the swap**
    last_candle_time = datetime(
        2025, 1, 10, 23, 0, tzinfo=timezone.utc
    )  # Sexta-feira, 23h

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.12, "high": 1.15, "low": 1.11, "close": close_price},
        name=last_candle_time,
    )

    # **Margin update**
    __backtest_position_apply_swap_to_positions(
        operation_class=operation_handler
    )  # Calculates and updates used margin, free margin and margin level
    __backtest_position_update_price_and_profit(
        operation_class=operation_handler
    )  # Calculates and updates used margin, free margin and margin level
    __backtest_account_update_margin(
        operation_class=operation_handler
    )  # Calculates and updates used margin, free margin and margin level
    margin_used = account.backtest_account_data.margin  # Total used margin
    margin_free = (
        account.backtest_account_data.margin_free
    )  # Free margin (equity - used margin)
    margin_level = account.backtest_account_data.margin_level  # Margin level (%)

    # **Expected calculations**
    expected_margin = round(
        (contract_size * close_price) / account.backtest_account_data.leverage, 2
    )  # Used margin
    expected_margin_free = round(
        account.backtest_account_data.equity - expected_margin, 2
    )  # Free margin (equity - used margin)
    expected_margin_level = round(
        (account.backtest_account_data.equity / expected_margin) * 100, 3
    )  # Margin level (%)

    # **Verifications**
    assert (
        margin_used == expected_margin
    ), f"Used margin incorrect. Expected: {expected_margin}, obtained: {margin_used}"
    assert (
        margin_free == expected_margin_free
    ), f"Free margin incorrect. Expected: {expected_margin_free}, obtained: {margin_free}"
    assert (
        margin_level == expected_margin_level
    ), f"Margin level incorrect. Expected: {expected_margin_level}%, obtained: {margin_level}%"


# **Test 3: Update of Equity with Zero Profit**
def test_update_equity_with_zero_profit(account: Account):
    """
    Tests the update of equity with zero profit (no open positions).
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Equity update without open positions**
    __backtest_account_update_equity(operation_handler)
    equity = account.backtest_account_data.equity

    # Equity should be equal to balance when there is no profit/loss
    expected_equity = 10000.0
    assert (
        equity == expected_equity
    ), f"Equity incorrect with zero profit. Expected: {expected_equity}, obtained: {equity}"


# **Test 4: Update of Margin with No Open Positions**
def test_update_account_margin_with_no_positions(account: Account):
    """
    Tests the update of margin when there are no open positions.
    """
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation

    # **Margin update without open positions**
    __backtest_account_update_margin(operation_handler)

    margin_used = account.backtest_account_data.margin
    margin_free = account.backtest_account_data.margin_free
    margin_level = account.backtest_account_data.margin_level

    # **When there are no open positions, used margin should be zero**
    assert (
        margin_used == 0.0
    ), f"Used margin incorrect. Expected: 0.0, obtained: {margin_used}"
    assert (
        margin_free == 10000.0
    ), f"Free margin incorrect. Expected: 10000.0, obtained: {margin_free}"
    assert margin_level == float(
        "inf"
    ), f"Margin level incorrect. Expected: infinite, obtained: {margin_level}"


# **Test 5: Verification of Margin Call (`__check_margin_call`)**
def test_check_margin_call(account: Account, caplog):
    """
    Tests the verification of margin call based on the margin level and stopout mode configured.

    Objective:
    - Verify if a `margin call` warning is emitted correctly when the margin level falls below the configured limit (`margin_so_call`).
    - Test different stopout modes (`percent` and `money`) and validate margin warnings.
    - Ensure that the calculated margin level is exactly equal to the desired level.
    """
    # **Initializes the backtest account with initial balance and leverage**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Margin and stopout parameters configuration**
    account.backtest_account_data.margin_so_mode = (
        ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    )  # Stopout by percentage
    account.backtest_account_data.margin_so_call = (
        50.0  # Minimum allowed margin level (%)
    )

    # **Market parameters configuration**
    symbol = "EURUSD"  # Currency pair
    contract_size = 100_000  # 1 lot = 100.000 units of the base currency
    tick_size = 0.00001  # Price precision (1 pip = 0.00001)
    volume = 1  # Position volume (1 lot)

    # **Last price candle before position**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Closing price of the candle
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
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # **Creating a new DataFrame for the new record with the same format as the existing DataFrame**
    new_row = pd.DataFrame([new_data], index=[symbol])

    # **Concatenating the new record to the existing DataFrame**
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Opening a sell position**
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,  # Order type: sell
        volume=volume,  # Position volume (1 lot)
        comment="Position 1 (Sell)",  # Comment identifying the position
    )

    # **Simulation of a new price to trigger a margin call scenario**
    desired_level = (
        40.0  # Desired margin level to simulate the margin call alert (40%)
    )
    margin_used = (
        close_price * contract_size * volume
    ) / account.backtest_account_data.leverage  # Used margin
    spread = (
        account.backtest_account_data.simulated_spread * tick_size
    )  # Spread value in points

    # **Calculation of the next closing price to reach the desired margin level**
    next_price = round(
        ((desired_level * margin_used) / 100 - account.backtest_account_data.balance)
        / (-contract_size * volume)
        + close_price
        - spread,
        5,
    )

    # **Updating the last candle with the new closing price**
    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.10, "high": 1.13, "low": 1.08, "close": next_price},
        name=last_candle_time,
    )

    # **Margin and profit calculation update**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Applies swap to open positions
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Updates profit/loss based on the last price
    __backtest_account_update_margin(
        operation_handler
    )  # Updates used margin, free margin and margin level

    # **Capture logs of level `WARNING` to verify warning messages**
    with caplog.at_level("WARNING"):
        __backtest_account_check_margin_call(
            operation_handler
        )  # Verify if a margin call alert is emitted

    # **Expected margin level calculation**
    expected_margin_level = (
        operation_handler.account_data.margin_level
    )  # Current margin level

    # **Verification of margin level and margin call**
    assert (
        round(expected_margin_level, 3) == desired_level
    ), f"Margin level is not at the expected level. Expected: {desired_level}%, obtained: {expected_margin_level:.2f}%"
    assert "[MARGIN CALL]" in caplog.text, "Margin call alert was not registered."
    assert (
        f"[MARGIN CALL] Margin level below the limit ({expected_margin_level:.2f}%)."
        in caplog.text
    ), "Alert message is incorrect."


# **Test 6: Stop Out Processing (`__process_stop_out`)**
def test_process_stop_out(account: Account, caplog):
    """
    Tests the stop out processing, verifying the closing of positions when the margin level falls below the allowed limit.

    Objective:
    - Verify if positions are closed correctly in FIFO order or by the largest loss, depending on `fifo_close`.
    - Validate alert logs and margin level after the stop out process.
    - Verify that multiple stop out logs are generated correctly.
    """
    # **Initializes the backtest account with initial balance and leverage**
    account.login_backtest(balance=10000, leverage=100)
    operation_handler = account.backtest_account_data.operation
    account.backtest_account_data.simulated_spread = 4  # Simulated spread of 4 pips

    # **Stop out parameters configuration**
    account.backtest_account_data.margin_so_mode = (
        ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    )  # Stop out by percentage
    account.backtest_account_data.margin_so_call = 50.0  # Margin call: 50%
    account.backtest_account_data.margin_so_so = 20.0  # Stop out: 20%
    account.backtest_account_data.fifo_close = False  # Close positions by largest loss

    # **Market parameters configuration**
    symbol = "EURUSD"
    contract_size = 100_000  # 1 lot = 100.000 units of the base currency
    tick_size = 0.00001  # Price precision (1 pip = 0.00001)

    # **Creation of the last price candle**
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    close_price = 1.12  # Closing price
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
            {"open": 1.10, "high": 1.13, "low": 1.08, "close": close_price},
            name=last_candle_time,
        ),
    }

    # **Creating a new DataFrame for the new record with the same format as the existing DataFrame**
    new_row = pd.DataFrame([new_data], index=[symbol])

    # **Concatenating the new record to the existing DataFrame**
    operation_handler.backtest_symbols_data = pd.concat(
        [operation_handler.backtest_symbols_data, new_row]
    )

    # **Opening multiple positions**
    sell_volume = 2  # 2 lots in the SELL position
    buy_volume = 1  # 1 lot in the BUY position
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,
        volume=buy_volume,
        comment="Position 1 (Buy)",
    )
    __backtest_position_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_SELL,
        volume=sell_volume,
        comment="Position 2 (Sell)",
    )

    # **Simulation of critical price to trigger stop out**
    desired_level = 10  # Critical margin level (10%)
    balance = account.backtest_account_data.balance
    spread = account.backtest_account_data.simulated_spread * tick_size
    margin_used_sell = (
        close_price * contract_size * sell_volume
    ) / account.backtest_account_data.leverage
    margin_used_buy = (
        (close_price + spread) * contract_size * buy_volume
    ) / account.backtest_account_data.leverage
    margin_used = margin_used_buy + margin_used_sell

    numerator = (
        (desired_level * margin_used / 100)
        - balance
        + (margin_used_buy * account.backtest_account_data.leverage)
        + (contract_size * sell_volume * (spread - close_price))
    )
    denominator = contract_size * (buy_volume - sell_volume)
    critical_price = numerator / denominator

    operation_handler.backtest_symbols_data.at[symbol, "last_candle"] = pd.Series(
        {"open": 1.10, "high": 1.13, "low": 1.08, "close": critical_price},
        name=last_candle_time,
    )

    # **Profit, margin and stop out verification**
    __backtest_position_apply_swap_to_positions(
        operation_handler
    )  # Applies swap to open positions
    __backtest_position_update_price_and_profit(
        operation_handler
    )  # Updates profit of open positions
    __backtest_account_update_margin(
        operation_handler
    )  # Updates used margin, free margin and margin level

    # **Capture logs to verify alert messages and stop out events**
    with caplog.at_level("INFO"):
        __backtest_account_process_stop_out(operation_handler)

    # **Log verification and status after stop out**
    stop_out_logs = [
        record.message for record in caplog.records if "[STOP OUT]" in record.message
    ]
    final_logs = [
        record.message
        for record in caplog.records
        if "[STOP OUT FINISHED]" in record.message
    ]

    # **Main verifications**
    assert len(stop_out_logs) > 0, "No stop out alert was registered."
    assert (
        len(final_logs) == 1
    ), "The final stop out log was not registered correctly."
    assert (
        account.backtest_account_data.margin_level
        > account.backtest_account_data.margin_so_so
    ), "The margin level was not restored after the stop out."
    assert (
        account.backtest_account_data.margin_level == 30
    ), "The restored margin level is not as expected (30%)."
    assert (
        len(account.backtest_account_data.positions) == 1
    ), "Not all positions were closed correctly during the stop out."

    # **Account value updates verification**
    assert (
        account.backtest_account_data.equity == 336.01
    ), "Equity updated incorrectly."
    assert (
        account.backtest_account_data.profit == 9648.0
    ), "Profit updated incorrectly."
    assert (
        account.backtest_account_data.balance == -9311.99
    ), "Balance updated incorrectly."
    assert (
        account.backtest_account_data.margin == 1120.04
    ), "Used margin updated incorrectly."
    assert (
        account.backtest_account_data.margin_free == -784.03
    ), "Free margin updated incorrectly."

    # **Stop out message verification**
    assert (
        "Margin level reached! Starting position closing..."
        in stop_out_logs[0]
    ), "Initial stop out alert message is incorrect."
    assert (
        "Margin level restored after position closing." in caplog.text
    ), "Margin restoration after stop out alert message was not registered."
    assert (
        "Balance" in final_logs[0] and "Equity" in final_logs[0]
    ), "Final stop out log does not contain balance and equity information."
