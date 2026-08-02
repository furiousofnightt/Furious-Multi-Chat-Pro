# Guia de Desenvolvimento

## Setup

O projeto usa **Python do sistema** (sem virtualenv):

```bash
py -m pip install -r requirements.txt
py run.py
```

## Estrutura

```
├── main.py                  # Ponto de entrada
├── build.py                 # Compilação PyInstaller
├── settings.json            # Configurações (gerado automaticamente)
├── chat_handlers/           # TwitchHandler, TikTokHandler, KickHandler
├── core/                    # ChatManager, SettingsManager, HotkeyManager
├── ui/                      # ChatWindow, ConfigWindow
├── utils/                   # translations, emoticons, tts_engine, resource_path
└── assets/                  # Ícones SVG, fontes TTF, logos
```

## Sinais PyQt6

Todos os handlers herdam de `BaseChatHandler` e emitem **4 valores** em `stats_updated`:

```python
stats_updated = pyqtSignal(int, int, int, int)  # (viewers, uptime, likes, total_views)
```

`total_views` é exclusivo do TikTok (via `RoomUserSeqEvent.total_user`). Twitch e Kick emitem `0`.

## Criptografia DPAPI

O `tiktok_session_id` é criptografado automaticamente pelo `SettingsManager` via `win32crypt`. Tokens em texto puro são convertidos ao próximo save. O valor no JSON aparece como `DPAPI:AQAAACMnd...`.

## Adicionando Nova Plataforma

1. Criar `chat_handlers/newplatform_handler.py` herdando `BaseChatHandler`
2. Emitir `stats_updated(viewers, 0, 0, 0)` — 4 valores obrigatórios
3. Registrar em `ChatManager.start_all()` e `restart_platform()`:
   ```python
   h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("nova", v, u, l, t))
   ```
4. Adicionar campos em `ConfigWindow` e traduções em `translations.py`

## Build

```bash
py build.py
```

Output em `dist/FuriousMultiChatPro/`. O script já inclui `--hidden-import=win32crypt` e `--hidden-import=PyQt6.QtWebEngineWidgets`.

## Erros Comuns

| Erro | Solução |
|------|---------|
| "PyQt6-WebEngine não instalado" | É ordem de import. `QWebEngineView` deve ser importado em `main.py` antes de `QApplication` ser criado |
| `win32crypt` não encontrado no .exe | Usar `py build.py`, que já tem `--hidden-import=win32crypt` |
| `settings.json` corrompido | Deletar o arquivo; será recriado com defaults |
| TikTok Rate Limit | Aguardar 16-24 horas |
