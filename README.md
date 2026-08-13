<div align="center">
  <h1>🌟 Furious Multi Chat Pro</h1>
  <p><strong>A plataforma definitiva para streamers gerenciarem chats de múltiplas redes simultaneamente.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Twitch-9146FF?style=for-the-badge&logo=twitch&logoColor=white" alt="Twitch" />
    <img src="https://img.shields.io/badge/TikTok-000000?style=for-the-badge&logo=tiktok&logoColor=white" alt="TikTok" />
    <img src="https://img.shields.io/badge/Kick-53FC18?style=for-the-badge&logo=kick&logoColor=black" alt="Kick" />
    <img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube" />
  </p>

  <br />

  <a href="https://furiousmultichat.pythonanywhere.com/">
    <img src="https://img.shields.io/badge/⬇️_BAIXAR_AGORA-0078D7?style=for-the-badge&logo=windows&logoColor=white" alt="Baixar Furious Multi Chat Pro" />
  </a>
  <br />
  <sub>Disponível para Windows 10/11</sub>
</div>

---

## 🎯 Sobre o Projeto

O **Furious Multi Chat Pro** é uma aplicação desktop de alta performance criada especificamente para streamers que transmitem em múltiplas plataformas. Ele unifica os chats da **Twitch, TikTok, Kick e YouTube** em uma única interface elegante, transparente e customizável, ideal para sobrepor em jogos ou utilizar no OBS Studio.

## ✨ Principais Funcionalidades

- **🌐 Chat Multi-Plataforma**: Capture e visualize mensagens do Twitch, TikTok, Kick e YouTube em tempo real em uma única janela.
- **📊 Estatísticas em Tempo Real**: Painel com viewers online, **total de visualizações acumuladas** (TikTok), uptime da transmissão e curtidas — tudo atualizado ao vivo.
- **🟢 Status de Conexão Inteligente**: Tooltip nos viewers que exibe o estado real de cada plataforma — "Offline" quando desconectada, "0" quando conectada mas sem espectadores, e o número real quando há viewers.
- **🎨 Design Premium & Glassmorphism**: Interface moderna, fluida e com suporte a transparência e efeito blur (desfoque nativo do Windows).
- **👻 Overlay Inteligente**: Modo "Sempre no Topo" (Always-on-top) com opacidade ajustável e função "Click-through" (clique através do chat) para não atrapalhar sua gameplay.
- **⌨️ Hotkeys Globais**: Atalhos de teclado customizáveis para ocultar/exibir ou limpar o chat rapidamente.
- **😎 Suporte Completo a Emotes**: Renderização em tempo real de emotes nativos da Twitch, Kick, além de suportar extensões populares como **7TV e BTTV**.
- **🔔 Notificações Visuais**: Alertas em formato de banner animado quando novos espectadores entram na live.
- **🛡️ Ferramentas de Moderação**: Sistema de *Blacklist* para censurar automaticamente palavras indesejadas.
- **⏳ Controle de Leitura**: Sistema de atraso e espaçamento de mensagens para facilitar a leitura em chats muito movimentados.
- **🗣️ Bot de Voz Neural (TTS)**: Leitura de mensagens com vozes de alta fidelidade (Azure), configuração independente por plataforma e filtro anti-spam.
- **🔒 Segurança de Dados (DPAPI)**: O token de sessão do TikTok é armazenado criptografado no `settings.json` usando a **Windows DPAPI**, vinculado ao usuário do Windows — ilegível por vírus ou outros programas.
- **🌍 Internacionalização**: Suporte nativo para Português (Brasil) e Inglês.

---

## 📋 Requisitos do Sistema

- **Sistema Operacional**: Windows 10 ou Windows 11 (necessário para os efeitos de transparência e blur)
- **Python**: Versão 3.12 ou superior (para execução via código-fonte)

## 🛠️ Instalação (Desenvolvedores)

Se você deseja rodar a aplicação a partir do código-fonte:

1. Clone o repositório ou baixe o código.
2. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o arquivo principal:
   ```bash
   python run.py
   ```

---

## 🔧 Configuração

Na primeira execução, o sistema gerará automaticamente o arquivo `settings.json` contendo suas preferências. Configure através da aba de configurações (ícone ⚙️) dentro da própria interface.

> **Nota de segurança**: O campo `tiktok_session_id` é salvo automaticamente criptografado com a DPAPI do Windows. Você verá um valor `DPAPI:...` no arquivo — isso é correto e esperado.

```json
{
    "twitch": "seu_canal_twitch",
    "tiktok": "seu_canal_tiktok",
    "kick": "seu_canal_kick",
    "youtube": "seu_video_id_ou_canal_youtube",
    "language": "pt-br",
    "opacity": 0.85,
    "theme": "dark",
    "click_through": false,
    "blacklist": ["palavrão1", "palavrão2"],
    "font_family": "Segoe UI Variable Display",
    "font_size": 11,
    "platform_colors": {
        "twitch": "#9146FF",
        "tiktok": "#FF0050",
        "kick": "#53FC18",
        "youtube": "#FF0000",
        "system": "#333333"
    },
    "tts_enabled": false,
    "tts_volume": 100,
    "tts_voice_twitch": "pt-BR-AntonioNeural",
    "tts_voice_tiktok": "pt-BR-FranciscaNeural",
    "tts_voice_kick": "pt-BR-ThalitaMultilingualNeural",
    "tts_voice_youtube": "pt-BR-DonatoNeural",
    "hotkey_toggle_visibility": "ctrl+shift+h",
    "hotkey_clear_chat": "ctrl+shift+c",
    "tiktok_session_id": "DPAPI:..."
}
```

## 🎮 Comandos e Atalhos (Hotkeys)

### Atalhos de Teclado (Padrão)
- `Ctrl + Shift + H`: Mostrar/Esconder janela do chat
- `Ctrl + Shift + C`: Limpar o histórico do chat
- `Ctrl + M`: Ativar/Desativar o Bot de Voz Neural (TTS)

### Comandos de Texto (No input do chat)
- `/clear` - Limpa todas as mensagens da tela
- `/config` - Abre a janela de configurações da aplicação

---

## 🔒 Segurança dos Dados

O campo `tiktok_session_id` no `settings.json` é criptografado automaticamente usando a **DPAPI (Data Protection API)** do Windows:

- A chave de criptografia está vinculada ao **usuário Windows logado** na máquina.
- Se o arquivo `settings.json` for copiado para outro computador, o token **não pode ser descriptografado**.
- Vírus do tipo "infostealer" que roubem o arquivo só verão dados ilegíveis (`DPAPI:AQAAANCMnd8...`).
- Nenhuma ação extra é necessária por parte do usuário — a criptografia é totalmente automática.

---

## ⚠️ Limitações Conhecidas (API de Terceiros)

**TikTok Live:**
Pode ocorrer uma perda de aproximadamente **10-15% das mensagens** de usuários específicos. Isso não é um erro da aplicação, mas sim uma limitação técnica da biblioteca `TikTokLive` que utiliza um proxy externo (`eulerstream.com`) para manter a conexão WebSocket. Este proxy pode filtrar mensagens de certos perfis.

- *Detalhes técnicos:* Ver `docs/TIKTOK-LIMITACOES.md`

---

## 🏗️ Arquitetura do Sistema

A aplicação foi desenhada com foco em performance e concorrência:
- **Fluxo de Mensagens**: O `ChatManager` inicializa instâncias isoladas (`handlers`) para cada plataforma. Os handlers conectam-se às APIs e enviam sinais (Thread-safe via PyQt6) para o `ChatWindow` renderizar na interface.
- **Fluxo de Stats**: O sinal `stats_updated(viewers, uptime, likes, total_views)` carrega 4 valores. O `ChatManager` propaga para a UI junto com o dicionário de status de conexão de cada plataforma.
- **Multithreading**:
  - `Thread Principal`: Gerencia a UI (PyQt6).
  - `AsyncManager`: Thread dedicada ao Event Loop do `asyncio` (usado no TikTok e Kick).
  - `Thread IRC`: Thread dedicada e leve para o socket da Twitch.
  - `HotkeyManager`: Thread de baixo nível para escuta global de atalhos.

## 📦 Build e Compilação

Para compilar o código em um executável standalone (.exe):

```bash
python build.py
```

O script `build.py` já inclui todas as flags necessárias, incluindo `--hidden-import=win32crypt` para a criptografia DPAPI funcionar corretamente no executável.

---

<div align="center">
  <p>Criado com 💜 para a comunidade de streamers.</p>
  <p><b>Propriedade de Furious Multi Chat Pro</b></p>
</div>
