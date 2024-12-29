# Forex Backtester

Bem-vindo ao **Forex Backtester**, um projeto para backtesting de estratégias no mercado Forex utilizando Python e Conda. Este repositório fornece uma estrutura modular e eficiente para desenvolver, testar e analisar estratégias de trading.

---

## **Recursos do Projeto**
- **Carregamento de Dados:**
  - Dados históricos de Forex obtidos de fontes gratuitas (ex.: Yahoo Finance).
  - Suporte para candles de alta resolução (ex.: 1 minuto, 1 hora).

- **Implementação de Estratégias:**
  - Estratégias modulares e personalizáveis.
  - Exemplo: Média Móvel, RSI.

- **Análise e Relatórios:**
  - Cálculo de métricas como drawdown, Sharpe ratio e retorno acumulado.
  - Geração de gráficos e relatórios automáticos.

- **Estrutura Modular:**
  - Organização clara em pastas: dados, estratégias, análises, documentação e logs.

---

## **Estrutura do Projeto**
A estrutura completa do projeto está documentada em [docs/project_structure.md](docs/project_structure.md). Aqui está uma visão geral:

```plaintext
forex-backtester/
│
├── data/                   # Armazenamento de dados históricos e processados
├── strategies/             # Implementação de estratégias
├── analysis/               # Scripts de análise de desempenho
├── logs/                   # Logs de operações e eventos
├── docs/                   # Documentação do projeto
├── tests/                  # Scripts de teste
├── notebooks/              # Notebooks Jupyter para exploração
├── utils/                  # Funções auxiliares
├── environment.yml         # Configuração do ambiente Conda
├── config.py               # Configurações globais
└── main.py                 # Ponto de entrada principal
```

---

## **Configuração do Ambiente**

### **1. Clonar o Repositório**
```bash
git clone https://github.com/seu-usuario/forex-backtester.git
cd forex-backtester
```

### **2. Criar o Ambiente Conda**
```bash
conda env create -f environment.yml
conda activate backtest-env
```

---

## **Como Usar**

### **1. Baixar Dados de Forex**
Modifique o arquivo `main.py` para incluir o par de moedas desejado e o intervalo de datas. Exemplo:
```python
symbol = "EURUSD=X"  # Par de Forex
start_date = "2023-01-01"
end_date = "2023-12-31"
data = yf.download(symbol, start=start_date, end=end_date, interval="1h")
```

### **2. Implementar Estratégias**
Adicione ou modifique estratégias na pasta `strategies/`. Use a classe base `base_strategy.py` como modelo.

### **3. Executar o Backtest**
Rode o script principal:
```bash
python main.py
```

### **4. Gerar Relatórios**
Os resultados, métricas e gráficos estarão disponíveis na pasta `logs/` ou conforme configurado no código.

---

## **Testes**
Para rodar os testes automatizados:
```bash
pytest tests/
```

---

## **Documentação Completa**
Consulte a documentação na pasta `docs/` para detalhes adicionais:
- **[Estrutura do Projeto](docs/project_structure.md)**
- **[Uso de APIs Externas](docs/api_usage.md)**
- **[Guia de Estratégias](docs/strategies_guide.md)**
- **[Guia de Análise](docs/analysis_guide.md)**

---

## **Contribuições**
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias ou novas funcionalidades.

---

## **Licença**
Este projeto está sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
