# monitor.py - Bloco A

# monitor.py - (Parte superior, junto com os outros imports)

# ... (outros imports, como from telegram import... )
import time
import csv
from datetime import datetime # Para registrar o horário da busca

# 🚨 Seu TELEGRAM_BOT_TOKEN aqui

# ... (Suas funções get_top_5_players e get_player_price)

# --- NOVA FUNÇÃO DE REGISTRO DE HISTÓRICO ---

def registrar_historico(jogador, preco_moedas, preco_formatado):
    """Adiciona a busca do jogador ao arquivo CSV."""
    
    # 1. Abre o arquivo CSV no modo 'a' (append/adicionar)
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # 2. Registra a data/hora atual
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 3. Escreve a nova linha de dados no arquivo
        writer.writerow([now, jogador, preco_moedas, preco_formatado])
        
    print(f"Histórico registrado: {jogador} | {preco_formatado}") # Log para você ver no console


# --- FUNÇÃO get_player_price (PRECISA SER ATUALIZADA) ---

def get_player_price(search_term):
    """SIMULA a busca do preço de um jogador e REGISTRA o histórico."""
    
    # Simulação da busca (AQUI você colocará seu código de scraping no futuro)
    time.sleep(1) 
    
    # Dados Simulados:
    preco_num = 1500000 # Valor em números inteiros para o CSV
    preco_texto = f"{preco_num:,}".replace(",", ".") + " moedas" # Formatado para o usuário (ex: 1.500.000)
    
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").upper()
    else: 
        player_name = search_term.title()
    
    # ⚠️ CHAMADA DA NOVA FUNÇÃO: REGISTRA A BUSCA NO CSV
    registrar_historico(player_name, preco_num, preco_texto)

    return f"O preço de **{player_name}** é: **{preco_texto}**."

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import time

# 🚨 CHAVE SECRETA: Troque "SEU_TOKEN_AQUI" pelo token que você pegou com o BotFather
TELEGRAM_BOT_TOKEN = "8370599851:AAGYNGyUoEmrMv3ZcKXzAJe1ixuJrwcB-Bg" 

# --- FUNÇÕES DE COLETA DE DADOS (SIMULADAS) ---

def get_top_5_players():
    """SIMULA a busca pelos 5 jogadores mais buscados no Futbin/Fut.gg."""
    # NO FUTURO: Aqui você colocará seu código de scraping/API.
    # Por enquanto, retornamos dados fixos para testar a interface do bot.
    return [
        {"nome": "Kylian Mbappé", "id": "mbappe_id"},
        {"nome": "V. van Dijk", "id": "vvd_id"},
        {"nome": "E. Haaland", "id": "haaland_id"},
        {"nome": "L. Messi", "id": "messi_id"},
        {"nome": "Vini Jr.", "id": "vinijr_id"}
    ]

def get_player_price(search_term):
    """SIMULA a busca do preço de um jogador específico."""
    # NO FUTURO: Aqui você fará a requisição real para o site.
    
    # Simula o tempo de busca
    time.sleep(1) 
    
    # Se o termo for um dos IDs (clique no botão), formatamos o nome
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").upper()
    else: # Se for busca por texto digitado
        player_name = search_term.title()
        
    return f"O preço de **{player_name}** é: **{1500000} moedas**." # Preço fictício

# monitor.py - Bloco B

# monitor.py - (Abaixo da função registrar_historico)

def get_trade_tip(jogador_nome, preco_atual_moedas):
    """Lê o histórico e fornece uma dica simples de trade."""
    
    historico = []
    # 1. Lê todo o histórico do arquivo CSV
    with open('preços_historico.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['jogador'].upper() == jogador_nome.upper():
                historico.append(row)
    
    # 2. Se há histórico:
    if len(historico) > 1:
        # Pega o preço mais recente ANTES da busca atual
        ultimo_registro = historico[-2]
        preco_anterior = int(ultimo_registro['preco_moedas'])
        
        diferenca = preco_atual_moedas - preco_anterior
        
        if diferenca > 0:
            return f"⬆️ **{diferenca:,} moedas mais caro** que a última busca ({ultimo_registro['data_hora']}). **PODE SER HORA DE VENDER!**"
        elif diferenca < 0:
            return f"⬇️ **{-diferenca:,} moedas mais barato** que a última busca ({ultimo_registro['data_hora']}). **PODE SER HORA DE COMPRAR!**"
        else:
            return "➡️ Preço estável desde a última busca."
    else:
        return "Primeiro registro. Busque novamente mais tarde para comparar os preços!"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita /start ou envia a primeira mensagem."""
    top_players = get_top_5_players()
    keyboard = []
    
    # Cria os botões para os 5 jogadores mais buscados
    for player in top_players:
        # data='SEARCH:{id}' é o que o bot recebe quando o botão é clicado
        button = InlineKeyboardButton(player["nome"], callback_data=f'SEARCH:{player["id"]}')
        keyboard.append([button]) 

    # Adiciona a opção de busca por nome, que não tem um ID de jogador
    keyboard.append([InlineKeyboardButton("🔎 Buscar por Nome (Digite abaixo)", callback_data='SEARCH_TEXT')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Olá! Qual jogador do EA FC 26 você quer pesquisar? Escolha um popular ou digite o nome:',
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário clica em qualquer botão inline."""
    query = update.callback_query
    await query.answer() # Sinaliza que o clique foi recebido

    # Separa a ação do valor (ex: 'SEARCH' e 'mbappe_id')
    action, value = query.data.split(':', 1)

    if action == 'SEARCH':
        # Busca o preço usando o ID do botão
        price_message = get_player_price(value) 

        await query.edit_message_text(
            text=f"✅ **Busca por Jogador Popular**\n\n{price_message}",
            parse_mode='Markdown'
        )

    elif action == 'SEARCH_TEXT':
        # Altera a mensagem para pedir o nome
        await query.edit_message_text(
            text="Ótimo! Por favor, **digite o nome completo** do jogador que você procura abaixo.",
            parse_mode='Markdown'
        )


async def handle_player_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita um texto que não é um comando."""
    search_term = update.message.text.strip()
    
    # Busca o preço usando o nome digitado
    price_message = get_player_price(search_term) 

    await update.message.reply_text(
        f"🔍 **Resultado da sua busca:**\n\n{price_message}",
        parse_mode='Markdown'
    )

# monitor.py - Bloco C

# monitor.py - (Dentro das funções button_callback e handle_player_search)

# ... (No final do Bloco B, substitua as funções originais pelas abaixo)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... código de início da função ...
    
    if action == 'SEARCH':
        price_message = get_player_price(value) # Esta função agora registra o CSV
        
        # Simulação para obter o preço numérico para a dica
        # No futuro, você ajustará o 'get_player_price' para retornar o preço numérico.
        preco_num_simulado = 1500000
        player_name = value.replace("_id", "").upper()

        # ⚠️ CHAMA A DICA DE TRADE
        trade_tip = get_trade_tip(player_name, preco_num_simulado)
        
        await query.edit_message_text(
            text=f"✅ **Busca por Jogador Popular**\n\n{price_message}\n\n---\n📊 **Dica de Trade:**\n{trade_tip}",
            parse_mode='Markdown'
        )

    # ... (o código elif action == 'SEARCH_TEXT' continua igual) ...


async def handle_player_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    search_term = update.message.text.strip()
    
    price_message = get_player_price(search_term) # Esta função agora registra o CSV

    # Simulação para obter o preço numérico para a dica
    preco_num_simulado = 1500000
    player_name = search_term.title()

    # ⚠️ CHAMA A DICA DE TRADE
    trade_tip = get_trade_tip(player_name, preco_num_simulado)

    await update.message.reply_text(
        f"🔍 **Resultado da sua busca:**\n\n{price_message}\n\n---\n📊 **Dica de Trade:**\n{trade_tip}",
        parse_mode='Markdown'
    )

def main() -> None:
    """Conecta o bot ao Telegram e inicia a escuta."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Adiciona os Handlers (ligações entre o Telegram e as nossas funções)
    # 1. /start chama a start_command
    application.add_handler(CommandHandler("start", start_command))
    
    # 2. Clique em qualquer botão inline chama a button_callback
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 3. Qualquer texto que NÃO for comando (~) chama a handle_player_search
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_search))

    print("🤖 Bot iniciado e ouvindo...")
    # Roda o bot e ele fica ativo 24/7 (ou enquanto seu script estiver rodando)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


# ----------------------------------------------------
# Bloco D: Execução
# ----------------------------------------------------

# Este código garante que a função main() seja chamada ao rodar o arquivo
if __name__ == '__main__':
    main()
