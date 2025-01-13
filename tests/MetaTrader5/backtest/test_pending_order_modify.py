# **Bibliotecas de Testes**
import pytest  # Biblioteca para criação e execução de testes unitários.

# **Bibliotecas de Datas e Horários**
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # Utilizadas para definir timestamps com fuso horário UTC e manipulação de datas/horas.

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo que contém informações da conta de trading (e.g., saldo, margem, nome da conta).
    MqlTradeOrder,  # Modelo que representa uma ordem de trade pendente ou executada.
    ENUM_ACCOUNT_TRADE_MODE,  # Enum que define o modo de operação da conta (e.g., demo, real).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para o modo de stop-out (e.g., percentual ou valor fixo).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para definir o tipo de margem da conta (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum que define os tipos de ordens a mercado (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum que define os tipos de ordens pendentes (e.g., BUY LIMIT, SELL STOP).
    ENUM_ORDER_TYPE_TIME,  # Enum para os tipos de expiração de ordens (e.g., GTC, tempo especificado).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_ORDER_TYPE,
)

# **Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_open,  # Função que simula a abertura de ordens pendentes em modo de backtest.
    __backtest_pending_order_modify,  # Função que simula a modificação de ordens pendentes em modo de backtest.
)

# **Classe de Conta**
from algo_trading.sources.MetaTrader5_source.account.account import (
    Account,
)  # Classe `Account` utilizada para login e gerenciamento das informações de conta de trading.

import pandas as pd


@pytest.fixture
def account():
    """Fixture que cria uma instância de conta para os testes.

    Simula o login em uma conta ao vivo.

    Returns:
        Account: Instância de conta com dados configurados.
    """
    account = Account()

    # Simula login na conta ao vivo antes do backtest
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


def test_backtest_modify_pending_order(account: Account):
    """
    Testa a função `__backtest_modify_pending_order` para verificar se uma ordem pendente
    é modificada corretamente.

    Verifica:
    1. Se a ordem pendente é selecionada e modificada com sucesso.
    2. Se os atributos principais da ordem (preço de entrada, stop-loss, take-profit, expiração, comentário) são atualizados.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.magic_number = 123456  # Define o "magic number" da conta para identificar operações automáticas
    account.backtest_account_data.type_filling = (
        ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY
    )  # Tipo de execução de ordens
    symbol = "EURUSD"

    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # Complete configuration
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
            {"open": 1.12, "high": 1.15, "low": 1.09, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # **Parâmetros da ordem pendente inicial**
    initial_order_type = (
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT
    )  # Ordem pendente do tipo SELL LIMIT
    initial_volume = 1.0  # Volume da ordem em lotes
    initial_price = 1.1300  # Preço de execução desejado
    initial_stop_price = 1.1350  # Stop-loss inicial
    initial_profit_price = 1.1250  # Take-profit inicial
    initial_expiration = last_candle_time + timedelta(
        days=2
    )  # Expiração inicial da ordem pendente
    initial_comment = "Initial pending order"

    # **Abertura da ordem pendente inicial**
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=initial_order_type,
        volume=initial_volume,
        price=initial_price,
        stop_price=initial_stop_price,
        profit_price=initial_profit_price,
        expiration=initial_expiration,
        comment=initial_comment,
    )

    # **Obter a ordem pendente criada**
    pending_order: MqlTradeOrder = account.backtest_account_data.orders[-1]
    ticket = pending_order.ticket  # ID da ordem pendente

    # **Novos parâmetros para modificar a ordem**
    new_price = 1.14  # Novo preço de execução
    new_stop_price = 1.1530  # Novo stop-loss
    new_profit_price = 0.9  # Novo take-profit
    new_expiration = last_candle_time + timedelta(days=3)  # Nova data de expiração
    new_comment = "Modified pending order"

    # **Modificar a ordem pendente**
    __backtest_pending_order_modify(
        operation_class=account.backtest_account_data.operation,
        ticket=ticket,
        price=new_price,
        stop_price=new_stop_price,
        profit_price=new_profit_price,
        expiration=new_expiration,
        comment=new_comment,
    )

    # **Verificações da modificação**
    assert (
        pending_order.price_open == new_price
    ), "O preço de execução não foi atualizado corretamente."
    assert (
        pending_order.sl == new_stop_price
    ), "O stop-loss não foi atualizado corretamente."
    assert (
        pending_order.tp == new_profit_price
    ), "O take-profit não foi atualizado corretamente."
    assert (
        pending_order.time_expiration == new_expiration
    ), "A data de expiração não foi atualizada corretamente."
    assert (
        pending_order.comment == new_comment
    ), "O comentário da ordem não foi atualizado corretamente."
    assert (
        pending_order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    ), "O tipo de tempo da ordem não foi atualizado corretamente para 'ORDER_TIME_SPECIFIED'."
    assert (
        pending_order.magic == account.backtest_account_data.magic_number
    ), "O magic number da ordem não foi mantido corretamente."


def test_validate_prices_buy_and_sell(account: Account):
    """
    Testa se os preços, stop loss (sl) e take profit (tp) são validados corretamente
    para ordens de compra (BUY) e venda (SELL).
    """
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # Complete configuration
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
            {"open": 1.12, "high": 1.15, "low": 1.09, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Configuração inicial
    price = 1.1300
    sl_buy = 1.1200
    tp_buy = 1.1400
    sl_sell = 1.1400
    tp_sell = 1.1200

    # Ordem de compra (BUY)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        volume=1.0,
        price=price,
        stop_price=sl_buy,
        profit_price=tp_buy,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Buy order test",
    )

    # Ordem de venda (SELL)
    __backtest_pending_order_open(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        volume=1.0,
        price=price,
        stop_price=sl_sell,
        profit_price=tp_sell,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Sell order test",
    )

    # Obter as ordens pendentes criadas
    buy_order = account.backtest_account_data.orders[-2]
    sell_order = account.backtest_account_data.orders[-1]

    # Valida os preços das ordens de compra e venda
    assert buy_order.sl == sl_buy, "Stop loss da ordem de compra está incorreto."
    assert buy_order.tp == tp_buy, "Take profit da ordem de compra está incorreto."
    assert sell_order.sl == sl_sell, "Stop loss da ordem de venda está incorreto."
    assert sell_order.tp == tp_sell, "Take profit da ordem de venda está incorreto."


def test_validate_invalid_prices(account: Account):
    """
    Testa se a validação levanta exceções para configurações de preços inválidos,
    incluindo stop loss (sl) e take profit (tp).
    """
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    operation_handler = account.backtest_account_data.operation
    symbol = "EURUSD"

    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)

    # Complete configuration
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
            {"open": 1.12, "high": 1.15, "low": 1.09, "close": 1.13},
            name=last_candle_time,
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # Configurações inválidas para teste
    invalid_price = 1.1300

    # Ordem de compra (BUY) com stop loss inválido (maior que o preço)
    with pytest.raises(ValueError, match="Invalid stop loss"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1400,  # Stop loss inválido
            profit_price=1.1400,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid buy order (SL)",
        )

    # Ordem de compra (BUY) com take profit inválido (menor que o preço)
    with pytest.raises(ValueError, match="Invalid take profit"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1200,
            profit_price=1.1200,  # Take profit inválido
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid buy order (TP)",
        )

    # Ordem de venda (SELL) com stop loss inválido (menor que o preço)
    with pytest.raises(ValueError, match="Invalid stop loss"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1200,  # Stop loss inválido
            profit_price=1.1200,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid sell order (SL)",
        )

    # Ordem de venda (SELL) com take profit inválido (maior que o preço)
    with pytest.raises(ValueError, match="Invalid take profit"):
        __backtest_pending_order_open(
            operation_class=operation_handler,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            volume=1.0,
            price=invalid_price,
            stop_price=1.1400,
            profit_price=1.1400,  # Take profit inválido
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid sell order (TP)",
        )
