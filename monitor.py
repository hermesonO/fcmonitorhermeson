import csv
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pytz import timezone

# ===================================================
# 1. CONFIGURAÇÃO E DADOS VISUAIS
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# Tipos de plataformas disponíveis (com emojis para visual)
PLATFORMS = {
    'PS': 'PlayStation 🎮', 
    'XB': 'Xbox 💚', 
    'PC': 'PC 💻'
}

# Novo Estado:
# 'WAITING_FOR_SEARCH_NAME': O bot espera o nome do jogador apenas para BUSCA.
# ------------------------------------------------------------------------------------------------------

# ===================================================
# 2. FUNÇÕES DE FORMATAÇÃO E DADOS
# ===================================================

def format_price(price):
    """Formata o número de moedas (ex: 1.000.000) e adiciona o ícone."""
    if price is None:
        return "N/D"
    price_str = f"{price:,}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{price_str} 🪙"

def registrar_historico(jogador, preco_moedas, plataforma):
    """Adiciona o registro de preço manual ao arquivo CSV."""
    # (Lógica omitida por ser a mesma, apenas para não lotar o código aqui)
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as f:
            f.readline()
    except FileNotFoundError:
        try:
            with open('preços_historico.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['data_hora', 'jogador', 'preco_moedas', 'plataforma'])
        except Exception as e:
            print(f"Erro ao criar preços_historico.csv: {e}")
            return
        
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        try:
            preco_limpo = int(str(preco_moedas).replace('.', '').replace(',', ''))
        except ValueError:
            preco_limpo = 0
            
        writer.writerow([now, jogador, preco_limpo, plataforma])
        
    print(f"Histórico registrado: {jogador} ({plataforma}) | {preco_limpo}")


def get_last_registered_price(player_name):
    """Busca o último preço registrado manualmente para um jogador."""
    historico = []
    player_name_upper = player_name.upper()
    
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['jogador'].upper() == player_name_upper:
                    historico.append(row)
    except FileNotFoundError:
        return None, "O histórico de preços está vazio."
    
    if historico:
        last_entry = historico[-1]
        
        try:
            dt_obj = datetime.strptime(last_entry['data_hora'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=TIMEZONE)
            preco_moedas = int(last_entry.get('preco_moedas', 0))
        except ValueError:
             return None, f"Erro de formato nos dados para {player_name}."

        price_message = (
            f"📚 Último Registro de **{player_name}**:\n"
            f"💰 **Preço:** {format_price(preco_moedas)}\n"
            f"🎮 **Plataforma:** {last_entry['plataforma']}\n"
            f"📅 **Atualizado em:** {dt_obj.strftime('%d/%m/%Y')} às {dt_obj.strftime('%H:%M:%S')} (UTC)"
        )

        return {
            "player_name": player_name,
            "preco_num": preco_moedas,
            "price_message": price_message,
        }, None
        
    return None, f"Nenhum preço registrado para **{player_name}**."


def get_trade_tip(jogador_nome, preco_atual_moedas):
    """Gera o 'gráfico simples' (Dica de Trade com emojis)."""
    
    historico = []
    player_name_upper = jogador_nome.upper()
    
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['jogador'].upper() == player_name_upper:
                    historico.append(row)
    except FileNotFoundError:
        return "Primeiro registro. Registre mais preços para ativar a Dica de Trade!"

    
    if len(historico) > 1:
        ultimo_registro = historico[-2]
        
        try:
            preco_anterior = int(ultimo_registro['preco_moedas'])
        except ValueError:
             return "Erro ao ler preço anterior."

        diferenca = preco_atual_moedas - preco_anterior
        
        diferenca_formatada = format_price(abs(diferenca))
        
        if diferenca > 0:
            return f"⬆️ **{diferenca_formatada} mais caro** que o registro anterior. **PODE SER HORA DE VENDER!**"
        elif diferenca < 0:
            return f"⬇️ **{diferenca_formatada} mais barato** que o registro anterior. **PODE SER HORA DE COMPRAR!**"
        else:
            return "➡️ Preço estável desde o registro anterior."
    else:
        return "Primeiro registro. Registre mais preços para ativar a Dica de Trade!"


def get_detailed_player_history(player_name, limit=3):
    """BUSCA DETALHADA: Retorna os últimos N registros de preço para um jogador específico."""
    historico = []
    player_name_upper = player_name.upper()
    
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['jogador'].upper() == player_name_upper:
                    historico.append(row)
    except FileNotFoundError:
        return "Histórico não encontrado."

    if len(historico) <= 1:
        return "Nenhum registro anterior para comparação."
        
    # Pega os últimos 'limit' registros e inverte para o mais recente ficar no topo
    recent_entries = historico[-limit:][::-1]
    
    detailed_history = []
    for entry in recent_entries:
        try:
            dt_obj = datetime.strptime(entry['data_hora'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=TIMEZONE)
            preco_moedas = int(entry.get('preco_moedas', 0))
        except ValueError:
            continue
            
        entry_line = (
            f"   • **{format_price(preco_moedas)}** ({entry['plataforma'].replace(' ', ' ')})\n"
            f"     Em: *{dt_obj.strftime('%d/%m %H:%M')}*"
        )
        detailed_history.append(entry_line)
        
    return "\n".join(detailed_history)


def get_all_registered_players():
    """Lê o CSV e retorna uma lista de todos os jogadores únicos registrados."""
    players = set()
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                players.add(row['jogador'].title())
    except FileNotFoundError:
        pass
        
    return sorted(list(players))

def get_recent_history(limit=5):
    """Retorna os últimos N registros do CSV."""
    history = []
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            history = list(reader)[-limit:]
    except FileNotFoundError:
        return []
    
    return history[::-1]


# ===================================================
# 3. HANDLERS E FLUXO DE CONVERSA
# ===================================================

async def handle_message_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com mensagens de texto do usuário, controlando o estado da conversa."""
    
    text = update.message.text.strip()
    user_data = context.user_data
    current_state = user_data.get('flow_state', 'READY')
    
    # ----------------------------------------------------
    # ESTADO: ESPERANDO NOME DO JOGADOR (REGISTRO)
    # ----------------------------------------------------
    if current_state == 'WAITING_FOR_PLAYER':
        
        player_name = text.title()
        user_data['temp_player_name'] = player_name
        user_data['flow_state'] = 'ASKING_FOR_PLATFORM'
        
        keyboard = [
            [InlineKeyboardButton(display_name, callback_data=f'PLATFORM:{key}') for key, display_name in PLATFORMS.items()]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Jogador: **{player_name}**\n\nEm qual plataforma você viu este preço? Escolha abaixo:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    # ----------------------------------------------------
    # ESTADO: ESPERANDO PREÇO
    # ----------------------------------------------------
    elif current_state == 'WAITING_FOR_PRICE':
        try:
            price = int(text.replace('.', '').replace(',', '')) 
        except ValueError:
            await update.message.reply_text("🚨 Preço inválido. Por favor, digite o preço apenas com números (ex: 1500000).")
            return
            
        player_name = user_data.get('temp_player_name')
        platform = user_data.get('temp_platform')

        if not player_name or not platform:
            await update.message.reply_text("🚨 Erro na sessão. Por favor, comece de novo com /start.")
            user_data['flow_state'] = 'READY'
            return

        registrar_historico(player_name, price, platform)
        trade_tip = get_trade_tip(player_name, price)

        user_data['flow_state'] = 'READY'
        user_data.pop('temp_player_name', None)
        user_data.pop('temp_platform', None)
        
        response_text = (
            f"✅ **Registro Concluído!**\n\n"
            f"**{player_name}** ({platform}) salvo por **{format_price(price)}**.\n"
            f"---\n"
            f"📈 **Dica de Trade:**\n{trade_tip}"
        )
        
        await update.message.reply_text(
            response_text,
            parse_mode='Markdown'
        )
        return

    # ----------------------------------------------------
    # ESTADO: ESPERANDO NOME DO JOGADOR (BUSCA)
    # ----------------------------------------------------
    elif current_state == 'WAITING_FOR_SEARCH_NAME':
        
        player_name_search = text.title()
        user_data['flow_state'] = 'READY' # Retorna para o estado normal após a busca
        
        result, error_msg = get_last_registered_price(player_name_search)
        
        if result:
            trade_tip = get_trade_tip(result["player_name"], result["preco_num"])
            detailed_history = get_detailed_player_history(result["player_name"], limit=3)

            response_text = (
                f"{result['price_message']}\n"
                f"---\n"
                f"📈 **Dica de Trade:**\n{trade_tip}\n"
                f"---\n"
                f"📚 **Últimos Registros (3):**\n"
                f"{detailed_history}"
            )
            
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown'
            )
            return

        else:
            await update.message.reply_text(
                f"🚨 Não encontrei registros para **{player_name_search}**.\n\n"
                f"Use /start para voltar ao menu ou **digite outro nome** para pesquisar novamente.",
                parse_mode='Markdown'
            )
            return
            
    # ----------------------------------------------------
    # ESTADO: PRONTO (QUALQUER OUTRO TEXTO)
    # ----------------------------------------------------
    elif current_state == 'READY':
        # Qualquer texto em estado 'READY' que não é comando volta ao menu principal
        await start_command(update, context)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita /start ou 'oi'. Menu Principal."""
    
    keyboard = [
        [InlineKeyboardButton("💰 Registrar Novo Preço", callback_data='MENU:REGISTRAR')],
        [InlineKeyboardButton("🔎 Pesquisar Jogador", callback_data='MENU:PESQUISAR')],
        [InlineKeyboardButton("📚 Histórico Completo", callback_data='MENU:HISTORICO')],
        [InlineKeyboardButton("⏱ Últimos 5 Registros", callback_data='MENU:RECENTES')],
        [InlineKeyboardButton("💾 Exportar Dados (CSV)", callback_data='MENU:EXPORTAR')], # 🚨 NOVO BOTÃO
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_source = update.callback_query.message if update.callback_query else update.message

    # Sempre limpa o estado ao voltar ao menu principal
    context.user_data['flow_state'] = 'READY' 

    await message_source.reply_text(
        "👋 **Menu Principal - Monitor de Preços**\n\n"
        "Selecione uma opção abaixo:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """NOVA FUNÇÃO: Envia o arquivo CSV do histórico."""
    try:
        if os.path.exists('preços_historico.csv'):
            with open('preços_historico.csv', 'rb') as doc:
                await update.message.reply_document(
                    document=doc,
                    caption="💾 **Seu Histórico de Preços (CSV):**\n\nPronto para análise em Excel ou Sheets!",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("🚨 Arquivo de histórico não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"🚨 Erro ao exportar: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com todos os botões inline (Plataforma, Menu, Histórico)."""
    query = update.callback_query
    await query.answer()

    action, value = query.data.split(':', 1)
    
    if action == 'MENU':
        if value == 'REGISTRAR':
            context.user_data['flow_state'] = 'WAITING_FOR_PLAYER'
            await query.edit_message_text(
                "💰 Ótimo! **Qual jogador você comprou ou está monitorando?**\n(Ex: Vini Jr.)",
                parse_mode='Markdown'
            )
        
        elif value == 'PESQUISAR':
            # 🚨 MUDANÇA DE ESTADO: Agora espera o nome para busca 🚨
            context.user_data['flow_state'] = 'WAITING_FOR_SEARCH_NAME'
            await query.edit_message_text(
                "🔎 Por favor, **digite o nome completo** do jogador que você procura abaixo.",
                parse_mode='Markdown'
            )
            
        elif value == 'HISTORICO':
            await history_command(query, context)
            
        elif value == 'RECENTES':
            await recent_history_command(query, context)
            
        elif value == 'EXPORTAR':
            # Executa o comando de exportar e remove o menu de botões
            await export_command(query.message, context)
            await query.delete_message()


    elif action == 'PLATFORM' and context.user_data.get('flow_state') == 'ASKING_FOR_PLATFORM':
        
        platform_name = PLATFORMS.get(value)
        context.user_data['temp_platform'] = platform_name
        context.user_data['flow_state'] = 'WAITING_FOR_PRICE'
        
        player_name = context.user_data.get('temp_player_name', 'o jogador')
        
        await query.edit_message_text(
            text=(
                f"Você escolheu **{platform_name}** para **{player_name}**.\n\n"
                f"Agora, **qual o preço em moedas** desta carta?\n"
                f"(Ex: 1500000)"
            ),
            parse_mode='Markdown'
        )
        
    elif action == 'SEARCH_HISTORY':
        player_name = value
        result, error_msg = get_last_registered_price(player_name)
        
        if result:
            trade_tip = get_trade_tip(result["player_name"], result["preco_num"])
            detailed_history = get_detailed_player_history(result["player_name"], limit=3)
            
            caption_text = (
                f"🔍 **Histórico de {player_name}**\n\n"
                f"{result['price_message']}\n"
                f"---\n"
                f"📈 **Dica de Trade:**\n{trade_tip}\n"
                f"---\n"
                f"📚 **Últimos Registros (3):**\n"
                f"{detailed_history}"
            )
            
            await query.edit_message_text(
                caption_text,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"🚨 Erro ao buscar histórico: {error_msg}")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra todos os jogadores que já foram registrados."""
    # (Lógica omitida por ser a mesma)
    message_source = update.callback_query.message if update.callback_query else update.message
    
    registered_players = get_all_registered_players()
    
    if not registered_players:
        await message_source.reply_text("📚 Seu histórico de preços está vazio. Use o menu principal para registrar o primeiro jogador!")
        return

    keyboard = []
    row = []
    for player in registered_players:
        row.append(InlineKeyboardButton(player, callback_data=f'SEARCH_HISTORY:{player}'))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📚 **Histórico Completo de Jogadores:**\nClique para ver o último preço registrado:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "📚 **Histórico Completo de Jogadores:**\nClique para ver o último preço registrado:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def recent_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra os últimos 5 registros de preço."""
    # (Lógica omitida por ser a mesma)
    recent_entries = get_recent_history(limit=5)
    
    if not recent_entries:
        await update.callback_query.edit_message_text("⏱ O histórico está vazio. Registre um preço primeiro!")
        return

    message_parts = ["⏱ **Últimos 5 Registros de Preço:**\n"]
    
    for entry in recent_entries:
        try:
            dt_obj = datetime.strptime(entry['data_hora'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=TIMEZONE)
            preco_moedas = int(entry.get('preco_moedas', 0))
        except ValueError:
            continue

        message_parts.append(
            f"🔸 **{entry['jogador']}** ({entry['plataforma']})\n"
            f"   Preço: **{format_price(preco_moedas)}**\n"
            f"   Em: *{dt_obj.strftime('%H:%M:%S')}*\n"
        )
        
    await update.callback_query.edit_message_text(
        "\n".join(message_parts),
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

    # Handlers (Adicionado o novo comando /exportar)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("historico", history_command))
    application.add_handler(CommandHandler("exportar", export_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_flow))

    print("🤖 Bot iniciado e ouvindo...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        __import__('pytz')
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
