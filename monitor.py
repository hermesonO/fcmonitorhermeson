# monitor.py - Bloco A

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
