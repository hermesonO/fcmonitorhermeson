# fcmonitorhermeson

Bot de monitoramento de preços de jogadores para o EA FC 26 Ultimate Team.

Este bot utiliza dados (simulados/scraping) de sites como Futbin e Fut.gg para fornecer os valores de mercado em tempo real.

## Funcionalidades
- Resposta interativa ao iniciar a conversa.
- Lista dos 5 jogadores mais buscados.
- Opção de buscar o preço de um jogador por nome.

## Como Usar o Bot (Para o Usuário)

1. Envie `/start` ou qualquer mensagem para o bot.
2. Escolha um dos jogadores populares ou clique em "Buscar por Nome".
3. Se escolher "Buscar por Nome", digite o nome completo do atleta.

## Próximos Passos (Desenvolvedor)

1. Implementar a lógica de scraping real nas funções `get_top_5_players()` e `get_player_price()` no `monitor.py`.
2. Configurar a hospedagem 24/7 (VPS, Railway, Heroku, etc.).
