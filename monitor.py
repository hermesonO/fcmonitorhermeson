import requests
import pandas as pd
import os
import time

# Pegando o token e chat_id dos Secrets do GitHub
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

def monitor_prices():
    # Lê os preços do CSV
    df = pd.read_csv("precos.csv")

    for index, row in df.iterrows():
        jogador = row["jogador"]
        preco_atual = row["preco_atual"]
        preco_anterior = row["preco_anterior"]

        if preco_atual > preco_anterior:
            send_message(f"📈 {jogador} subiu de {preco_anterior} para {preco_atual} coins")
        elif preco_atual < preco_anterior:
            send_message(f"📉 {jogador} caiu de {preco_anterior} para {preco_atual} coins")
        else:
            print(f"{jogador} não teve alteração")

if __name__ == "__main__":
    monitor_prices()
