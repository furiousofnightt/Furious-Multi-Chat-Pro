# FAQ - Perguntas Frequentes

## Geral

### O que é o Furious Multi Chat Pro?

Uma aplicação desktop para streamers que permite visualizar e exibir chat de múltiplas plataformas (Twitch, TikTok, Kick) em uma única interface flutuante e personalizável.

### Quais plataformas são suportadas?

- **Twitch**: Via conexão IRC direta
- **TikTok**: Via biblioteca TikTokLive (WebSocket)
- **Kick**: Via biblioteca kickpython (WebSocket)

### É gratuito?

Sim, projeto de código aberto.

## Instalação

### Como instalar?

1. Ter Python 3.12+ instalado
2. Clonar/baixar o projeto
3. `pip install -r requirements.txt`
4. `python run.py`

Ou baixar o executável pronto (quando disponível).

### Posso usar sem Python?

Sim, quando houver release com executável standalone. O executável não requer Python instalado.

## Configuração

### Como configurar minhas contas?

1. Execute o programa
2. Clique no botão de engrenagem (⚙️)
3. Preencha os campos:
   - Twitch: nome do canal (ex: `alanzoka`)
   - TikTok: nome do usuário (ex: `virginia`)
   - Kick: nome do canal (ex: `xqc`)
4. Salve

### O arquivo settings.json é seguro?

Sim. Contém apenas nomes de canais, não senhas ou tokens. Pode ser compartilhado sem riscos.

### Posso usar só uma plataforma?

Sim. Deixe os outros campos vazios nas configurações.

## Funcionalidades

### O que é Glassmorphism?

Efeito visual de vidro fosco (blur + transparência). Disponível no Windows 11. Deixa a janela com aparência moderna.

### Como funciona o sistema de hotkeys?

Atalhos de teclado que funcionam mesmo quando o programa não está focado:
- **Ctrl+Shift+H**: Mostrar/Esconder janela
- **Ctrl+Shift+C**: Limpar chat

### Posso mudar as hotkeys?

Sim. Vá em Configurações → Comportamento → Atalhos de Teclado.

### O que é o "Atraso para Leitura"?

Adiciona delay entre mensagens (em segundos). Útil se você quer ler cada mensagem sem pressa.

## Problemas Conhecidos

### Mensagens do TikTok não aparecem

**Cenário**: Alguns usuários específicos nunca aparecem no chat, mesmo mandando mensagens.

**Causa**: Limitação do servidor de proxy usado pela biblioteca TikTokLive (~15% de mensagens podem ser perdidas).

**Solução**: Não há solução no momento. É uma limitação técnica documentada.

**Ver detalhes**: `docs/TIKTOK-LIMITACOES.md`

### Emotes não aparecem

**Possíveis causas**:
1. Sem conexão com internet (emotes são baixados)
2. Emote não existe no cache de terceiros
3. Erro no download

**Solução**: Verifique conexão. Emotes são baixados automaticamente.

### Janela não fica transparente

**Causa**: Glassmorphism requer Windows 11. No Windows 10, apenas transparência básica funciona.

**Solução**: Ajuste a opacidade nas configurações.

### Hotkeys não funcionam

**Possíveis causas**:
1. Outro programa está usando a mesma combinação
2. Permissões de administrador necessárias
3. Teclado com layout diferente

**Solução**: Tente outra combinação de teclas nas configurações.

### Conexão Twitch cai frequentemente

**Causa**: IRC pode desconectar por inatividade.

**Comportamento esperado**: Reconexão automática a cada 30 segundos.

### TikTok desconecta com "Rate Limit"

**Causa**: Muitas tentativas de conexão em pouco tempo.

**Solução**: Aguarde 16-24 horas antes de tentar novamente.

## Uso

### Como usar como overlay no OBS?

1. Configure a janela para "Always on top" (fixar)
2. Ajuste opacidade para ~85%
3. Posicione sobre o jogo/aplicação
4. Use "Window Capture" no OBS se quiser capturar só o chat

### Posso clicar através da janela?

Sim. Ative "Click-through" nas configurações. A janela ficará transparente a cliques.

### Como limpar o chat?

- Hotkey: **Ctrl+Shift+C**
- Comando no chat: `/clear`
- Botão no menu (se disponível)

### O que é a Blacklist?

Lista de palavras que serão censuradas no chat (substituídas por *****). Configure em Configurações → Comportamento.

## Técnico

### Por que mensagens do TikTok às vezes não aparecem?

A biblioteca TikTokLive depende de um servidor de proxy externo (`eulerstream.com`). Este servidor pode:
- Estar sobrecarregado
- Estar sendo rate-limited pelo TikTok
- Filtrar mensagens de usuários específicos

Não é um bug no nosso código. Ver documentação técnica detalhada.

### Posso contribuir com o projeto?

Sim! O código é aberto. Veja `docs/GUIA-DESENVOLVIMENTO.md`.

### Como reportar bugs?

1. Verifique se já não é um problema conhecido
2. Anote os passos para reproduzir
3. Cole logs do console
4. Descreva o comportamento esperado vs atual

### O programa coleta meus dados?

Não. Todas as conexões são diretas com as plataformas. Nenhum dado é enviado para servidores terceiros (exceto conexões necessárias com TikTok/Twitch/Kick).

## Dúvidas Específicas por Plataforma

### Twitch

**Precisa de OAuth/token?**
Não. Usamos conexão anônima (justinfan).

**Funciona em canal privado?**
Não. Apenas canais públicos.

### TikTok

**Precisa de login?**
Não, mas conectar com conta pode melhorar estabilidade (não implementado ainda).

**Funciona em live privada?**
Não. Apenas lives públicas.

**Por que às vezes demora para conectar?**
O servidor de sign pode estar lento. Aguarde alguns segundos.

### Kick

**Precisa de API key?**
Não.

**Funciona em todo canal?**
Sim, desde que seja live pública.

## Performance

### O programa consome muita RAM?

Normalmente usa 50-150MB. Cache de emotes pode aumentar temporariamente.

### Consome muita internet?

Mínimo. Apenas texto (chat), sem vídeo.

### Posso rodar 24/7?

Sim. Reconexões automáticas garantem estabilidade.

## Outros

### Posso mudar as cores?

Sim. Configurações → Aparência → Cores das plataformas.

### Posso mudar a fonte?

Sim. Configurações → Aparência → Fonte do Chat.

### Tem suporte a temas claro?

No momento, apenas tema dark está disponível.

### Como faço para atualizar?

Se via código: `git pull` e reinstale dependências.

Se via executável: baixe a nova versão e substitua.

### Perdi minhas configurações!

O arquivo `settings.json` pode ter sido corrompido. Delete-o e reconfigure.

### O programa fecha sozinho!

Verifique `crash_log.txt` na pasta do programa. Pode ser erro não tratado.

### Posso usar em Linux/Mac?

Teoricamente sim (Python é multiplataforma), mas:
- Glassmorphism só funciona no Windows 11
- Hotkeys globais podem variar
- Não testado ativamente

## Contato

Para dúvidas não cobertas aqui, consulte:
- Documentação técnica em `docs/`
- Logs do console
- Código fonte (para desenvolvedores)
