# Limitações do TikTok Live - Documentação Técnica

## Resumo Executivo

O Furious Multi Chat Pro captura aproximadamente **90% das mensagens** do TikTok Live. Cerca de **10% das mensagens de usuários específicos** não aparecem no chat, mesmo estando visíveis no TikTok Live Studio oficial.

## O Problema

### Sintomas Observados
- Mensagens de usuários específicos (ex: @021Leozin) nunca aparecem no chat
- Outros usuários (ex: @Cat, @Juh.Silvax) funcionam normalmente
- Quando um usuário afetado envia mensagem, nenhuma delas passa
- Não há erros no console — as mensagens simplesmente não chegam

### Evidências
- Mensagem aparece no TikTok Live Studio: ✅
- Mensagem lida pelo bot de voz Tikfinity: ✅
- Mensagem capturada por nossa aplicação: ❌
- Logs de debug ([DEBUG-ALL], [TikTok-*]): Silêncio quando mensagem é enviada

## Causa Raiz

### Arquitetura da Conexão

```
[Nosso App] → [TikTokLive Python Lib] → [EulerStream Proxy] → [TikTok Servers]
```

A biblioteca `TikTokLive` (Python) usa obrigatoriamente um **servidor de proxy externo**:

```python
# TikTokLive/client/web/web_settings.py
tiktok_sign_url: str = "https://tiktok.eulerstream.com"
```

Todas as mensagens passam por este servidor antes de chegar na nossa aplicação.

### Por que Algumas Mensagens são Perdidas?

1. **Filtragem no Proxy**: O servidor `eulerstream.com` pode estar aplicando filtros que descartam mensagens de certos usuários
2. **Rate Limiting**: O servidor pode estar sendo rate-limited pelo TikTok e perdendo mensagens
3. **Shadow Ban**: Usuários afetados podem estar em shadow ban, onde suas mensagens são "silenciadas" mas ainda visíveis no app oficial
4. **Protocolo Diferente**: Usuários mobile podem ter mensagens enviadas por canais diferentes que o proxy não captura

### O que NÃO é o Problema

❌ **Nosso código**: Testes extensivos mostram que handlers estão funcionando
❌ **Handlers insuficientes**: Adicionamos handlers para 4+ tipos de eventos
❌ **Parsing de mensagem**: Mensagens que chegam são parseadas corretamente
❌ **Conexão websocket**: Conexão permanece estável

## Eventos Mapeados

A biblioteca TikTokLive mapeia os seguintes eventos protobuf:

| Protobuf Message | Evento Python | Status |
|------------------|-------------|--------|
| WebcastChatMessage | CommentEvent | ✅ Funciona (maioria) |
| WebcastCommentsMessage | CommentsEvent | ✅ Capturado |
| WebcastBarrageMessage | BarrageEvent | ✅ Capturado (filtrado) |
| WebcastEcBarrageMessage | EcBarrageEvent | ✅ Capturado (filtrado) |
| WebcastEmoteChatMessage | EmoteChatEvent | ✅ Capturado |
| Desconhecido | UnknownEvent | ✅ Fallback |

## Tentativas de Solução

### 1. Handlers Múltiplos ✅ Implementado
Adicionamos handlers para todos os tipos de evento de chat possíveis:
- `CommentEvent`
- `CommentsEvent`
- `BarrageEvent`
- `EcBarrageEvent`
- `EmoteChatEvent`
- `UnknownEvent`

**Resultado**: Não resolveu — mensagens perdidas não chegam em NENHUM handler

### 2. Debug de Websocket ✅ Implementado
Adicionamos debug para capturar TODOS os pacotes websocket:
```python
@self.client.on(WebsocketResponseEvent)
async def on_websocket_debug(event: WebsocketResponseEvent):
```

**Resultado**: Quando usuário afetado manda mensagem, NENHUM pacote aparece no debug

### 3. Scraping de HTML ❌ Não Funcionou
Tentamos fazer scraping da página HTML para capturar mensagens:
- O TikTok Live não carrega mensagens no HTML inicial
- Mensagens são carregadas 100% dinamicamente via WebSocket
- Impossível capturar via scraping

### 4. Análise de Biblioteca Node.js 📊 Pesquisado
A biblioteca original em Node.js (`TikTok-Live-Connector`) tem a mesma arquitetura e usa o mesmo servidor `eulerstream.com`.

Opções disponíveis na versão Node.js:
- `disableEulerFallbacks`: Desabilita rotas de fallback (não resolve)
- `signedWebSocketProvider`: Permite servidor de sign customizado (requer infraestrutura própria)

## Soluções Possíveis (e suas Complexidades)

### Opção A: Migrar para Node.js
**Complexidade**: 🔴 Alta
**Esforço**: Reescrever handlers em JavaScript, criar bridge Python↔Node
**Benefício**: Possivelmente melhor tratamento de edge cases
**Probabilidade de Sucesso**: Baixa (mesmo servidor de proxy)

### Opção B: Servidor de Sign Próprio
**Complexidade**: 🔴🔴 Muito Alta
**Esforço**: 
- Hospedar servidor próprio (VPS/cloud)
- Implementar algoritmo de sign do TikTok
- Manter atualizações conforme TikTok muda
**Benefício**: Controle total, sem rate limits
**Probabilidade de Sucesso**: Alta (se implementado corretamente)
**Custo**: $10-50/mês em infraestrutura

### Opção C: Documentar Limitação
**Complexidade**: 🟢 Baixa
**Esforço**: Adicionar nota no README
**Benefício**: Transparência com usuários
**Probabilidade de Sucesso**: 100%

### Opção D: Implementar Fallback via API TikTok Oficial
**Complexidade**: 🔴 Alta
**Esforço**: 
- TikTok não tem API oficial pública para Live
- Requer engenharia reversa contínua
**Probabilidade de Sucesso**: Baixa

## Recomendação

Recomendamos **Opção C (Documentar)** como solução imediata, com **Opção B (Servidor Próprio)** como possibilidade futura se o projeto crescer.

## Nota para Desenvolvedores

### Como Verificar se é o Mesmo Problema

Se um usuário reportar mensagens faltando:

1. Pergunte o nome exato do usuário afetado
2. Verifique se TODAS as mensagens dele faltam (consistência por usuário)
3. Verifique se ele aparece no TikTok Live Studio
4. Se sim → É esta limitação conhecida

### Debug Útil

Para investigar futuros problemas relacionados, habilite o debug no `tiktok_handler.py`:

```python
# Linhas ~309-365 no on_websocket_debug
print(f"[DEBUG-ALL] method={method}")
```

Isso mostrará TODOS os métodos de mensagem recebidos. Se não aparecer nada quando o usuário afetado mandar mensagem, confirma que é perda no servidor proxy.

## Referências

- Biblioteca Python: https://github.com/isaackogan/TikTokLive
- Biblioteca Node.js: https://github.com/zerodytrash/TikTok-Live-Connector
- Servidor de Proxy: https://tiktok.eulerstream.com (documentação limitada)
- Issue relacionado no repositório TikTokLive: (verificar periodicamente)

## Changelog de Investigação

- **Abril 2025**: Problema identificado — mensagens de @021Leozin não apareciam
- **Investigação**: Handlers múltiplos adicionados, debug implementado
- **Conclusão**: Problema no servidor de proxy, não no nosso código
- **Status**: Documentado e aceito como limitação conhecida
