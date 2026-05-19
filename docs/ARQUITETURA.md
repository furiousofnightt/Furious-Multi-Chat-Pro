# Arquitetura do Furious Multi Chat Pro

## Visão Geral

O Furious Multi Chat Pro é uma aplicação desktop construída com **PyQt6** que integra chats de múltiplas plataformas de streaming em uma única interface.

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN APPLICATION                         │
│                         (main.py)                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   ChatWindow │  │ ConfigWindow│  │    ChatManager      │ │
│  │  (UI Layer)  │  │  (Settings) │  │  (Business Logic)   │ │
│  └──────┬──────┘  └─────────────┘  └──────────┬──────────┘ │
│         │                                      │            │
│         │◄────────── Signals ──────────────────│            │
│         │                                      │            │
│  ┌──────┴──────────────────────────────────────┴──────────┐ │
│  │              HANDLERS DE CHAT                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │ Twitch   │  │ TikTok   │  │ Kick     │             │ │
│  │  │ (Thread) │  │ (Asyncio)│  │ (Asyncio)│             │ │
│  │  └──────────┘  └──────────┘  └──────────┘             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Módulos Principais

### 1. Core Layer (`core/`)

#### ChatManager (`chat_manager.py`)
- **Responsabilidade**: Orquestrar todos os handlers de chat
- **Funcionalidades**:
  - Iniciar/parar conexões com múltiplas plataformas
  - Gerenciar fila de mensagens (delay opcional)
  - Filtrar palavras da blacklist
  - Emitir status de conexão para UI
  - Gerenciar thread AsyncManager para TikTok/Kick

#### SettingsManager (`settings_manager.py`)
- **Responsabilidade**: Persistência de configurações
- **Formato**: JSON (`settings.json`)
- **Configurações**:
  - Credenciais de plataformas (nomes de usuário)
  - Aparência (cores, fontes, opacidade)
  - Comportamento (idioma, hotkeys, delay)
  - Blacklist de palavras

#### HotkeyManager (`hotkey_manager.py`)
- **Responsabilidade**: Capturar atalhos de teclado globais
- **Biblioteca**: `keyboard` (hook global Windows)
- **Sinais**: toggle_visibility_requested, clear_chat_requested
- **Segurança**: Thread separada, não bloqueia UI

### 2. Chat Handlers (`chat_handlers/`)

Todos herdam de `BaseChatHandler`:

```python
class BaseChatHandler(QObject):
    message_received = pyqtSignal(str, str, str)  # (user, text, platform)
    user_joined = pyqtSignal(str, str)           # (username, platform)
    status_changed = pyqtSignal(bool)            # (connected)
    stats_updated = pyqtSignal(int, int, int)   # (viewers, uptime, likes)
```

#### TwitchHandler (`twitch_handler.py`)
- **Protocolo**: IRC (Internet Relay Chat)
- **Conexão**: Socket TCP direto em thread separada
- **Porta**: 6667 (IRC padrão)
- **Autenticação**: Anônima (justinfan)
- **Recursos**:
  - Tags IRC para emotes nativos
  - Suporte a emotes 7TV/BTTV por nome
  - Buffer de linhas para evitar fragmentação
  - Reconexão automática a cada 30s em caso de erro

#### TikTokHandler (`tiktok_handler.py`)
- **Biblioteca**: `TikTokLive`
- **Conexão**: WebSocket via servidor de proxy EulerStream
- **Eventos capturados**:
  - `CommentEvent` (mensagens normais)
  - `CommentsEvent` (mensagens em lote)
  - `BarrageEvent` (mensagens tipo barrage)
  - `EcBarrageEvent` (e-commerce barrage)
  - `EmoteChatEvent` (emotes)
  - `UnknownEvent` (fallback para mensagens não reconhecidas)
- **Recursos**:
  - Cache de ícones de presentes
  - Sincronização de uptime via HTML scraping
  - Handlers múltiplos para compatibilidade
- **Limitação**: ~15% de mensagens podem ser perdidas (limitação do proxy)

#### KickHandler (`kick_handler.py`)
- **Biblioteca**: `kickpython`
- **Conexão**: WebSocket assíncrono
- **Recursos**:
  - Badges SVG (mod, vip, og, founder, etc.)
  - Emotes via regex `[emote:ID:NAME]`
  - Sistema de cache local de emotes

### 3. UI Layer (`ui/`)

#### ChatWindow (`main_window.py`)
- **Responsabilidade**: Janela flutuante do chat
- **Funcionalidades**:
  - QLabel com HTML para estilização
  - Scroll automático ou manual
  - Sistema de notificações de entrada (banner)
  - Barra de ferramentas com botões
  - Campo de comando (/clear, /config)
  - Tray icon para minimizar
  - Animações de fade in/out
- **Efeitos Visuais**:
  - Glassmorphism (blur + transparência) - Windows 11
  - Always on top (fixar janela)
  - Click-through (opcional)
  - Opacidade ajustável

#### ConfigWindow (`config_window.py`)
- **Responsabilidade**: Interface de configurações
- **Abas**:
  - Geral: nomes de usuário, idioma, opacidade
  - Aparência: cores, fontes, glassmorphism
  - Comportamento: delay, hotkeys, blacklist
  - Sobre: informações do app

### 4. Utils (`utils/`)

#### Translations (`translations.py`)
- **Sistema**: Dicionário centralizado PT-BR / EN
- **Uso**: `get_translation(key, language, **kwargs)`
- **Chaves**: Mensagens de sistema, labels de UI, notificações

#### Emoticons (`emoticons.py`)
- **Cache**: Pasta temporária por sessão (`tempfile.mkdtemp`)
- **Download**: URLs externas → arquivos locais
- **Formatos**: PNG, GIF, WEBP
- **Emotes de terceiros**: Mapeamento 7TV/BTTV para IDs
- **Cleanup**: Pasta temporária removida ao fechar

#### Resource Path (`resource_path.py`)
- **Responsabilidade**: Resolver caminhos em dev vs PyInstaller
- **Uso**: `resource_path("assets/icon.png")`

## Fluxo de Dados

### Recebimento de Mensagem

1. Handler detecta mensagem na plataforma
2. Handler processa (emotes, badges, filtragem)
3. Emite sinal `message_received(user, text, platform)`
4. ChatManager recebe sinal (thread-safe via Qt)
5. Aplica filtro de blacklist
6. Adiciona à fila (se delay ativo) ou envia direto
7. ChatWindow.render_message() exibe com HTML

### Atualização de Status

1. Handler detecta conexão/desconexão
2. Emite `status_changed(bool)`
3. ChatManager atualiza dicionário interno
4. Emite `status_changed(platform, bool)`
5. ChatWindow atualiza indicadores visuais (bolinhas coloridas)

## Threading Model

```
Thread Principal (PyQt6)
├── ChatWindow (UI)
├── ChatManager (signals/slots)
└── HotkeyManager (hook global)

AsyncManager Thread (uma única)
└── Event Loop asyncio
    ├── TikTokHandler (WebSocket)
    └── KickHandler (WebSocket)

Twitch Thread (uma por conexão)
└── Socket IRC bloqueante
```

## Sinais PyQt6 Importantes

### ChatManager → ChatWindow
- `status_changed(platform: str, connected: bool)`
- Indicadores visuais de conexão

### Handlers → ChatManager
- `message_received(author: str, message: str, platform: str)`
- `user_joined(username: str, platform: str)`
- `status_changed(connected: bool)`
- `stats_updated(viewers: int, uptime: int, likes: int)`

### HotkeyManager → Main
- `toggle_visibility_requested()`
- `clear_chat_requested()`

## Persistência

### Arquivo: `settings.json`
```json
{
    "twitch": "nome_canal",
    "tiktok": "nome_usuario",
    "kick": "nome_canal",
    "language": "pt-br",
    "opacity": 0.85,
    "theme": "dark",
    "click_through": false,
    "blacklist": ["palavra1", "palavra2"],
    "font_family": "Inter",
    "font_size": 11,
    "platform_colors": {
        "twitch": "#9146FF",
        "tiktok": "#FF0050",
        "kick": "#53FC18"
    },
    "hotkey_toggle_visibility": "ctrl+shift+h",
    "hotkey_clear_chat": "ctrl+shift+c",
    "message_delay": 0
}
```

## Dependências Externas

| Biblioteca | Uso | Plataformas |
|------------|-----|-------------|
| PyQt6 | Interface gráfica | Todas |
| twitchio | Twitch (alternativa, mas usamos IRC raw) | Twitch |
| TikTokLive | Conexão TikTok | TikTok |
| kickpython | Conexão Kick | Kick |
| keyboard | Hotkeys globais | Todas |
| httpx | Requisições HTTP | Todas |
| aiohttp | Async HTTP | TikTok, Kick |

## Pontos de Extensão

Para adicionar uma nova plataforma:

1. Criar `NewPlatformHandler` herdando `BaseChatHandler`
2. Implementar `start()` ou `start_with_loop(loop)`
3. Emitir sinais conforme mensagens chegam
4. Adicionar no `ChatManager.start_all()`
5. Adicionar campos no `ConfigWindow`
6. Adicionar traduções em `translations.py`
