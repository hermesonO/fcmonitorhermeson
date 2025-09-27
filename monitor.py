import time
import csv
import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
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

# Cabeçalhos robustos para simular um navegador Chrome (evita bloqueios)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ===================================================
# 2. FUNÇÕES DE DADOS E SCRAPING MULTI-SITE
# ===================================================

def registrar_historico(jogador, preco_moedas, preco_formatado):
    """Adiciona a busca do jogador ao arquivo CSV."""
    
    # Se o arquivo não existe, cria-o com o cabeçalho
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as f:
            f.readline()
    except FileNotFoundError:
        try:
            # Tenta criar o arquivo na pasta correta
            with open('preços_historico.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['data_hora', 'jogador', 'preco_moedas', 'preco_formatado'])
        except Exception as e:
            print(f"Erro ao criar preços_historico.csv: {e}")
            return
        
    # Abre o arquivo CSV no modo 'a' (append/adicionar)
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Registra a data/hora atual
        now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        
        # Escreve a nova linha de dados no arquivo
        writer.writerow([now, jogador, preco_moedas, preco_formatado])
        
    print(f"Histórico registrado: {jogador} | {preco_formatado}")


def clean_price_text(price_text):
    """Limpa o texto do preço, removendo moedas, K, pontos e vírgulas."""
    # Remove 'K' (para milhares) e trata a formatação brasileira (ponto separador de milhar)
    cleaned = price_text.lower().replace('k', '').replace('.', '').replace(',', '').strip()
    
    # Tenta converter para inteiro. Se for '589', retorna 589000
    try:
        num = int(cleaned)
        # Se o preço for pequeno (ex: 589), e o texto original tinha 'K', adiciona zeros
        if 'k' in price_text.lower():
            return num * 1000
        return num
    except ValueError:
        return None # Retorna None se a limpeza falhar


def scrape_futbin(player_name):
    """Tenta extrair o preço do Futbin."""
    
    # O Futbin exige uma URL de busca mais complexa para encontrar o ID.
    # Para simplificar, vamos tentar uma busca direta (que pode falhar) e procurar o preço.
    
    # Formata o nome para a URL (Futbin geralmente prefere o nome na URL)
    search_term = player_name.lower().replace(" ", "+")
    url = f"https://www.futbin.com/search?query={search_term}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ⚠️ Ponto Crítico do FUTBIN:
        # Tenta encontrar o preço no resultado da busca ou na página redirecionada.
        # Busca pela classe onde o preço geralmente é exibido (exemplo baseado em inspeção comum)
        price_element = soup.find('span', class_='ps4_price') 
        
        if not price_element:
            price_element = soup.find('span', class_='ps4_price_val') # Tentativa secundária
            
        if price_element:
            price_text = price_element.get_text(strip=True)
            final_price = clean_price_text(price_text)
            
            if final_price is not None:
                return final_price, "FUTBIN (Real)"
            else:
                return None, "FUTBIN (Formato Inválido)"

        return None, "FUTBIN (Elemento Não Encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Futbin Erro: {e}")
        return None, "FUTBIN (Erro de Conexão)"


def scrape_futwiz(player_name):
    """Tenta extrair o preço do Futwiz (Secundário)."""
    
    search_slug = player_name.lower().replace(" ", "-").replace(".", "").replace("'", "")
    # A URL do Futwiz precisa do ID, então vamos usar uma URL de busca que pode falhar
    url = f"https://www.futwiz.com/en/fifa24/search/price/{search_slug}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ⚠️ Ponto Crítico do FUTWIZ (Classe do Preço):
        price_element = soup.find('div', class_='pc-price')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            final_price = clean_price_text(price_text)
            
            if final_price is not None:
                return final_price, "FUTWIZ (Real)"
            else:
                return None, "FUTWIZ (Formato Inválido)"

        return None, "FUTWIZ (Elemento Não Encontrado)"

    except requests.exceptions.RequestException as e:
        print(f"Futwiz Erro: {e}")
        return None, "FUTWIZ (Erro de Conexão)"


def fetch_price_from_web(player_name):
    """
    Coordena as tentativas de scraping.
    """
    
    # 1. TENTA FUTBIN (Prioridade)
    price, source = scrape_futbin(player_name)
    if price is not None:
        return price, source

    # 2. TENTA FUTWIZ (Fallback)
    price, source = scrape_futwiz(player_name)
    if price is not None:
        return price, source
        
    # 3. FALLBACK FINAL (Simulação Aleatória)
    time.sleep(1) 
    preco_num_simulado = random.randint(1000000, 2000000)
    
    # Se todas as fontes falharam, a última fonte será a que falhou por último
    # (ou a mais prioritária que identificou o erro)
    # Aqui, a última fonte que tentamos foi o FUTWIZ:
    return preco_num_simulado, "ERRO: Todos os sites falharam (Simulado)"


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
    
    # Lógica de formatação de nome:
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").title()
    else: 
        player_name = search_term.title()
    
    # 🚨 CHAMADA DO SCRAPING REAL ENCAREADO 🚨
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
