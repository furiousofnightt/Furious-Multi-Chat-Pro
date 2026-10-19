# Aba de Espectadores Online (TikTok) - Documentação Técnica

## 1. Visão Geral

A aba de **Espectadores Online** permite que o streamer visualize em tempo real a lista completa de todos os usuários logados presentes na transmissão do TikTok. O foco é permitir a leitura dos nomes para agradecimentos individuais durante ou no encerramento da live.

---

## 2. Arquitetura e Fluxo de Dados

```
[TikTok Webcast API]
         │  GET /webcast/ranklist/online_audience/ (a cada 4s)
         ▼
[TikTokHandler._sync_online_audience_loop] (Asyncio)
         │  viewers_list_updated.emit(viewers_list)
         ▼
[ChatWindow.update_tiktok_viewers] (Thread Principal Qt)
         │
         ▼
[OnlineViewersListWidget.set_viewers]
         ├── Lista vazia → exibe placeholder limpo imediatamente (100% tempo real)
         ├── Atualização in-place se a lista não mudou de ordem (zero lag)
         └── Reconstrução dos cards se houve novos usuários ou reordenação
                 ▼
         [ViewerCardWidget] (Avatar + #Rank + Nickname + @username + Pontos)
```

### Fluxo do Botão "Sincronizar" (Manual)

```
[Usuário clica "↺ Sincronizar"]
         │
         ▼
[OnlineViewersListWidget.trigger_sync]
         │  sync_requested.emit()
         ▼
[ChatWindow.request_sync_viewers]
         │  Localiza TikTokHandler ativo via _chat_manager.handlers
         ▼
[TikTokHandler.request_sync_now]
         │  asyncio.run_coroutine_threadsafe(_one_shot_sync(), loop)
         ▼
[GET /webcast/ranklist/online_audience/] — chamada fresca, sem cache
         │  viewers_list_updated.emit(resultado)
         ▼
[OnlineViewersListWidget.set_viewers] — UI atualizada em tempo real
```

---

## 3. Componentes da Interface

### 3.1. `OnlineViewersListWidget` (`ui/main_window.py`)
- Página gerenciada pelo `QStackedWidget` da janela principal (Index 1).
- Header contendo:
  - Botão de voltar ao chat (`← Voltar`).
  - Título com contador de espectadores (`X online (TikTok)`).
  - **Botão `↺ Sincronizar`**: força uma requisição imediata fresca à API do TikTok (sem cache).
  - **Label de horário** da última atualização (`Atualizado HH:MM:SS`).
  - Botões de ajuste rápido de fonte (`A-` e `A+`).
- ScrollArea com renderização suave e transparente (efeito Glassmorphism).

#### Sinais emitidos
| Sinal | Quando |
|---|---|
| `back_requested` | Usuário clica em `← Voltar` |
| `open_settings_requested` | Usuário clica em `⚙ Abrir Configurações` dentro de um banner |
| `sync_requested` | Usuário clica em `↺ Sincronizar` |

### 3.2. `ViewerCardWidget` (`ui/main_window.py`)
- Card individual de espectador contendo:
  - **Badge de numeração**: `#1`, `#2`, `#N` para todos os usuários da lista (inclusive os com 0 pontos).
  - **Foto de perfil circular**: Download assíncrono com cache Base64 local.
  - **Nome e @username**: Formatados via RichText com suporte a escalonamento dinâmico.
  - **Badge de pontuação**: `X pts` estilizado com gradiente.

---

## 4. Botão de Sincronização Manual

### Comportamento
- **Clique único**: Dispara `TikTokHandler.request_sync_now()` que faz uma requisição HTTP fresca diretamente na API.
- **Rate-limit visual**: O botão fica desabilitado por **2,5 segundos** após cada clique para evitar flood na API.
- **Sem cache**: Todos os dados exibidos vêm diretamente da resposta atual da API. Se a API retornar lista vazia, a aba exibe o placeholder limpo imediatamente — sem manter dados velhos na tela.
- **Feedback visual**: O label ao lado do botão exibe `Atualizado HH:MM:SS` a cada resposta recebida (automática ou manual).

### Quando usar
- A aba ficou vazia após algumas horas de live (loop interno parou por queda momentânea do WebSocket).
- Queira confirmar quem está online agora antes de se despedir.

---

## 5. Controle Dinâmico de Fonte

A classe `ViewerCardWidget` possui a variável de controle `_font_size` (padrão: 15px).
- **Botão `A-`**: Reduz a fonte em 1px (mínimo de 10px).
- **Botão `A+`**: Aumenta a fonte em 1px (máximo de 24px).
- O método `OnlineViewersListWidget.adjust_font_size()` atualiza todos os cards instantaneamente sem recarregar a lista da API.

---

## 6. Comportamento da Lista por Estado

| Estado | O que aparece |
|---|---|
| Sem login TikTok | Banner vermelho: "Login TikTok necessário" + botão `⚙ Abrir Configurações` |
| Sem canal TikTok configurado | Banner vermelho: "TikTok não configurado" + botão `⚙ Abrir Configurações` |
| Live ativa, espectadores presentes | Cards de espectadores em tempo real |
| Live ativa, API retorna vazia | Placeholder "Nenhum espectador na lista no momento" + horário |
| Handler desconectado (sem live) | Placeholder neutro |

> **Sem cache em nenhum estado**: qualquer resposta recebida da API (incluindo lista vazia) é refletida imediatamente na tela sem retenção de dados antigos.

---

## 7. Proteções de Autenticação & Rate Limit

1. **Early-Exit sem `sessionid`**:
   - Se o usuário não tiver realizado login nas Configurações, o loop encerra imediatamente sem disparar nenhuma requisição HTTP.
   - Isso elimina riscos de banimento ou erro `HTTP 429` (Too Many Requests).
2. **Tratamento de Sessão Expirada (`401` / `403`)**:
   - Caso o token expire, o loop entra em pausa de 30 segundos entre verificações.
3. **Rate-limit do botão Sincronizar**:
   - Botão desabilitado por 2,5s após cada clique para não gerar spam de requisições manuais.
4. **Cards Informativos (Banners de Estado)**:
   - Sem Login: Banner orientando a fazer login nas Configurações, com botão de atalho `⚙ Abrir Configurações`.
   - Sem Canal: Banner indicando que nenhum canal TikTok foi configurado.

---

## 8. Causa Raiz do Bug "Aba Vazia após 2-3h de Live"

O loop `_sync_online_audience_loop` roda enquanto `self.is_running and self._already_connected`. Se o WebSocket TikTok sofrer uma queda momentânea de rede, o evento `on_disconnect` define `_already_connected = False`, encerrando o loop. Se a reconexão automática não acontecer (por exemplo, a live continuou no app TikTok mas o WebSocket do handler não reconectou), o loop não retoma — e a aba para de receber atualizações.

**Solução imediata**: clicar em **↺ Sincronizar** força uma requisição fresca independente do estado do loop.
