import pandas as pd
import time

def rodar_monitor():
    print("✅ Monitor iniciado...")

    try:
        # Lê o arquivo de preços
        precos = pd.read_csv("precos.csv")
        print("📊 Preços carregados com sucesso:")
        print(precos.head())  # Mostra só as 5 primeiras linhas
    except Exception as e:
        print("⚠️ Erro ao ler precos.csv:", e)

if __name__ == "__main__":
    rodar_monitor()
    time.sleep(2)  # espera 2 segundos só pra simular execução
    print("🏁 Monitor finalizado")
