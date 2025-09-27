name: Rodar script

on:
  workflow_dispatch: # permite rodar manualmente
  schedule:
    - cron: "0 * * * *" # roda a cada 1 hora

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Configurar Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Instalar dependências
      run: pip install -r requirements.txt

    - name: Rodar script
      run: python monitor.py
