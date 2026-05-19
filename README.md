# Furious Multi Chat Pro

Aplicação desktop multi-plataforma para streamers capturarem e exibirem chat de múltiplas plataformas simultaneamente (Twitch, TikTok, Kick).

## 🚀 Funcionalidades

- **Chat Multi-Plataforma**: Capture mensagens do Twitch, TikTok e Kick simultaneamente
- **Interface Moderna**: Design com glassmorphism, animações suaves e personalização completa
- **Hotkeys Globais**: Atalhos de teclado para mostrar/esconder e limpar o chat
- **Overlay para Streaming**: Janela sempre no topo com opacidade ajustável
- **Suporte a Emotes**: Exibe emotes da Twitch (nativos), 7TV, BTTV e Kick
- **Notificações de Entrada**: Banners animados quando usuários entram na live
- **Filtro de Palavras**: Blacklist para censurar palavras indesejadas
- **Suporte Multilíngue**: Português (Brasil) e Inglês
- **Atraso de Mensagens**: Opção para "lentidão" nas mensagens (útil para leitura)

## 📋 Requisitos

- Python 3.12+
- Windows 10/11 (com suporte a transparência e blur)
- Dependências listadas em `requirements.txt`

## 🛠️ Instalação

```bash
pip install -r requirements.txt
```

## ▶️ Execução

```bash
python run.py
```

## 📁 Estrutura do Projeto

```
chat-geral-ttk-twitch-kick/
├── run.py                  # Entry point da aplicação
├── main.py                 # Inicialização do QApplication e sistema principal
├── requirements.txt        # Dependências Python
├── settings.json          # Configurações do usuário (gerado automaticamente)
│
├── core/                   # Núcleo da aplicação
│   ├── chat_manager.py    # Gerenciamento de handlers e fila de mensagens
│   ├── settings_manager.py # Persistência de configurações
│   ├── hotkey_manager.py  # Sistema de hotkeys globais
│   └── __init__.py
│
├── chat_handlers/          # Handlers de chat por plataforma
│   ├── base_handler.py    # Classe abstrata base
│   ├── twitch_handler.py # Integração IRC com Twitch
│   ├── tiktok_handler.py # Integração via TikTokLive
│   ├── kick_handler.py   # Integração via KickAPI
│   └── __init__.py
│
├── ui/                     # Interface do usuário (PyQt6)
│   ├── main_window.py     # Janela principal do chat
│   ├── config_window.py  # Janela de configurações
│   └── __init__.py
│
├── utils/                  # Utilitários
│   ├── translations.py    # Sistema de internacionalização
│   ├── emoticons.py     # Processamento e cache de emotes
│   ├── resource_path.py  # Resolução de caminhos (dev vs build)
│   └── blur_window.py    # Efeito de blur para Windows
│
└── assets/                 # Recursos estáticos
    ├── fonts/            # Fontes customizadas
    ├── *.svg             # Ícones e badges
    └── *.png             # Ícones de plataformas
```

## 🔧 Configuração

Ao executar pela primeira vez, o arquivo `settings.json` é criado automaticamente com valores padrão:

```json
{
    "twitch": "",
    "tiktok": "",
    "kick": "",
    "language": "pt-br",
    "opacity": 0.85,
    "theme": "dark",
    "click_through": false,
    "blacklist": [],
    "font_family": "Segoe UI Variable Display",
    "font_size": 11,
    "platform_colors": {
        "twitch": "#9146FF",
        "tiktok": "#FF0050",
        "kick": "#53FC18",
        "system": "#333333"
    }
}
```

## 🎮 Hotkeys Padrão

- **Ctrl+Shift+H**: Mostrar/Esconder janela
- **Ctrl+Shift+C**: Limpar chat

## 📝 Comandos no Chat

- `/clear` - Limpa o chat
- `/config` - Abre configurações

## ⚠️ Limitações Conhecidas

### TikTok Live

Aproximadamente **15% das mensagens de usuários específicos** podem não aparecer no chat. Isso ocorre porque:

1. A biblioteca TikTokLive usa um servidor de proxy (`eulerstream.com`) para conexão WebSocket
2. Este servidor pode filtrar mensagens de usuários que:
   - Estão em shadow ban
   - Usam versões específicas do app móvel
   - Têm restrições na conta
3. Não é um bug no nosso código — é uma limitação da API de terceiros

**Solução alternativa**: Não há solução simples no momento. Migrar para uma biblioteca Node.js diferente ou criar um servidor de sign próprio exigiria refactoring significativo.

**Recomendação**: Documentar esta limitação para usuários finais.

## 🏗️ Arquitetura

### Fluxo de Mensagens

1. **ChatManager** inicia handlers para cada plataforma ativa
2. **Handlers** conectam-se às APIs e emitem sinais PyQt
3. **Sinais** são processados na thread principal (thread-safe)
4. **Fila de mensagens** opcional para atraso entre mensagens
5. **UI** exibe mensagens com HTML/CSS styling

### Threads e Event Loops

- **Thread principal**: UI do PyQt6
- **AsyncManager**: Thread dedicada para event loop asyncio (TikTok/Kick)
- **Thread IRC**: Uma thread por conexão Twitch
- **HotkeyManager**: Thread para captura global de teclas

## 📦 Build

Para criar executável standalone:

```bash
python build.py
```

Ou diretamente com PyInstaller:

```bash
pyinstaller FuriousMultiChatPro.spec
```

## 🐛 Debug

O aplicativo cria logs no console. Para salvar erros:

- Erros críticos são salvos em `crash_log.txt`

## 📄 Licença

Projeto proprietário - Furious Multi Chat Pro

## 👥 Autores

Desenvolvido para streamers brasileiros e internacionais.
