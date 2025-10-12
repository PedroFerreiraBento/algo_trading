from setuptools import setup, find_packages

setup(
    name="algo_trading",  # Package name
    version="0.1.0",  # Version initial
    description="A simple backtesting framework for algorithmic trading.",
    author="Pedro Bento",
    author_email="pedro.techfinance@gmail.com",
    url="https://github.com/PedroFerreiraBento/AlgoTrading",  # Repository on GitHub
    packages=find_packages(),  # Detect automatically packages
    install_requires=[
        "pandas==2.2.3",         # Version specific according to environment.yml
        "numpy==1.26.4",         # Version specific
        "yfinance==0.2.28",      # Version specific
        "pyarrow==17.0.0",       # Version specific
        "tables==3.9.2",         # Version specific
        "matplotlib==3.9.2",     # Version specific
        "notebook==7.2.2",       # Version specific
        "pytest==7.4.4",         # Version specific
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12.8",  # Version minimum of Python according to environment.yml
)
