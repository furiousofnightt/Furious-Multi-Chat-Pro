# Arquitetura do Furious Multi Chat Pro

## Diagrama de Componentes

```
main.py
├── ChatWindow (UI)           ← ui/main_window.py
│   ├── QStackedWidget
│   │   ├── Chat Page (Index 0)
│   │   └── OnlineViewersListWidget (Index 1)
│   │       └── ViewerCardWidget (Lista de Cards com avatar/rank/pts)
├── ConfigWindow (Settings)   ← ui/config_window.py
├── ChatManager               ← core/chat_manager.py
│   ├── TwitchHandler         ← chat_handlers/twitch_handler.py  (Thread IRC)
│   ├── TikTokHandler         ← chat_handlers/tiktok_handler.py  (Asyncio)
│   ├── KickHandler           ← chat_handlers/kick_handler.py    (Asyncio)
│   └── YoutubeHandler        ← chat_handlers/youtube_handler.py (Thread/Poller)
├── SettingsManager           ← core/settings_manager.py
├── HotkeyManager             ← core/hotkey_manager.py
└── TTSManager                ← utils/tts_engine.py
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
```

> `total_views` é preenchido pelo TikTok via `RoomUserSeqEvent.total_user`.
> `viewers_list_updated` emite a lista completa de usuários online (`rank`, `user_id`, `nickname`, `display_id`, `score`, `avatar_urls`, `total_online`).

### ChatManager → ChatWindow
```python
status_changed         = pyqtSignal(str, bool)              # (platform, connected)
platform_stats_updated = pyqtSignal(str, int, int, int, int) # (platform, viewers, uptime, likes, total_views)
```

## Fluxo de Mensagem

```
Handler → message_received(user, text, platform)
    → ChatManager: blacklist + fila de delay
    → ChatWindow.add_message (HTML render)
    → TTSManager.read_message (se ativo)
```

## Fluxo de Audiência Online (TikTok)

```
_sync_online_audience_loop (Asyncio, a cada 4s)
    → GET https://webcast.tiktok.com/webcast/ranklist/online_audience/
    → Extração de 100% dos espectadores logados + total na sala
    → TikTokHandler.viewers_list_updated.emit(viewers_list)
    → ChatWindow.update_tiktok_viewers(viewers_list)
    → OnlineViewersListWidget.set_viewers(viewers_list)
        → Atualização in-place se a lista for idêntica (zero lag)
        → Renderização de ViewerCardWidget (foto, nome, @username, #rank, pontos)
```

## Proteção de Autenticação e Rate-Limit (TikTok)

1. **Sem SessionID**: O loop `_sync_online_audience_loop` encerra imediatamente (`return`), sem emitir nenhuma requisição HTTP para o TikTok.
2. **Erro 401/403 (Token Expirado)**: Pausa de 30 segundos entre tentativas, evitando flood.
3. **Streamer Desconectado / Removido**: `ChatManager.restart_platform("tiktok")` limpa a lista de espectadores e redefine o card para `TikTok não configurado`.

## Segurança (SettingsManager)

O `tiktok_session_id` é criptografado/descriptografado automaticamente via **Windows DPAPI** (`win32crypt`):
- **Salvar**: texto puro → `CryptProtectData` → `"DPAPI:..."` no JSON
- **Carregar**: detecta prefixo `DPAPI:` → `CryptUnprotectData` → texto em memória

## Dependências Principais

| Biblioteca | Uso |
|------------|-----|
| PyQt6 | Interface gráfica e event loop principal |
| PyQt6-WebEngine | Login TikTok (WebView) |
| TikTokLive | WebSocket TikTok via EulerStream |
| httpx | Requisições assíncronas Webcast API e download de avatares |
| kickpython | WebSocket Kick |
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
