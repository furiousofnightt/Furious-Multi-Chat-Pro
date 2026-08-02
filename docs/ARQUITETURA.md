# Arquitetura do Furious Multi Chat Pro

## Diagrama de Componentes

```
main.py
├── ChatWindow (UI)           ← ui/main_window.py
├── ConfigWindow (Settings)   ← ui/config_window.py
├── ChatManager               ← core/chat_manager.py
│   ├── TwitchHandler         ← chat_handlers/twitch_handler.py  (Thread IRC)
│   ├── TikTokHandler         ← chat_handlers/tiktok_handler.py  (Asyncio)
│   └── KickHandler           ← chat_handlers/kick_handler.py    (Asyncio)
├── SettingsManager           ← core/settings_manager.py
├── HotkeyManager             ← core/hotkey_manager.py
└── TTSManager                ← utils/tts_engine.py
```

## Threading

```
Thread Principal (PyQt6)
├── ChatWindow (render UI)
└── ChatManager (slots/signals)

AsyncManager Thread (única, permanente)
└── Event Loop asyncio
    ├── TikTokHandler
    └── KickHandler

Twitch Thread
└── Socket IRC bloqueante
```

## Sinais PyQt6

### Handlers → ChatManager
```python
message_received = pyqtSignal(str, str, str)      # (user, text, platform)
user_joined      = pyqtSignal(str, str)           # (username, platform)
status_changed   = pyqtSignal(bool)               # (connected)
stats_updated    = pyqtSignal(int, int, int, int) # (viewers, uptime, likes, total_views)
```

> `total_views` é preenchido apenas pelo TikTok via `RoomUserSeqEvent.total_user`. Twitch e Kick emitem `0`.

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

## Fluxo de Stats (TikTok)

```
RoomUserSeqEvent
    → _total_views = event.total_user
    → stats_updated(viewers, uptime, likes, total_views)
    → ChatManager._on_platform_stats
    → ChatWindow.update_live_stats(v, u, l, t)
    → ChatWindow.update_secondary_viewers(platform_viewers, platform_status)
        → Tooltip: número colorido (conectado) | "Offline" cinza (desconectado)
```

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
| kickpython | WebSocket Kick |
| edge-tts + pygame-ce | Bot de voz neural |
| pywin32 | Criptografia DPAPI |
| PyInstaller | Geração do executável |
