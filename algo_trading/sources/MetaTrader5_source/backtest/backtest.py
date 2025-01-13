# **Bibliotecas de Tipagem e Manipulação de Datas**
from typing import (
    Callable,
    List,
    TYPE_CHECKING,
)

# Tipos usados para anotações de funções e listas tipadas
from datetime import (
    datetime,
    timezone,
    time,
    timedelta,
)

# Para manipulação de objetos de data/hora com fuso horário UTC
import time as time_rand

# Para geração dos tickets aleatórios
import random

# **Modelos e Enums do MetaTrader5**
from algo_trading.sources.MetaTrader5_source.models.metatrader import (
    MqlPositionInfo,  # Modelo com informações sobre uma posição aberta
    MqlTradeDeal,  # Modelo com informações sobre um deal de trade (resultado de execução)
    MqlTradeOrder,  # Modelo com informações sobre uma ordem de trade pendente ou executada
    ENUM_ACCOUNT_MARGIN_MODE,  # Enum para modos de margem da conta (ex.: netting, hedging)
    ENUM_DEAL_TYPE,  # Enum para tipos de deal (ex.: DEAL_TYPE_BUY, DEAL_TYPE_SELL)
    ENUM_DEAL_ENTRY,  # Enum para tipos de entrada no mercado (IN - entrada, OUT - saída, INOUT - reversão)
    ENUM_DEAL_REASON,  # Enum para motivos de execução de um deal (ex.: expert, manual)
    ENUM_ORDER_TYPE,  # Enum para tipos de ordens (compra, venda, limite, stop, etc.)
    ENUM_ORDER_REASON,  # Enum para razões de execução de ordens (ex.: robô, usuário, stop-out)
    ENUM_ORDER_TYPE_MARKET,  # Enum específico para ordens de mercado (compra/venda a mercado)
    ENUM_ORDER_TYPE_PENDING,  # Enum específico para ordens pendentes (ex.: buy limit, sell stop)
    ENUM_ORDER_STATE,  # Enum para estados de uma ordem (pendente, concluída, cancelada, etc.)
    ENUM_POSITION_REASON,  # Enum para motivos de abertura de posição (ex.: expert advisor)
    ENUM_POSITION_TYPE,  # Enum para tipos de posição aberta (ex.: buy/sell)
    ENUM_ORDER_TYPE_TIME,  # Enum para tipos de ordens baseados em tempo (ex.: Good Till Canceled - GTC)
    ENUM_SYMBOL_CALC_MODE,  # Enum para tipo de calculo de lucro e margin
    ENUM_ACCOUNT_STOPOUT_MODE,
    ENUM_SYMBOL_SWAP_MODE,
    validate_prices,
)


# **Utilitários para Funções de Datas, Trades e Exceções**
from algo_trading.sources.MetaTrader5_source.utils.dates import (
    get_timestamp_ms,
)  # Função que retorna timestamp em milissegundos
from algo_trading.sources.MetaTrader5_source.utils.trades import (
    compute_profit,  # Função que calcula o lucro ou prejuízo de uma posição com base nos preços e volumes
    get_order,  # Função que busca uma ordem específica a partir do seu `ticket`
)
from algo_trading.sources.MetaTrader5_source.utils.exceptions import (
    CouldNotSelectPosition,
    InsufficientMarginError,
)  # Exceção personalizada para quando uma posição não pode ser selecionada

# **Configuração de Logs**
import logging  # Biblioteca de logging para registrar informações durante a execução

import pandas as pd
from decimal import Decimal


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)  # Configuração do formato e nível de logs

# **Importação Condicional para Tipagem**
# Importa `Operation` apenas em tempo de análise estática para evitar dependências cíclicas.
if TYPE_CHECKING:
    from algo_trading.sources.MetaTrader5_source.operation.operation import (
        Operation,
    )  # Classe responsável por gerenciar as operações


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
            return (
                ENUM_DEAL_ENTRY.DEAL_ENTRY_OUT
            )  # Entrada de tipo "OUT" (fechamento da posição).

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
    )

    return profit


def __validate_operation_handler_attributes_for_symbol(
    operation_class: "Operation",  # Objeto que gerencia os dados de operação e informações da conta
    symbol: str,  # Par de moedas (ex.: "EURUSD")
):
    """
    Valida os atributos necessários para o símbolo especificado no contexto de operações
    de backtest. Verifica a existência de dados obrigatórios em um DataFrame indexado por símbolo.
    """
    # DataFrame com os dados de backtest
    symbols_data = operation_class.backtest_symbols_data

    # Verifica se o índice do símbolo existe no DataFrame
    if symbol not in symbols_data.index:
        raise ValueError(
            f"Dados para o símbolo '{symbol}' estão ausentes no DataFrame."
        )

    # Extração dos dados da linha correspondente ao símbolo
    symbol_data = symbols_data.loc[symbol]

    # Lista de colunas obrigatórias para validação
    required_columns = [
        "tick_size",  # Tick size (float)
        "contract_size",  # Contract size (int)
        "trade_calc_mode",  # Enum para modo de cálculo (int)
        "swap_mode",  # Enum para swap mode (int)
        "swap_long",  # Taxa de swap long (float)
        "swap_short",  # Taxa de swap short (float)
        "swap_rollover3days",  # Dia de rollover (int)
        "last_candle",  # Último candle (Series ou equivalente)
    ]

    # Verifica se todas as colunas obrigatórias estão presentes
    missing_columns = [
        col for col in required_columns if col not in symbols_data.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Os dados para o símbolo '{symbol}' estão faltando as colunas necessárias: {', '.join(missing_columns)}."
        )

    # Validação de valores nulos ou ausentes para o símbolo específico
    if symbol_data.isnull().any():
        raise ValueError(
            f"Os dados para o símbolo '{symbol}' contêm valores nulos ou ausentes nas seguintes colunas: "
            f"{', '.join(symbol_data[symbol_data.isnull()].index)}."
        )

    # Validação de valores críticos para o símbolo
    if symbol_data["tick_size"] <= 0:
        raise ValueError(
            f"O 'tick_size' deve ser maior que zero para o símbolo '{symbol}'."
        )
    if symbol_data["contract_size"] <= 0:
        raise ValueError(
            f"O 'contract_size' deve ser maior que zero para o símbolo '{symbol}'."
        )

    # Validação específica da coluna 'last_candle'
    if (
        not isinstance(symbol_data["last_candle"], pd.Series)
        or symbol_data["last_candle"].empty
    ):
        raise ValueError(
            f"A coluna 'last_candle' para o símbolo '{symbol}' é inválida ou está vazia."
        )

    # Validação bem-sucedida
    return True


def __generate_unique_ticket():
    """
    Gera um ticket único combinando timestamp em milissegundos e número aleatório.

    Returns:
        int: Ticket único.
    """
    # Timestamp atual em milissegundos
    timestamp_ms = int(time_rand.time() * 1000)

    # Número aleatório grande para adicionar mais aleatoriedade (7 dígitos)
    random_part = random.randint(1000000, 9999999)

    # Combina os dois para formar o ticket
    ticket = int(f"{timestamp_ms}{random_part}")

    return ticket


def __convert_order_to_position_type(order_type: ENUM_ORDER_TYPE) -> ENUM_POSITION_TYPE:
    """
    Converte o tipo de ordem pendente para o tipo de posição correspondente (`BUY` ou `SELL`).

    Args:
        order_type (ENUM_ORDER_TYPE): Tipo de ordem pendente.

    Returns:
        ENUM_POSITION_TYPE: Tipo de posição correspondente.
    """
    if order_type in {
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT,
    }:
        return ENUM_POSITION_TYPE.POSITION_TYPE_BUY

    if order_type in {
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP,
        ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT,
    }:
        return ENUM_POSITION_TYPE.POSITION_TYPE_SELL

    raise ValueError(f"Tipo de ordem desconhecido: {order_type}")


def __validate_order_price(
    operation_class: "Operation", 
    symbol: str,
    order_type: ENUM_ORDER_TYPE, 
    price: float,
    stop_limit: float = 0
):
    last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle
    
    spread = (operation_class.account_data.simulated_spread * operation_class.backtest_symbols_data.loc[symbol].tick_size)
    # **Validações específicas por tipo de ordem**
    if order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT:
        if price > last_candle["close"] + spread:
            raise ValueError(
                f"Preço {price} para BUY_LIMIT deve ser menor que o preço atual ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT:
        if price < last_candle["close"]:
            raise ValueError(
                f"Preço {price} para SELL_LIMIT deve ser maior que o preço atual ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP:
        if price < last_candle["close"] + spread:
            raise ValueError(
                f"Preço {price} para BUY_STOP deve ser maior que o preço atual ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP:
        if price > last_candle["close"]:
            raise ValueError(
                f"Preço {price} para SELL_STOP deve ser menor que o preço atual ({last_candle['close']})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT:
        if price < last_candle["close"] + spread:
            raise ValueError(
                f"Preço inicial {price} para BUY_STOP_LIMIT deve ser maior que o preço atual ({last_candle['close']})"
            )
        if stop_limit > price:
            raise ValueError(
                f"Preço de limite {stop_limit} para BUY_STOP_LIMIT deve ser menor que o preço inicial ({price})"
            )
    elif order_type == ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT:
        if price > last_candle["close"]:
            raise ValueError(
                f"Preço inicial {price} para SELL_STOP_LIMIT deve ser menor que o preço atual ({last_candle['close']})"
            )
        if stop_limit < price:
            raise ValueError(
                f"Preço de limite {stop_limit} para SELL_STOP_LIMIT deve ser maior que o preço inicial ({price})"
            )


def __validate_order_volume(
    operation_class: "Operation",
    symbol: str,
    order_type: ENUM_ORDER_TYPE_PENDING,
    volume: float,
):
    """
    Valida o volume da ordem pendente com base nas restrições de volume do símbolo, considerando ordens pendentes e posições abertas.

    Args:
        operation_class (Operation): Classe de operação contendo os dados de backtest.
        symbol (str): Símbolo do ativo (ex.: "EURUSD").
        order_type (ENUM_ORDER_TYPE_PENDING): Tipo de ordem pendente (ex.: BUY_LIMIT, SELL_STOP).
        volume (float): Volume da ordem pendente.

    Raises:
        ValueError: Se o volume não atender às restrições definidas.
    """
    symbol_data = operation_class.backtest_symbols_data.loc[symbol]

    volume_min = symbol_data.volume_min
    volume_max = symbol_data.volume_max
    volume_step = symbol_data.volume_step
    volume_limit = symbol_data.volume_limit

    # Verifica se o volume é inferior ao volume mínimo permitido
    if volume < volume_min:
        raise ValueError(
            f"Volume {volume} abaixo do mínimo permitido ({volume_min}) para {symbol}."
        )

    # Verifica se o volume é superior ao volume máximo permitido
    if volume > volume_max:
        raise ValueError(
            f"Volume {volume} acima do máximo permitido ({volume_max}) para {symbol}."
        )

    # Verifica se o volume respeita o incremento mínimo (volume_step)
    if Decimal(str(volume)) % Decimal(str(volume_step)) != 0:
        raise ValueError(
            f"Volume {volume} não é múltiplo do incremento mínimo ({volume_step}) para {symbol}."
        )

    # Determina a direção com base no tipo de ordem (compra/venda)
    is_buy_order = order_type in {
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
        ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
    }

    # Calcula o volume agregado na mesma direção (ordens pendentes + posições abertas)
    total_volume_in_direction = sum(
        order.volume_current
        for order in operation_class.account_data.orders
        if order.symbol == symbol
        and (order.type in {
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT,
        }
        if is_buy_order else
        order.type in {
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP,
            ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT,
        })
    ) + sum(
        position.volume
        for position in operation_class.account_data.positions
        if position.symbol == symbol
        and ((position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY) if is_buy_order else (position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL))
    )

    # Verifica se o volume agregado não ultrapassa o limite definido
    if volume_limit > 0 and total_volume_in_direction + volume > volume_limit:
        raise ValueError(
            f"O volume agregado na direção {'BUY' if is_buy_order else 'SELL'} ({total_volume_in_direction + volume}) excede o limite permitido ({volume_limit}) para {symbol}."
        )


def __validate_position_volume(
    operation_class: "Operation",
    symbol: str,
    position_type: ENUM_POSITION_TYPE,
    volume: float,
):
    """
    Valida o volume de uma posição com base nas restrições de volume do símbolo.

    Args:
        operation_class (Operation): Classe de operação contendo os dados de backtest.
        symbol (str): Símbolo do ativo (ex.: "EURUSD").
        position_type (ENUM_POSITION_TYPE): Tipo de ordem de mercado (ex.: BUY, SELL).
        volume (float): Volume da posição.

    Raises:
        ValueError: Se o volume não atender às restrições definidas.
    """
    symbol_data = operation_class.backtest_symbols_data.loc[symbol]

    volume_min = symbol_data.volume_min
    volume_max = symbol_data.volume_max
    volume_step = symbol_data.volume_step
    volume_limit = symbol_data.volume_limit

    # Verifica se o volume é inferior ao volume mínimo permitido
    if volume < volume_min:
        raise ValueError(
            f"Volume {volume} abaixo do mínimo permitido ({volume_min}) para {symbol}."
        )

    # Verifica se o volume é superior ao volume máximo permitido
    if volume > volume_max:
        raise ValueError(
            f"Volume {volume} acima do máximo permitido ({volume_max}) para {symbol}."
        )

    # Verifica se o volume respeita o incremento mínimo (volume_step)
    if Decimal(str(volume)) % Decimal(str(volume_step)) != 0:
        raise ValueError(
            f"Volume {volume} não é múltiplo do incremento mínimo ({volume_step}) para {symbol}."
        )

    # Calcula o volume agregado na direção da ordem (considerando posições abertas e ordens pendentes)
    total_volume_in_direction = sum(
        pos.volume
        for pos in operation_class.account_data.positions
        if pos.symbol == symbol and pos.type == position_type
    )

    # Verifica se o volume agregado não ultrapassa o limite definido
    if volume_limit > 0 and total_volume_in_direction + volume > volume_limit:
        raise ValueError(
            f"O volume agregado na direção {position_type.name} ({total_volume_in_direction + volume}) "
            f"excede o limite permitido ({volume_limit}) para {symbol}."
        )

# Create Deal -------------------------------------------------------------------------------------
def __backtest_create_a_deal(
    operation_class: "Operation",
    symbol: str,
    deal_time: datetime,
    order_type: ENUM_ORDER_TYPE,
    volume: float,
    price: float,
    position: MqlPositionInfo,
    fee: float = 0,
    commission: float = 0,
    order: int = None,
    comment: str = "",
) -> MqlTradeDeal:
    """
    Cria um deal durante o backtest e atualiza os dados da conta se for um fechamento ou reversão de posição.

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
    random_ticket = __generate_unique_ticket()

    # **2. Definição do ID da ordem**
    order_id = (
        order if order is not None else get_timestamp_ms(datetime.now(timezone.utc))
    )

    # **3. Determinação do tipo de deal (BUY/SELL)**
    deal_type = __get_deal_type(order_type=order_type)

    # **4. Determinação do tipo de entrada (IN, OUT, INOUT)**
    entry = __get_entry(order_type=order_type, volume=volume, position=position)

    # **5. Cálculo do lucro do deal**
    if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_IN:
        close_volume = (
            volume if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_INOUT else position.volume
        )

        profit = __backtest_get_profit(
            operation_class=operation_class,
            symbol=symbol,
            position_type=position.type,
            price_open=position.price_open,
            price_close=price,
            price_volume=close_volume,
        )
    else:
        profit = 0  # Entradas não têm lucro imediatamente

    # **6. Cálculo do Swap Proporcional ao Deal**
    if volume <= position.volume:
        # Fechamento parcial ou total: calcula o swap proporcional
        swap_deal = position.swap * (volume / position.volume) if position.swap else 0
        position.swap -= swap_deal  # Atualiza o swap restante na posição
    else:
        # Reversão: aplica todo o swap restante da posição e inicia com swap zero para o volume adicional
        swap_deal = position.swap  # Aplica todo o swap da posição
        position.swap = 0  # Zera o swap na posição
        volume_excedente = volume - position.volume  # Volume que reverteu a direção
        logging.info(
            f"[REVERSE] Reversão detectada - Volume excedente: {volume_excedente} lotes"
        )

    # **7. Ajuste do profit da conta para saídas e reversões**
    if entry != ENUM_DEAL_ENTRY.DEAL_ENTRY_IN:
        # Reduz o `profit` total das posições abertas
        operation_class.account_data.profit -= position.profit

        # Atualiza o saldo da conta com o lucro/prejuízo do fechamento
        operation_class.account_data.balance = round(
            operation_class.account_data.balance + profit + swap_deal, 2
        )

        # Recalcula a margem após o fechamento/reversão
        __backtest_account_update_margin(operation_class=operation_class)

    # **8. Criação do objeto `MqlTradeDeal`**
    deal = MqlTradeDeal(
        symbol=symbol,
        ticket=random_ticket,
        order=order_id,
        time=deal_time.replace(microsecond=0),
        time_msc=deal_time,
        type=deal_type,
        entry=entry,
        position_id=position.ticket,
        volume=volume,
        price=price,
        commission=commission,
        swap=round(swap_deal, 2),  # Swap aplicado ao deal
        profit=profit,
        fee=fee,
        comment=comment,
        magic=operation_class.account_data.magic_number,
        reason=ENUM_DEAL_REASON.DEAL_REASON_EXPERT,
        external_id=None,
    )

    # **9. Log do Deal**
    logging.info(
        f"[DEAL] {symbol} - Ticket: {random_ticket} | Tipo: {'BUY' if deal_type == ENUM_DEAL_TYPE.DEAL_TYPE_BUY else 'SELL'} "
        f"| Volume: {volume} | Preço: {price:.5f} | Lucro: {profit:.2f} | Swap Aplicado: {swap_deal:.2f} "
        f"| Saldo Atualizado: {operation_class.account_data.balance:.2f}"
    )

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
    # Converte o tipo de ordem de mercado (BUY/SELL) para o tipo de posição correspondente.
    position_type = __convert_order_to_position_type(order_type)

    # Criação do objeto `MqlPositionInfo` representando a posição aberta.
    position = MqlPositionInfo(
        ticket=__generate_unique_ticket(),  # Ticket único gerado com timestamp.
        time=position_time,  # Tempo de abertura da posição.
        time_msc=position_time,  # Tempo com precisão de milissegundos.
        time_update=position_time,  # Tempo da última atualização (inicialmente igual ao de abertura).
        time_update_msc=position_time,  # Tempo com precisão em milissegundos.
        type=position_type,  # Tipo de posição (compra/venda).
        magic=operation_class.account_data.magic_number,  # Identificador do robô/expert.
        identifier=__generate_unique_ticket(),  # Identificador único da posição.
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
    # Converte o tipo de ordem de mercado (BUY/SELL) para o tipo de posição correspondente.
    position_type = __convert_order_to_position_type(order_type)

    # Criação do objeto `MqlPositionInfo` representando a posição aberta.
    position = MqlPositionInfo(
        ticket=__generate_unique_ticket(),  # Ticket único gerado com timestamp.
        time=position_time,  # Tempo de abertura da posição.
        time_msc=position_time,  # Tempo com precisão de milissegundos.
        time_update=position_time,  # Tempo da última atualização (inicialmente igual ao de abertura).
        time_update_msc=position_time,  # Tempo com precisão em milissegundos.
        type=position_type,  # Tipo de posição (compra/venda).
        magic=operation_class.account_data.magic_number,  # Identificador do robô/expert.
        identifier=__generate_unique_ticket(),  # Identificador único da posição.
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
        position.time = opened_position.time
        position.time_msc = opened_position.time_msc
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
                position.identifier = __generate_unique_ticket()

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


def __backtest_position_open(
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
        ValueError: Caso os dados de volume ou margem não sejam válidos.
    """
    __validate_operation_handler_attributes_for_symbol(
        operation_class=operation_class, symbol=symbol
    )

    # **Validação do volume**
    __validate_position_volume(operation_class, symbol, order_type, volume)

    # Recupera o candle mais recente para simular o estado de mercado atual.
    last_candle = operation_class.backtest_symbols_data.loc[symbol, "last_candle"]

    # Define o timestamp do candle como o tempo da posição.
    position_time = last_candle.name

    # Recupera o spread simulado e o tamanho de tick para o par de moedas.
    simulated_spread: int = operation_class.account_data.simulated_spread
    trade_tick_size: float = operation_class.backtest_symbols_data.loc[symbol].tick_size

    # Define o preço de entrada com base no tipo de ordem (compra ou venda).
    if order_type == ENUM_ORDER_TYPE_MARKET.ORDER_TYPE_BUY:
        # Ordem de compra: utiliza o preço de fechamento do candle + spread (para simular o preço ASK).
        price = last_candle.close + (trade_tick_size * simulated_spread)
    else:
        # Ordem de venda: utiliza diretamente o preço de fechamento do candle (para simular o preço BID).
        price = last_candle.close

    # **Cálculo da margem necessária** (para abrir a posição)
    contract_size = operation_class.backtest_symbols_data.loc[symbol, "contract_size"]
    leverage = operation_class.account_data.leverage
    margin_required = (volume * contract_size * price) / leverage

    # **Verificação de margem disponível**
    if operation_class.account_data.margin_free < margin_required:
        raise InsufficientMarginError(
            f"Margem insuficiente para abrir posição de {volume} lote(s) em '{symbol}'. "
            f"Margem necessária: {margin_required:.2f}, Margem livre: {operation_class.account_data.margin_free:.2f}"
        )

    # Verifica o tipo de conta e aplica a lógica correspondente:
    # - Hedge: permite múltiplas posições na mesma direção ou direções opostas.
    # - Netting: permite apenas uma posição agregada por símbolo.
    if (
        operation_class.account_data.margin_mode
        == ENUM_ACCOUNT_MARGIN_MODE.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
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

    # Atualiza os dados após execução
    __process_account_update_data(operation_class=operation_class)

    # Retorna True para indicar que a operação foi bem-sucedida na simulação.
    return True

# Open Pending Order ------------------------------------------------------------------------------
def __backtest_pending_order_open(
    operation_class: "Operation",
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
    """
    Abre uma ordem pendente em uma conta de backtest com validação de volume e preço.
    """
    __validate_operation_handler_attributes_for_symbol(
        operation_class=operation_class, symbol=symbol
    )

    # Valida o volume da ordem
    __validate_order_volume(
        operation_class=operation_class, symbol=symbol, order_type=order_type, volume=volume
    )

    # Recupera o candle mais recente para simular o estado de mercado atual.
    last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle

    # Define o timestamp do candle como o tempo da posição.
    position_time = last_candle.name
    order_time = position_time
    current_time_ms = get_timestamp_ms(order_time)

    type_time = (
        ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
        if expiration
        else ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC
    )

    __validate_order_price(
        operation_class=operation_class,
        symbol=symbol,
        price=price,
        order_type=order_type,
        stop_limit=stop_limit,
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
        magic=operation_class.account_data.magic_number,
        type_filling=operation_class.account_data.type_filling,
        comment=comment,
    )

    operation_class.account_data.orders.append(order)


def __backtest_pending_order_modify(
    operation_class: "Operation",
    ticket: int,
    price: float,
    stop_price: float = 0,
    profit_price: float = 0,
    expiration: datetime = None,
    comment: str = "",
):
    # Select the order
    order: MqlTradeOrder = get_order(
        list_orders=operation_class.account_data.orders, ticket=ticket
    )

    if expiration:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED
    else:
        type_time = ENUM_ORDER_TYPE_TIME.ORDER_TIME_GTC

        # Check if stop or take profit is defined
    
    if stop_price or profit_price:
        # Validate the stoplimit, sl and tp
        validate_prices(price=price, sl=stop_price, tp=profit_price, order_type=order.type)

    __validate_order_price(
        operation_class=operation_class,
        symbol=order.symbol,
        price=price,
        order_type=order.type,
        stop_limit=order.price_stoplimit,
    )

    # Change the order attributes
    order.update(
        price_open=price,
        sl=stop_price,
        tp=profit_price,
        comment=comment,
        type_filling=operation_class.account_data.type_filling,
        magic=operation_class.account_data.magic_number,
        time_expiration=expiration,
        type_time=type_time,
    )


def __backtest_position_modify(
    operation_class: "Operation",
    stop_price: float = 0,
    profit_price: float = 0,
    position: int = None,
    comment: str = "",
):
    position_not_found_error = CouldNotSelectPosition("Could not select the position.")

    # If position not received, try to get it
    if position is None:
        # If there is only one position opened, get it
        if len(operation_class.account_data.positions) == 1:
            position = operation_class.account_data.positions[0].ticket
        else:
            raise position_not_found_error

    # Get the position from account positions
    position_selected: List[MqlPositionInfo] = [
        mqlposition
        for mqlposition in operation_class.account_data.positions
        if mqlposition.ticket == position
    ]

    # Check if the position exists
    if len(position_selected) != 1:
        raise position_not_found_error

    # Select the position object
    position_selected: MqlPositionInfo = position_selected[0]
    
    # Check if stop or take profit is defined
    if stop_price or profit_price:
        price = position_selected.price_current

        position_type = position_selected.type
        if position_type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
            order_type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY
        else:
            order_type = ENUM_ORDER_TYPE.ORDER_TYPE_SELL

        # Validate the stoplimit, sl and tp
        validate_prices(price=price, sl=stop_price, tp=profit_price, order_type=order_type)

    position_selected.update(
        sl=stop_price,
        tp=profit_price,
        comment=comment,
    )

    # Atualiza os dados após execução
    __process_account_update_data(operation_class=operation_class)


def __backtest_position_close(
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
    position_selected: List[MqlPositionInfo] = [
        position
        for position in operation_class.account_data.positions
        if position.ticket == position_ticket
    ]

    # **2. Verificação da Existência da Posição**
    if len(position_selected) != 1:
        raise CouldNotSelectPosition("[ERROR]: Could not select the position.")

    # **3. Recupera a posição e atributos necessários**
    position_selected = position_selected[0]
    symbol = position_selected.symbol
    last_candle = operation_class.backtest_symbols_data.loc[
        symbol
    ].last_candle  # Último candle disponível
    deal_time = last_candle.name  # Define o timestamp do candle como o tempo do deal

    # **4. Determina preço de execução e tipo de ordem inversa**
    if position_selected.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        price = last_candle.close  # Preço de fechamento para ordens de venda
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_SELL  # Ordem de venda
    else:
        price = last_candle.close + (
            operation_class.backtest_symbols_data.loc[symbol].tick_size
            * operation_class.account_data.simulated_spread
        )
        order_type = ENUM_ORDER_TYPE.ORDER_TYPE_BUY  # Ordem de compra

    # **5. Criação e Registro do Deal**
    deal = __backtest_create_a_deal(
        deal_time=deal_time,
        position=position_selected,
        symbol=symbol,
        order_type=order_type,
        volume=position_selected.volume,
        price=price,
        fee=fee,
        commission=commission,
        order=None,
        comment=comment,
        operation_class=operation_class,
    )
    operation_class.account_data.history_deals.append(deal)

    # **6. Atualização de Saldo e Equity com base no profit do deal**
    __backtest_account_update_equity(operation_class=operation_class)

    # **7. Remoção da Posição da Lista**
    operation_class.account_data.positions.remove(position_selected)

    # **8. Log do Fechamento**
    logging.info(
        f"[CLOSE POSITION] Posição {position_selected.ticket} encerrada em {symbol} | Lucro: {deal.profit:.2f} | "
        f"Saldo Atual: {operation_class.account_data.balance:.2f} | Equity: {operation_class.account_data.equity:.2f}"
    )

    # **9. Atualiza os dados após execução**
    __process_account_update_data(operation_class=operation_class)


# Pending Orders Management -----------------------------------------------------------------------
def __backtest_pending_order_check_triggered(operation_class: "Operation") -> None:
    """
    Verifica se alguma ordem pendente foi ativada com base no preço `high` e `low` do último candle.
    Para ordens `STOP_LIMIT`, verifica o acionamento do preço inicial e, se necessário,
    cria uma ordem `LIMIT`. Para ordens `LIMIT` e `STOP`, abre posições diretamente.

    Args:
        operation_class (Operation): Classe de operação com informações da conta e ordens pendentes.

    Returns:
        None: A função não retorna nada, mas abre posições ou cria ordens `LIMIT` conforme necessário.
    """
    # **Iteração sobre todas as ordens pendentes**
    spread_points = operation_class.account_data.simulated_spread
    for order in operation_class.account_data.orders[:]:  # Cópia da lista para evitar erros ao modificar
        symbol = order.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle
        order_triggered = False  # Variável de controle para verificar se a ordem foi ativada
        spread = spread_points * operation_class.backtest_symbols_data.loc[symbol].tick_size

        # **Verificação de preços por tipo de ordem**
        if order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT:
            # `BUY_LIMIT`: Preço do mercado (`low`) deve ser menor ou igual ao preço da ordem
            if last_candle.low + spread <= order.price_open:
                logging.info(
                    f"[INFO] Ordem `BUY_LIMIT` {order.ticket} atingida em {symbol} a {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT:
            # `SELL_LIMIT`: Preço do mercado (`high`) deve ser maior ou igual ao preço da ordem
            if last_candle.high >= order.price_open:
                logging.info(
                    f"[INFO] Ordem `SELL_LIMIT` {order.ticket} atingida em {symbol} a {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP:
            # `BUY_STOP`: Preço do mercado (`high`) deve ser maior ou igual ao preço da ordem
            if last_candle.high + spread >= order.price_open:
                logging.info(
                    f"[INFO] Ordem `BUY_STOP` {order.ticket} atingida em {symbol} a {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP:
            # `SELL_STOP`: Preço do mercado (`low`) deve ser menor ou igual ao preço da ordem
            if last_candle.low <= order.price_open:
                logging.info(
                    f"[INFO] Ordem `SELL_STOP` {order.ticket} atingida em {symbol} a {order.price_open}"
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT:
            # `BUY_STOP_LIMIT`: Preço do mercado (`high`) deve ser maior ou igual ao preço inicial
            if last_candle.high + spread >= order.price_open:
                logging.info(
                    f"[INFO] Ordem `BUY_STOP_LIMIT` {order.ticket} atingida em {symbol}."
                )
                # Cria uma ordem `LIMIT` pendente
                __backtest_pending_order_open(
                    operation_class=operation_class,
                    expiration=order.time_expiration,
                    order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_LIMIT,
                    price=order.price_stoplimit,
                    symbol=symbol,
                    volume=order.volume_initial,
                    profit_price=order.tp,
                    stop_price=order.sl,
                    stop_limit=0,
                    comment=f"Created LIMIT order from STOP_LIMIT #{order.ticket}",
                )
                order_triggered = True

        elif order.type == ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_STOP_LIMIT:
            # `SELL_STOP_LIMIT`: Preço do mercado (`low`) deve ser menor ou igual ao preço inicial
            if last_candle.low <= order.price_open:
                logging.info(
                    f"[INFO] Ordem `SELL_STOP_LIMIT` {order.ticket} atingida em {symbol}."
                )
                # Cria uma ordem `LIMIT` pendente
                __backtest_pending_order_open(
                    operation_class=operation_class,
                    expiration=order.time_expiration,
                    order_type=ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_SELL_LIMIT,
                    price=order.price_stoplimit,
                    symbol=symbol,
                    volume=order.volume_initial,
                    profit_price=order.tp,
                    stop_price=order.sl,
                    stop_limit=0,
                    comment=f"Created LIMIT order from STOP_LIMIT {order.ticket}",
                )
                order_triggered = True

        else:
            logging.warning(f"[WARNING] Tipo de ordem {order.type} não reconhecido.")
            continue  # Ignora tipos não reconhecidos
            
        # **Abertura da posição apenas se a ordem foi ativada**
        if order_triggered:
            original_close = (
                last_candle.close
            )  # Salva o valor original do close do candle

            # Ajusta temporariamente o close para o preço da ordem
            try:
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ] = last_candle.copy()
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ]["close"] = order.price_open

                if order.type not in (ENUM_ORDER_TYPE_PENDING.ORDER_TYPE_BUY_STOP_LIMIT, ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT):
                    # **Abertura da posição com o preço da ordem**
                    try:
                        # **Abertura da posição com o preço da ordem**
                        __backtest_position_open(
                            operation_class=operation_class,
                            symbol=symbol,
                            order_type=order.type,
                            volume=order.volume_current,
                            stop_price=order.sl,
                            profit_price=order.tp,
                            commission=0,
                            fee=0,
                            comment=f"Activated pending order {order.ticket}",
                        )
                    except Exception as e:
                        # Loga o erro e continua a execução
                        logging.error(
                            f"Erro ao abrir a posição para a ordem {order.ticket} no símbolo {symbol} (A ordem não será acionada, mas será excluída): {str(e)}"
                        )

                # Remove a ordem após ser ativada
                operation_class.account_data.orders.remove(order)
                logging.info(f"[INFO] Ordem {order.ticket} removida após ativação.")

            finally:
                # **Restaura o valor original do close do candle**   
                operation_class.backtest_symbols_data.at[
                    symbol, "last_candle"
                ]["close"] = original_close

            

def __backtest_pending_order_check_expiration(operation_class: "Operation") -> None:
    """
    Verifica se alguma ordem pendente expirou com base na data/hora atual e remove ordens expiradas.

    Args:
        operation_class (Operation): Classe de operação com informações da conta e ordens pendentes.

    Returns:
        None: A função não retorna nada, mas remove ordens expiradas do atributo `orders` do `account_data`.
    """
    # Valida atributos para cada símbolo presente nas ordens pendentes
    symbols = set([order.symbol for order in operation_class.account_data.orders])
    for symbol in symbols:
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

    # Filtra as ordens expiradas
    expired_orders = []
    for order in operation_class.account_data.orders:
        last_candle_time = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle.name

        if order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED:
            # `ORDER_TIME_SPECIFIED`: Ordem expira no horário exato especificado
            if (
                order.time_expiration is not None
                and order.time_expiration <= last_candle_time
            ):
                expired_orders.append(order)

        elif order.type_time == ENUM_ORDER_TYPE_TIME.ORDER_TIME_SPECIFIED_DAY:
            # `ORDER_TIME_SPECIFIED_DAY`: Expira às 23:59:59 do dia especificado
            if order.time_expiration is not None:
                expiration_day_end = datetime.combine(
                    order.time_expiration.date(), time(23, 59, 59), tzinfo=timezone.utc
                )
                if expiration_day_end <= last_candle_time:
                    expired_orders.append(order)

    # Remove as ordens expiradas
    for expired_order in expired_orders:
        operation_class.account_data.orders.remove(expired_order)
        logging.info(
            f"Ordem {expired_order.ticket} para {expired_order.symbol} foi removida devido à expiração."
        )


# Positions Management ----------------------------------------------------------------------------
def __backtest_position_check_stop_loss_reached(operation_class: "Operation") -> None:
    """
    Verifica se o stop loss foi atingido para as posições abertas com base no `high` e `low` do último candle.
    Caso o stop loss seja atingido, a posição é fechada automaticamente no preço do stop loss.

    Args:
        operation_class (Operation): Classe de operação contendo dados da conta e posições abertas.

    Returns:
        None: A função não retorna nada, mas fecha posições que atingiram o stop loss.
    """
    for position in operation_class.account_data.positions[
        :
    ]:  # Cópia da lista para evitar erros
        symbol = position.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle  # Último candle disponível

        if position.sl > 0:  # Verifica se há um stop loss configurado
            stop_loss_reached = (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
                and last_candle.low <= position.sl
            ) or (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                and last_candle.high >= position.sl
            )

            if stop_loss_reached:
                logging.warning(
                    f"[STOP LOSS] Posição {position.ticket} em {symbol} atingiu o stop loss a {position.sl}"
                )

                # **Armazenamento do `close` original do candle**
                original_close = last_candle.close

                operation_last_candle = operation_class.backtest_symbols_data.loc[
                    symbol
                ].last_candle

                try:
                    # Ajusta temporariamente o `close` para o preço de stop loss
                    operation_last_candle = last_candle.copy()
                    operation_last_candle["close"] = position.sl

                    # **Fechamento da posição**
                    __backtest_position_close(
                        operation_class=operation_class,
                        position_ticket=position.ticket,
                        comment="Stop loss reached",
                    )

                finally:
                    # **Restauração do valor original do `close`**
                    operation_last_candle.close = original_close


def __backtest_position_check_take_profit_reached(operation_class: "Operation") -> None:
    """
    Verifica se o take profit foi atingido para as posições abertas com base no `high` e `low` do último candle.
    Caso o take profit seja atingido, a posição é fechada automaticamente no preço do take profit.

    Args:
        operation_class (Operation): Classe de operação contendo dados da conta e posições abertas.

    Returns:
        None: A função não retorna nada, mas fecha posições que atingiram o take profit.
    """
    for position in operation_class.account_data.positions[
        :
    ]:  # Cópia da lista para evitar erros
        symbol = position.symbol
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        last_candle = operation_class.backtest_symbols_data.loc[
            symbol
        ].last_candle  # Último candle disponível

        if position.tp > 0:  # Verifica se há um take profit configurado
            take_profit_reached = (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY
                and last_candle.high >= position.tp
            ) or (
                position.type == ENUM_POSITION_TYPE.POSITION_TYPE_SELL
                and last_candle.low <= position.tp
            )

            if take_profit_reached:
                logging.info(
                    f"[TAKE PROFIT] Posição {position.ticket} em {symbol} atingiu o take profit a {position.tp}"
                )

                # **Armazenamento do `close` original do candle**
                original_close = last_candle.close

                operation_last_candle = operation_class.backtest_symbols_data.loc[
                    symbol
                ].last_candle
                try:
                    # Ajusta temporariamente o `close` para o preço do take profit
                    operation_last_candle = last_candle.copy()
                    operation_last_candle.close = position.tp

                    # **Fechamento da posição**
                    __backtest_position_close(
                        operation_class=operation_class,
                        position_ticket=position.ticket,
                        comment="Take profit reached",
                    )

                finally:
                    # **Restauração do valor original do `close`**
                    operation_class.backtest_symbols_data.loc[
                        symbol
                    ].last_candle.close = original_close


def __backtest_position_update_price_and_profit(operation_class: "Operation") -> None:
    """
    Atualiza o preço atual e o lucro/prejuízo das posições abertas com base no último preço disponível.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e posições abertas.

    Returns:
        None: A função não retorna nada, mas atualiza o preço atual e o lucro/prejuízo das posições abertas.
    """
    # **Zera o lucro total da conta antes de calcular o lucro das posições**
    operation_class.account_data.profit = 0

    # **Iteração sobre todas as posições abertas**
    for position in operation_class.account_data.positions:
        symbol = position.symbol

        # **Validação de atributos essenciais para o símbolo**
        __validate_operation_handler_attributes_for_symbol(
            operation_class=operation_class, symbol=symbol
        )

        # **Obtém o último candle para o símbolo**
        last_candle = operation_class.backtest_symbols_data.loc[symbol].last_candle

        # Utiliza o preço de fechamento (`close`) do candle como preço atual
        if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
            last_price = last_candle.close  # Preço de fechamento para ordens de venda
        else:
            last_price = last_candle.close + (
                operation_class.backtest_symbols_data.loc[symbol].tick_size
                * operation_class.account_data.simulated_spread
            )

        # **Atualiza o preço atual da posição**
        position.price_current = round(last_price, 5)

        # **Calcula o lucro/prejuízo com base no preço atual**
        profit = __backtest_get_profit(
            operation_class=operation_class,
            symbol=symbol,
            price_open=position.price_open,  # Preço de abertura da posição
            price_close=position.price_current,  # Preço atual
            price_volume=position.volume,  # Volume da posição
            position_type=position.type,  # Tipo da posição (compra/venda)
        )

        # **Atualiza o lucro/prejuízo na posição**
        position.profit = profit

        # **Acumula o lucro/prejuízo total da conta**
        operation_class.account_data.profit = round(
            operation_class.account_data.profit + profit + position.swap, 2
        )

        # **Log da atualização**
        logging.info(
            f"[ATUALIZAÇÃO] Posição {position.ticket} ({'BUY' if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY else 'SELL'}) "
            f"em {symbol}: Preço Atual: {last_price:.5f} | Lucro/Prejuízo: {profit:.2f} {operation_class.account_data.currency}"
        )


# Account Management ------------------------------------------------------------------------------
def __backtest_account_update_equity(operation_class: "Operation") -> None:
    """
    Atualiza o equity da conta com base no saldo atual e o lucro/prejuízo das posições abertas.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e posições abertas.

    Returns:
        None: A função não retorna nada, mas atualiza o atributo `equity` da conta.
    """
    account_data = operation_class.account_data

    # **Atualização do Equity**
    account_data.equity = round(account_data.balance + account_data.profit, 2)

    # **Log da atualização de Equity**
    logging.info(
        f"[ATUALIZAÇÃO DE EQUITY] Saldo: {account_data.balance:.2f}, "
        f"Lucro/Prejuízo Aberto: {account_data.profit:.2f}, "
        f"Equity: {account_data.equity:.2f}"
    )


def __backtest_account_update_margin(operation_class: "Operation") -> None:
    """
    Atualiza os valores de margem da conta com base no modo de cálculo de margem.

    Esta função calcula apenas os valores dinâmicos que mudam com as posições abertas:
    - `margin`: Margem total utilizada pelas posições abertas.
    - `margin_free`: Margem livre da conta (`equity - margin`).
    - `margin_level`: Nível de margem (percentual entre `equity` e `margin`).

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e posições abertas.

    Returns:
        None: A função atualiza os atributos de margem (`margin`, `margin_free` e `margin_level`) no `account_data`.
    """
    account_data = operation_class.account_data

    # **Atualiza o Equity antes de calcular a margem**
    __backtest_account_update_equity(operation_class)

    # **Inicializa a margem total utilizada**
    total_margin_used = 0.0

    # **Iteração sobre todas as posições abertas para calcular a margem usada**
    for position in account_data.positions:
        symbol = position.symbol
        trade_calc_mode = operation_class.backtest_symbols_data.loc[
            symbol
        ].trade_calc_mode
        position_open_price = position.price_open

        # **Obtém informações do símbolo**
        contract_size = operation_class.backtest_symbols_data.loc[symbol].contract_size
        leverage = account_data.leverage

        # **Cálculo de Margem com base no modo de cálculo do símbolo**
        if trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_CFDLEVERAGE,
        ]:
            margin = (position.volume * contract_size * position_open_price) / leverage

        elif (
            trade_calc_mode == ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE
        ):
            margin = position.volume * contract_size * position_open_price

        elif trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_FUTURES,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_FUTURES,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
        ]:
            margin = position.volume * operation_class.initial_margin.get(symbol, 0)

        elif trade_calc_mode in [
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_EXCH_STOCKS,
            ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_CFD,
        ]:
            margin = position.volume * contract_size * position_open_price

        elif trade_calc_mode == ENUM_SYMBOL_CALC_MODE.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            margin = 0  # Ativos não negociáveis não consomem margem

        else:
            logging.warning(f"Modo de cálculo desconhecido para o símbolo: {symbol}")
            margin = 0

        # **Soma a margem calculada ao total de margem usada**
        total_margin_used += margin

    # **Atualização dos atributos de margem na conta**
    account_data.margin = round(total_margin_used, 2)  # Margem total usada
    account_data.margin_free = round(
        account_data.equity - total_margin_used, 2
    )  # Margem livre

    # **Nível de Margem**
    if total_margin_used > 0:
        account_data.margin_level = round(
            (account_data.equity / total_margin_used) * 100, 3
        )
    else:
        account_data.margin_level = float(
            "inf"
        )  # Quando não há margem usada, o nível de margem é infinito

    # **Logs de informações de margem**
    logging.info(
        f"[MARGEM ATUALIZADA] Margem Usada: {account_data.margin:.2f}, Margem Livre: {account_data.margin_free:.2f}, "
        f"Nível de Margem: {account_data.margin_level:.2f}%"
    )


def __backtest_account_check_margin_call(operation_class: "Operation") -> None:
    """
    Verifica se o nível de margem da conta atingiu o limite definido (`margin_so_call`) e,
    se necessário, emite um alerta de margin call.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta.

    Returns:
        None: A função não retorna nada, mas pode emitir logs de alerta caso o nível de margem esteja crítico.
    """
    account_data = operation_class.account_data

    # Verifica o modo de cálculo do nível de margem
    if (
        account_data.margin_so_mode
        == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
    ):
        # Nível de margem baseado em porcentagem
        if account_data.margin_level <= account_data.margin_so_call:
            logging.warning(
                f"[MARGIN CALL] Nível de margem abaixo do limite ({account_data.margin_level:.2f}%). "
                f"Margem mínima permitida: {account_data.margin_so_call}%."
            )

    elif (
        account_data.margin_so_mode
        == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_MONEY
    ):
        # Nível de margem baseado em valor monetário
        if account_data.margin_free <= account_data.margin_so_call:
            logging.warning(
                f"[MARGIN CALL] Margem livre abaixo do limite ({account_data.margin_free:.2f} {account_data.currency}). "
                f"Margem mínima permitida: {account_data.margin_so_call} {account_data.currency}."
            )


def __backtest_account_process_stop_out(operation_class: "Operation") -> None:
    """
    Processa o evento de stop out, encerrando posições abertas caso o nível de margem fique abaixo do limite
    estabelecido pela corretora. As posições são encerradas na ordem definida pelo parâmetro `fifo_close`:
    - Se `True`: posições fechadas em ordem FIFO.
    - Se `False`: posições fechadas pela maior perda não realizada.

    Ao final, a margem da conta é atualizada.

    Args:
        operation_class (Operation): Classe de operação com informações da conta e posições abertas.

    Returns:
        None: A função não retorna nada, mas fecha posições e atualiza os dados da conta.
    """
    account_data = operation_class.account_data

    # Verifica se o nível de margem está abaixo do stop out level.
    if account_data.margin_level > 0:
        if (
            account_data.margin_so_mode
            == ENUM_ACCOUNT_STOPOUT_MODE.ACCOUNT_STOPOUT_MODE_PERCENT
        ):
            stop_out_triggered = account_data.margin_level <= account_data.margin_so_so
        else:
            stop_out_triggered = account_data.equity <= account_data.margin_so_so
    else:
        # Se a margem nível é 0 ou negativa, desencadeia stop out diretamente
        stop_out_triggered = True

    # **Se o stop out não foi atingido, retorna sem ações**
    if not stop_out_triggered:
        return

    logging.warning(
        "[STOP OUT] Nível de margem atingido! Iniciando fechamento das posições..."
    )

    # **Ordenação das posições**
    if account_data.fifo_close:
        # Ordenação FIFO: Fecha pela ordem de abertura (mais antiga primeiro)
        positions_to_close = sorted(
            account_data.positions, key=lambda pos: pos.time_msc
        )
    else:
        # Ordenação pela maior perda não realizada: Fecha primeiro as posições com maior prejuízo
        positions_to_close = sorted(account_data.positions, key=lambda pos: pos.profit)

    # **Fechamento das posições até liberar margem suficiente**
    for position in positions_to_close:
        __backtest_position_close(
            operation_class=operation_class,
            position_ticket=position.ticket,
            comment="Stop out triggered",
        )

        # Atualiza os dados de margem após cada fechamento
        __backtest_position_update_price_and_profit(operation_class=operation_class)
        __backtest_account_update_margin(operation_class=operation_class)

        # Verifica se o nível de margem voltou a estar acima do limite após fechar posições
        if account_data.margin_level > account_data.margin_so_so:
            logging.info(
                "[STOP OUT] Nível de margem restaurado após fechamento das posições."
            )
            break

    # **Log final após processo de stop out**
    logging.info(
        f"[STOP OUT FINALIZADO] Saldo: {account_data.balance:.2f} | Equity: {account_data.equity:.2f} | "
        f"Nível de Margem: {account_data.margin_level:.2f}%"
    )


# Swap Management ---------------------------------------------------------------------------------
def __backtest_position_apply_swap_to_positions(operation_class: "Operation") -> None:
    """
    Aplica swaps às posições abertas com base no `last_candle` e no histórico de `backtest_last_swap_date`.
    Verifica se passou do horário de fechamento de NY (22:00 UTC) e aplica os swaps cumulativos corretamente.

    Args:
        operation_class (Operation): Classe contendo as informações das posições abertas e parâmetros da conta.
    """
    last_swap_date = operation_class.account_data.backtest_last_swap_date
    last_candle_time = max(
        candle.name for candle in operation_class.backtest_symbols_data["last_candle"]
    )

    # **Caso especial: primeira aplicação de swap**
    if last_swap_date is None:
        if not operation_class.account_data.positions:
            # Nenhuma posição aberta, então atualiza apenas a última data de swap
            operation_class.account_data.backtest_last_swap_date = last_candle_time
        else:
            # Atualiza a última data de swap para a data da posição mais antiga
            oldest_position_time = min(
                position.time for position in operation_class.account_data.positions
            )
            operation_class.account_data.backtest_last_swap_date = oldest_position_time
        return

    # Calcula a diferença de dias entre o último swap e o último candle
    days_diff = (last_candle_time.date() - last_swap_date.date()).days

    # **Evita reprocessar se o último swap já foi aplicado após as 22h do mesmo dia**
    last_close_time = last_swap_date.replace(hour=22, minute=0, second=0, microsecond=0)
    if (
        last_swap_date >= last_close_time
        and last_swap_date.date() == last_candle_time.date()
    ):
        return

    # **Itera sobre os dias pendentes para aplicar os swaps**
    for i in range(days_diff + 1):
        current_date = last_swap_date + timedelta(days=i)  # Data atual no loop
        close_time_current = current_date.replace(
            hour=22, minute=0, second=0, microsecond=0
        )  # Horário de fechamento

        # **Se o último swap foi aplicado após 22h, ignora este dia**
        if (
            last_swap_date.date() == current_date.date()
            and close_time_current < last_swap_date
        ):
            continue

        # **Se ainda não chegou às 22h no último dia, não aplica o swap**
        if (
            current_date.date() == last_candle_time.date()
            and last_candle_time < close_time_current
        ):
            continue

        # **Ignora sábado e domingo (mercado fechado)**
        weekday = (current_date.weekday() + 1) % 7  # Ajusta para que domingo seja 0
        if weekday in (0, 6):
            continue

        # **Evita reaplicar swap no mesmo dia após 22h**
        if (
            last_swap_date >= close_time_current
            and current_date == last_swap_date.date()
        ):
            continue

        # **Aplica swap às posições abertas**
        for position in operation_class.account_data.positions:
            # **Ignora posições abertas após a data atual**
            if position.time > close_time_current:
                continue

            symbol = position.symbol
            rollover_day = operation_class.backtest_symbols_data.loc[
                symbol, "swap_rollover3days"
            ]  # Dia padrão de rollover triplo é quarta-feira

            # **Calcula multiplicador de swap (triplo na quarta-feira, normal nos outros dias)**
            swap_multiplier = 3 if weekday == rollover_day else 1
            swap_value = __backtest_position_calculate_swap(
                operation_class, position, swap_multiplier
            )
            position.swap += swap_value

            # **Log informativo com os detalhes do swap aplicado**
            logging.info(
                f"[SWAP] {position.symbol} | Data: {current_date.strftime('%Y-%m-%d')} | "
                f"Swap aplicado: {swap_value:.2f} | Multiplier: {swap_multiplier}x | Swap Total: {position.swap:.2f} | "
                f"Position Time: {position.time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    # **Atualiza a última data de swap para o horário do último candle**
    operation_class.account_data.backtest_last_swap_date = last_candle_time


def __backtest_position_calculate_swap(
    operation_class: "Operation", position: "MqlPositionInfo", multiplier: int
) -> float:
    """
    Calcula o valor do swap para uma posição com base no tipo de swap e no multiplicador.

    Args:
        operation_class (Operation): Classe contendo as informações da conta e do mercado.
        position (MqlPositionInfo): Posição aberta para a qual o swap será calculado.
        multiplier (int): Multiplicador do swap (1 para dias normais, 3 para quarta-feira no Forex).

    Returns:
        float: Valor do swap calculado.
    """
    symbol = position.symbol
    swap_mode = operation_class.backtest_symbols_data.loc[symbol].swap_mode
    trade_contract_size = operation_class.backtest_symbols_data.loc[
        symbol
    ].contract_size
    volume = position.volume
    last_price = operation_class.backtest_symbols_data.loc[symbol].last_candle.close

    if position.type == ENUM_POSITION_TYPE.POSITION_TYPE_BUY:
        swap_rate = operation_class.backtest_symbols_data.loc[symbol].swap_long
    else:
        swap_rate = operation_class.backtest_symbols_data.loc[symbol].swap_short

    # Calcula o swap com base no modo
    if swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_POINTS:
        swap_value = swap_rate * multiplier * volume
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_SYMBOL:
        swap_value = swap_rate * multiplier * volume * trade_contract_size * last_price
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_MARGIN:
        swap_value = swap_rate * multiplier * volume
    elif swap_mode == ENUM_SYMBOL_SWAP_MODE.SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT:
        swap_value = swap_rate * multiplier * volume * trade_contract_size
    else:
        swap_value = 0  # Nenhum swap para modos desativados ou não suportados

    return round(swap_value, 2)


# New Candle --------------------------------------------------------------------------------------
def __process_account_update_data(operation_class: "Operation"):
    """
    Atualiza os dados da operação após a geração de um novo candle.

    Objetivos:
    - Aplicar swaps às posições abertas.
    - Atualizar o preço atual e o lucro/prejuízo das posições.
    - Atualizar os dados de margem da conta (margem usada, margem livre e nível de margem).
    - Verificar se há necessidade de emitir um alerta de `margin call`.
    - Verificar se há necessidade de processar um `stop out` e fechar posições.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e das posições.
    """
    # **Aplicação de swaps**
    __backtest_position_apply_swap_to_positions(operation_class=operation_class)

    # **Atualização do preço e cálculo de lucro/prejuízo**
    __backtest_position_update_price_and_profit(operation_class=operation_class)

    # **Atualização de dados de margem**
    __backtest_account_update_margin(operation_class=operation_class)

    # **Verificação de `margin call`**
    __backtest_account_check_margin_call(operation_class=operation_class)

    # **Processamento de `stop out` se necessário**
    __backtest_account_process_stop_out(operation_class=operation_class)


def __process_account_after_candle_event(operation_class: "Operation"):
    """
    Processa eventos relacionados a ordens pendentes e posições após a geração de um novo candle.

    Objetivos:
    - Verificar se ordens pendentes foram acionadas pelo preço atual.
    - Verificar se ordens pendentes expiraram devido ao tempo.
    - Verificar se posições abertas atingiram o `stop loss` e precisam ser fechadas.
    - Verificar se posições abertas atingiram o `take profit` e precisam ser fechadas.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e das posições.
    """
    # **Verificação de acionamento de ordens pendentes**
    __backtest_pending_order_check_triggered(operation_class=operation_class)

    # **Verificação de ordens pendentes expiradas**
    __backtest_pending_order_check_expiration(operation_class=operation_class)

    # **Verificação de posições que atingiram o `stop loss`**
    __backtest_position_check_stop_loss_reached(operation_class=operation_class)

    # **Verificação de posições que atingiram o `take profit`**
    __backtest_position_check_take_profit_reached(operation_class=operation_class)


def __process_account_new_candle_event(operation_class: "Operation"):
    """
    Processa eventos relacionados à geração de um novo candle.

    Objetivos:
    - Executar verificações após o fechamento do candle para atualizar ordens e posições.
    - Atualizar os dados das posições abertas e da conta, como margem, lucro e alertas de risco.

    Args:
        operation_class (Operation): Classe de operação contendo os dados da conta e das posições.
    """
    # **Processamento de eventos após o fechamento do candle**
    __process_account_after_candle_event(operation_class=operation_class)

    # **Atualização de dados após um novo candle**
    __process_account_update_data(operation_class=operation_class)


# Decorators --------------------------------------------------------------------------------------
def decorator_backtest_position_open(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_open(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_pending_order_open(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_pending_order_open(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_position_modify(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_modify(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_pending_order_modify(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_pending_order_modify(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_backtest_position_close(func: Callable):
    def check_backtest_account(*args, **kwargs):
        if args[0].account_data.is_backtest_account:
            __backtest_position_close(*args, **kwargs)
            return True
        else:
            return func(*args, **kwargs)

    return check_backtest_account


def decorator_update_candles(func: Callable):
    def check_backtest_account(*args, **kwargs):
        func_return = func(*args, **kwargs)
        __process_account_new_candle_event(operation_class=args[0])
        return func_return

    return check_backtest_account
