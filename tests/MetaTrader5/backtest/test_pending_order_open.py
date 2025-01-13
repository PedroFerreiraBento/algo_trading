# **Bibliotecas de Testes**
import pytest  # Biblioteca para criação e execução de testes unitários

# **Bibliotecas de Datas e Horários**
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # Utilizadas para definir timestamps com fuso horário UTC e manipulação de datas/horas.

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlAccountInfo,  # Modelo que contém informações da conta de trading (e.g., saldo, margem, nome da conta).
    ENUM_ACCOUNT_TRADE_MODE,  # Enum que define o modo de operação da conta (e.g., demo, real).
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para o modo de stop-out (e.g., percentual ou valor fixo).
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para definir o tipo de margem da conta (e.g., hedge, netting).
    ENUM_ORDER_TYPE_MARKET,  # Enum que define os tipos de ordens a mercado (e.g., BUY/SELL).
    ENUM_ORDER_TYPE_PENDING,  # Enum que define os tipos de ordens pendentes (e.g., BUY LIMIT, SELL STOP).
    ENUM_ORDER_TYPE_TIME,  # Enum para os tipos de expiração de ordens (e.g., GTC, tempo especificado).
    MqlTradeOrder,  # Modelo que representa uma ordem de trade pendente ou executada.
    ENUM_ORDER_STATE,  # Enum para o estado da ordem (e.g., `ORDER_STATE_PLACED`, `ORDER_STATE_FILLED`).
    ENUM_ORDER_REASON,  # Enum que indica a razão para a criação da ordem (e.g., manual, expert).
    ENUM_SYMBOL_CALC_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    ENUM_ORDER_TYPE,
)

# **Exceções Personalizadas**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
)  # Exceção personalizada levantada quando não é possível selecionar uma posição com base no ticket.

# **Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_pending_order_open,  # Função que simula a abertura de ordens pendentes em modo de backtest.
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


def test_backtest_open_pending_order(account: Account):
    """
    Testa a função `__backtest_open_pending_order` para verificar se uma ordem pendente é aberta corretamente.

    Verifica:
    1. Se a ordem pendente é adicionada à lista de ordens.
    2. Se os atributos importantes da ordem (símbolo, tipo de ordem, volume, preço, etc.) estão corretos.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.magic_number = 987654  # Define o "magic number" da conta para identificar operações automáticas
    account.backtest_account_data.type_filling = (
        ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY
    )  # Tipo de execução de ordens
    symbol = "EURUSD"

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
            name=datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc),
        ),
    }

    # Cria um DataFrame para o novo registro com o mesmo formato do DataFrame existente
    new_row = pd.DataFrame([new_data], index=[symbol])
    account.backtest_account_data.operation.backtest_symbols_data = pd.concat(
        [account.backtest_account_data.operation.backtest_symbols_data, new_row]
    )

    # **Parâmetros da ordem pendente**
    order_type = (
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT
    )  # Ordem pendente do tipo BUY LIMIT
    volume = 1.0  # Volume da ordem em lotes
    price = 1.1200  # Preço de execução desejado (limite)
    stop_limit = 0.0  # Não usado neste caso
    stop_price = 1.1150  # Stop-loss
    profit_price = 1.1300  # Take-profit
    expiration = datetime.now(timezone.utc) + timedelta(
        days=2
    )  # Expiração da ordem pendente
    comment = "Pending order test"

    # **Abertura da ordem pendente**
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=order_type,
        volume=volume,
        price=price,
        stop_limit=stop_limit,
        stop_price=stop_price,
        profit_price=profit_price,
        expiration=expiration,
        comment=comment,
    )

    # **Verificações**
    # Verifica se há uma nova ordem pendente na lista de ordens
    assert (
        len(account.backtest_account_data.orders) == 1
    ), "A ordem pendente não foi adicionada corretamente."

    # Obtém a ordem pendente criada
    pending_order: MqlTradeOrder = account.backtest_account_data.orders[-1]

    assert pending_order.symbol == symbol, "O símbolo da ordem pendente está incorreto."
    assert pending_order.type == order_type, "O tipo de ordem pendente está incorreto."
    assert (
        pending_order.volume_initial == volume
    ), "O volume inicial da ordem pendente está incorreto."
    assert (
        pending_order.price_open == price
    ), "O preço de execução desejado está incorreto."
    assert pending_order.sl == stop_price, "O preço de stop-loss está incorreto."
    assert pending_order.tp == profit_price, "O preço de take-profit está incorreto."
    assert (
        pending_order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    ), "O tipo de expiração da ordem pendente está incorreto."
    assert (
        pending_order.time_expiration == expiration
    ), "O tempo de expiração da ordem pendente está incorreto."
    assert (
        pending_order.comment == comment
    ), "O comentário da ordem pendente está incorreto."
    assert (
        pending_order.magic == 987654
    ), "O magic number da ordem pendente está incorreto."

    # Verifica se o estado da ordem pendente é "ORDER_STATE_PLACED"
    assert (
        pending_order.state == ENUM_ORDER_STATE.ORDER_STATE_PLACED
    ), "O estado da ordem deveria ser 'ORDER_STATE_PLACED'."
    assert (
        pending_order.reason == ENUM_ORDER_REASON.ORDER_REASON_EXPERT
    ), "A razão da ordem deveria ser 'ORDER_REASON_EXPERT'."


def test_validate_pending_order_prices_with_spread(account: Account):
    """
    Testa a função `__backtest_pending_order_open` para validar preços
    com base no spread e tipo de ordem pendente.

    Verifica:
    1. Se as validações para preços das ordens pendentes são realizadas corretamente.
    2. Se exceções são levantadas para preços fora do intervalo permitido.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(
        balance=5000, leverage=100
    )  # Inicia a conta com saldo de $5.000 e alavancagem 1:100
    account.backtest_account_data.magic_number = (
        987654  # Define o "magic number" da conta
    )
    account.backtest_account_data.simulated_spread = (
        2  # Define o spread simulado em pontos
    )
    symbol = "EURUSD"

    # Configuração do candle mais recente
    last_candle_time = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
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

    # Recupera o preço atual e calcula o spread
    close_price = 1.13  # Preço de fechamento do último candle
    tick_size = 1e-05
    spread = account.backtest_account_data.simulated_spread * tick_size

    # **Testes de preços válidos**
    valid_price_buy_limit = close_price - 0.005
    valid_price_sell_limit = close_price + 0.005

    # Ordem BUY_LIMIT válida
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
        volume=1.0,
        price=valid_price_buy_limit,
        stop_limit=0,
        stop_price=1.12,
        profit_price=1.14,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid BUY_LIMIT order",
    )

    # Ordem SELL_LIMIT válida
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
        volume=1.0,
        price=valid_price_sell_limit,
        stop_limit=0,
        stop_price=1.14,
        profit_price=1.12,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid SELL_LIMIT order",
    )

    # **Testes de preços inválidos**
    invalid_price_buy_limit = (
        close_price + 0.005
    )  # BUY_LIMIT não pode ser maior ou igual ao preço atual
    invalid_price_sell_limit = (
        close_price - 0.005
    )  # SELL_LIMIT não pode ser menor ou igual ao preço atual
    invalid_price_buy_stop = (
        close_price - 0.005
    )  # BUY_STOP não pode ser menor ou igual ao preço atual com spread
    invalid_price_sell_stop = (
        close_price + spread + 0.005
    )  # SELL_STOP não pode ser maior ou igual ao preço atual

    # BUY_LIMIT inválido
    with pytest.raises(ValueError, match="deve ser menor que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
            volume=1.0,
            price=invalid_price_buy_limit,
            stop_limit=0,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_LIMIT order",
        )

    # SELL_LIMIT inválido
    with pytest.raises(ValueError, match="deve ser maior que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
            volume=1.0,
            price=invalid_price_sell_limit,
            stop_limit=0,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_LIMIT order",
        )

    # BUY_STOP inválido
    with pytest.raises(ValueError, match="deve ser maior que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
            volume=1.0,
            price=invalid_price_buy_stop,
            stop_limit=0,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP order",
        )

    # SELL_STOP inválido
    with pytest.raises(ValueError, match="deve ser menor que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
            volume=1.0,
            price=invalid_price_sell_stop,
            stop_limit=0,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP order",
        )

    # **Testes de preços válidos para STOP_LIMIT**
    valid_price_buy_stop_limit = close_price + spread + 0.005
    valid_stop_limit_buy = (
        valid_price_buy_stop_limit - 0.002
    )  # Stop limit menor que o preço inicial
    valid_price_sell_stop_limit = close_price - 0.005
    valid_stop_limit_sell = (
        valid_price_sell_stop_limit + 0.002
    )  # Stop limit maior que o preço inicial

    # BUY_STOP_LIMIT válido
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
        volume=1.0,
        price=valid_price_buy_stop_limit,
        stop_limit=valid_stop_limit_buy,
        stop_price=1.12,
        profit_price=1.14,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid BUY_STOP_LIMIT order",
    )

    # SELL_STOP_LIMIT válido
    __backtest_pending_order_open(
        operation_class=account.backtest_account_data.operation,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
        volume=1.0,
        price=valid_price_sell_stop_limit,
        stop_limit=valid_stop_limit_sell,
        stop_price=1.14,
        profit_price=1.12,
        expiration=datetime.now(timezone.utc) + timedelta(days=1),
        comment="Valid SELL_STOP_LIMIT order",
    )

    # **Testes de preços inválidos para STOP_LIMIT**
    invalid_price_buy_stop_limit = (
        close_price - 0.005
    )  # Preço inicial menor que o preço atual
    invalid_stop_limit_buy = (
        invalid_price_buy_stop_limit + 0.002
    )  # Stop limit maior que o preço inicial
    invalid_price_sell_stop_limit = (
        close_price + spread + 0.005
    )  # Preço inicial maior que o preço atual
    invalid_stop_limit_sell = (
        invalid_price_sell_stop_limit - 0.002
    )  # Stop limit menor que o preço inicial

    # BUY_STOP_LIMIT inválido
    with pytest.raises(ValueError, match="deve ser maior que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_buy_stop_limit,
            stop_limit=valid_stop_limit_buy,
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP_LIMIT order",
        )

    # Configuração para o teste
    invalid_price_buy_stop_limit = close_price + spread + 0.005  # Preço inicial válido
    invalid_stop_limit_buy = (
        invalid_price_buy_stop_limit + 0.002
    )  # Stop limit inválido (maior que o preço inicial)

    # Testa se a exceção é levantada para um `stop_limit` inválido
    with pytest.raises(ValueError, match="deve ser menor que o preço inicial"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_buy_stop_limit,
            stop_limit=invalid_stop_limit_buy,  # Stop limit inválido
            stop_price=1.12,
            profit_price=1.14,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid BUY_STOP_LIMIT order (stop_limit)",
        )

    # SELL_STOP_LIMIT inválido
    with pytest.raises(ValueError, match="deve ser menor que o preço atual"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            volume=1.0,
            price=invalid_price_sell_stop_limit,
            stop_limit=valid_stop_limit_sell,
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP_LIMIT order",
        )

    # Configuração para o teste
    valid_price_sell_stop_limit = (
        close_price - 0.005
    )  # Preço inicial válido (menor que o preço atual)
    invalid_stop_limit_sell = (
        valid_price_sell_stop_limit - 0.002
    )  # Stop limit inválido (menor que o preço inicial)

    # Testa se a exceção é levantada para um `stop_limit` inválido
    with pytest.raises(ValueError, match="deve ser maior que o preço inicial"):
        __backtest_pending_order_open(
            operation_class=account.backtest_account_data.operation,
            symbol=symbol,
            order_type=ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
            volume=1.0,
            price=valid_price_sell_stop_limit,  # Preço inicial válido
            stop_limit=invalid_stop_limit_sell,  # Stop limit inválido
            stop_price=1.14,
            profit_price=1.12,
            expiration=datetime.now(timezone.utc) + timedelta(days=1),
            comment="Invalid SELL_STOP_LIMIT order (stop_limit)",
        )
