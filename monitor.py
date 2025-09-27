import time
import csv
import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pytz import timezone

# 🚨 BIBLIOTECAS PARA ACESSO À WEB (API-BASED) 🚨
import requests
# BeautifulSoup não é mais necessário para a API, mas mantemos por segurança.
from bs4 import BeautifulSoup 
# ------------------------------------

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# Lista de User-Agents (ainda útil, mas menos crítica para APIs)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]

# URL da API de busca do Futbin (para encontrar o ID do jogador)
FUTBIN_SEARCH_API = "https://www.futbin.com/search_players"
# URL da API de preço do Futbin (o ID será inserido aqui)
FUTBIN_PRICE_API = "https://www.futbin.com/mobile/player_prices?player_id=" 

# ===================================================
# 2. FUNÇÕES DE DADOS E ACESSO À API DO FUTBIN
# ===================================================

def get_player_id(player_name):
    """Usa a API de busca do Futbin para encontrar o ID do jogador."""
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        # A API de busca exige o termo de pesquisa no parâmetro 'term'
        response = requests.get(FUTBIN_SEARCH_API, headers=headers, params={'term': player_name}, timeout=10)
        response.raise_for_status()
        
        # O retorno é um JSON com uma lista de jogadores correspondentes
        results = response.json()
        
        if results and len(results) > 0:
            # Pega o ID do primeiro e melhor resultado
            return results[0].get('id')
            
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Erro na API de busca do Futbin para {player_name}: {e}")
        return None

def get_price_from_api(player_id):
    """Usa a API de preço do Futbin com o ID para obter o preço em JSON."""
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    url = FUTBIN_PRICE_API + str(player_id)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # O retorno é um JSON com os preços por plataforma (PS, XBOX, PC)
        prices_data = response.json()
        
        # O Futbin retorna um dicionário com o ID do jogador como chave principal
        player_data = prices_data.get(str(player_id))
        
        if player_data:
            # Pegamos o preço da plataforma PS (PlayStation) como padrão
            price_info = player_data.get('prices', {}).get('ps')
            
            if price_info and 'LCPrice' in price_info:
                # O preço está formatado como string, ex: '1,500,000'
                price_text = price_info['LCPrice'].replace(',', '') # Remove vírgulas
                return int(price_text), "FUTBIN (API - PS)"
                
        return None, "FUTBIN (API - Preço não encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Erro na API de preço do Futbin para ID {player_id}: {e}")
        return None, "FUTBIN (API - Erro de Conexão)"


def fetch_price_from_web(player_name):
    """
    Coordena a busca do preço usando a API do Futbin.
    """
    
    # 1. Busca o ID do jogador
    player_id = get_player_id(player_name)
    
    if player_id:
        # 2. Se o ID foi encontrado, busca o preço
        price, source = get_price_from_api(player_id)
        
        if price is not None:
            return price, source

    # FALLBACK FINAL (Simulação Aleatória)
    time.sleep(1) 
    preco_num_simulado = random.randint(1000000, 2000000)
    
    # A fonte indicará que o processo de busca do ID falhou
    return preco_num_simulado, "ERRO: Falha na API do Futbin (Simulado)"


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
    """SIMULA a busca pelos 5 jogadores mais buscados."""
    # Para ser 100% real, esta função também teria que usar a API do Futbin
    return [
        {"nome": "Kylian Mbappé", "id": "mbappe_id"},
        {"nome": "V. van Dijk", "id": "vvd_id"},
        {"nome": "E. Haaland", "id": "haaland_id"},
        {"nome": "L. Messi", "id": "messi_id"},
        {"nome": "Vini Jr.", "id": "vinijr_id"}
    ]


def get_player_price(search_term):
    """
    Função principal que chama a API do Futbin.
    """
    
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").title()
    else: 
        player_name = search_term.title()
    
    # 🚨 CHAMADA DA API REAL 🚨
    preco_num, source_site = fetch_price_from_web(player_name)
    
    current_time_str = datetime.now(TIMEZONE).strftime('%H:%M:%S')
        
    preco_texto = f"{preco_num:,}".replace(",", "X").replace(".", ",").replace("X", ".") + " moedas"

    registrar_historico(player_name, preco_num, preco_texto)

    return {
        "player_name": player_name,
        "preco_num": preco_num,
        "price_message": f"O preço de **{player_name}** é: **{preco_texto}**.",
        "time_now": current_time_str,
        "source_site": source_site
    }


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
    # Garante que as bibliotecas necessárias para o acesso à API estejam instaladas
    try:
        __import__('pytz')
        __import__('requests')
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
