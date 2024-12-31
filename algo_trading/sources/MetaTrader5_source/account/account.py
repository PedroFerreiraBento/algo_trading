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

    @decorator_validate_mt5_connection
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

    def get_current_account_data(self, backtest: bool = False) -> Optional[MqlAccountInfo]:
        """Get data for the current account (live or backtest)."""
        if backtest:
            if not self.backtest_account_data:
                self.logger.warning("No backtest account is currently active.")
            return self.backtest_account_data
        else:
            if not self.live_account_data:
                self.logger.warning("No live account is currently active.")
            return self.live_account_data