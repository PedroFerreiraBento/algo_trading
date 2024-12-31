import logging
from typing import List, Dict, Optional, Union
import pandas as pd
from enum import Enum
from algo_trading.data_storage import DataStorage
from algo_trading.account_handler import AccountHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Position ----------------------------------------------------------------------------------------
class PositionType(Enum):
    BUY = "BUY"  # Represents a buy position
    SELL = "SELL"  # Represents a sell position

class OrderType(Enum):
    BUY = 1  # Represents a buy order
    SELL = 2  # Represents a sell order
    MODIFY = 3  # Represents a modification to an existing position
    CLOSE = 4  # Represents closing an active position

class PositionStatus(Enum):
    ACTIVE = 1  # Position is currently active
    CLOSED = 2  # Position has been closed

# Position ----------------------------------------------------------------------------------------
class Position:
    """
    Represents an active position in the market.
    """

    def __init__(
        self,
        position_id: int,
        type: PositionType,
        open_price: float,
        quantity: float,
        symbol: str,  # Symbol of the asset or currency pair
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        open_time: Optional[pd.Timestamp] = None,
    ):
        self.position_id = position_id
        self.type = type
        self.open_price = open_price
        self.quantity = quantity
        self.symbol = symbol  # Store the asset or currency pair symbol
        self.sl = sl
        self.tp = tp
        self.open_time = open_time or pd.Timestamp.now()
        self.status = PositionStatus.ACTIVE
        self.close_price = None
        self.close_time = None
        self.reason = None  # Add reason attribute for closures

    def close(
        self,
        close_price: float,
        close_time: Optional[pd.Timestamp] = None,
        reason: Optional[str] = None,
    ):
        """
        Close this position and calculate profit or loss.
        Args:
            close_price (float): Price at which the position was closed.
            close_time (Optional[pd.Timestamp]): Timestamp when the position was closed.
            reason (Optional[str]): Reason for closing the position.
        """
        if self.status != PositionStatus.ACTIVE:
            logger.warning(f"Position #{self.position_id} is already closed.")
            return

        self.close_price = close_price
        self.close_time = close_time or pd.Timestamp.now()

        self.status = PositionStatus.CLOSED
        self.reason = reason  # Store the reason for closure
        logger.info(
            f"Position #{self.position_id} on {self.symbol} closed, Reason: {reason}"
        )

# Order -------------------------------------------------------------------------------------------
class OrderStatus(Enum):
    PENDING = 1  # Order is pending execution
    EXECUTED = 2  # Order has been executed
    CANCELLED = 3  # Order has been cancelled

class Order:
    """
    Represents an order in the system, which can be used to open, close, or modify positions.
    """

    def __init__(
        self,
        order_id: int,
        type: OrderType,
        price: float,
        quantity: float,
        symbol: str,  # Symbol of the asset or currency pair
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        status: OrderStatus = OrderStatus.PENDING,
        max_time_active: Optional[int] = None,
        creation_time: Optional[pd.Timestamp] = None,
        position_reference: Optional[Position] = None,  # Reference to a Position object
    ):
        self.order_id = order_id
        self.type = type
        self.price = price
        self.quantity = quantity
        self.symbol = symbol  # Store the asset or currency pair symbol
        self.sl = sl
        self.tp = tp
        self.status = status
        self.max_time_active = max_time_active
        self.creation_time = creation_time or pd.Timestamp.now()
        self.reason = None  # Add reason attribute for cancellations
        self.position_reference = position_reference  # Link to a Position object

    def cancel(self, reason: str):
        """
        Cancel this order and log the reason.
        Args:
            reason (str): Reason for cancelling the order.
        """
        if self.status != OrderStatus.PENDING:
            logger.warning(
                f"Order {self.order_id} cannot be cancelled as it is not pending."
            )
            return

        self.status = OrderStatus.CANCELLED
        self.reason = reason  # Store the reason for cancellation
        logger.info(f"Order {self.order_id} on {self.symbol} cancelled: {reason}")

# Operations Handler ------------------------------------------------------------------------------
class PositionHandler:
    """
    Manages orders, positions, risk limits, and performance statistics.
    Attributes:
        pending_orders (List[Order]): List of pending orders.
        positions (List[Position]): List of all active positions.
    """

    def __init__(
        self,
        account_handler: AccountHandler,
    ):
        # Active Orders and Positions
        self.pending_orders: List[Order] = []  # Orders waiting for execution
        self.positions: List[Position] = []  # Active positions
        
        # Order ID counter
        self._order_counter = 1

        # Position ID counter
        self._position_counter = 1

        # Account Handler
        self.account_handler = account_handler
        self.account_handler.position_handler = self

    # Manual Actions ------------------------------------------------------------------------------
    def create_order(
        self,
        type: OrderType,
        price: float,
        quantity: float,
        symbol: str,  # Adicionado: O símbolo do ativo ou par de moedas
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        max_time_active: Optional[int] = None,
        creation_time: Optional[pd.Timestamp] = None,
    ):
        """
        Create a new order.
        Args:
            type (OrderType): Type of order (buy, sell, modify, close).
            price (float): Target price for the order.
            quantity (float): Quantity for the order.
            symbol (str): Symbol of the asset or currency pair (e.g., "EURUSD").
            sl (Optional[float]): Stop loss price for the order.
            tp (Optional[float]): Take profit price for the order.
            max_time_active (Optional[int]): Maximum time in seconds the order can remain active.
            creation_time (Optional[pd.Timestamp]): Timestamp when the order was created.
        """
        self._validate_order_params(type, price, quantity, sl, tp, max_time_active)

        # Get the next ID and increment the counter
        order_id = self._order_counter
        self._order_counter += 1

        new_order = Order(
            order_id=order_id,
            type=type,
            price=price,
            quantity=quantity,
            symbol=symbol,  # Passa o símbolo para a nova ordem
            sl=sl,
            tp=tp,
            status=OrderStatus.PENDING,
            max_time_active=max_time_active,
            creation_time=creation_time,
        )
        self.pending_orders.append(new_order)
        logger.info(f"Order created: {new_order.__dict__}")

    def edit_order(self, order_id: int, **kwargs):
        """
        Edit an existing pending order by updating its attributes.
        Args:
            order_id (int): The ID of the order to edit.
            **kwargs: Key-value pairs of attributes to update (e.g., price, quantity, sl, tp).
        """
        for order in self.pending_orders:
            if order.order_id == order_id:
                if order.status != OrderStatus.PENDING:
                    logger.warning(
                        f"Order {order_id} cannot be edited as it is not pending."
                    )
                    return

                # Get attrobutes to be validated
                price = kwargs.get("price", order.price)
                quantity = kwargs.get("quantity", order.quantity)
                sl = kwargs.get("sl", order.sl)
                tp = kwargs.get("tp", order.tp)
                max_time_active = kwargs.get(
                    "max_time_active", order.max_time_active
                )

                # Validate the updates
                self._validate_order_params(
                    type=order.type,
                    price=price,
                    quantity=quantity,
                    sl=sl,
                    tp=tp,
                    max_time_active=max_time_active,
                )
                
                # Update attributes if provided
                order.price = price
                order.quantity = quantity
                order.sl = sl
                order.tp = tp
                order.max_time_active = max_time_active

                logger.info(f"Order {order_id} updated: {order.__dict__}")
                return

        logger.warning(f"Order {order_id} not found in pending orders.")

    def modify_position(self, price: float, sl: Optional[float], tp: Optional[float]):
        """
        Modify an active position's parameters.
        Args:
            price (float): New price for the position.
            sl (Optional[float]): New stop loss price for the position.
            tp (Optional[float]): New take profit price for the position.
        """
        for position in self.positions:
            if position.status == PositionStatus.ACTIVE:
                position.sl = sl if sl else position.sl
                position.tp = tp if tp else position.tp
                logger.info(f"Position modified: {position.__dict__}")

    def _validate_position_params(
        self,
        type: PositionType,
        open_price: float,
        quantity: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ):
        """
        Validate position parameters for creation or editing.
        Args:
            type (PositionType): Type of the position (BUY or SELL).
            open_price (float): Opening price of the position.
            quantity (float): Quantity of the position.
            sl (Optional[float]): Stop-loss price for the position.
            tp (Optional[float]): Take-profit price for the position.
        Raises:
            ValueError: If any validation fails.
        """
        if open_price <= 0:
            raise ValueError("Open price must be greater than zero.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if type == PositionType.BUY:
            if sl is not None and sl >= open_price:
                raise ValueError(
                    "Stop-loss for a BUY position must be below the open price."
                )
            if tp is not None and tp <= open_price:
                raise ValueError(
                    "Take-profit for a BUY position must be above the open price."
                )

        if type == PositionType.SELL:
            if sl is not None and sl <= open_price:
                raise ValueError(
                    "Stop-loss for a SELL position must be above the open price."
                )
            if tp is not None and tp >= open_price:
                raise ValueError(
                    "Take-profit for a SELL position must be below the open price."
                )

    def _validate_order_params(
        self,
        type: OrderType,
        price: float,
        quantity: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        max_time_active: Optional[int] = None,
    ):
        """
        Validate order parameters for creation or editing.
        Args:
            type (OrderType): Type of order (buy, sell, modify, close).
            price (float): Target price for the order.
            quantity (float): Quantity for the order.
            sl (Optional[float]): Stop loss price for the order.
            tp (Optional[float]): Take profit price for the order.
            max_time_active (Optional[int]): Maximum time in seconds the order can remain active.
        Raises:
            ValueError: If any validation fails.
        """
        if price <= 0:
            raise ValueError("Price must be greater than zero.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if max_time_active is not None and max_time_active <= 0:
            raise ValueError("Max time active must be greater than zero.")

        if type == OrderType.BUY:
            if sl is not None and sl >= price:
                raise ValueError(
                    "Stop-loss for a BUY order must be below the entry price."
                )
            if tp is not None and tp <= price:
                raise ValueError(
                    "Take-profit for a BUY order must be above the entry price."
                )

        if type == OrderType.SELL:
            if sl is not None and sl <= price:
                raise ValueError(
                    "Stop-loss for a SELL order must be above the entry price."
                )
            if tp is not None and tp >= price:
                raise ValueError(
                    "Take-profit for a SELL order must be below the entry price."
                )

    # Process orders and positions ----------------------------------------------------------------
    def update(self, latest_data: Dict[str, float]):
        """
        Central function to update the handler with the latest data,
        processing pending orders and active positions.

        Args:
            latest_data (dict): A dictionary containing the latest price and timestamp.
                Example: {"Close": 100.5, "Timestamp": "2024-01-01 10:00:00"}
        """
        latest_price = latest_data["Close"]
        current_time = pd.Timestamp(latest_data["Timestamp"])

        # Process pending orders
        self._process_pending_orders(latest_price, current_time)

        # Process active positions
        self._process_active_positions(latest_price, current_time)

        logger.info("Update completed. Pending orders and active positions processed.")

    def close_position(
        self,
        price: float,
        quantity: float,
        close_time: Optional[pd.Timestamp] = None,
        reason: Optional[str] = None,
        position: Optional[Position] = None,
    ):
        """
        Close active positions based on the given price and quantity.
        Args:
            price (float): Price at which the position is being closed.
            quantity (float): Quantity of the position being closed.
            close_time (Optional[pd.Timestamp]): Timestamp when the position was closed.
            reason (Optional[str]): Reason for closing the position.
            position (Optional[Position]): Specific Position object to close.
        """
        target_positions = [position] if position else self.positions[:]

        for position in target_positions:
            if position.status != PositionStatus.ACTIVE:
                continue

            if quantity > position.quantity:
                logger.warning(
                    f"Attempted to close more than available quantity for Position #{position.position_id}."
                )
                raise ValueError("Cannot close more than the available quantity.")

            # Handle partial closure
            if quantity < position.quantity:
                remaining_quantity = position.quantity - quantity

                # Update the original position with the remaining quantity
                position.quantity = remaining_quantity
                logger.info(
                    f"Position #{position.position_id} updated with remaining quantity: {remaining_quantity}"
                )

                # Create a new position for the closed portion
                closed_position = Position(
                    position_id=self._position_counter,  # New ID for the closed portion
                    type=position.type,
                    open_price=position.open_price,
                    quantity=quantity,
                    sl=None,  # SL and TP do not apply to closed portions
                    tp=None,
                    open_time=position.open_time,
                )
                self._position_counter += 1
                closed_position.close(price, close_time, f"{reason} - Partial Close")
                self.account_handler._save_closed_positions(
                    closed_position
                )  # Persist the closed position
                logger.info(
                    f"Position #{closed_position.position_id} partially closed and saved to historical positions."
                )
                return

            # Full closure
            position.close(price, close_time, reason)
            self.positions.remove(position)
            self.account_handler._save_closed_positions(position)  # Persist the closed position
            logger.info(
                f"Position #{position.position_id} fully closed and saved to historical positions."
            )
            break

    def cancel_order(self, order: Order, reason: str):
        """
        Cancel a pending order and move it to the historical orders.
        Args:
            order (Order): The order to be cancelled.
            reason (str): Reason for cancellation.
        """
        if order.status != OrderStatus.PENDING:
            logger.warning(
                f"Order {order.order_id} is not pending and cannot be cancelled."
            )
            return

        order.cancel(reason)  # Utilize o método interno do objeto Order
        self.pending_orders.remove(order)
        self.account_handler._save_historical_orders(order)  # Persist the cancelled order
        logger.info(f"Order {order.order_id} cancelled and saved to historical orders.")

    def _execute_order(self, order: Order):
        """
        Execute an order and convert it to a position if applicable.
        Args:
            order (Order): The order to be executed.
        """
        if order.status != OrderStatus.PENDING:
            logger.warning(
                f"Order {order.order_id} is not pending and cannot be executed."
            )
            return

        if order.type == OrderType.BUY or order.type == OrderType.SELL:
            # Validate position parameters before creating
            self._validate_position_params(
                type=PositionType.BUY if order.type == OrderType.BUY else PositionType.SELL,
                open_price=order.price,
                quantity=order.quantity,
                sl=order.sl,
                tp=order.tp,
            )

            position_id = self._position_counter
            self._position_counter += 1

            # Create a new position and assign to the order
            new_position = Position(
                position_id=position_id,
                type=PositionType.BUY if order.type == OrderType.BUY else PositionType.SELL,
                open_price=order.price,
                quantity=order.quantity,
                symbol=order.symbol,  # Passa o símbolo da ordem para a posição
                sl=order.sl,
                tp=order.tp,
                open_time=order.creation_time,
            )

            self.positions.append(new_position)
            order.position_reference = (
                new_position  # Link the order to the newly created position
            )
            logger.info(
                f"Order {order.order_id} on {order.symbol} executed and converted to position #{new_position.position_id}."
            )

        elif order.type == OrderType.MODIFY and order.position_reference:
            # Modify the specified position directly
            position = order.position_reference
            if position.status == PositionStatus.ACTIVE:
                position.sl = order.sl if order.sl else position.sl
                position.tp = order.tp if order.tp else position.tp
                logger.info(
                    f"Position #{position.position_id} on {position.symbol} modified based on order {order.order_id}."
                )

        elif order.type == OrderType.CLOSE and order.position_reference:
            # Close the specified position directly
            position = order.position_reference
            if position.status == PositionStatus.ACTIVE:
                self.close_position(
                    price=order.price,
                    quantity=order.quantity,
                    reason="Closed via linked order",
                    close_time=pd.Timestamp.now(),
                    position=position,  # Pass the specific position directly
                )

        order.status = OrderStatus.EXECUTED
        self.account_handler._save_historical_orders(order)  # Save the historical orders
        self.pending_orders.remove(order)

    def _should_execute_order(self, order: Order, current_price: float) -> bool:
        """
        Determine if an order should be executed based on the current price.
        Args:
            order (Order): The order to evaluate.
            current_price (float): The current market price.
        Returns:
            bool: True if the order should be executed, False otherwise.
        """
        if order.type == OrderType.BUY and current_price <= order.price:
            return True
        if order.type == OrderType.SELL and current_price >= order.price:
            return True
        return False

    def _process_pending_orders(self, current_price: float, current_time: pd.Timestamp):
        """
        Process all pending orders to determine if they should be executed or cancelled.
        Args:
            current_price (float): The current market price to evaluate against pending orders.
            current_time (pd.Timestamp): The current time to evaluate against max_time_active.
        """
        for order in self.pending_orders[:]:
            if order.status != OrderStatus.PENDING:
                continue  # Skip non-pending orders for safety

            if (
                order.max_time_active
                and (current_time - order.creation_time).total_seconds()
                > order.max_time_active
            ):
                self.cancel_order(order, "Timeout reached.")
                continue

            if self._should_execute_order(order, current_price):
                self._execute_order(order)

    def _process_active_positions(
        self, latest_price: float, current_time: pd.Timestamp
    ):
        """
        Process active positions to check for SL or TP conditions.
        Args:
            latest_price (float): Current market price.
            current_time (pd.Timestamp): Current timestamp.
        """
        for position in self.positions[:]:
            if position.status != PositionStatus.ACTIVE:
                continue  # Skip closed positions for safety

            if position.sl and latest_price <= position.sl:
                self._process_stop_loss(position, current_time)

            if position.tp and latest_price >= position.tp:
                self._process_take_profit(position, current_time)

    def _process_stop_loss(self, position: Position, current_time: pd.Timestamp):
        """
        Close a position due to Stop Loss being hit.
        Args:
            position (Position): The position to close.
            current_time (pd.Timestamp): Current timestamp.
        """
        logger.info(f"Stop Loss triggered for Position #{position.position_id}")
        self.close_position(
            price=position.sl,
            quantity=position.quantity,
            close_time=current_time,
            reason="Stop Loss triggered",  # Adiciona o motivo explícito
            position=position,
        )

    def _process_take_profit(self, position: Position, current_time: pd.Timestamp):
        """
        Close a position due to Take Profit being hit.
        Args:
            position (Position): The position to close.
            current_time (pd.Timestamp): Current timestamp.
        """
        logger.info(f"Take Profit triggered for Position #{position.position_id}")
        self.close_position(
            price=position.tp,
            quantity=position.quantity,
            close_time=current_time,
            reason="Take Profit triggered",  # Adiciona o motivo explícito
            position=position,
        )

