# Imports para tipagem e manipulação de datas
from typing import Callable, List, TYPE_CHECKING  # Tipos usados para anotações de funções e listas
from datetime import datetime, timezone  # Para manipulação de objetos de data/hora com timezone

# Imports relacionados aos modelos do MetaTrader5
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlPositionInfo,  # Modelo com informações sobre uma posição aberta
    MqlTradeDeal,  # Modelo com informações sobre um deal de trade
    MqlSymbolInfo,  # Modelo com informações sobre o símbolo negociado
    MqlTradeOrder,  # Modelo com informações sobre a ordem de trade
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modos de margem da conta
    ENUM_DEAL_TYPE,  # Enum para tipos de deal (DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_DEAL_ENTRY,  # Enum para tipos de entrada (IN, OUT, INOUT)
    ENUM_DEAL_REASON,  # Enum para motivos de execução de um deal
    ENUM_ORDER_TYPE,  # Enum para tipos de ordens (compra, venda, limite, stop, etc.)
    ENUM_ORDER_REASON,  # Enum para razões de execução de ordens
    ENUM_ORDER_TYPE_MARKET,  # Enum específico para ordens de mercado
    ENUM_ORDER_TYPE_PENDING,  # Enum específico para ordens pendentes
    ENUM_ORDER_STATE,  # Enum para estados de uma ordem (pendente, concluída, etc.)
    ENUM_POSITION_REASON,  # Enum para motivos de abertura de posição
    ENUM_POSITION_TYPE,  # Enum para tipos de posição (buy/sell)
    ENUM_ORDER_TYPE_TIME,  # Enum para tipos de ordens baseados em tempo (válida até cancelada, até um tempo específico)
)

# Imports relacionados às taxas e candles
from algo_trading.sources.MetaTrader5_source.rates import Rates  # Classe responsável por requisições de candles e ticks

# Imports de utilitários (funções de data, trades e exceções)
from algo_trading.sources.MetaTrader5_source.utils.dates import get_timestamp_ms  # Função para obter timestamp em milissegundos
from algo_trading.sources.MetaTrader5_source.utils.trades import (
    compute_profit,  # Função para calcular lucro ou prejuízo de uma posição
    get_last_tick,  # Função para obter o último tick de preço
    get_order,  # Função para buscar uma ordem específica
)
from algo_trading.sources.MetaTrader5_source.utils.exceptions import CouldNotSelectPosition  # Exceção levantada quando não é possível selecionar uma posição


if TYPE_CHECKING:
    from algo_trading.sources.MetaTrader5_source.operation.operation import Operation

# Auxiliary Function ------------------------------------------------------------------------------
def __get_deal_type(
    order_type: ENUM_ORDER_TYPE,
) -> ENUM_DEAL_TYPE:
    """
    Determina o tipo de deal com base no tipo de ordem (compra ou venda).

    Args:
        order_type (ENUM_ORDER_TYPE): Tipo de ordem (compra, venda, limite, stop, etc.).

    Raises:
        TypeError: Levantado se o tipo de ordem for inválido ou não reconhecido.

    Returns:
        ENUM_DEAL_TYPE: Tipo de deal correspondente:
            - `DEAL_TYPE_BUY`: Representa uma operação de compra.
            - `DEAL_TYPE_SELL`: Representa uma operação de venda.
    """

    # Verifica se o tipo de ordem é uma operação de compra (buy)
    if order_type in (
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY,  # Ordem de compra a mercado.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,  # Ordem de compra limite.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,  # Ordem de compra stop.
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,  # Ordem de compra stop com limite.
    ):
        return ENUM_DEAL_TYPE.DEAL_TYPE_BUY  # Retorna o tipo de deal "BUY".

    # Verifica se o tipo de ordem é uma operação de venda (sell)
    if order_type in (
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL,  # Ordem de venda a mercado.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,  # Ordem de venda limite.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,  # Ordem de venda stop.
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,  # Ordem de venda stop com limite.
    ):
        return ENUM_DEAL_TYPE.DEAL_TYPE_SELL  # Retorna o tipo de deal "SELL".

    # Lança um erro se o tipo de ordem não for reconhecido
    raise TypeError("Invalid order type")

def __get_entry(
    volume: float,
    order_type: ENUM_ORDER_TYPE,
    position: MqlPositionInfo,
) -> ENUM_DEAL_ENTRY:
    """
    Determina o tipo de entrada do deal com base no volume da ordem, tipo de ordem
    e direção da posição aberta.

    Args:
        volume (float): Volume do deal (lote).
        order_type (ENUM_ORDER_TYPE): Tipo de ordem (compra, venda, limite, stop, etc.).
        position (MqlPositionInfo): Informações da posição aberta, incluindo tipo e volume.

    Returns:
        ENUM_DEAL_ENTRY: Tipo de entrada do deal:
            - `DEAL_ENTRY_IN`: Nova entrada (abertura de posição na mesma direção).
            - `DEAL_ENTRY_OUT`: Fechamento total ou parcial da posição aberta.
            - `DEAL_ENTRY_INOUT`: Reversão (fechamento e abertura de posição oposta).
    """

    # **Verificação de direções opostas:**
    # - Caso 1: A posição atual é "BUY" (compra) e a ordem é de "SELL" (venda).
    # - Caso 2: A posição atual é "SELL" (venda) e a ordem é de "BUY" (compra).
    if (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
        and order_type
        in (
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
            ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
        )
    ) or (
        position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
        and order_type
        in (
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
            ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
        )
    ):
        # **Caso 1: Fechamento total ou parcial da posição existente:**
        if volume <= position.volume:
            return ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT  # Entrada de tipo "OUT" (fechamento da posição).

        # **Caso 2: Reversão de posição:**
        # - Quando o volume da nova ordem é maior que o volume da posição atual.
        return ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT  # Entrada "INOUT" (reverte a posição).

    # **Caso 3: Nova entrada (posição na mesma direção):**
    # Retorna "IN" se a posição atual e a nova ordem têm a mesma direção.
    return ENUM_DEAL_ENTRY.DEAL_ENTRY_IN

def __backtest_get_profit(
    operation_class: "Operation",
    symbol: str,
    price_open: float,
    price_close: float,
    price_volume: float,
    position_type: ENUM_POSITION_TYPE,
    account_currency: str,
) -> float:
    """
    Calcula o lucro ou prejuízo de uma posição de backtest com base nos preços de abertura e fechamento,
    volume negociado e moeda base da conta.

    Args:
        operation_class (Operation): Classe de operação com dados de conversão e parâmetros de negociação.
        symbol (str): Par de moedas (exemplo: "EURUSD").
        price_open (float): Preço de abertura da posição.
        price_close (float): Preço de fechamento da posição.
        price_volume (float): Volume da posição em lotes.
        position_type (ENUM_POSITION_TYPE): Tipo de posição (compra ou venda).
        account_currency (str): Moeda base da conta de negociação (exemplo: "USD").

    Returns:
        float: Lucro ou prejuízo calculado da posição.
    """

    # Calcula o lucro da posição usando a função `compute_profit`.
    profit: float = compute_profit(
        operation_class=operation_class,
        position_type=position_type,
        price_open=price_open,
        price_close=price_close,
        price_volume=price_volume,
        symbol=symbol,
        account_currency=account_currency,
    )

    return profit

def __validate_operation_handler_attributes_for_symbol(
    operation_class: "Operation",  # Objeto que gerencia os dados de operação e informações da conta
    symbol: str,  # Par de moedas (ex.: "EURUSD")
):
    # Verifica se há dados de candles disponíveis para a simulação.
    if not operation_class.last_candle:
        raise ValueError("Dados de candles ausentes: 'last_candle' não definido.")

    # Verifica se o par de moedas está presente nos dados de candles.
    if symbol not in operation_class.last_candle:
        raise ValueError(f"O símbolo '{symbol}' não está presente nos dados de candles.")

    # Verifica se há informações sobre tick sizes disponíveis.
    if not operation_class.tick_sizes:
        raise ValueError("Tamanhos de tick ausentes: 'tick_sizes' não definidos.")

    # Verifica se o par de moedas está presente nos dados de tick sizes.
    if symbol not in operation_class.tick_sizes:
        raise ValueError(f"O símbolo '{symbol}' não está presente nos tick sizes.")

    # Verifica se há informações sobre contract sizes disponíveis.
    if not operation_class.contract_sizes:
        raise ValueError("Tamanhos dos contratos ausentes: 'contract_sizes' não definidos.")

    # Verifica se o par de moedas está presente nos dados de contract sizes.
    if symbol not in operation_class.contract_sizes:
        raise ValueError(f"O símbolo '{symbol}' não está presente nos contract sizes.")


# Create Deal -------------------------------------------------------------------------------------
def __backtest_create_a_deal(
    operation_class: "Operation",  # Objeto que gerencia os dados de operação e informações da conta
    symbol: str,  # Par de moedas (ex.: "EURUSD")
    deal_time: datetime,  # Data e hora em que o deal é realizado
    order_type: ENUM_ORDER_TYPE,  # Tipo de ordem (ex.: BUY, SELL)
    volume: float,  # Volume da ordem (em lotes)
    price: float,  # Preço da execução do deal
    position: MqlPositionInfo,  # Informações da posição aberta (tipo, volume, preço de abertura, etc.)
    fee: float = 0,  # Taxa da ordem (opcional)
    commission: float = 0,  # Comissão aplicada na execução (opcional)
    order: int = None,  # Identificador da ordem (opcional)
    comment: str = "",  # Comentário sobre o deal (opcional)
) -> MqlTradeDeal:
    """
    Cria um deal durante o backtest.

    Args:
        operation_class (Operation): Classe de operação com dados de conversão e informações da conta.
        symbol (str): Par de moedas (exemplo: "EURUSD").
        deal_time (datetime): Data e hora do deal.
        order_type (ENUM_ORDER_TYPE): Tipo de ordem (compra, venda, limite, etc.).
        volume (float): Volume da ordem em lotes.
        price (float): Preço da execução do deal.
        position (MqlPositionInfo): Informações da posição aberta (tipo, volume, preço de abertura, etc.).
        fee (float, optional): Taxa aplicada à ordem. Padrão: 0.
        commission (float, optional): Comissão aplicada à ordem. Padrão: 0.
        order (int, optional): ID da ordem. Se `None`, será gerado automaticamente.
        comment (str, optional): Comentário sobre o deal. Padrão: "".

    Returns:
        MqlTradeDeal: Objeto contendo os detalhes do deal.
    """

    # **1. Geração do ticket do deal**
    # Gera um número de ticket exclusivo com base no timestamp em milissegundos.
    random_ticket = get_timestamp_ms(deal_time)

    # **2. Definição do ID da ordem**
    # Se um ID de ordem não for fornecido, gera um ID automaticamente com base no timestamp atual.
    order_id = (
        order if order is not None else get_timestamp_ms(datetime.now(timezone.utc))
    )

    # **3. Determinação do tipo de deal (BUY/SELL)**
    # Utiliza a função `__get_deal_type` para retornar o tipo de deal correspondente ao tipo de ordem.
    deal_type = __get_deal_type(order_type=order_type)

    # **4. Determinação do tipo de entrada (IN, OUT, INOUT)**
    # Verifica se o deal é uma entrada (`IN`), saída (`OUT`) ou reversão (`INOUT`).
    entry = __get_entry(
        order_type=order_type,
        volume=volume,
        position=position,
    )

    # **5. Cálculo do lucro do deal**
    if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_IN:
        # Para saídas ou reversões, calcula o volume de fechamento:
        # - Para `OUT`: Usa o volume informado.
        # - Para `INOUT`: Fecha totalmente a posição atual.
        close_volume = (
            volume if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT else position.volume
        )

        # Chama `__backtest_get_profit` para calcular o lucro ou prejuízo do deal.
        profit = __backtest_get_profit(
            operation_class=operation_class,
            symbol=symbol,
            account_currency=operation_class.account_data.currency,
            position_type=position.type,
            price_open=position.price_open,  # Preço de abertura da posição original
            price_close=price,  # Preço de fechamento do deal
            price_volume=close_volume,  # Volume utilizado no cálculo
        )        

    else:
        # Para entradas (`IN`), o lucro é sempre zero, pois é uma nova posição aberta.
        profit = 0

    # **6. Criação do objeto `MqlTradeDeal`**
    deal = MqlTradeDeal(
        symbol=symbol,  # Par de moedas
        ticket=random_ticket,  # ID exclusivo do deal
        order=order_id,  # ID da ordem
        time=deal_time.replace(microsecond=0),  # Data/hora do deal (sem microsegundos)
        time_msc=deal_time,  # Data/hora completa em milissegundos
        type=deal_type,  # Tipo de deal (BUY/SELL)
        entry=entry,  # Tipo de entrada (IN, OUT, INOUT)
        position_id=position.ticket,  # ID da posição associada ao deal
        volume=volume,  # Volume do deal em lotes
        price=price,  # Preço da execução do deal
        commission=commission,  # Comissão aplicada ao deal
        swap=0,  # Swap (zero para backtests)
        profit=profit,  # Lucro ou prejuízo do deal
        fee=fee,  # Taxa associada ao deal
        comment=comment,  # Comentário sobre o deal
        magic=operation_class.account_data.magic_number,  # Magic number para identificação automática
        reason=ENUM_DEAL_REASON.DEAL_REASON_EXPERT,  # Razão do deal (por expert)
        external_id=None,  # ID externo (não utilizado)
    )

    # **7. Retorno do objeto `MqlTradeDeal`**
    return deal

# Open Position -----------------------------------------------------------------------------------
def __hedge_create_position_and_deal(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    position_time: datetime,
    price: float,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> None:
    """
    Cria uma nova posição e um deal correspondente em uma conta de backtest com hedge habilitado.

    Args:
        operation_class (Operation): Classe de operação contendo dados da conta e métodos auxiliares.
        symbol (str): Par de moedas negociado (ex.: "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Tipo de ordem de mercado (BUY/SELL).
        position_time (datetime): Momento de criação da posição.
        price (float): Preço de execução da ordem.
        volume (float): Volume da ordem em lotes.
        stop_price (float, optional): Preço de stop-loss. Defaults to 0.
        profit_price (float, optional): Preço de take-profit. Defaults to 0.
        commission (float, optional): Comissão aplicada ao deal. Defaults to 0.
        fee (float, optional): Taxas adicionais aplicadas ao deal. Defaults to 0.
        comment (str, optional): Comentário opcional sobre a operação. Defaults to "".

    Returns:
        None: A função não retorna nada, mas atualiza os dados de posição e histórico de deals.
    """

    # Gera um identificador único para a posição com base no timestamp do horário da posição.
    position_time_ms = get_timestamp_ms(position_time)

    # Converte o tipo de ordem de mercado (BUY/SELL) para o tipo de posição correspondente.
    position_type = ENUM_POSITION_TYPE(order_type)

    # Criação do objeto `MqlPositionInfo` representando a posição aberta.
    position = MqlPositionInfo(
        ticket=get_timestamp_ms(datetime.now(tz=timezone.utc)),  # Ticket único gerado com timestamp.
        time=position_time,  # Tempo de abertura da posição.
        time_msc=position_time,  # Tempo com precisão de milissegundos.
        time_update=position_time,  # Tempo da última atualização (inicialmente igual ao de abertura).
        time_update_msc=position_time,  # Tempo com precisão em milissegundos.
        type=position_type,  # Tipo de posição (compra/venda).
        magic=operation_class.account_data.magic_number,  # Identificador do robô/expert.
        identifier=position_time_ms,  # Identificador único da posição.
        reason=ENUM_POSITION_REASON.POSITION_REASON_EXPERT,  # Razão da abertura (expert advisor).
        volume=volume,  # Volume da posição em lotes.
        price_open=price,  # Preço de abertura da posição.
        price_current=price,  # Preço atual da posição (inicialmente igual ao preço de abertura).
        sl=stop_price,  # Preço de stop-loss.
        tp=profit_price,  # Preço de take-profit.
        swap=0,  # Swap (não aplicável no backtest).
        profit=0,  # Lucro (inicialmente zero).
        symbol=symbol,  # Símbolo negociado (par de moedas).
        comment=comment,  # Comentário opcional.
        external_id=None,  # ID externo (não utilizado no backtest).
    )

    # Criação de um `MqlTradeDeal` correspondente à nova posição.
    deal = __backtest_create_a_deal(
        operation_class=operation_class,  # Classe de operação associada.
        position=position,  # Posição para a qual o deal será criado.
        symbol=symbol,  # Par de moedas do deal.
        order_type=order_type,  # Tipo de ordem associada ao deal (BUY/SELL).
        deal_time=position.time,  # Tempo do deal.
        price=position.price_current,  # Preço de execução do deal.
        volume=volume,  # Volume do deal.
        fee=fee,  # Taxa adicional.
        commission=commission,  # Comissão aplicada.
        order=None,  # ID da ordem (None significa que será gerado um novo ID automaticamente).
        comment=comment,  # Comentário opcional.
    )

    # Adiciona a nova posição ao conjunto de posições abertas.
    operation_class.account_data.positions.append(position)

    # Adiciona o deal ao histórico de deals.
    operation_class.account_data.history_deals.append(deal)

def __netting_create_position_and_deal(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    position_time: datetime,
    price: float,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> None:
    """
    Cria ou atualiza uma posição em uma conta de backtest com netting habilitado.

    Em contas netting, é mantida apenas uma posição agregada por símbolo.
    Dependendo do tipo de operação (compra/venda) e do volume, pode ocorrer
    fechamento parcial, total ou reversão de posição.

    Args:
        operation_class (Operation): Classe de operação contendo dados da conta e métodos auxiliares.
        symbol (str): Par de moedas negociado (ex.: "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Tipo de ordem de mercado (BUY/SELL).
        position_time (datetime): Momento de criação da posição.
        price (float): Preço de execução da ordem.
        volume (float): Volume da ordem em lotes.
        stop_price (float, optional): Preço de stop-loss. Defaults to 0.
        profit_price (float, optional): Preço de take-profit. Defaults to 0.
        commission (float, optional): Comissão aplicada ao deal. Defaults to 0.
        fee (float, optional): Taxa adicional aplicada ao deal. Defaults to 0.
        comment (str, optional): Comentário opcional sobre a operação. Defaults to "".

    Returns:
        None: A função não retorna nada, mas atualiza os dados de posição e histórico de deals.
    """

    # Gera um identificador único para a posição com base no timestamp do horário da posição.
    position_time_ms = get_timestamp_ms(position_time)

    # Converte o tipo de ordem de mercado (BUY/SELL) para o tipo de posição correspondente.
    position_type = ENUM_POSITION_TYPE(order_type)

    # Criação do objeto `MqlPositionInfo` representando a posição aberta.
    position = MqlPositionInfo(
        ticket=get_timestamp_ms(datetime.now(tz=timezone.utc)),  # Ticket único gerado com timestamp.
        time=position_time,  # Tempo de abertura da posição.
        time_msc=position_time,  # Tempo com precisão de milissegundos.
        time_update=position_time,  # Tempo da última atualização (inicialmente igual ao de abertura).
        time_update_msc=position_time,  # Tempo com precisão em milissegundos.
        type=position_type,  # Tipo de posição (compra/venda).
        magic=operation_class.account_data.magic_number,  # Identificador do robô/expert.
        identifier=position_time_ms,  # Identificador único da posição.
        reason=ENUM_POSITION_REASON.POSITION_REASON_EXPERT,  # Razão da abertura (expert advisor).
        volume=volume,  # Volume da posição em lotes.
        price_open=price,  # Preço de abertura da posição.
        price_current=price,  # Preço atual da posição (inicialmente igual ao preço de abertura).
        sl=stop_price,  # Preço de stop-loss.
        tp=profit_price,  # Preço de take-profit.
        swap=0,  # Swap (não aplicável no backtest).
        profit=0,  # Lucro (inicialmente zero).
        symbol=symbol,  # Símbolo negociado (par de moedas).
        comment=comment,  # Comentário opcional.
        external_id=None,  # ID externo (não utilizado no backtest).
    )

    # Verifica se já existe uma posição aberta para o símbolo.
    if operation_class.account_data.positions:
        opened_position = operation_class.account_data.positions[0]

        # A posição atualizada recebe o identificador e informações da posição aberta.
        position.identifier = opened_position.identifier
        position.volume = opened_position.volume
        position.type = opened_position.type

        # Caso a posição aberta seja na direção oposta à ordem atual.
        if opened_position.type != position_type:
            # Fechamento total: os volumes são iguais.
            if opened_position.volume == volume:
                deal = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Remove a posição fechada da lista de posições.
                del operation_class.account_data.positions[0]
                operation_class.account_data.history_deals.append(deal)

            # Fechamento parcial: volume da posição aberta é maior.
            elif opened_position.volume > volume:
                deal = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Atualiza o volume restante da posição após o fechamento parcial.
                position.volume = round(position.volume - volume, 2)
                operation_class.account_data.positions[0] = position
                operation_class.account_data.history_deals.append(deal)

            # Reversão de posição: volume da nova ordem é maior.
            elif opened_position.volume < volume:
                # Gera um novo identificador para a posição revertida.
                position.identifier = position_time_ms

                # Cria um deal de fechamento para a posição aberta.
                deal_close = __backtest_create_a_deal(
                    deal_time=position.time,
                    position=opened_position,
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    price=position.price_current,
                    operation_class=operation_class,
                    fee=fee,
                    commission=commission,
                    order=None,
                    comment=comment,
                )

                # Calcula o novo volume e atualiza o tipo de posição.
                position.volume = round(abs(position.volume - volume), 2)
                if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
                    position.type = ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                else:
                    position.type = ENUM_POSITION_TYPE.POSITION_TYPE_BUY

                # Atualiza o preço de abertura com o preço atual.
                position.price_open = position.price_current

                operation_class.account_data.positions[0] = position
                operation_class.account_data.history_deals.append(deal_close)

        # Caso a nova ordem seja na mesma direção da posição aberta.
        else:
            deal = __backtest_create_a_deal(
                deal_time=position.time,
                position=position,
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=position.price_current,
                operation_class=operation_class,
                fee=fee,
                commission=commission,
                order=None,
                comment=comment,
            )

            # Calcula o novo volume total e preço médio ponderado.
            total_volume = round(position.volume + volume, 2)
            mean_price = (
                (opened_position.price_open * opened_position.volume)
                + (position.price_open * volume)
            ) / total_volume

            # Atualiza o volume, preço de abertura e preço atual.
            position.volume = total_volume
            position.price_open = mean_price
            position.price_current = price

            # Substitui a posição existente pela nova posição agregada.
            operation_class.account_data.positions[0] = position
            operation_class.account_data.history_deals.append(deal)
    else:
        # Cria uma nova posição se não houver posição aberta.
        deal = __backtest_create_a_deal(
            operation_class=operation_class,
            position=position,
            symbol=symbol,
            order_type=order_type,
            deal_time=position.time,
            price=position.price_current,
            volume=volume,
            fee=fee,
            commission=commission,
            order=None,
            comment=comment,
        )
        operation_class.account_data.positions.append(position)
        operation_class.account_data.history_deals.append(deal)

def __backtest_open_position(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_MARKET,
    volume: float,
    stop_price: float = 0,
    profit_price: float = 0,
    commission: float = 0,
    fee: float = 0,
    comment: str = "",
) -> bool:
    """
    Abre uma posição em uma conta de backtest.

    Esta função simula a abertura de uma posição de mercado em um ambiente de backtest,
    utilizando dados de candles e spread simulados para replicar condições realistas.

    Args:
        operation_class (Operation): Classe de operação com dados da conta e contexto de backtest.
        symbol (str): Par de moedas ou ativo a ser negociado (ex.: "EURUSD").
        order_type (ENUM_ORDER_TYPE_MARKET): Tipo de ordem de mercado (ex.: BUY ou SELL).
        volume (float): Volume da posição (tamanho do lote).
        stop_price (float, optional): Preço de stop-loss. Padrão: 0 (sem stop-loss).
        profit_price (float, optional): Preço de take-profit. Padrão: 0 (sem take-profit).
        commission (float, optional): Comissão aplicada à operação. Padrão: 0.
        fee (float, optional): Taxa adicional aplicada à operação. Padrão: 0.
        comment (str, optional): Comentário opcional sobre a operação. Padrão: "".

    Returns:
        bool: True, indicando que a ordem foi processada com sucesso na simulação.

    Raises:
        ValueError: Caso dados essenciais como candles, spreads ou tamanhos de tick estejam ausentes.
    """
    __validate_operation_handler_attributes_for_symbol(operation_class=operation_class, symbol=symbol)

    # Recupera o candle mais recente para simular o estado de mercado atual.
    last_candle = operation_class.last_candle[symbol]

    # Define o timestamp do candle como o tempo da posição.
    position_time = last_candle.name

    # Recupera o spread simulado e o tamanho de tick para o par de moedas.
    simulated_spread: int = operation_class.account_data.simulated_spread
    trade_tick_size: float = operation_class.tick_sizes[symbol]

    # Define o preço de entrada com base no tipo de ordem (compra ou venda).
    if order_type == ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY:
        # Ordem de compra: utiliza o preço de fechamento do candle + spread (para simular o preço ASK).
        price = last_candle.close + (trade_tick_size * simulated_spread)
    else:
        # Ordem de venda: utiliza diretamente o preço de fechamento do candle (para simular o preço BID).
        price = last_candle.close

    # Verifica o tipo de conta e aplica a lógica correspondente:
    # - Hedge: permite múltiplas posições na mesma direção ou direções opostas.
    # - Netting: permite apenas uma posição agregada por símbolo.
    if (
        operation_class.account_data.margin_mode == ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
    ):
        # Cria uma nova posição e deal para contas hedge.
        __hedge_create_position_and_deal(
            operation_class=operation_class,
            symbol=symbol,
            order_type=order_type,
            position_time=position_time,
            price=price,
            stop_price=stop_price,
            profit_price=profit_price,
            volume=volume,
            commission=commission,
            fee=fee,
            comment=comment,
        )
    else:
        # Cria ou atualiza a posição agregada para contas netting.
        __netting_create_position_and_deal(
            operation_class=operation_class,
            symbol=symbol,
            order_type=order_type,
            position_time=position_time,
            price=price,
            stop_price=stop_price,
            profit_price=profit_price,
            volume=volume,
            commission=commission,
            fee=fee,
            comment=comment,
        )

    # Retorna True para indicar que a operação foi bem-sucedida na simulação.
    return True

# Open Pending Order ------------------------------------------------------------------------------
def __backtest_open_pending_order(
    trade_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_PENDING,
    volume: float,
    price: float,
    stop_limit: float = 0,
    stop_price: float = 0,
    profit_price: float = 0,
    expiration: datetime = None,
    comment: str = "",
):
    order_time = datetime.now(timezone.utc)
    current_time_ms = get_timestamp_ms(order_time)

    type_time = (
        ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
        if expiration
        else ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC
    )

    order = MqlTradeOrder(
        ticket=current_time_ms,
        symbol=symbol,
        type=order_type,
        time_setup=order_time.replace(microsecond=0),
        time_setup_msc=order_time,
        volume_initial=volume,
        volume_current=volume,
        price_stoplimit=stop_limit,
        price_open=price,
        price_current=price,
        tp=profit_price,
        sl=stop_price,
        type_time=type_time,
        time_expiration=expiration,
        state=ENUM_ORDER_STATE.ORDER_STATE_PLACED,
        reason=ENUM_ORDER_REASON.ORDER_REASON_EXPERT,
        magic=trade_class.magic_number,
        type_filling=trade_class.type_filling,
        comment=comment,
    )

    trade_class.account_data.orders.append(order)

def __backtest_modify_pending_order(
    trade_class: "Operation",
    ticket: int,
    price: float,
    stop_price: float = 0,
    profit_price: float = 0,
    expiration: datetime = None,
    comment: str = "",
):
    # Select the order
    order: MqlTradeOrder = get_order(
        list_orders=trade_class.account_data.orders, ticket=ticket
    )

    if expiration:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    else:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC

    # Change the order attributes
    order.update(
        price_open=price,
        sl=stop_price,
        tp=profit_price,
        comment=comment,
        type_filling=trade_class.type_filling,
        magic=trade_class.magic_number,
        time_expiration=expiration,
        type_time=type_time,
    )

def __backtest_modify_position(
    trade_class: "Operation",
    stop_price: float = None,
    profit_price: float = None,
    position: int = None,
    comment: str = "",
):
    position_not_found_error = CouldNotSelectPosition(
        "[ERROR]: Could not select the position."
    )

    # If position not received, try to get it
    if position is None:
        # If there is only one position opened, get it
        if len(trade_class.account_data.positions) == 1:
            position = trade_class.account_data.positions[0].ticket
        else:
            raise position_not_found_error

    # Get the position from account positions
    position_selected: List[MqlPositionInfo] = [
        mqlposition
        for mqlposition in trade_class.account_data.positions
        if mqlposition.ticket == position
    ]

    # Check if the position exists
    if len(position_selected) != 1:
        raise position_not_found_error

    # Select the position object
    position_selected: MqlSymbolInfo = position_selected[0]

    position_selected.update(
        sl=stop_price,
        tp=profit_price,
        commen=comment,
    )

def __backtest_close_position(
    operation_class: "Operation",  # Classe de operação com informações sobre a conta e métodos auxiliares.
    position_ticket: int,  # Ticket da posição que será encerrada.
    commission: float = 0,  # Comissão aplicada ao fechamento da posição.
    fee: float = 0,  # Taxa associada ao fechamento da posição.
    comment: str = "",  # Comentário opcional sobre o fechamento.
):
    """
    Fecha uma posição em modo de backtest.

    Args:
        operation_class (Operation): Classe de operação com dados da conta e métodos auxiliares.
        position_ticket (int): ID da posição que será fechada.
        commission (float, optional): Comissão cobrada na operação de fechamento. Padrão: 0.
        fee (float, optional): Taxa adicional aplicada na operação. Padrão: 0.
        comment (str, optional): Comentário sobre o fechamento da posição. Padrão: "".

    Raises:
        CouldNotSelectPosition: Exceção levantada caso a posição com o `ticket` especificado não seja encontrada.
    """

    # **1. Seleção da Posição**
    # Busca a posição com o `ticket` fornecido na lista de posições abertas.
    position_selected: List[MqlPositionInfo] = [
        position
        for position in operation_class.account_data.positions
        if position.ticket == position_ticket
    ]

    # **2. Verificação da Existência da Posição**
    # Verifica se apenas uma posição corresponde ao `ticket`.
    if len(position_selected) != 1:
        raise CouldNotSelectPosition("[ERROR]: Could not select the position.")  # Exceção caso não exista ou existam múltiplas posições com o mesmo `ticket`.

    # **3. Seleção da Posição**
    # Recupera o objeto da posição.
    position_selected: MqlPositionInfo = position_selected[0]
    symbol = position_selected.symbol  # Par de moedas da posição.

    # **4. Validação de Atributos**
    # Valida se o `operation_class` possui atributos válidos para o símbolo em questão.
    __validate_operation_handler_attributes_for_symbol(
        operation_class=operation_class, symbol=symbol
    )

    # **5. Recuperação do Último Candle**
    # Obtém o último candle do par de moedas para simular o estado de mercado.
    last_candle = operation_class.last_candle[symbol]
    deal_time = last_candle.name  # Define o timestamp do candle como o tempo do deal.
    simulated_spread: int = operation_class.account_data.simulated_spread  # Spread simulado em pontos.
    trade_tick_size: float = operation_class.tick_sizes[symbol]  # Tamanho mínimo do tick de preço.

    # **6. Definição do Tipo de Ordem e Preço**
    # Determina o tipo de ordem e o preço com base no tipo de posição aberta.
    if position_selected.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        # **Para posições de compra:**
        # - O fechamento é uma ordem de venda (`SELL`).
        # - O preço de fechamento é o preço de `close` do candle ajustado pelo spread (simulando o preço ASK).
        price = last_candle.close + (trade_tick_size * simulated_spread)
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_SELL  # Ordem de venda.
    else:
        # **Para posições de venda:**
        # - O fechamento é uma ordem de compra (`BUY`).
        # - O preço de fechamento é o preço de `close` do candle (simulando o preço BID).
        price = last_candle.close
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY  # Ordem de compra.

    # **7. Criação do Deal de Fechamento**
    # Cria o objeto `MqlTradeDeal` com as informações do fechamento.
    deal = __backtest_create_a_deal(
        deal_time=deal_time,  # Data/hora do deal.
        position=position_selected,  # Posição a ser fechada.
        symbol=symbol,  # Par de moedas.
        order_type=order_type,  # Tipo de ordem (BUY/SELL).
        volume=position_selected.volume,  # Volume da posição.
        price=price,  # Preço de execução.
        fee=fee,  # Taxa associada ao deal.
        commission=commission,  # Comissão aplicada.
        order=None,  # ID da ordem (gerado automaticamente).
        comment=comment,  # Comentário sobre o fechamento.
        operation_class=operation_class,  # Classe de operação.
    )

    # **8. Registro do Deal no Histórico**
    # Adiciona o deal ao histórico de operações realizadas.
    operation_class.account_data.history_deals.append(deal)

    # **9. Remoção da Posição**
    # Remove a posição da lista de posições abertas.
    del operation_class.account_data.positions[
        operation_class.account_data.positions.index(position_selected)
    ]

# Decorators --------------------------------------------------------------------------------------
def decorator_backtest_open_position(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_open_position(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account

def decorator_backtest_open_pending_order(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_open_pending_order(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account

def decorator_backtest_modify_position(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_modify_position(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account

def decorator_backtest_modify_pending_order(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_modify_pending_order(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account

def decorator_backtest_close_position(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_close_position(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account
