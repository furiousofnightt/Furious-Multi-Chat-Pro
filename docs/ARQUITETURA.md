# Arquitetura do Furious Multi Chat Pro

## Diagrama de Componentes

```
main.py
├── ChatWindow (UI)                    ← ui/main_window.py  (~1060 linhas)
│   ├── _setup_window_once()           # Setup único: event filters, mouse tracking, msg inicial
│   ├── apply_theme()                  # Apenas visual; cached por _last_bg_alpha/_last_text_alpha
│   └── QStackedWidget
│       ├── ChatPageWidget (Index 0)   ← ui/widgets/chat_page.py
│       │   ├── JoinNotificationBanner ← ui/widgets/notifications.py
│       │   ├── QScrollArea + HeightAwareWidget  ← ui/widgets/custom_layouts.py
│       │   └── FlowLayout (por mensagem)        ← ui/widgets/custom_layouts.py
│       ├── OnlineViewersListWidget (Index 1)  ← ui/widgets/viewers_page.py
│       │   └── ViewerCardWidget (Avatar/Rank/Pts)
│       └── LiveGiftsListWidget (Index 2)      ← ui/widgets/gifts_page.py
│           └── LiveGiftCardWidget (Avatar + Nome + Presente + Tempo)
├── ConfigWindow (Settings)            ← ui/config_window.py
├── ChatManager                        ← core/chat_manager.py
│   ├── TwitchHandler  ← chat_handlers/twitch_handler.py  (Thread IRC)
│   ├── TikTokHandler  ← chat_handlers/tiktok_handler.py  (Asyncio)
│   ├── KickHandler    ← chat_handlers/kick_handler.py    (Asyncio + Centrifugo)
│   └── YoutubeHandler ← chat_handlers/youtube_handler.py (Thread/Poller)
├── BadgeManager       ← utils/badge_manager.py  (Renderizador Unificado de Badges)
├── SettingsManager    ← core/settings_manager.py
├── HotkeyManager      ← core/hotkey_manager.py
└── TTSManager         ← utils/tts_engine.py
```

## Threading

```
Thread Principal (PyQt6)
├── ChatWindow (render UI de Chat e Espectadores)
└── ChatManager (slots/signals)

AsyncManager Thread (única, permanente)
└── Event Loop asyncio
    ├── TikTokHandler (Websocket + Loop de Audiência Online a cada 4s)
    └── KickHandler

Twitch Thread
└── Socket IRC bloqueante

YouTube Thread
└── Poller de chat ao vivo
```

## Sinais PyQt6

### Handlers → ChatManager
```python
message_received     = pyqtSignal(str, str, str)      # (user, text, platform)
user_joined          = pyqtSignal(str, str)           # (username, platform)
status_changed       = pyqtSignal(bool)               # (connected)
stats_updated        = pyqtSignal(int, int, int, int) # (viewers, uptime, likes, total_views)
viewers_list_updated = pyqtSignal(list)               # lista de dicionários de espectadores online
gift_received        = pyqtSignal(dict)               # dados do presente recebido (TikTok apenas)
```

> `total_views` é preenchido pelo TikTok via `RoomUserSeqEvent.total_user`.
> `viewers_list_updated` emite a lista completa de usuários online (`rank`, `user_id`, `nickname`, `display_id`, `score`, `avatar_urls`, `total_online`).
> `gift_received` é emitido apenas quando `event.streaking == False` (fim de rajada), com `gift_count` acumulado.

### ChatManager → ChatWindow
```python
status_changed         = pyqtSignal(str, bool)              # (platform, connected)
platform_stats_updated = pyqtSignal(str, int, int, int, int) # (platform, viewers, uptime, likes, total_views)
```

### OnlineViewersListWidget → ChatWindow
```python
back_requested          = pyqtSignal()   # usuário clicou em ← Voltar
open_settings_requested = pyqtSignal()   # usuário clicou em ⚙ Abrir Configurações (banners)
sync_requested          = pyqtSignal()   # usuário clicou em ↺ Sincronizar
```

### LiveGiftsListWidget → ChatWindow
```python
back_requested = pyqtSignal()   # usuário clicou em Voltar
```

## Fluxo de Mensagem

```
Handler → message_received(user, text, platform)
    → ChatManager: blacklist + fila de delay
    → ChatWindow.add_message()
        → ChatPageWidget.add_message()  (ui/widgets/chat_page.py)
            → FlowLayout por mensagem (badge + nome + palavras/emotes)
            → HeightAwareWidget para recalcular altura com quebra de linha
            → Suporte CJK: chunks de 6 chars para wrap correto
            → animate_message() — fade-in via QGraphicsOpacityEffect (removido após animação)
            → Limite de 200 mensagens (LRU: remove o mais antigo)
    → TTSManager.add_message (se ativo e plataforma não for 'system'/'tiktok_event')
```

## Fluxo de Audiência Online (TikTok)

```
_sync_online_audience_loop (Asyncio, a cada 4s)
    → GET https://webcast.tiktok.com/webcast/ranklist/online_audience/
    → Extração de 100% dos espectadores logados + total na sala
    → TikTokHandler.viewers_list_updated.emit(viewers_list)  ← inclui lista vazia sem fallback de memória
    → ChatWindow.update_tiktok_viewers(viewers_list)
    → OnlineViewersListWidget.set_viewers(viewers_list)
        → Lista vazia → placeholder limpo + horário (sem reter dados antigos)
        → Atualização in-place se a lista for idêntica (zero lag)
        → Renderização de ViewerCardWidget (foto, nome, @username, #rank, pontos)

[Botão ↺ Sincronizar]  ←  sync_requested signal
    → ChatWindow.request_sync_viewers()
    → TikTokHandler.request_sync_now()  (asyncio.run_coroutine_threadsafe)
    → GET /webcast/ranklist/online_audience/  (requisição fresca, sem cache)
    → viewers_list_updated.emit(resultado)  → mesmo fluxo acima
```

## Fluxo de Presentes da Live (TikTok)

```
GiftEvent (WebSocket TikTokLive) — event.streaking == False
    → TikTokHandler.on_gift()  [Asyncio]
    → gift_received.emit(gift_data)  ← dict com user, gift_name, gift_count, diamond_count, timestamp...
    → ChatWindow.add_gift(gift_data)  [Thread Principal Qt — AutoConnection]
        → Badge de notificação no botão do header (se usuário não estiver na aba)
    → LiveGiftsListWidget.add_gift(gift_data)
        → Cria LiveGiftCardWidget (avatar + nome + "enviou X" + ícone + xN + tempo relativo)
        → Instala eventFilter + mouseTracking no card e filhos (para resize da janela)
        → Auto-scroll para o último presente (QTimer 50ms)
```

> **Limpeza de sessão:** `clear_gifts()` é chamado apenas em `start_all()` (nova sessão). Reconexões automáticas do WebSocket mantêm a lista intacta.

## Proteção de Autenticação e Rate-Limit (TikTok)

1. **Sem SessionID**: O loop `_sync_online_audience_loop` encerra imediatamente (`return`), sem emitir nenhuma requisição HTTP para o TikTok.
2. **Erro 401/403 (Token Expirado)**: Pausa de 30 segundos entre tentativas, evitando flood.
3. **Rate-limit do botão Sincronizar**: Botão desabilitado por 2,5s após cada clique.
4. **Streamer Desconectado / Removido**: `ChatManager.restart_platform("tiktok")` limpa a lista de espectadores e redefine o card para `TikTok não configurado`.

## Segurança (SettingsManager)

O `tiktok_session_id` é criptografado/descriptografado automaticamente via **Windows DPAPI** (`win32crypt`):
- **Salvar**: texto puro → `CryptProtectData` → `"DPAPI:..."` no JSON
- **Carregar**: detecta prefixo `DPAPI:` → `CryptUnprotectData` → texto em memória

## apply_theme — Otimização de Performance

O método `apply_theme()` em `ChatWindow` foi otimizado para eliminar o freeze de 3-5s
que ocorria ao alterar a opacidade de fundo durante transmissões ao vivo.

| Comportamento anterior | Comportamento atual |
|---|---|
| `setStyleSheet` sempre executado | Só executa se `bg_alpha` mudou (`_last_bg_alpha`) |
| `installEventFilter` repetido em ~15 widgets | Rodava apenas 1 vez, em `_setup_window_once()` |
| `apply_blur` (DWM) síncrono, bloqueava o repaint | Diferido com `QTimer.singleShot(0, ...)` |
| `add_message("sistema inicializado")` em todo save | Rodava 1x no startup; nas demais via flag `_window_setup_done` |

```python
# Exemplo do cache de opacidade:
last_bg = getattr(self, '_last_bg_alpha', None)
if last_bg != bg_alpha:
    self._last_bg_alpha = bg_alpha
    self.central_widget.setStyleSheet(...)  # Só repinta se mudou

# apply_blur diferido:
QTimer.singleShot(0, lambda: apply_blur(self.winId(), ...))
```

## Dependências Principais

| Biblioteca | Uso |
|------------|-----|
| PyQt6 | Interface gráfica e event loop principal |
| PyQt6-WebEngine | Login TikTok (WebView) |
| TikTokLive | WebSocket TikTok via EulerStream |
| httpx | Requisições assíncronas Webcast API e download de avatares |
| curl_cffi | Requisições HTTP com impersonate Chrome (Cloudflare bypass para Kick e APIs) |
| websockets | Conexão em tempo real nativa ao Centrifugo da Kick |
| edge-tts / gtts + pygame-ce | Bot de voz (Motor Neural Edge ou Google TTS alternativo) |
| pywin32 | Criptografia DPAPI |
| PyInstaller | Geração do executável |

## Sistema de Voz (TTS)

```
ChatWindow / Hotkey (Ctrl+M)
    └── TTSManager (utils/tts_engine.py)
            ├── Motor Edge (edge-tts): Vozes neurais Microsoft Azure
            └── Motor Google (gtts): Voz alternativa Google Translate pt-BR
            └── Player de Áudio: pygame-ce (pygame.mixer) com controle de volume
```
- **Failover / Alternativa**: Se a Microsoft aplicar bloqueios ou mudanças no Edge TTS, o usuário pode selecionar o motor Google TTS diretamente na interface.
- **Isolamento Total**: O TTS roda de forma assíncrona/em background sem travar a interface gráfica ou o processamento de mensagens.
