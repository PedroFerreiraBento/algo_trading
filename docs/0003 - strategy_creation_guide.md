# Documentação para Criação de Estratégias

## Sumário
- [Documentação para Criação de Estratégias](#documentação-para-criação-de-estratégias)
  - [Sumário](#sumário)
  - [Visão Geral](#visão-geral)
    - [Principais Recursos:](#principais-recursos)
  - [Estrutura da Classe](#estrutura-da-classe)
    - [Classe Base: `AbstractStrategy`](#classe-base-abstractstrategy)
    - [Principais Atributos](#principais-atributos)
    - [Principais Métodos](#principais-métodos)
      - [**`update(ohlc_data)`**](#updateohlc_data)
      - [**`initialize_indicators()`**](#initialize_indicators)
      - [**`identify_entry_signals()`**](#identify_entry_signals)
      - [**`identify_exit_signals()`**](#identify_exit_signals)
      - [**`process_entry_signals(entry_signals)`**](#process_entry_signalsentry_signals)
      - [**`process_exit_signals(exit_signals)`**](#process_exit_signalsexit_signals)
      - [**`monitor_positions()`**](#monitor_positions)
  - [Exemplo: Estratégia de Cruzamento de SMA](#exemplo-estratégia-de-cruzamento-de-sma)
    - [Implementação](#implementação)
    - [Exemplo de Parâmetros](#exemplo-de-parâmetros)
    - [Uso](#uso)
  - [Considerações Importantes](#considerações-importantes)
  - [Melhorias Adicionais](#melhorias-adicionais)
  - [Conclusão](#conclusão)

---

## Visão Geral
Esta documentação explica como criar e implementar estratégias de trading utilizando a classe `AbstractStrategy`. A classe fornece um framework estruturado para desenvolver diversos tipos de estratégias, apoiando modularidade, reutilização e manutenibilidade.

### Principais Recursos:
1. **Extensibilidade:** Suporta uma ampla gama de estratégias (ex.: baseadas em indicadores, dirigidas por ML/RL, configurações fixas de SL/TP).
2. **Tratamento de Erros:** Levanta exceções em estágios-chave para garantir uma operação robusta.
3. **Modularidade:** Cada componente da estratégia (ex.: entrada, saída, monitoramento) é isolado para facilitar a personalização.
4. **Logging Detalhado:** Sistema de logging integrado para rastreamento e depuração.

---

## Estrutura da Classe

### Classe Base: `AbstractStrategy`
A `AbstractStrategy` é projetada como uma classe abstrata que exige que subclasses implementem métodos específicos. O fluxo de trabalho gira em torno do método `update`, que coordena todo o ciclo de vida de uma estratégia.

### Principais Atributos
- **`position_handler`:** Gerencia ordens e posições, incluindo criação, atualizações e encerramentos.
- **`params`:** Um dicionário de parâmetros específicos da estratégia (ex.: períodos de indicadores, níveis de SL/TP).
- **`state`:** Armazena valores calculados ou dados intermediários (ex.: valores de SMA).
- **`ohlc_data`:** Dados OHLCV atualizados a cada tick.
- **`context`:** Armazenamento dinâmico para atributos dependentes da lógica, como métricas históricas.

### Principais Métodos

#### **`update(ohlc_data)`**
Coordena o ciclo de vida da estratégia, chamando:
1. **`preprocess_data`:** Prepara dados brutos (opcional).
2. **`initialize_indicators`:** Atualiza ou inicializa indicadores.
3. **`identify_entry_signals`:** Identifica sinais de entrada com base em condições.
4. **`process_entry_signals`:** Valida e executa sinais de entrada.
5. **`identify_exit_signals`:** Identifica sinais de saída para posições ativas.
6. **`process_exit_signals`:** Valida e executa sinais de saída.
7. **`monitor_positions`:** Ajusta ou monitora posições abertas dinamicamente.

Levanta exceções para erros encontrados em qualquer um desses estágios.

#### **`initialize_indicators()`**
Inicializa ou atualiza indicadores. Deve ser implementado em subclasses.

#### **`identify_entry_signals()`**
Retorna uma lista de sinais de entrada, cada um definido como um dicionário com as chaves:
- `action`: Tipo de ação (ex.: `"buy"` ou `"sell"`).
- `quantity`: Quantidade a ser negociada.
- `sl`: Nível de Stop Loss (opcional).
- `tp`: Nível de Take Profit (opcional).

#### **`identify_exit_signals()`**
Retorna uma lista de sinais de saída, cada um definido como um dicionário com as chaves:
- `action`: Tipo de ação (ex.: `"close"`).
- `quantity`: Quantidade a ser fechada.
- `position_id`: ID da posição a ser fechada (opcional).

#### **`process_entry_signals(entry_signals)`**
Valida e executa sinais de entrada usando o `position_handler`.

#### **`process_exit_signals(exit_signals)`**
Valida e executa sinais de saída usando o `position_handler`.

#### **`monitor_positions()`**
Monitora e ajusta posições abertas. Opcional para sobrescrever em estratégias dinâmicas.

---

## Exemplo: Estratégia de Cruzamento de SMA
Abaixo está um exemplo de uma estratégia simples de cruzamento de SMA utilizando o framework `AbstractStrategy`.

### Implementação
```python
class SMACrossoverStrategy(AbstractStrategy):
    def initialize_indicators(self):
        """
        Calcula SMAs curtas e longas com base nos parâmetros.
        """
        close_prices = self.ohlc_data["Close"]
        self.state["sma_short"] = close_prices.rolling(window=self.params["short_period"]).mean()
        self.state["sma_long"] = close_prices.rolling(window=self.params["long_period"]).mean()

    def identify_entry_signals(self) -> List[Dict]:
        """
        Identifica sinais de entrada com base no cruzamento de SMA.
        Returns:
            List[Dict]: Configurações para entradas.
        """
        sma_short = self.state["sma_short"]
        sma_long = self.state["sma_long"]
        entry_signals = []

        if sma_short.iloc[-1] > sma_long.iloc[-1] and sma_short.iloc[-2] <= sma_long.iloc[-2]:
            entry_signals.append({
                "action": "buy",
                "quantity": self.params["quantity"],
                "sl": self.params["sl"],
                "tp": self.params["tp"],
            })
        elif sma_short.iloc[-1] < sma_long.iloc[-1] and sma_short.iloc[-2] >= sma_long.iloc[-2]:
            entry_signals.append({
                "action": "sell",
                "quantity": self.params["quantity"],
                "sl": self.params["sl"],
                "tp": self.params["tp"],
            })
        return entry_signals

    def identify_exit_signals(self) -> List[Dict]:
        """
        Identifica sinais de saída com base nas condições de SMA.
        Returns:
            List[Dict]: Configurações para saídas.
        """
        exit_signals = []
        for position in self.position_handler.positions:
            if position.type == "buy" and self.state["sma_short"].iloc[-1] < self.state["sma_long"].iloc[-1]:
                exit_signals.append({
                    "action": "close",
                    "quantity": position.quantity,
                    "position_id": position.position_id,
                })
            elif position.type == "sell" and self.state["sma_short"].iloc[-1] > self.state["sma_long"].iloc[-1]:
                exit_signals.append({
                    "action": "close",
                    "quantity": position.quantity,
                    "position_id": position.position_id,
                })
        return exit_signals
```

### Exemplo de Parâmetros
```python
params = {
    "short_period": 50,
    "long_period": 200,
    "quantity": 1,
    "sl": 0.02,  # Nível de Stop Loss
    "tp": 0.04,  # Nível de Take Profit
}
```

### Uso
```python
position_handler = PositionHandler(initial_balance=10000)
strategy = SMACrossoverStrategy(position_handler, params)

# Atualiza a estratégia com novos dados de mercado
data = {"Close": [100, 102, 104, 103, 105]}  # Exemplo de dados OHLC
strategy.update(data)
```

---

## Considerações Importantes
1. **Validação de Parâmetros:** Certifique-se de que todos os parâmetros necessários estejam definidos em `params`.
2. **Tratamento de Exceções:** Utilize o levantamento de exceções integrado para evitar comportamentos indefinidos.
3. **Logging:** Use logs para depurar problemas durante o desenvolvimento e monitorar operações ao vivo.

---

## Melhorias Adicionais
- **Estratégias Baseadas em Machine Learning:**
  - Implemente os hooks `preprocess_data` e `evaluate_model`.
  - Armazene previsões de modelos em `state` ou `context` para uso posterior.

- **Ajustes Dinâmicos de Posições:**
  - Sobrescreva `monitor_positions` para implementar trailing SL ou ajustes baseados em capital.

---

## Conclusão
A classe `AbstractStrategy` fornece uma base robusta para construir estratégias de trading diversas. Implementando os métodos abstratos e aproveitando a estrutura modular, você pode rapidamente desenvolver e testar estratégias adaptadas às suas necessidades específicas.
