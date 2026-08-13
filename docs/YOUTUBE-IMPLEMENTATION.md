# Implementação e Ajustes do YouTube

Este documento detalha o funcionamento e as recentes correções implementadas no `YoutubeHandler` e na integração com o `ChatManager`.

## 1. Captura de Viewers do YouTube (Web Scraping)

A contagem de visualizações do YouTube não é enviada diretamente pelos eventos de chat da biblioteca `pytchat`. Para contornar isso, implementamos um sistema de scraping leve direto no HTML da página da live.

### O Problema do Regex Frágil
Anteriormente, o sistema utilizava uma única expressão regular (`"viewCount":\{"runs":\[\{"text":"([\d,]+)'`) para buscar os viewers. Contudo, o layout de resposta do YouTube muda frequentemente com base na localização (traduções como "visualizações"), popularidade e estado da live. Quando o padrão mudava, o regex falhava silenciosamente e enviava `0` viewers de forma contínua.

### A Nova Lógica de Scraping Robusta
O scraper agora tenta ler o HTML buscando três formatos distintos de entrega do YouTube, nesta ordem de prioridade:
1. **Formato Padrão (`runs text`)**: `r'"viewCount":\{"runs":\[\{"text":"([\d,]+)'`
2. **Formato Simples (`videoViewCountRenderer simpleText`)**: `r'"videoViewCountRenderer":\{"viewCount":\{"simpleText":"([\d,]+)'`
3. **Formato Concorrente (`concurrentViewers`)**: `r'"concurrentViewers":\{"simpleText":"([\d,]+)'`

Quando qualquer um destes padrões encontra os viewers (ex: `"597"` ou `"1.200"`), ocorre o bypass das vírgulas e pontos, e o valor validado é emitido para a tela.

## 2. Emissão do Sinal de Stats (Fix)

Havia um bug crítico na emissão de estatísticas. O YouTube tentava acionar:
```python
self.viewers_updated.emit(int(vc), "youtube")
```
No entanto, o sinal `viewers_updated` **não existe** na base `BaseChatHandler`. A chamada gerava uma exceção que era abafada por um bloco `try-except` (tornando-a invisível no log). 
A solução foi utilizar o sinal correto, emitindo os 4 parâmetros obrigatórios da arquitetura do aplicativo:
```python
self.stats_updated.emit(int(vc), 0, 0, 0)
```

## 3. Fallback no Chat Manager

O painel de estatísticas principais da UI (Cronômetro e Total de Curtidas) foi projetado para ser dominado pelo TikTok. Caso o TikTok não esteja conectado, o sistema usa um fallback.
O YouTube havia sido esquecido nessa cadeia de fallback no `core/chat_manager.py`.

**Correção**:
Foi adicionado explicitamente o `youtube` na checagem de fallback (`elif platform in ("twitch", "kick", "youtube"):`). Isso permite que conectar **somente o YouTube** alimente adequadamente a HUD de viewers principais e faça o relógio (Uptime) começar do zero.

## 4. Desconexões e Limpeza de Ghosts

O `ConfigWindow` sofria de uma omissão no `main.py` onde apenas Twitch, TikTok, Kick e Mudanças de Idioma engatilhavam um `restart_all()` do chat_manager. Alterar o username do YouTube e salvar não disparava a reinicialização; deixando o `YoutubeHandler` conectado mesmo após remover seu arroba nas configurações.

**Solução:**
- A lógica no `main.py` foi reescrita para fazer restarts granulares: apenas as plataformas modificadas são paradas/reiniciadas (`chat_manager.restart_platform()`), poupando os chats estáveis de reconexões desnecessárias.
- Quando uma plataforma é removida e o handler é forçado a parar, seu número de viewers armazenado na memória cache do UI (`self._platform_viewers`) é obrigatoriamente redefinido para `0`. Isso elimina "fantasmas" no Tooltip de status.
