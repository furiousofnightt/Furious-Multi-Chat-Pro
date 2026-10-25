# Guia de Desenvolvimento

## Setup

O projeto usa **Python do sistema** (sem virtualenv):

```bash
py -m pip install -r requirements.txt
py run.py
```

## Estrutura

```
├── main.py                    # Ponto de entrada
├── build.py                   # Compilação PyInstaller
├── settings.json              # Configurações (gerado automaticamente)
├── chat_handlers/             # TwitchHandler, TikTokHandler, KickHandler, YoutubeHandler
├── core/                      # ChatManager, SettingsManager, HotkeyManager
├── ui/
│   ├── main_window.py           # ChatWindow (orquestrador principal)
│   ├── config_window.py         # ConfigWindow (painel de configurações)
│   └── widgets/                 # Pacote de widgets modulares (extraídos do monolito)
│       ├── __init__.py          # Re-exporta todas as classes públicas
│       ├── chat_page.py         # ChatPageWidget — feed de chat, scroll, mensagens
│       ├── notifications.py     # JoinNotificationBanner — banner animado de entrada
│       ├── custom_layouts.py    # FlowLayout + HeightAwareWidget
│       ├── viewers_page.py      # ViewerCardWidget + OnlineViewersListWidget
│       └── gifts_page.py        # LiveGiftCardWidget + LiveGiftsListWidget
├── utils/                     # translations, tts_engine, resource_path, badge_manager...
└── assets/                    # Ícones SVG, fontes TTF, logos
```

## Pacote `ui/widgets/`

Criado para modularizar o `main_window.py` original (~2800 linhas). Cada arquivo tem responsabilidade única:

| Módulo | Classes Exportadas | Responsabilidade |
|--------|--------------------|------------------|
| `chat_page.py` | `ChatPageWidget` | Feed principal de mensagens: scroll, FlowLayout por mensagem, suporte a emotes/GIFs/CJK, fade-in, limite de 200 msgs |
| `notifications.py` | `JoinNotificationBanner` | Banner animado (fade-in/out) com fila de entrada de usuários, ajuste dinâmico de tamanho de fonte |
| `custom_layouts.py` | `FlowLayout`, `HeightAwareWidget` | Layout que quebra linha automaticamente + widget que recalcula altura real com base na largura |
| `viewers_page.py` | `ViewerCardWidget`, `OnlineViewersListWidget` | Aba de espectadores online TikTok: cards com avatar circular, rank, score, botões de sincronizar/voltar |
| `gifts_page.py` | `LiveGiftCardWidget`, `LiveGiftsListWidget` | Aba de presentes da live: cards com avatar, nome, descrição do presente, contagem e tempo relativo |

Importe sempre pelo pacote:

```python
from ui.widgets import ChatPageWidget, OnlineViewersListWidget, LiveGiftsListWidget
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
2. Emitir `stats_updated(viewers, 0, 0, 0)` — 4 valores obrigatórios (onde o TikTok usa uptime/total, enquanto os demais herdam 0).
3. Registrar em `ChatManager.start_all()` e no controle dinâmico em `main.py` (`open_config`).
4. Conectar os Stats:
   ```python
   h.stats_updated.connect(lambda v, u, l, t: self.platform_stats_updated.emit("nova", v, u, l, t))
   ```
5. Registrar a plataforma na lista de fallback de painel (`core/chat_manager.py` no método `_on_platform_stats`), para caso a plataforma esteja rodando sozinha, ela seja capaz de engatilhar o start do timer nativo da GUI e comandar os Views principais da tela.
6. Adicionar campos em `ConfigWindow` e as chaves em `translations.py`.

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
