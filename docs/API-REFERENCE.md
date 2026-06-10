# API Reference - Furious Multi Chat Pro

## Core Module

### ChatManager

Gerenciador central de chat e handlers.

```python
class ChatManager(QObject):
    status_changed = pyqtSignal(str, bool)  # (platform, connected)
```

#### Métodos

##### `__init__(self, settings, window)`
Inicializa o gerenciador com settings e referência à janela principal.

##### `start_all()`
Inicia todos os handlers configurados nas settings.
- Limpa filas e estados
- Inicia AsyncManager para TikTok/Kick
- Conecta handlers aos sinais
- Atualiza status inicial

##### `stop_all(total_stop=True)`
Para todos os handlers.
- `total_stop=True`: Para também o AsyncManager (uso no encerramento)
- `total_stop=False`: Mantém loop async (uso em restart)

##### `restart_all()`
Reinicia todas as conexões (stop + start com delay).

##### `on_message_received(author, message, platform)`
Slot para receber mensagens de handlers.
- Aplica filtro de blacklist
- Gerencia fila de delay
- Envia para UI

##### `filter_message(message)`
Aplica filtro de palavras da blacklist.
- Retorna mensagem censurada (*****)
- Case-insensitive
- Preserva pontuação

##### `update_status(platform, connected)`
Atualiza status de conexão e emite sinal.

##### `handle_command(cmd)`
Processa comandos de chat (/clear, /config).

---

### SettingsManager

Gerenciador de configurações JSON.

```python
class SettingsManager:
    settings: dict  # Configurações carregadas
```

#### Métodos

##### `__init__(filename="settings.json")`
Carrega settings do arquivo ou cria com defaults.

##### `load_settings()`
Retorna dict com configurações mergeadas (defaults + arquivo).

##### `save_settings()`
Persiste settings no arquivo JSON.

#### Estrutura de Configurações

```python
defaults = {
    "twitch": "",           # str: nome do canal Twitch
    "tiktok": "",           # str: nome do usuário TikTok
    "kick": "",             # str: nome do canal Kick
    "language": "pt-br",    # str: pt-br ou en
    "opacity": 0.85,        # float: 0.0 - 1.0
    "theme": "dark",        # str: dark (único por enquanto)
    "click_through": False, # bool: permite clicar através
    "blacklist": [],        # list[str]: palavras bloqueadas
    "font_family": "Segoe UI Variable Display",  # str
    "font_size": 11,        # int
    "platform_colors": {    # dict: cores por plataforma
        "twitch": "#9146FF",
        "tiktok": "#FF0050",
        "kick": "#53FC18",
        "system": "#333333"
    },
    "hotkey_toggle_visibility": "ctrl+shift+h",  # str
    "hotkey_clear_chat": "ctrl+shift+c",         # str
    "message_delay": 0      # float: segundos entre mensagens
}
```

---

### HotkeyManager

Gerenciador de atalhos de teclado globais.

```python
class HotkeyManager(QObject):
    toggle_visibility_requested = pyqtSignal()
    clear_chat_requested = pyqtSignal()
```

#### Métodos

##### `__init__(self, settings)`
Recebe settings para ler combinações de teclas.

##### `start()`
Registra hooks globais para as hotkeys configuradas.

##### `stop()`
Remove todos os hooks e para o listener.

---

## Chat Handlers

### BaseChatHandler (Abstract)

Classe base para todos os handlers.

```python
class BaseChatHandler(QObject):
    message_received = pyqtSignal(str, str, str)   # (user, text, platform)
    user_joined = pyqtSignal(str, str)            # (username, platform)
    status_changed = pyqtSignal(bool)             # (connected)
    stats_updated = pyqtSignal(int, int, int)     # (viewers, uptime, likes)
```

#### Atributos

- `username: str` - Nome do canal/usuário
- `platform: str` - Identificador da plataforma
- `is_running: bool` - Estado de execução
- `language: str` - Idioma para mensagens de sistema

#### Métodos

##### `set_language(lang)`
Define idioma para mensagens de sistema.

##### `start()` / `start_with_loop(loop)`
Inicia o handler. Implementação específica por plataforma.

##### `stop()`
Para o handler de forma segura.

---

### TwitchHandler

Handler para Twitch via IRC.

```python
class TwitchHandler(BaseChatHandler):
    platform = "twitch"
```

#### Características
- Conexão IRC direta (socket TCP)
- Thread dedicada
- Autenticação anônima (justinfan)
- Suporte a emotes nativos e de terceiros (7TV/BTTV)

---

### TikTokHandler

Handler para TikTok via TikTokLive.

```python
class TikTokHandler(BaseChatHandler):
    platform = "tiktok"
```

#### Características
- Asyncio/WebSocket via TikTokLive
- Múltiplos handlers de evento
- Cache de ícones de presentes
- Sincronização de uptime

#### Eventos Capturados
- `CommentEvent` - Mensagens normais
- `CommentsEvent` - Mensagens em lote
- `BarrageEvent` - Mensagens barrage (com filtro de sistema)
- `EcBarrageEvent` - E-commerce barrage (com filtro de sistema)
- `EmoteChatEvent` - Emotes especiais
- `UnknownEvent` - Fallback

#### Limitações
- ~15% de mensagens podem ser perdidas (limitação do servidor proxy)
- Ver documentação detalhada: `docs/TIKTOK-LIMITACOES.md`

---

### KickHandler

Handler para Kick via kickpython.

```python
class KickHandler(BaseChatHandler):
    platform = "kick"
```

#### Características
- WebSocket assíncrono
- Badges SVG customizados
- Emotes via regex `[emote:ID:NAME]`

---

## Utils

### Translations

Sistema de internacionalização.

```python
def get_translation(key: str, language: str = "pt-br", *args, **kwargs) -> str
```

#### Uso
```python
msg = get_translation("twitch_connected", "pt-br", "canal123")
# Retorna: "Conectado ao canal #canal123"
```

#### Idiomas Suportados
- `pt-br` - Português (Brasil)
- `en` - English

---

### Emoticons

Processamento e cache de emotes.

```python
def get_emote_url(url: str, emote_id: str) -> str | None
```

Baixa emote da URL, salva em arquivo temporário local, retorna `file:///` URL.

#### Emotes de Terceiros
```python
# Mapeamento de nomes para IDs 7TV
THIRD_PARTY_CACHE = {
    "thimag1Risada": "651f893e3752e5576d1e4335",
    "KEKW": "60ae5267e0358896085e3966",
    "LULW": "60ae5244e0358896085e3962",
    "POGGERS": "60ae529ee0358896085e3972",
}
```

#### Cleanup
Pasta temporária de emotes é removida automaticamente ao fechar via `atexit`.

---

### Resource Path

```python
def resource_path(relative_path: str) -> str
```

Resolve caminho relativo para absoluto, funcionando em:
- Desenvolvimento (diretório do script)
- PyInstaller build (pasta temporária)

---

### TTS Engine (`tts_engine.py`)

Sistema de geração e reprodução de voz.

```python
class TTSManager(QObject):
    def __init__(self, parent=None):
```

#### Características
- Baseado no `edge-tts` (vozes neurais Azure)
- Player via `pygame.mixer` (reprodução simultânea de SFX/TTS)
- Usa thread de baixo nível para download de áudio.

#### Métodos Principais
- `read_message(username: str, msg: str, platform: str)` - Processa e enfileira uma mensagem.
- `toggle_mute() -> bool` - Ativa ou desativa a reprodução de voz e limpa a fila.
- `clear_queue()` - Esvazia a fila de leitura e encerra a voz atual se estiver tocando.
- `play_sfx(filename: str)` - Toca efeitos sonoros pequenos sem travar o áudio TTS.

#### Componentes Auxiliares
- `TextCleaner`: Filtra mensagens, limitando repetições (spam) e removendo URLs/Tags HTML antes da leitura.

---

## UI Components

### ChatWindow

Janela principal do chat.

#### Sinais
- `settings_requested` - Emitido quando usuário clica em configurações
- `command_executed(str)` - Emitido quando comando é enviado

#### Métodos Principais
- `add_message(author, message, platform)` - Adiciona mensagem ao chat
- `clear_chat()` - Limpa todas as mensagens
- `apply_theme(settings)` - Aplica configurações visuais
- `toggle_pin()` - Alterna sempre no topo
- `update_live_stats(viewers, uptime, likes)` - Atualiza estatísticas

### JoinNotificationBanner

Banner de notificação de entrada de usuários.

```python
class JoinNotificationBanner(QFrame):
    def add_user(self, username: str, platform: str)
```

- Sistema de fila (deque)
- Animações fade in/out
- Timer automático para esconder

---

## Fluxos de Sinal PyQt6

### Mensagem Recebida

```
Handler.message_received
    ↓ (pyqtSignal)
ChatManager.on_message_received
    ↓ (processa blacklist/fila)
ChatWindow.add_message
    ↓ (renderiza HTML)
UI QLabel
```

### Status de Conexão

```
Handler.status_changed
    ↓ (pyqtSignal)
ChatManager.update_status
    ↓ (pyqtSignal)
ChatWindow.update_status_indicator
    ↓ (atualiza bolinha colorida)
UI
```

### Hotkey Pressionada

```
keyboard (global hook)
    ↓
HotkeyManager._listener
    ↓ (pyqtSignal)
Main.toggle_window_visibility
    ↓
ChatWindow.show()/hide()
```

---

## Constantes e Configurações

### Cores Padrão
```python
PLATFORM_COLORS = {
    "twitch": "#9146FF",
    "tiktok": "#FF0050", 
    "kick": "#53FC18",
    "system": "#333333"
}
```

### IRC Twitch
```python
TWITCH_IRC_SERVER = "irc.chat.twitch.tv"
TWITCH_IRC_PORT = 6667
```

### TikTokLive
```python
TIKTOK_SIGN_URL = "https://tiktok.eulerstream.com"
```

---

## Exemplos de Uso

### Criar Handler Customizado

```python
from chat_handlers.base_handler import BaseChatHandler

class MyPlatformHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "myplatform"
    
    def start(self):
        self.is_running = True
        # Implementar lógica de conexão
        # Emitir sinais quando mensagens chegarem
        self.message_received.emit("user", "hello", "myplatform")
    
    def stop(self):
        self.is_running = False
        # Limpar recursos
```

### Adicionar no ChatManager

```python
# chat_manager.py em start_all()
if self.settings.settings.get("myplatform"):
    h = MyPlatformHandler(self.settings.settings["myplatform"])
    h.message_received.connect(self.on_message_received)
    h.start()
    self.handlers.append(h)
```
