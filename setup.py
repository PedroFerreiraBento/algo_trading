from setuptools import setup, find_packages

setup(
    name="algo_trading",  # Nome do pacote
    version="0.1.0",  # Versão inicial
    description="A Python library for managing data storage and yfinance integration.",
    author="Pedro Bento",
    author_email="pedro.techfinance@gmail.com",
    url="https://github.com/seu_usuario/AlgoTrading",  # Repositório no GitHub
    packages=find_packages(),  # Detecta automaticamente os pacotes
    install_requires=[
        "pandas==2.2.3",         # Versão específica conforme o environment.yml
        "numpy==1.26.4",         # Versão específica
        "yfinance==0.2.28",      # Versão específica
        "pyarrow==17.0.0",       # Versão específica
        "tables==3.9.2",         # Versão específica
        "matplotlib==3.9.2",     # Versão específica
        "notebook==7.2.2",       # Versão específica
        "pytest==7.4.4",         # Versão específica
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12.8",  # Versão mínima do Python conforme o environment.yml
)
