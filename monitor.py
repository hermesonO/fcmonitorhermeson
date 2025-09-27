import csv
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pytz import timezone

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone('UTC') 

# Tipos de plataformas disponíveis para o botão
PLATFORMS = {
    'PS': 'PlayStation', 
    'XB': 'Xbox', 
    'PC': 'PC'
}

# ===================================================
# 2. FUNÇÕES DE DADOS E HISTÓRICO
# ===================================================

def registrar_historico(jogador, preco_moedas, plataforma):
    """Adiciona o registro de preço manual ao arquivo CSV."""
    
    # 1. Cria o arquivo se não existir (com novo cabeçalho)
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
        
    # 2. Adiciona a nova linha
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Formata a data e hora atual
        now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        
        # Formata o preço para garantir que seja um número (sem separador de milhar)
        # Tenta limpar o preço de formatação (ex: 1.000.000 -> 1000000)
        try:
            preco_limpo = int(str(preco_moedas).replace('.', '').replace(',', ''))
        except ValueError:
            print(f"Erro ao limpar preço: {preco_moedas}")
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
                # Busca pelo nome (case-insensitive)
                if row['jogador'].upper() == player_name_upper:
                    historico.append(row)
    except FileNotFoundError:
        return None, "O histórico de preços está vazio."
    
    if historico:
        # Retorna o último registro
        last_entry = historico[-1]
        
        try:
            # Converte a string de data_hora para um objeto datetime para formatação
            dt_obj = datetime.strptime(last_entry['data_hora'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=TIMEZONE)
            
            # Converte o preço para número, se possível
            preco_moedas = int(last_entry.get('preco_moedas', 0))

        except ValueError:
             return None, f"Erro de formato nos dados para {player_name}."


        # Formatação do preço (1.000.000)
        def format_price(price):
            return f"{price:,}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        
        price_message = (
            f"O último preço de **{player_name}** foi:\n"
            f"💰 **Preço:** {format_price(preco_moedas)} moedas\n"
            f"🎮 **Plataforma:** {last_entry['plataforma']}\n"
            f"📅 **Data:** {dt_obj.strftime('%d/%m/%Y')} às {dt_obj.strftime('%H:%M:%S')} (UTC)"
        )

        return {
            "player_name": player_name,
            "preco_num": preco_moedas,
            "price_message": price_message,
            "last_update": dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
            "plataforma": last_entry['plataforma']
        }, None
        
    return None, f"Nenhum preço registrado para **{player_name}**."


def get_trade_tip(jogador_nome, preco_atual_moedas):
    """Lê o histórico e fornece uma dica simples de trade, usando o preço registrado."""
    
    historico = []
    player_name_upper = jogador_nome.upper()
    
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['jogador'].upper() == player_name_upper:
                    historico.append(row)
    except FileNotFoundError:
        return "Primeiro registro. Busque novamente mais tarde para comparar os preços!"

    
    if len(historico) > 1:
        # Pega o penúltimo registro
        ultimo_registro = historico[-2]
        
        try:
            preco_anterior = int(ultimo_registro['preco_moedas'])
        except ValueError:
             return "Erro ao ler preço anterior. Verifique o formato do CSV."

        diferenca = preco_atual_moedas - preco_anterior
        
        # Formatação da diferença
        diferenca_formatada = f"{abs(diferenca):,}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        if diferenca > 0:
            return f"⬆️ **{diferenca_formatada} moedas mais caro** que o registro anterior ({ultimo_registro['data_hora']}). **PODE SER HORA DE VENDER!**"
        elif diferenca < 0:
            return f"⬇️ **{diferenca_formatada} moedas mais barato** que o registro anterior ({ultimo_registro['data_hora']}). **PODE SER HORA DE COMPRAR!**"
        else:
            return "➡️ Preço estável desde o registro anterior."
    else:
        return "Primeiro registro. Registre mais preços para ativar a Dica de Trade!"


# ===================================================
# 3. HANDLERS DE CONVERSA E FLUXO
# ===================================================

# Esta função lida com o início do fluxo de registro e com mensagens de texto genéricas.
async def handle_message_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com mensagens de texto do usuário, controlando o estado da conversa."""
    
    text = update.message.text.strip()
    user_data = context.user_data
    current_state = user_data.get('flow_state', 'READY')
    
    # ----------------------------------------------------
    # ESTADO: ESPERANDO NOME DO JOGADOR
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
            f"Jogador: **{player_name}**\n\nEm qual plataforma você viu este preço?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    # ----------------------------------------------------
    # ESTADO: ESPERANDO PREÇO
    # ----------------------------------------------------
    elif current_state == 'WAITING_FOR_PRICE':
        try:
            # Remove pontos e vírgulas (ex: 1.000.000 ou 1,000,000)
            price = int(text.replace('.', '').replace(',', '')) 
        except ValueError:
            await update.message.reply_text("🚨 Preço inválido. Por favor, digite o preço apenas com números (ex: 1500000).")
            return
            
        player_name = user_data.get('temp_player_name')
        platform = user_data.get('temp_platform')

        if not player_name or not platform:
            # Safety check
            await update.message.reply_text("🚨 Erro na sessão. Por favor, comece de novo com /start.")
            user_data['flow_state'] = 'READY'
            return

        # 1. Registrar no histórico
        registrar_historico(player_name, price, platform)
        
        # 2. Obter a dica de trade
        trade_tip = get_trade_tip(player_name, price)

        # 3. Finalizar e limpar o estado
        user_data['flow_state'] = 'READY'
        user_data.pop('temp_player_name', None)
        user_data.pop('temp_platform', None)
        
        await update.message.reply_text(
            f"✅ **Registro Concluído!**\n\n"
            f"**{player_name}** ({platform}) salvo por **{price:,} moedas**.\n"
            f"---\n"
            f"📊 **Dica de Trade:**\n{trade_tip}",
            parse_mode='Markdown'
        )
        return

    # ----------------------------------------------------
    # ESTADO: PRONTO (Nova mensagem ou Busca de Histórico)
    # ----------------------------------------------------
    elif current_state == 'READY':
        
        # 1. Tenta buscar um preço já existente (Assumindo que o usuário digitou um nome)
        player_name_search = text.title()
        result, error_msg = get_last_registered_price(player_name_search)
        
        if result:
            # Preço encontrado, mostra o histórico
            trade_tip = get_trade_tip(result["player_name"], result["preco_num"])
            
            await update.message.reply_text(
                f"🔍 **Resultado da Busca de Histórico**\n\n"
                f"{result['price_message']}\n"
                f"---\n"
                f"📊 **Dica de Trade:**\n{trade_tip}",
                parse_mode='Markdown'
            )
            return

        elif "oi" in text.lower() or "olá" in text.lower() or "ola" in text.lower() or "registro" in text.lower():
            # Se for um cumprimento ou intenção de registrar, inicia o fluxo.
            user_data['flow_state'] = 'WAITING_FOR_PLAYER'
            await update.message.reply_text(
                "👋 Olá! Vamos registrar um preço. **Qual jogador você comprou ou está monitorando?**\n(Ex: Vinicius Jr.)",
                parse_mode='Markdown'
            )
            return
            
        else:
            # Mensagem desconhecida, assume que é para iniciar o registro
            user_data['flow_state'] = 'WAITING_FOR_PLAYER'
            await update.message.reply_text(
                f"Não encontrei um registro para **{player_name_search}**.\n\n"
                f"Vamos começar um novo registro. **Qual jogador você está monitorando?**",
                parse_mode='Markdown'
            )
            return


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário digita /start. Inicia o fluxo."""
    context.user_data['flow_state'] = 'WAITING_FOR_PLAYER'
    
    await update.message.reply_text(
        "👋 Bem-vindo ao Monitor de Preços Manual!\n\n"
        "Vamos registrar um novo preço. **Qual jogador você comprou ou está monitorando?**\n(Ex: Vinicius Jr.)",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função executada quando o usuário clica nos botões de plataforma."""
    query = update.callback_query
    await query.answer()

    action, platform_key = query.data.split(':', 1)
    
    if action == 'PLATFORM' and context.user_data.get('flow_state') == 'ASKING_FOR_PLATFORM':
        
        platform_name = PLATFORMS.get(platform_key)
        context.user_data['temp_platform'] = platform_name
        context.user_data['flow_state'] = 'WAITING_FOR_PRICE'
        
        player_name = context.user_data.get('temp_player_name', 'o jogador')
        
        await query.edit_message_text(
            text=(
                f"Você escolheu **{platform_name}** para **{player_name}**.\n\n"
                f"Agora, **qual o preço em moedas** desta carta na plataforma?\n"
                f"(Ex: 1500000)"
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

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    # Este handler lida com todas as mensagens de texto que não são comandos
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_flow))

    print("🤖 Bot iniciado e ouvindo...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    # Garante que as bibliotecas necessárias estejam instaladas
    try:
        __import__('pytz')
    except ImportError as e:
        print(f"ERRO DE DEPENDÊNCIA: {e}. Por favor, instale: pip install -r requirements.txt --user")
    
    main()
