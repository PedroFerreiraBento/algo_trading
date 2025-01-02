"""
Account Management for MetaTrader5

This module provides a high-level interface for managing live and backtest trading accounts in MetaTrader5.
It includes functionalities to log into live accounts, simulate backtest accounts, update account data,
and retrieve the current account's state.

Classes:
--------
- Account:
    Manages the interaction with MetaTrader5 accounts, both live and simulated backtest accounts.

Main Features:
--------------
1. **Live Account Management**:
    - Log into a live MetaTrader5 account using the `login_live` method.
    - Retrieve updated account information with `update_live_account_data`.
    - Log out from the current live session using `logout`.

2. **Backtest Account Simulation**:
    - Create a simulated backtest account using the `login_backtest` method.
    - Use simulated account data for strategy testing and experimentation.

Dependencies:
-------------
- MetaTrader5 Python module (imported as `mt5`).
- Custom models and utilities from `algo_trading.sources.MetaTrader5_source`.

Usage Example:
--------------
```python
from algo_trading.sources.MetaTrader5_source.account.account import Account

# Initialize account manager
account_manager = Account()

# Login to a live account
live_account_data = account_manager.login_live(
    login=123456, server="demo.server.com", password="password123"
)

# Update live account data
account_manager.update_live_account_data()

# Create a backtest account
backtest_account_data = account_manager.login_backtest(balance=10000)

# Logout from live account
account_manager.logout()
"""

import logging
from typing import Optional

import MetaTrader5 as mt5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,
    ENUM_ACCOUNT_TRADE_MODE,
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_ACCOUNT_MARGIN_MODE,
)
from algo_trading.sources.MetaTrader5_source.utils.metatrader import decorator_validate_mt5_connection


class Account:
    def __init__(self):
        self.live_account_data: Optional[MqlAccountInfo] = None
        self.backtest_account_data: Optional[MqlAccountInfo] = None

        # Configure logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def login_live(
        self,
        login: int,
        server: str,
        password: str,
        timeout: int = 60_000,
        portable: bool = False,
        path: str = "",
        update_on_login: bool = True,
    ) -> MqlAccountInfo:
        """Log into a live account."""
        if not mt5.initialize(
            path, login=login, server=server, password=password, timeout=timeout, portable=portable
        ):
            error_message = f"Login failed for live account. Error code = {mt5.last_error()}"
            mt5.shutdown()
            self.logger.error(error_message)
            raise ConnectionError(error_message)

        self.logger.info(f"Successfully logged in to live account #{login}")

        if update_on_login:
            self.update_live_account_data()

        return self.live_account_data

    def logout(self) -> None:
        """Log out from the current live session."""
        mt5.shutdown()
        self.logger.info("Successfully logged out.")

    @decorator_validate_mt5_connection
    def update_live_account_data(self) -> None:
        """Fetch updated live account data."""
        account_info = mt5.account_info()
        if not account_info:
            raise ConnectionError("Failed to retrieve live account data. No connection established.")

        self.live_account_data = MqlAccountInfo.parse_account(account_info)
        self.logger.info("Live account data successfully updated.")

    def login_backtest(
        self,
        balance: float = 5_000,
        leverage: int = 100,
        limit_orders: int = 200,
        margin_mode: ENUM_ACCOUNT_MARGIN_MODE = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
    ) -> MqlAccountInfo:
        """Simulate a backtest account."""
        if not self.live_account_data:
            error_message = "Cannot create a backtest account without first logging into a live account."
            self.logger.error(error_message)
            raise PermissionError(error_message)

        backtest_account = MqlAccountInfo(
            is_backtest_account=True,
            balance=balance,
            leverage=leverage,
            limit_orders=limit_orders,
            margin_mode=margin_mode,
            login=9999999,
            trade_mode=ENUM_ACCOUNT_TRADE_MODE.ACCOUNT_TRADE_MODE_DEMO,
            margin_so_mode=ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT,
            currency_digits=2,
            fifo_close=False,
            credit=0,
            profit=0,
            equity=balance,
            margin=0,
            margin_free=balance,
            margin_level=0,
            margin_so_call=50,
            margin_so_so=30,
            margin_initial=0,
            margin_maintenance=0,
            assets=0,
            liabilities=0,
            commission_blocked=0,
            trade_allowed=True,
            trade_expert=True,
            name="Backtest Account",
            server="Backtest Server",
            currency="USD",
            company="Backtest Company",
        )

        self.backtest_account_data = backtest_account
        self.logger.info("Backtest account successfully created.")
        return backtest_account