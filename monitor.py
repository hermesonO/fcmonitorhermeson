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
# ------------------------------------

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# 🚨 CHAVE DE ACESSO DO FUTBIN (Definida no PythonAnywhere)
# O valor 'FUT_WEB' é um valor conhecido que simula a requisição de um navegador.
FUTBIN_API_KEY = os.environ.get("FUTBIN_API_KEY") 

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]

# URLs da API do Futbin
FUTBIN_SEARCH_API = "https://www.futbin.com/search_players"
FUTBIN_PRICE_API = "https://www.futbin.com/mobile/player_prices?player_id=" 

# ===================================================
# 2. FUNÇÕES DE DADOS E ACESSO À API DO FUTBIN
# ===================================================

def get_headers():
    """Gera o cabeçalho de requisição com User-Agent rotativo e a API Key."""
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        # Este cabeçalho é essencial para simular uma requisição AJAX
        'X-Requested-With': FUTBIN_API_KEY 
    }
    # Adiciona referer para simular que a requisição veio do próprio site
    if 'FUT_WEB' in FUTBIN_API_KEY:
         headers['Referer'] = 'https://www.futbin.com/'
         
    return headers


def get_player_id(player_name):
    """Usa a API de busca do Futbin para encontrar o ID do jogador."""
    
    headers = get_headers()
    
    try:
        response = requests.get(FUTBIN_SEARCH_API, headers=headers, params={'term': player_name}, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        
        if results and len(results) > 0:
            return results[0].get('id')
            
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Erro na API de busca do Futbin para {player_name}: {e}")
        return None

def get_price_from_api(player_id):
    """Usa a API de preço do Futbin com o ID para obter os preços em JSON (PS e XBOX)."""
    
    headers = get_headers()
    url = FUTBIN_PRICE_API + str(player_id)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        prices_data = response.json()
        player_data = prices_data.get(str(player_id))
        
        if player_data:
            price_info = player_data.get('prices', {})
            
            # --- EXTRAÇÃO DO PREÇO DO PS ---
            ps_price_text = price_info.get('ps', {}).get('LCPrice', '')
            # Remove vírgulas e tenta converter
            ps_price = int(ps_price_text.replace(',', '')) if ps_price_text.replace(',', '').isdigit() else None
            
            # --- EXTRAÇÃO DO PREÇO DO XBOX ---
            xbox_price_text = price_info.get('xbox', {}).get('LCPrice', '')
            xbox_price = int(xbox_price_text.replace(',', '')) if xbox_price_text.replace(',', '').isdigit() else None
            
            # Retorna um dicionário com os preços e a fonte
            if ps_price or xbox_price:
                return {
                    "ps_price": ps_price,
                    "xbox_price": xbox_price,
                    "source": "FUTBIN (API - PS/XBOX)"
                }
                
        # Se encontrou o ID, mas não encontrou o preço
        return None, "FUTBIN (API - Preço não encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Erro na API de preço do Futbin para ID {player_id}: {e}")
        return None, "FUTBIN (API - Erro de Conexão)"


def fetch_price_from_web(player_name):
    """
    Coordena a busca do preço usando a API do Futbin e retorna os preços das plataformas.
    """
    
    # Verifica se a chave foi definida (para evitar erros de Simulado)
    if not FUTBIN_API_KEY:
        return {
            "ps_price": random.randint(1000000, 2000000), 
            "xbox_price": random.randint(1000000, 2000000), 
            "source": "ERRO: Chave FUTBIN_API_KEY não definida (Simulado)"
        }
        
    # 1. Busca o ID do jogador
    player_id = get_player_id(player_name)
    
    if player_id:
        # 2. Se o ID foi encontrado, busca o preço
        result = get_price_from_api(player_id)
        
        if isinstance(result, dict):
            return result

    # FALLBACK FINAL (Simulação Aleatória)
    time.sleep(1) 
    
    return {
        "ps_price": random.randint(1000000, 2000000), 
        "xbox_price": random.randint(1000000, 2000000), 
        "source": "ERRO: Falha na API do Futbin (Simulado)"
    }


def registrar_historico(jogador, preco_moedas, preco_formatado):
    """Adiciona a busca do jogador ao arquivo CSV."""
    
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
    return [
        {"nome": "Kylian Mbappé", "id": "mbappe_id"},
        {"nome": "V. van Dijk", "id": "vvd_id"},
        {"nome": "E. Haaland", "id": "haaland_id"},
        {"nome": "L. Messi", "id": "messi_id"},
        {"nome": "Vini Jr.", "id": "vinijr_id"}
    ]


def get_player_price(search_term):
    """
    Função principal que prepara a mensagem final.
    """
    
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").title()
    else: 
        player_name = search_term.title()
    
    # 🚨 CHAMADA DA API REAL 🚨
    price_data = fetch_price_from_web(player_name)
    
    current_time_str = datetime.now(TIMEZONE).strftime('%H:%M:%S')
    
    # --- PREPARAÇÃO DA MENSAGEM FINAL ---
    
    # Usamos o preço do PS para o histórico e a dica de trade
    preco_num_ps = price_data.get("ps_price", 0) 
    
    # Formatação dos preços para exibição
    
    def format_price(price):
        if price:
            # Formatação de milhares (1.000.000)
            return f"{price:,}".replace(",", "X").replace(".", ",").replace("X", ".") + " moedas"
        return "N/D"

    preco_ps_texto = format_price(price_data.get("ps_price"))
    preco_xbox_texto = format_price(price_data.get("xbox_price"))
    
    price_message = (
        f"O preço de **{player_name}** é:\n"
        f"🔹 **PlayStation:** {preco_ps_texto}\n"
        f"🟢 **Xbox:** {preco_xbox_texto}"
    )

    registrar_historico(player_name, preco_num_ps, preco_ps_texto)

    return {
        "player_name": player_name,
        "preco_num": preco_num_ps, # Mantém apenas o PS para a dica de trade
        "price_message": price_message,
        "time_now": current_time_str,
        "source_site": price_data.get("source")
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
