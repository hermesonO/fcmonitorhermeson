import time
import csv
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===================================================
# 1. CONFIGURAÇÃO
# ===================================================

# 🚨 CHAVE SECRETA: Seu Token
# Depois (Seguro)
import os # Adicione essa importação se ela ainda não existir
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# ===================================================
# 2. FUNÇÕES DE DADOS (SIMULADAS) E HISTÓRICO CSV
# ===================================================

def registrar_historico(jogador, preco_moedas, preco_formatado):
    """Adiciona a busca do jogador ao arquivo CSV."""
    
    # Se o arquivo não existe, cria-o com o cabeçalho
    try:
        with open('preços_historico.csv', 'r', encoding='utf-8') as f:
            f.readline()
    except FileNotFoundError:
        with open('preços_historico.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['data_hora', 'jogador', 'preco_moedas', 'preco_formatado'])

    # Abre o arquivo CSV no modo 'a' (append/adicionar)
    with open('preços_historico.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Registra a data/hora atual
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Escreve a nova linha de dados no arquivo
        writer.writerow([now, jogador, preco_moedas, preco_formatado])
        
    print(f"Histórico registrado: {jogador} | {preco_formatado}")


def get_top_5_players():
    """SIMULA a busca pelos 5 jogadores mais buscados no Futbin/Fut.gg."""
    # NO FUTURO: Coloque seu código de scraping aqui.
    return [
        {"nome": "Kylian Mbappé", "id": "mbappe_id"},
        {"nome": "V. van Dijk", "id": "vvd_id"},
        {"nome": "E. Haaland", "id": "haaland_id"},
        {"nome": "L. Messi", "id": "messi_id"},
        {"nome": "Vini Jr.", "id": "vinijr_id"}
    ]


def get_player_price(search_term):
    """SIMULA a busca do preço de um jogador e REGISTRA o histórico."""
    
    # Simulação da busca de preço real (AQUI entra seu código de scraping!)
    time.sleep(1)
    
    # ⚠️ VALORES SIMULADOS - Substitua pela busca real do Futbin/Fut.gg
    preco_num = 1500000 
    
    # Lógica de formatação de nome:
    if "_id" in search_term:
        player_name = search_term.replace("_id", "").upper()
    else: 
        player_name = search_term.title()
        
    # Formatação do preço para exibição (ex: 1.500.000 moedas)
    preco_texto = f"{preco_num:,}".replace(",", "X").replace(".", ",").replace("X", ".") + " moedas"

    # REGISTRA A BUSCA NO CSV
    registrar_historico(player_name, preco_num, preco_texto)

    # Retorna o nome e o preço numérico e formatado para ser usado na função de dica
    return {
        "player_name": player_name,
        "preco_num": preco_num,
        "price_message": f"O preço de **{player_name}** é: **{preco_texto}**."
    }


def get_trade_tip(jogador_nome, preco_atual_moedas):
    """Lê o histórico e fornece uma dica simples de trade."""
    
    historico = []
    
    try:
        # 1. Lê todo o histórico do arquivo CSV
        with open('preços_historico.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Compara o jogador, ignorando maiúsculas/minúsculas
                if row['jogador'].upper() == jogador_nome.upper():
                    historico.append(row)
    except FileNotFoundError:
        return "Primeiro registro. Busque novamente mais tarde para comparar os preços!"

    
    # 2. Se há histórico suficiente (mais de 1 registro, já que o último é o que acabamos de adicionar)
    if len(historico) > 1:
        # Pega o preço mais recente ANTES da busca atual (penúltimo item)
        ultimo_registro = historico[-2]
        try:
            preco_anterior = int(ultimo_registro['preco_moedas'])
        except ValueError:
             return "Erro ao ler preço anterior. Verifique o formato do CSV."

        diferenca = preco_atual_moedas - preco_anterior
        
        # Formata a diferença
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
        # 1. Busca o preço e registra o histórico
        result = get_player_price(value)
        
        # 2. Gera a dica de trade
        trade_tip = get_trade_tip(result["player_name"], result["preco_num"])
        
        await query.edit_message_text(
            text=f"✅ **Busca por Jogador Popular**\n\n{result['price_message']}\n\n---\n📊 **Dica de Trade:**\n{trade_tip}",
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
    
    # 1. Busca o preço e registra o histórico
    result = get_player_price(search_term) 

    # 2. Gera a dica de trade
    trade_tip = get_trade_tip(result["player_name"], result["preco_num"])

    await update.message.reply_text(
        f"🔍 **Resultado da sua busca:**\n\n{result['price_message']}\n\n---\n📊 **Dica de Trade:**\n{trade_tip}",
        parse_mode='Markdown'
    )


# ===================================================
# 4. EXECUÇÃO
# ===================================================

def main() -> None:
    """Conecta o bot ao Telegram e inicia a escuta."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers (Ligações entre o Telegram e as nossas funções)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_search))

    print("🤖 Bot iniciado e ouvindo...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
