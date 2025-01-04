# **Bibliotecas de Testes**
import pytest  # Biblioteca para criação e execução de testes unitários

# **Bibliotecas de Datas e Horários**
from datetime import datetime, timezone  # Utilizado para definir timestamps e fusos horários

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    ENUM_ORDER_TYPE,  # Enum para tipos de ordens (e.g., BUY, SELL)
    MqlTradeDeal,  # Modelo que representa um deal de trade
    MqlAccountInfo,  # Modelo que representa as informações da conta
    ENUM_ACCOUNT_TRADE_MODE,  # Enum para modo de trade da conta (e.g., demo, real)
    ENUM_ACCOUNT_STOPOUT_MODE,  # Enum para o modo de stop-out (percentual ou valor fixo)
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para o modo de margem da conta (e.g., hedge, netting)
    ENUM_ORDER_TYPE_MARKET,  # Enum para ordens de mercado (e.g., BUY/SELL a mercado)
)

# **Exceções Personalizadas**
from algo_trading.sources.MetaTrader5_source.utils.exceptions import CouldNotSelectPosition  # Exceção levantada quando uma posição não pode ser selecionada

# **Funções de Backtest**
from algo_trading.sources.MetaTrader5_source.backtest.backtest import (
    __backtest_close_position,  # Função para fechar posições em modo de backtest
    __backtest_open_position,  # Função para abrir posições em modo de backtest
)

# **Classe de Conta**
from algo_trading.sources.MetaTrader5_source.account.account import Account  # Classe `Account` para login e gerenciamento de informações de conta

# **Bibliotecas de Dados**
import pandas as pd  # Biblioteca utilizada para manipulação de datas e criação de séries temporais


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


def test_backtest_close_position_success(account: Account):
    """
    Testa a função `__backtest_close_position` para garantir que uma posição seja fechada corretamente em modo de backtest.

    Verifica:
    1. Se a posição com o `ticket` especificado é encerrada corretamente.
    2. Se o deal de fechamento é criado e adicionado ao histórico de deals.
    3. Se a posição é removida da lista de posições abertas após o fechamento.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)
    account.backtest_account_data.simulated_spread = 4
    account.backtest_account_data.magic_number = 123456

    # **Configuração da posição inicial**
    symbol = "EURUSD"
    initial_volume = 1.0  # Volume de 1 lote
    position_time = datetime(2025, 1, 3, tzinfo=timezone.utc)

    # Mock de candle para simular o estado do mercado
    mock_candle = {
        "open": 1.1300,
        "high": 1.1320,
        "low": 1.1280,
        "close": 1.1250,  # Preço de fechamento (para simular BID)
        "tick_volume": 200,
    }
    mock_time_index = pd.to_datetime(position_time)
    last_candle = pd.Series(mock_candle, name=mock_time_index)

    # Configurações do manipulador de operações
    operation_handler = account.backtest_account_data.operation
    operation_handler.last_candle = {symbol: last_candle}
    operation_handler.contract_sizes = {symbol: 100_000}  # Tamanho do contrato padrão
    operation_handler.tick_sizes = {symbol: 1e-05}


    # **Configuração do modo hedge**
    operation_handler.account_data.margin_mode = ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING  # Permite múltiplas posições no mesmo ativo

    # **Abertura da posição inicial**
    __backtest_open_position(
        operation_class=operation_handler,
        symbol=symbol,
        order_type=ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY,  # Ordem de compra a mercado
        volume=initial_volume,  # Volume de 1 lote
        stop_price=1.12,  # Preço de stop-loss
        profit_price=1.13,  # Preço de take-profit
        comment="Teste de Hedge Mode",
    )
    position = account.backtest_account_data.positions[-1]
    
    operation_handler.last_candle[symbol]["close"] = 1.1300

    # **Fechamento da posição**
    __backtest_close_position(
        operation_class=operation_handler,
        position_ticket=position.ticket,
        commission=5.0,  # Comissão fictícia
        fee=1.0,  # Taxa fictícia
        comment="Close position test",
    )

    # **Verificações**
    assert len(account.backtest_account_data.positions) == 0, "A posição deveria ter sido removida após o fechamento."
    assert len(account.backtest_account_data.history_deals) == 3, "Deveria haver um deal no histórico após o fechamento."

    deal: MqlTradeDeal = account.backtest_account_data.history_deals[-1]
    

    assert deal.symbol == symbol, "O símbolo do deal está incorreto."
    assert deal.type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL, "O tipo de ordem de fechamento deveria ser SELL."
    assert deal.volume == initial_volume, "O volume do deal deveria ser igual ao volume da posição."
    assert deal.comment == "Close position test", "O comentário do deal está incorreto."
    assert deal.profit == 500, "O lucro deveria ser positivo, já que a posição foi fechada com lucro."

    
def test_backtest_close_position_not_found(account: Account):
    """
    Testa se a função `__backtest_close_position` levanta uma exceção ao tentar fechar uma posição inexistente.
    """
    # **Configuração da conta de backtest**
    account.login_backtest(balance=5000, leverage=100)

    # Tenta fechar uma posição com um `ticket` inexistente
    with pytest.raises(CouldNotSelectPosition, match=r"Could not select the position"):
        __backtest_close_position(
            operation_class=account.backtest_account_data.operation,
            position_ticket=99999,  # Ticket inexistente
            comment="Close non-existent position",
        )
