import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AbstractStrategy(ABC):
    def __init__(self, position_handler, params: Optional[Dict] = None) -> None:
        """
        Inicializa a estratégia com um gerenciador de posições e parâmetros configuráveis.

        Args:
            position_handler: Instância do PositionHandler para gerenciar posições.
            params (Optional[Dict]): Parâmetros da estratégia (e.g., períodos de indicadores, SL/TP).
        """
        self.position_handler = position_handler  # Gerenciador de posições para criar, ajustar e fechar ordens.
        self.params = params or {}  # Parâmetros configuráveis da estratégia, fornecidos pelo usuário.
        self.state = {}  # Armazena o estado interno da estratégia, como valores de indicadores técnicos.
        self.ohlc_data = None  # Dados de mercado mais recentes (e.g., OHLCV), atualizados a cada tick.
        self.context = {}  # Contexto dinâmico usado para lógica adicional, como histórico ou métricas personalizadas.
        logger.info("Estratégia inicializada com os parâmetros fornecidos.")

    def update(self, ohlc_data: Dict) -> None:
        """
        Método principal que organiza o fluxo da estratégia.

        Args:
            ohlc_data (Dict): Dados de mercado (e.g., OHLCV) atualizados.

        Raises:
            Exception: Levanta exceção em caso de erro em qualquer etapa.
        """
        self.ohlc_data = ohlc_data  # Atualiza os dados de mercado para a execução da lógica da estratégia.
        logger.info("Início da atualização com novos dados de mercado.")

        try:
            self.preprocess_data()
            logger.info("Pré-processamento dos dados concluído.")
        except Exception as e:
            logger.error(f"Erro no pré-processamento dos dados: {e}")
            raise

        try:
            self.initialize_indicators()
            logger.info("Indicadores técnicos inicializados/atualizados.")
        except Exception as e:
            logger.error(f"Erro ao inicializar indicadores: {e}")
            raise

        try:
            entry_signals = self.identify_entry_signals()
            self.process_entry_signals(entry_signals)
            logger.info(f"Sinais de entrada processados: {len(entry_signals)} sinais executados.")
        except Exception as e:
            logger.error(f"Erro ao identificar/processar sinais de entrada: {e}")
            raise

        try:
            exit_signals = self.identify_exit_signals()
            self.process_exit_signals(exit_signals)
            logger.info(f"Sinais de saída processados: {len(exit_signals)} sinais executados.")
        except Exception as e:
            logger.error(f"Erro ao identificar/processar sinais de saída: {e}")
            raise

        try:
            self.monitor_positions()
            logger.info("Monitoramento e ajustes de posições concluídos.")
        except Exception as e:
            logger.error(f"Erro ao monitorar posições: {e}")
            raise

    def preprocess_data(self) -> None:
        """
        Pré-processa os dados de mercado antes da lógica principal.
        Útil para estratégias que exigem transformação dos dados.
        """
        pass

    @abstractmethod
    def initialize_indicators(self) -> None:
        """
        Inicializa ou atualiza indicadores técnicos usados na estratégia.
        Deve ser sobrescrito por classes concretas.
        """
        pass

    @abstractmethod
    def identify_entry_signals(self) -> List[Dict]:
        """
        Identifica sinais para abrir novas posições.

        Returns:
            List[Dict]: Lista de configurações para entradas.
        """
        pass

    @abstractmethod
    def identify_exit_signals(self) -> List[Dict]:
        """
        Identifica sinais para fechar ou ajustar posições existentes.

        Returns:
            List[Dict]: Lista de configurações para saídas.
        """
        pass

    def process_entry_signals(self, entry_signals: List[Dict]) -> None:
        """
        Processa e executa múltiplos sinais de entrada.

        Args:
            entry_signals (List[Dict]): Lista de configurações de entrada.
        """
        for signal in entry_signals:
            self._validate_and_execute_signal(signal, entry=True)

    def process_exit_signals(self, exit_signals: List[Dict]) -> None:
        """
        Processa e executa múltiplos sinais de saída.

        Args:
            exit_signals (List[Dict]): Lista de configurações de saída.
        """
        for signal in exit_signals:
            self._validate_and_execute_signal(signal, entry=False)

    def _validate_and_execute_signal(self, signal: Dict, entry: bool) -> None:
        """
        Valida e executa um sinal, seja de entrada ou saída.

        Args:
            signal (Dict): Configuração do sinal a ser validado.
            entry (bool): True se for um sinal de entrada, False se for de saída.
        """
        action = signal.get("action")  # Tipo de ação: "buy", "sell", "close".
        quantity = signal.get("quantity")  # Quantidade a ser negociada.
        sl = signal.get("sl", None)  # Stop Loss, se aplicável.
        tp = signal.get("tp", None)  # Take Profit, se aplicável.
        position_id = signal.get("position_id", None)  # ID da posição, se aplicável.
        price = self.ohlc_data["Close"].iloc[-1]  # Preço atual do mercado.

        if quantity <= 0:
            logger.warning(f"Sinal inválido detectado: {signal}")
            return

        if entry:
            if action == "buy":
                self.position_handler.create_order("buy", price, quantity, sl=sl, tp=tp)
                logger.info(f"Ordem de compra executada: {signal}")
            elif action == "sell":
                self.position_handler.create_order("sell", price, quantity, sl=sl, tp=tp)
                logger.info(f"Ordem de venda executada: {signal}")
        else:
            if action == "close":
                if position_id:
                    position = next(
                        (p for p in self.position_handler.positions if p.position_id == position_id),
                        None
                    )
                    if position:
                        self.position_handler.close_position(price, quantity, position=position)
                        logger.info(f"Posição {position_id} fechada: {signal}")
                else:
                    self.position_handler.close_position(price, quantity)
                    logger.info(f"Posição genérica fechada: {signal}")

    def monitor_positions(self) -> None:
        """
        Monitora e ajusta posições abertas com base nas condições do mercado.
        Pode ser sobrescrito para implementar lógica customizada.
        """
        pass
