import time
import csv
import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pytz import timezone

# 🚨 BIBLIOTECAS PARA SCRAPING 🚨
import requests
from bs4 import BeautifulSoup
# ------------------------------------

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# Lista de User-Agents para evitar bloqueio por repetição
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]


# ===================================================
# 2. FUNÇÕES DE DADOS E SCRAPING MULTI-SITE
# ===================================================

def clean_price_text(price_text):
    """Limpa o texto do preço, removendo K/M e formatação de milhar."""
    
    # Remove qualquer caracter que não seja número, K, M, ponto ou vírgula
    price_text = price_text.lower().replace('.', '').replace(',', '').strip()

    if 'm' in price_text:
        # Preços em Milhões (ex: 1.5M -> 1500000)
        num = float(price_text.replace('m', '')) * 1000000
    elif 'k' in price_text:
        # Preços em Milhares (ex: 500K -> 500000)
        num = float(price_text.replace('k', '')) * 1000
    else:
        # Preços sem notação (assume que já é o número total)
        num = float(price_text)

    # Arredonda e retorna como inteiro (ex: 1500000)
    return int(num) if num is not None else None


def scrape_futbin(player_name):
    """
    Tenta extrair o preço do Futbin usando o recurso de busca e redirecionamento.
    """
    
    # 1. Tenta acessar a URL de busca
    search_term = player_name.lower().replace(" ", "+")
    url = f"https://www.futbin.com/search?query={search_term}"
    
    # Escolhe um User-Agent aleatório para cada busca
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        # Permite redirecionamento (o Futbin redireciona a busca para a página do jogador)
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status() # Verifica erros HTTP

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ⚠️ Ponto Crítico do FUTBIN:
        # O preço PS4/5 geralmente está em 'span' com classes específicas
        # Tentativa 1: Preço principal no topo da página
        price_element = soup.find('span', class_='ps4_price') 
        
        if not price_element:
            # Tentativa 2: Preço principal dentro de uma div
            price_element = soup.find('div', class_='ps4_price_val') 
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            final_price = clean_price_text(price_text)
            
            if final_price is not None:
                return final_price, "FUTBIN (Real)"
            else:
                print(f"Futbin Erro: Formato de preço inválido: {price_text}")
                return None, "FUTBIN (Formato Inválido)"

        # Se não encontrou o elemento, pode ser uma página de múltiplos resultados
        print("Futbin Erro: Elemento de preço não encontrado. Talvez seja página de busca.")
        return None, "FUTBIN (Elemento Não Encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Futbin Erro de Conexão: {e}")
        return None, "FUTBIN (Erro de Conexão)"


def fetch_price_from_web(player_name):
    """
    Coordena a tentativa de scraping principal no Futbin.
    """
    
    # Tenta o scraping
    price, source = scrape_futbin(player_name)
    
    if price is not None:
        return price, source
        
    # FALLBACK FINAL (Simulação Aleatória)
    time.sleep(1) 
    preco_num_simulado = random.randint(1000000, 2000000)
    
    return preco_num_simulado, "ERRO: Busca Real Falhou (Simulado)"


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
    
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").title()
    else: 
        player_name = search_term.title()
    
    # 🚨 CHAMADA DO SCRAPING REAL 🚨
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
    # Garante que as bibliotecas necessárias para o scraping estejam instaladas
    try:
        __import__('pytz')
        __import__('requests')
        __import__('bs4')
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
