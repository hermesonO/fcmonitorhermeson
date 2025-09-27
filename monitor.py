import time
import csv
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
from pytz import timezone

# 🚨 NOVAS BIBLIOTECAS PARA SCRAPING 🚨
import requests
from bs4 import BeautifulSoup
# ------------------------------------

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Define o fuso horário
TIMEZONE = timezone('UTC') 

# ===================================================
# 2. FUNÇÕES DE DADOS E SCRAPING REAL
# ===================================================

def fetch_price_from_web(player_name):
    """
    Tenta extrair o preço de um jogador do Futwiz usando um termo de busca.
    
    RETORNA: (preco_em_moedas_int, site_fonte)
    """
    
    # Formata o nome para a URL (ex: "Kylian Mbappé" vira "kylian-mbappe")
    search_slug = player_name.lower().replace(" ", "-").replace(".", "").replace("'", "")
    
    # URL de exemplo do Futwiz para um jogador. 
    # ATENÇÃO: É preciso encontrar o ID correto no Futwiz para ser mais preciso!
    # Usaremos uma busca simples com um ID fixo para o teste inicial, 
    # pois buscar pelo nome completo é complexo.
    if "mbappe" in search_slug:
        # Exemplo de URL de preço (pode não funcionar 100% se o Futwiz mudar)
        url = "https://www.futwiz.com/en/fifa24/player/kylian-mbappe/12345" # Usando ID fictício de exemplo
    else:
        # Para jogadores que não são Mbappé, vamos usar um ID genérico para simplificar
        # (Você precisará de uma lógica de busca REAL aqui)
        url = f"https://www.futwiz.com/en/fifa24/player/{search_slug}/12345"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Lança exceção se o status for 4xx ou 5xx
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ⚠️ ESTE É O PONTO CRÍTICO! Você deve inspecionar a página 
        # e encontrar a CLASSE ou o ID exato onde o preço está.
        # Este é apenas um CHUTE baseado em estruturas comuns.
        price_element = soup.find('div', class_='pc-price') 
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            
            # Limpa o texto: remove vírgulas, pontos e 'K' (para milhares)
            cleaned_price = price_text.replace('k', '000').replace('.', '').replace(',', '').strip()
            
            # Tenta converter para inteiro. Se houver erro na limpeza, retorna a simulação.
            try:
                final_price = int(cleaned_price)
                return final_price, "FUTWIZ (Real)"
            except ValueError:
                print(f"Erro de conversão após limpeza: {cleaned_price}")
                return random.randint(1000000, 2000000), "FUTWIZ (Erro de Scraping)"

        else:
            return random.randint(1000000, 2000000), "FUTWIZ (Elemento não Encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição web para {player_name}: {e}")
        return random.randint(1000000, 2000000), "FUTWIZ (Erro de Conexão)"


def registrar_historico(jogador, preco_moedas, preco_formatado):
    """Adiciona a busca do jogador ao arquivo CSV."""
    
    # ... (código da função registrar_historico permanece o mesmo) ...
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as f:
            f.readline()
    except FileNotFoundError:
        try:
            with open('preços_historico.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['data_hora', 'jogador', 'preco_moedas', 'preco_formatado'])
        except Exception as e:
            print(f"Erro ao criar preços_historico.csv: {e}")
            return
        
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        
        writer.writerow([now, jogador, preco_moedas, preco_formatado])
        
    print(f"Histórico registrado: {jogador} | {preco_formatado}")


def get_top_5_players():
    """SIMULA a busca pelos 5 jogadores mais buscados. Você deve usar requests+BS4 aqui também."""
    return [
        {"nome": "Kylian Mbappé", "id": "mbappe_id"},
        {"nome": "V. van Dijk", "id": "vvd_id"},
        {"nome": "E. Haaland", "id": "haaland_id"},
        {"nome": "L. Messi", "id": "messi_id"},
        {"nome": "Vini Jr.", "id": "vinijr_id"}
    ]


def get_player_price(search_term):
    """
    Função principal que chama o scraping real.
    """
    
    # Lógica de formatação de nome:
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").title()
    else: 
        player_name = search_term.title()
    
    # 🚨 CHAMADA DO SCRAPING REAL 🚨
    # Se o scraping falhar, ele retorna a simulação (random)
    preco_num, source_site = fetch_price_from_web(player_name)
    
    # Captura o horário AGORA
    current_time_str = datetime.now(TIMEZONE).strftime('%H:%M:%S')
        
    # Formatação do preço (ex: 1.500.000 moedas)
    preco_texto = f"{preco_num:,}".replace(",", "X").replace(".", ",").replace("X", ".") + " moedas"

    # REGISTRA A BUSCA NO CSV
    registrar_historico(player_name, preco_num, preco_texto)

    # Retorna todos os dados necessários
    return {
        "player_name": player_name,
        "preco_num": preco_num,
        "price_message": f"O preço de **{player_name}** é: **{preco_texto}**.",
        "time_now": current_time_str,
        "source_site": source_site
    }

# ... (Função get_trade_tip, start_command, button_callback, handle_player_search e main permanecem as mesmas)
# O código a seguir é a continuação do monitor.py

def get_trade_tip(jogador_nome, preco_atual_moedas):
    """Lê o histórico e fornece uma dica simples de trade."""
    
    historico = []
    
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['jogador'].upper() == jogador_nome.upper():
                    historico.append(row)
    except FileNotFoundError:
        return "Primeiro registro. Busque novamente mais tarde para comparar os preços!"

    
    if len(historico) > 1:
        ultimo_registro = historico[-2]
        try:
            preco_anterior = int(ultimo_registro['preco_moedas'])
        except ValueError:
             return "Erro ao ler preço anterior. Verifique o formato do CSV."

        diferenca = preco_atual_moedas - preco_anterior
        
        diferenca_formatada = f"{abs(diferenca):,}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        if diferenca > 0:
            return f"⬆️ **{diferenca_formatada} moedas mais caro** que a última busca ({ultimo_registro['data_hora']}). **PODE SER HORA DE VENDER!**"
        elif diferenca < 0:
            return f"⬇️ **{diferenca_formatada} moedas mais barato** que a última busca ({ultimo_registro['data_hora']}). **PODE SER HORA DE COMPRAR!**"
        else:
            return "➡️ Preço estável desde a última busca."
    else:
        return "Primeiro registro. Busque novamente mais tarde para comparar os preços!"


# ===================================================
# 3. FUNÇÕES DE DIÁLOGO DO TELEGRAM 
# ===================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita /start."""
    top_players = get_top_5_players()
    keyboard = []
    
    for player in top_players:
        button = InlineKeyboardButton(player["nome"], callback_data=f'SEARCH:{player["id"]}')
        keyboard.append([button]) 

    keyboard.append([InlineKeyboardButton("🔎 Buscar por Nome (Digite abaixo)", callback_data='SEARCH_TEXT')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Olá! Qual jogador do EA FC 26 você quer pesquisar? Escolha um popular ou digite o nome:',
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário clica em qualquer botão inline."""
    query = update.callback_query
    await query.answer()

    action, value = query.data.split(':', 1)

    if action == 'SEARCH':
        result = get_player_price(value)
        trade_tip = get_trade_tip(result["player_name"], result["preco_num"])
        
        await query.edit_message_text(
            text=(
                f"✅ **Busca por Jogador Popular**\n\n"
                f"{result['price_message']}\n\n"
                f"🕒 Atualizado às **{result['time_now']} (UTC)**\n"
                f"🌐 Fonte: **{result['source_site']}**\n"
                f"---\n"
                f"📊 **Dica de Trade:**\n{trade_tip}"
            ),
            parse_mode='Markdown'
        )

    elif action == 'SEARCH_TEXT':
        await query.edit_message_text(
            text="Ótimo! Por favor, **digite o nome completo** do jogador que você procura abaixo.",
            parse_mode='Markdown'
        )


async def handle_player_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita um texto que não é um comando."""
    search_term = update.message.text.strip()
    
    result = get_player_price(search_term) 

    trade_tip = get_trade_tip(result["player_name"], result["preco_num"])

    await update.message.reply_text(
        (
            f"🔍 **Resultado da sua busca:**\n\n"
            f"{result['price_message']}\n\n"
            f"🕒 Atualizado às **{result['time_now']} (UTC)**\n"
            f"🌐 Fonte: **{result['source_site']}**\n"
            f"---\n"
            f"📊 **Dica de Trade:**\n{trade_tip}"
        ),
        parse_mode='Markdown'
    )


# ===================================================
# 4. EXECUÇÃO
# ===================================================

def main() -> None:
    """Conecta o bot ao Telegram e inicia a escuta."""
    if not TELEGRAM_BOT_TOKEN:
        print("ERRO CRÍTICO: Token do Telegram não encontrado! Verifique a variável de ambiente.")
        return
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers (Ligações entre o Telegram e as nossas funções)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_search))

    print("🤖 Bot iniciado e ouvindo...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    # Garante que as bibliotecas necessárias para o scraping estejam instaladas
    try:
        __import__('pytz')
        __import__('requests')
        __import__('bs4')
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
