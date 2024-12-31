import logging
from typing import List, Dict, Optional, Union, TYPE_CHECKING
from datetime import datetime
from algo_trading.data_storage import DataStorage
import pandas as pd

# Importa apenas durante a checagem de tipos
if TYPE_CHECKING:
    from .position_handler import Position, PositionHandler, Order

logger = logging.getLogger(__name__)


class AccountHandler:
    HISTORICAL_ORDERS_FILE = "historical_orders.pkl"
    CLOSED_POSITIONS_FILE = "closed_positions.pkl"

    def __init__(
        self, base_currency: str, initial_balance: float, leverage: float
    ) -> None:
        """
        Initializes the AccountHandler with the base currency, initial balance, and leverage.

        Args:
            base_currency (str): The account's base currency (e.g., USD, EUR).
            initial_balance (float): The initial balance of the account.
            leverage (float): The leverage allowed on the account.
        """
        # Base Account Data -----------------------------------------------------------------------
        # The currency in which the account balance is denominated (e.g., USD, EUR).
        self.base_currency = base_currency

        # The initial amount of money in the account.
        self.initial_balance = initial_balance

        # The current available balance in the account, starting as the initial balance.
        self.current_balance = initial_balance

        # The leverage factor, determining the maximum position size relative to the balance.
        self.leverage = leverage

        # Margins ---------------------------------------------------------------------------------
        # The total margin currently being used for open positions.
        self.total_margin = 0.0

        # The free margin available for opening new positions or absorbing losses.
        self.free_margin = initial_balance

        # The ratio of equity to margin, expressed as a percentage.
        self.margin_level = None

        # PnL (Profit and Loss) -------------------------------------------------------------------
        # The realized profit or loss from closed positions.
        self.realized_pnl = 0.0

        # The unrealized profit or loss from currently open positions.
        self.unrealized_pnl = 0.0

        # Capital Total ---------------------------------------------------------------------------
        # The total equity in the account (balance + unrealized PnL).
        self.equity = initial_balance

        # Exposição -------------------------------------------------------------------------------
        # The total exposure in the market
        # (sum of all open position volumes multiplied by their entry prices).
        self.current_exposure = 0.0

        # Custos e Taxas --------------------------------------------------------------------------
        # The total accumulated fees from swap operations (overnight interest).
        self.swap_fees = 0.0

        # The total accumulated commissions paid for opening and closing positions.
        self.commissions = 0.0

        # Drawdowns -------------------------------------------------------------------------------
        # The maximum drawdown observed during a single trading day.
        self.daily_drawdown = 0.0

        # The largest overall loss from a peak in equity.
        self.max_drawdown = 0.0

        # Históricos ------------------------------------------------------------------------------
        # A list of all historical orders, including executed and canceled orders.
        self.historical_orders: List[Dict] = []

        # A list of all closed positions with details like profit or loss.
        self.closed_positions: List[Dict] = []

        # A list of historical exchange rates for tracking price changes.
        self.exchange_rate_history: List[Dict] = []

        # Performance -----------------------------------------------------------------------------
        # The proportion of profitable trades to total trades.
        self.win_rate = 0.0

        # The ratio of total profit to total loss from closed positions.
        self.profit_factor = 0.0

        # The average profit per winning trade.
        self.average_profit = 0.0

        # The average loss per losing trade.
        self.average_loss = 0.0

        # Sessões ---------------------------------------------------------------------------------
        # A dictionary tracking statistics for different trading sessions (e.g., London, New York).
        self.session_stats: Dict[str, Dict] = {}

        # Operações Automáticas -------------------------------------------------------------------
        # A log of automated trading operations performed by the system.
        self.auto_operations_log: List[Dict] = []

        # Position Handler ------------------------------------------------------------------------
        self.position_handler: "PositionHandler" = None

    # Gerenciamento de Margens
    def calculate_required_margin(self, volume: float, price: float) -> float:
        """
        Calculates the required margin for a given volume and price.

        Args:
            volume (float): The trading volume.
            price (float): The price of the instrument.

        Returns:
            float: The required margin.
        """
        return volume * price / self.leverage

    def update_margin_on_position_change(self, margin_change: float) -> None:
        """
        Updates the total and free margins based on a margin change.

        Args:
            margin_change (float): The change in margin (positive or negative).
        """
        self.total_margin += margin_change
        self.free_margin = self.equity - self.total_margin
        self.calculate_margin_level()

    def calculate_margin_level(self) -> None:
        """
        Calculates and updates the margin level.
        """
        if self.total_margin > 0:
            self.margin_level = (self.equity / self.total_margin) * 100
        else:
            self.margin_level = None

    # Lucro e Prejuízo
    def update_realized_pnl(self, profit_or_loss: float) -> None:
        """
        Updates the realized PnL and adjusts the current balance.

        Args:
            profit_or_loss (float): The realized profit or loss.
        """
        self.realized_pnl += profit_or_loss
        self.current_balance += profit_or_loss
        self.update_equity()

    def calculate_unrealized_pnl(
        self, current_prices: Dict[str, Dict[str, float]]
    ) -> None:
        
        """
        Calculates the unrealized PnL based on active positions and current prices, considering bid/ask prices.

        Args:
            current_prices (Dict[str, Dict[str, float]]): Dictionary of current prices for pairs. Each pair should include 'bid' and/or 'ask'.
        """
        
        self._validate_position_handler_set()
                
        for position in self.position_handler.position:
            position: "Position" 
            symbol = position.symbol
            entry_price = position.open_price
            volume = position.quantity
            position_type = position.type

            pnl = 0
            if symbol in current_prices and (
                (
                    "bid" in current_prices[symbol]
                    and "ask" in current_prices[symbol]
                ) or (
                    "close" in current_prices[symbol]
                )
            ):
                pnl += current_prices[symbol].get("bid") if position_type == "BUY" else current_prices[symbol].get("ask")
                if position_type == "BUY":
                    # Use the bid price for BUY positions
                    pnl += (
                        current_prices[symbol].get("bid", entry_price) - entry_price
                    ) * volume
                elif position_type == "SELL":
                    # Use the ask price for SELL positions
                    pnl += (
                        entry_price - current_prices[symbol].get("ask", entry_price)
                    ) * volume
            else:
                raise ValueError("Missing current prices")

        self.unrealized_pnl = pnl
        self.update_equity()
    
    def calculate_unrealized_pnl(
        self,
        current_prices: Dict[str, Dict[str, float]],
    ) -> float:
        """
        Converts PnL to the base currency using cross rates if necessary, with support for simulated spreads.

        Args:
            pnl (float): The PnL in the position's quote currency.
            symbol (str): The trading pair symbol (e.g., EURGBP).
            current_prices (Dict[str, Dict[str, float]]): Current prices for each symbol, including 'bid', 'ask', or 'close'.
            intermediate_currency (str): The default intermediate currency for cross conversions (default is 'USD').
            use_simulated_spread (bool): Whether to apply a simulated spread when bid/ask prices are unavailable.
            simulated_spreads (Optional[Dict[str, float]]): A dictionary mapping symbols to their respective simulated spread values.
            taxes_per_conversion (float): Fixed tax amount per conversion.
            commission_per_conversion (float): Fixed commission amount per conversion.

        Returns:
            float: The PnL converted to the base currency.
        """
        
        
        pair_base, pair_quote = symbol[:3], symbol[3:]

        # Case 1: PnL is already in base currency
        if pair_quote == self.base_currency:
            return pnl

        # Case 2: Direct conversion
        if pair_base == self.base_currency:
            return convert_directly(pnl, symbol, current_prices, to_base=True, use_simulated_spread=use_simulated_spread, simulated_spreads=simulated_spreads)

        # Case 3: Cross currency conversion
        cross_pnl = convert_cross_currency(
            pnl,
            pair_quote,
            self.base_currency,
            current_prices,
            intermediate_currency,
            use_simulated_spread,
            simulated_spreads,
        )

        # Apply taxes and commissions
        cross_pnl -= taxes_per_conversion
        cross_pnl -= commission_per_conversion

        return cross_pnl

    # Capital Total
    def update_equity(self) -> None:
        """
        Updates the equity based on the current balance and unrealized PnL.
        """
        self.equity = self.current_balance + self.unrealized_pnl

    # Exposição
    def calculate_exposure(self, active_positions: List[Dict]) -> None:
        """
        Calculates the total market exposure for active positions.

        Args:
            active_positions (List[Dict]): List of active positions.
        """
        self.current_exposure = sum(
            pos["volume"] * pos["entry_price"] for pos in active_positions
        )

    # Taxas e Custos
    def add_swap_fee(self, position_id: int, swap_value: float) -> None:
        """
        Adds a swap fee to the account's accumulated swap fees.

        Args:
            position_id (int): The ID of the position.
            swap_value (float): The swap fee value.
        """
        self.swap_fees += swap_value
        logger.info(f"Swap fee added for position {position_id}: {swap_value}")

    def add_commission(self, order_id: int, commission_value: float) -> None:
        """
        Adds a commission to the account's accumulated commissions.

        Args:
            order_id (int): The ID of the order.
            commission_value (float): The commission value.
        """
        self.commissions += commission_value
        logger.info(f"Commission added for order {order_id}: {commission_value}")

    # Drawdowns
    def calculate_daily_drawdown(self, initial_daily_balance: float) -> None:
        """
        Calculates the daily drawdown based on the initial daily balance.

        Args:
            initial_daily_balance (float): The initial balance at the start of the day.
        """
        self.daily_drawdown = initial_daily_balance - self.current_balance

    def calculate_max_drawdown(self, max_equity: float) -> None:
        """
        Calculates the maximum drawdown observed so far.

        Args:
            max_equity (float): The maximum equity observed.
        """
        drawdown = max_equity - self.equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

    # Históricos
    def record_order(self, order: Dict) -> None:
        """
        Records an order in the account's order history.

        Args:
            order (Dict): The order details.
        """
        self.historical_orders.append(order)
        logger.info(f"Order recorded: {order}")

    def record_position(self, position: Dict) -> None:
        """
        Records a closed position in the account's position history.

        Args:
            position (Dict): The position details.
        """
        self.closed_positions.append(position)
        logger.info(f"Position recorded: {position}")

    def add_exchange_rate(
        self, pair: str, rate: float, timestamp: Optional[datetime] = None
    ) -> None:
        """
        Adds an exchange rate to the account's exchange rate history.

        Args:
            pair (str): The currency pair.
            rate (float): The exchange rate.
            timestamp (Optional[datetime]): The timestamp of the rate. Defaults to now.
        """
        self.exchange_rate_history.append(
            {"pair": pair, "rate": rate, "timestamp": timestamp or datetime.now()}
        )
        logger.info(f"Exchange rate added for {pair}: {rate}")

    def get_exchange_rate_history(self, pair: Optional[str] = None) -> List[Dict]:
        """
        Retrieves the exchange rate history, optionally filtered by pair.

        Args:
            pair (Optional[str]): The currency pair to filter by.

        Returns:
            List[Dict]: The filtered or complete exchange rate history.
        """
        if pair:
            return [
                entry for entry in self.exchange_rate_history if entry["pair"] == pair
            ]
        return self.exchange_rate_history

    # Performance de Posições
    def calculate_win_rate(self) -> None:
        """
        Calculates the win rate based on closed positions.
        """
        winning_positions = [p for p in self.closed_positions if p["profit"] > 0]
        self.win_rate = (
            len(winning_positions) / len(self.closed_positions)
            if self.closed_positions
            else 0.0
        )

    def calculate_profit_factor(self) -> None:
        """
        Calculates the profit factor based on closed positions.
        """
        total_profit = sum(
            p["profit"] for p in self.closed_positions if p["profit"] > 0
        )
        total_loss = abs(
            sum(p["profit"] for p in self.closed_positions if p["profit"] < 0)
        )
        self.profit_factor = (
            total_profit / total_loss if total_loss > 0 else float("inf")
        )

    def generate_performance_report(self) -> Dict[str, Union[float, None]]:
        """
        Generates a performance report with key metrics.

        Returns:
            Dict[str, Union[float, None]]: The performance report.
        """
        return {
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "average_profit": self.average_profit,
            "average_loss": self.average_loss,
        }

    # Sessões de Negociação
    def track_session_activity(self, session_name: str, stats: Dict) -> None:
        """
        Tracks activity for a specific trading session.

        Args:
            session_name (str): The name of the session (e.g., London, New York).
            stats (Dict): Statistics for the session.
        """
        if session_name not in self.session_stats:
            self.session_stats[session_name] = {"trades": 0, "profit": 0.0, "loss": 0.0}
        self.session_stats[session_name]["trades"] += stats.get("trades", 0)
        self.session_stats[session_name]["profit"] += stats.get("profit", 0.0)
        self.session_stats[session_name]["loss"] += stats.get("loss", 0.0)

    def get_session_summary(self, session_name: str) -> Dict[str, Union[int, float]]:
        """
        Retrieves a summary of statistics for a specific trading session.

        Args:
            session_name (str): The name of the session.

        Returns:
            Dict[str, Union[int, float]]: The session summary.
        """
        return self.session_stats.get(session_name, {})

    # Registro de Operações Automáticas
    def log_auto_operation(self, event: Dict) -> None:
        """
        Logs an automatic operation in the account.

        Args:
            event (Dict): Details of the automatic operation.
        """
        self.auto_operations_log.append(event)
        logger.info(f"Automatic operation logged: {event}")

    def get_auto_operations_log(self) -> List[Dict]:
        """
        Retrieves the log of automatic operations.

        Returns:
            List[Dict]: The log of automatic operations.
        """
        return self.auto_operations_log

    # Monitoramento de Risco
    def check_margin_call(self) -> bool:
        """
        Checks if a margin call should be triggered.

        Returns:
            bool: True if margin call conditions are met, False otherwise.
        """
        if self.margin_level and self.margin_level < 100:
            logger.warning("Margin call triggered! Free margin critically low.")
            return True
        return False

    def trigger_stop_out(self) -> bool:
        """
        Checks if a stop out should be triggered.

        Returns:
            bool: True if stop out conditions are met, False otherwise.
        """
        if self.margin_level and self.margin_level < 50:
            logger.critical("Stop out triggered! Positions are being liquidated.")
            return True
        return False


    # Main Operations -----------------------------------------------------------------------------
    # Update
    def update(
        self,
        current_prices: Dict[str, Dict[str, float]],
    ) -> None:
        """
        Updates the account state with the latest active positions and market prices.

        Args:
            current_prices (Dict[str, Dict[str, float]]): Dictionary of current prices for pairs. Each pair should include:
                - 'bid': float -> The current bid price.
                - 'ask': float -> The current ask price.
        """
        # Validate attribute set
        self._validate_position_handler_set()
        
        # Recalculate unrealized PnL
        self.calculate_unrealized_pnl(current_prices)

        # Recalculate exposure
        self.calculate_exposure()

        # Recalculate total margin
        total_margin = 0.0
        for position in self.position_handler.positions:
            if "margin" in position:
                total_margin += position["margin"]
            else:
                # Calculate margin dynamically if not provided
                price = (
                    current_prices[position["pair"]]["ask"]
                    if position["type"] == "BUY"
                    else current_prices[position["pair"]]["bid"]
                )
                margin = self.calculate_required_margin(position["volume"], price)
                total_margin += margin

        self.total_margin = total_margin
        self.free_margin = self.equity - self.total_margin

        # Recalculate margin level
        self.calculate_margin_level()

        # Calculate session stats (if relevant)
        now = datetime.now()
        session_name = self.get_session_name(
            now
        )  # Define logic to get session name (e.g., "London")
        session_stats = self.calculate_session_stats(session_name, now)

        logger.info(f"Session stats for {session_name}: {session_stats}")

        # Risk checks
        if self.check_margin_call():
            logger.warning("Margin call conditions met.")
        if self.trigger_stop_out():
            logger.critical("Stop out triggered. Liquidating positions.")

        logger.info("Account state updated successfully.")

        # Read and save files -------------------------------------------------------------------------

    # Reset
    def reset(self) -> None:
        """
        Resets all account parameters to their initial state.
        """
        # Reset Account Paramenters
        self._reset_account()
        self._reset_positions()
    
    def _reset_account(self) -> None:
        """
        Resets all account parameters to their initial state.
        """
        # Reset Account Paramenters
        self.current_balance = self.initial_balance
        self.total_margin = 0.0
        self.free_margin = self.initial_balance
        self.margin_level = None
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.equity = self.initial_balance
        self.current_exposure = 0.0
        self.swap_fees = 0.0
        self.commissions = 0.0
        self.daily_drawdown = 0.0
        self.max_drawdown = 0.0
        self.historical_orders.clear()
        self.closed_positions.clear()
        self.exchange_rate_history.clear()
        self.win_rate = 0.0
        self.profit_factor = 0.0
        self.average_profit = 0.0
        self.average_loss = 0.0
        self.session_stats.clear()
        self.auto_operations_log.clear()
        logger.info("Account has been reset to its initial state.")
    
    def _reset_positions(self) -> None:
        # Validate attribute is already set
        self._validate_position_handler_set()
        
        # Clear all in-memory data
        self.position_handler.positions.clear()
        self.position_handler.pending_orders.clear()
        self.position_handler._order_counter = 1
        self.position_handler._position_counter = 1

        # Remove historical files
        for file_path in [self.HISTORICAL_ORDERS_FILE, self.CLOSED_POSITIONS_FILE]:
            DataStorage.remove_file(file_path)

        logger.info(
            "PositionHandler has been reset. All positions, orders, and historical data have been cleared."
        )        

    def _validate_position_handler_set(self) -> None:
        if not self.position_handler:
            raise ValueError("PositionHandler has not been set for this account.")

    # File Interaction ----------------------------------------------------------------------------
    def get_historical_orders(self) -> List["Order"]:
        try:
            data = DataStorage.read_pickle(self.HISTORICAL_ORDERS_FILE)
            return data if data else []
        except Exception as e:
            logger.error(f"Failed to load historical orders: {e}")
            return []

    def get_closed_positions(self) -> List["Order"]:
        try:
            data = DataStorage.read_pickle(self.CLOSED_POSITIONS_FILE)
            # Se data for None ou um DataFrame vazio, retorna uma lista vazia
            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                return pd.DataFrame()

            return data
        except Exception as e:
            logger.error(f"Failed to load closed positions: {e}")
            return []

    def _save_historical_orders(self, order: "Order"):
        self._save_to_file(order, self.HISTORICAL_ORDERS_FILE)

    def _save_closed_positions(self, position: "Position"):
        self._save_to_file(position, self.CLOSED_POSITIONS_FILE)

    def _save_to_file(self, obj: Union["Order", "Position"], file_path: str) -> None:
        """
        Append an object (Order or Position) to a file using DataStorage.
        Args:
            obj (Union[Order, Position]): The object to save.
            file_path (str): The file path where the object should be saved.
        """
        df_obj = pd.DataFrame([obj.__dict__])
        DataStorage.append_to_file(df_obj, file_path, file_type="pickle")
        logger.info(f"Appended {type(obj).__name__} {obj.__dict__} to {file_path}")
