import pytest
import pandas as pd
from algo_trading.position_handler import (
    PositionHandler,
    OrderType,
    PositionStatus,
    OrderStatus,
)


@pytest.fixture
def handler():
    """Fixture para instanciar o OperationHandler com saldo inicial."""
    return PositionHandler(initial_balance=10000)


@pytest.fixture
def reset_handler(handler: PositionHandler):
    """Fixture to reset handler after each test."""
    yield
    handler.reset()


def test_create_position(handler: PositionHandler, reset_handler):
    """Testa a criação de uma posição a partir de uma ordem."""
    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    assert position.type == OrderType.BUY
    assert position.open_price == 100
    assert position.quantity == 10
    assert position.sl == 95
    assert position.tp == 110
    assert position.status == PositionStatus.ACTIVE


def test_close_position(handler: PositionHandler, reset_handler):
    """Testa o fechamento de uma posição."""
    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    handler.close_position(
        price=105, quantity=10, reason="Manual close", position=position
    )

    assert position.status == PositionStatus.CLOSED
    assert position.close_price == 105
    assert position.profit_loss == (105 - 100) * 10
    assert position.reason == "Manual close"


def test_partial_close_position(handler: PositionHandler, reset_handler):
    """Testa o fechamento parcial de uma posição."""
    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    handler.close_position(
        price=105, quantity=5, reason="Partial close", position=position
    )

    # Verifica se a posição original foi ajustada corretamente
    assert len(handler.positions) == 1  # A posição original permanece ativa
    assert handler.positions[0].quantity == 5
    assert handler.positions[0].status == PositionStatus.ACTIVE

    # Verifica se a parte fechada foi registrada no histórico
    closed_positions = handler.get_closed_positions()
    assert len(closed_positions) == 1  # Apenas uma parte foi fechada
    closed_position = closed_positions.iloc[0]
    assert closed_position.status == PositionStatus.CLOSED
    assert closed_position.quantity == 5
    assert closed_position.close_price == 105
    assert closed_position.profit_loss == (105 - 100) * 5
    assert closed_position.reason == "Partial close - Partial Close"


def test_multiple_partial_closes(handler: PositionHandler, reset_handler):
    """Testa múltiplos fechamentos parciais de uma posição."""
    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    handler.close_position(
        price=105, quantity=3, reason="Partial close", position=position
    )
    handler.close_position(
        price=107, quantity=2, reason="Another partial close", position=position
    )

    # Verifica o estado restante da posição
    assert handler.positions[0].quantity == 5
    assert handler.positions[0].status == PositionStatus.ACTIVE

    # Verifica o histórico de posições fechadas
    closed_positions = handler.get_closed_positions()
    assert len(closed_positions) == 2
    assert closed_positions.iloc[0].profit_loss == (105 - 100) * 3
    assert closed_positions.iloc[1].profit_loss == (107 - 100) * 2


def test_full_close_after_partial(handler: PositionHandler, reset_handler):
    """Testa fechamento completo após fechamento parcial."""
    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    handler.close_position(
        price=105, quantity=5, reason="Partial close", position=position
    )
    handler.close_position(
        price=108, quantity=5, reason="Final close", position=position
    )

    # Verifica que não restam posições ativas
    assert len(handler.positions) == 0

    # Verifica o histórico
    closed_positions = handler.get_closed_positions()
    assert len(closed_positions) == 2
    assert closed_positions.iloc[0].quantity == 5
    assert closed_positions.iloc[1].quantity == 5
    assert closed_positions.iloc[0].profit_loss == (105 - 100) * 5
    assert closed_positions.iloc[1].profit_loss == (108 - 100) * 5


def test_take_profit_trigger(handler: PositionHandler, reset_handler):
    """Testa o acionamento do take profit."""

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    handler._process_active_positions(latest_price=110, current_time=pd.Timestamp.now())

    assert len(handler.positions) == 0
    closed_positions = handler.get_closed_positions()
    assert len(closed_positions) == 1
    assert closed_positions.iloc[0].reason == "Take Profit triggered"


def test_stop_loss_trigger(handler: PositionHandler, reset_handler):
    """Testa o acionamento do stop loss."""

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    handler._process_active_positions(latest_price=95, current_time=pd.Timestamp.now())

    assert len(handler.positions) == 0
    closed_positions = handler.get_closed_positions()
    assert len(closed_positions) == 1
    assert closed_positions.iloc[0].reason == "Stop Loss triggered"


def test_modify_position(handler: PositionHandler, reset_handler):
    """Testa a modificação de uma posição ativa."""

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]
    handler.modify_position(price=100, sl=96, tp=112)

    assert position.sl == 96
    assert position.tp == 112


def test_statistics(handler: PositionHandler, reset_handler):
    """Testa o cálculo de estatísticas após operações."""

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])
    handler.close_position(
        price=105, quantity=10, reason="Manual close", position=handler.positions[0]
    )

    stats = handler.calculate_statistics()

    assert stats["total_positions"] == 1
    assert stats["closed_positions"] == 1
    assert stats["active_positions"] == 0
    assert stats["total_profit_loss"] == 50
    assert stats["win_rate"] == 1.0


def test_close_position_excess_quantity(handler: PositionHandler, reset_handler):

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    handler._execute_order(handler.pending_orders[0])

    position = handler.positions[0]

    with pytest.raises(
        ValueError, match="Cannot close more than the available quantity."
    ):
        handler.close_position(
            price=105, quantity=15, reason="Excess close", position=position
        )


def test_invalid_position_parameters(handler: PositionHandler, reset_handler):

    with pytest.raises(ValueError):
        handler.create_order(OrderType.BUY, price=-1, quantity=10, sl=95, tp=110)

    with pytest.raises(ValueError):
        handler.create_order(OrderType.SELL, price=100, quantity=-5, sl=105, tp=90)


def test_cancel_order(handler: PositionHandler, reset_handler):

    handler.create_order(OrderType.BUY, price=100, quantity=10, sl=95, tp=110)
    order = handler.pending_orders[0]

    handler.cancel_order(order, reason="User cancel")

    assert order.status == OrderStatus.CANCELLED
    assert order.reason == "User cancel"
    assert len(handler.pending_orders) == 0


def test_order_timeout(handler: PositionHandler, reset_handler):

    handler.create_order(OrderType.BUY, price=100, quantity=10, max_time_active=5)
    order = handler.pending_orders[0]

    handler._process_pending_orders(
        current_price=90, current_time=pd.Timestamp.now() + pd.Timedelta(seconds=10)
    )

    assert order.status == OrderStatus.CANCELLED
    assert len(handler.pending_orders) == 0


def test_order_not_executed(handler: PositionHandler, reset_handler):

    handler.create_order(OrderType.BUY, price=100, quantity=10)
    order = handler.pending_orders[0]

    handler._process_pending_orders(current_price=101, current_time=pd.Timestamp.now())

    assert order.status == OrderStatus.PENDING
    assert len(handler.positions) == 0
