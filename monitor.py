import time
import csv
import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pytz import timezone
import re # Nova importação para expressões regulares

# 🚨 BIBLIOTECAS PARA SCRAPING 🚨
import requests
from bs4 import BeautifulSoup
# ------------------------------------

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# FUTBIN_API_KEY não é mais necessário para este método, mas a lógica de headers permanece.
FUTBIN_API_KEY = os.environ.get("FUTBIN_API_KEY", "FUT_WEB") # Valor default de segurança

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]

# URL Base para TENTATIVA DE SCRAPING NO FUTBIN (voltando à busca por URL de redirecionamento)
FUTBIN_SEARCH_URL = "https://www.futbin.com/search?query=" 

# ===================================================
# 2. FUNÇÕES DE DADOS E SCRAPING HTML
# ===================================================

def clean_price_text(price_text):
    """Limpa o texto do preço, removendo formatação de milhar/milhão."""
    
    # Remove qualquer caracter que não seja número (0-9)
    price_text = re.sub(r'[^\d]', '', price_text)
    
    return int(price_text) if price_text.isdigit() else None


def get_headers():
    """Gera o cabeçalho de requisição com User-Agent rotativo."""
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        # Mantemos o X-Requested-With e Referer para simular melhor o navegador
        'X-Requested-With': FUTBIN_API_KEY, 
        'Referer': 'https://www.futbin.com/'
    }
    return headers


def scrape_futbin_html(player_name):
    """
    Tenta extrair o preço do Futbin forçando o redirecionamento.
    """
    
    search_term = player_name.lower().replace(" ", "+")
    url = f"{FUTBIN_SEARCH_URL}{search_term}"
    
    try:
        # Acessa a URL de busca e segue o redirecionamento para a página do jogador
        response = requests.get(url, headers=get_headers(), timeout=10, allow_redirects=True)
        response.raise_for_status() 

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ⚠️ TENTATIVA DE ENCONTRAR OS PREÇOS PS e XBOX NA PÁGINA REDIRECIONADA
        
        # O preço PS4/5 geralmente está em 'span' ou 'div' com classes específicas
        # Tentativa 1: Classe principal do preço PS
        ps_element = soup.find('span', class_='ps4_price')
        if not ps_element:
            ps_element = soup.find('div', class_='ps4_price_val')
        
        # Tentativa 2: Classe principal do preço Xbox
        xbox_element = soup.find('span', class_='xbox_price')
        if not xbox_element:
            xbox_element = soup.find('div', class_='xbox_price_val')
            
        ps_price = clean_price_text(ps_element.get_text(strip=True)) if ps_element else None
        xbox_price = clean_price_text(xbox_element.get_text(strip=True)) if xbox_element else None
        
        if ps_price or xbox_price:
            return {
                "ps_price": ps_price,
                "xbox_price": xbox_price,
                "source": "FUTBIN (HTML Scraping)"
            }
        
        print("Futbin Erro: Elementos de preço PS/XBOX não encontrados.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Futbin Erro de Conexão/Bloqueio: {e}")
        return None


def fetch_price_from_web(player_name):
    """
    Tenta o scraping principal no Futbin.
    """
    
    # Tenta o scraping
    result = scrape_futbin_html(player_name)
    
    if result:
        return result
        
    # FALLBACK FINAL (Simulação Aleatória)
    time.sleep(1) 
    
    return {
        "ps_price": random.randint(1000000, 2000000), 
        "xbox_price": random.randint(1000000, 2000000), 
        "source": "ERRO: Todos os métodos falharam (Simulado)"
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
    
    # 🚨 CHAMADA DO SCRAPING REAL 🚨
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
        __import__('bs4') # Necessário para o scraping
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
