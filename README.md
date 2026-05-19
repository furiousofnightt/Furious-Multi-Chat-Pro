<div align="center">
  <h1>🌟 Furious Multi Chat Pro</h1>
  <p><strong>A plataforma definitiva para streamers gerenciarem chats de múltiplas redes simultaneamente.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Twitch-9146FF?style=for-the-badge&logo=twitch&logoColor=white" alt="Twitch" />
    <img src="https://img.shields.io/badge/TikTok-000000?style=for-the-badge&logo=tiktok&logoColor=white" alt="TikTok" />
    <img src="https://img.shields.io/badge/Kick-53FC18?style=for-the-badge&logo=kick&logoColor=black" alt="Kick" />
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

O **Furious Multi Chat Pro** é uma aplicação desktop de alta performance criada especificamente para streamers que transmitem em múltiplas plataformas. Ele unifica os chats da **Twitch, TikTok e Kick** em uma única interface elegante, transparente e customizável, ideal para sobrepor em jogos ou utilizar no OBS Studio.

## ✨ Principais Funcionalidades

- **🌐 Chat Multi-Plataforma**: Capture e visualize mensagens do Twitch, TikTok e Kick em tempo real e em uma única janela.
- **🎨 Design Premium & Glassmorphism**: Interface moderna, fluida e com suporte a transparência e efeito blur (desfoque nativo do Windows).
- **👻 Overlay Inteligente**: Modo "Sempre no Topo" (Always-on-top) com opacidade ajustável e função "Click-through" (clique através do chat) para não atrapalhar sua gameplay.
- **⌨️ Hotkeys Globais**: Atalhos de teclado customizáveis para ocultar/exibir ou limpar o chat rapidamente.
- **😎 Suporte Completo a Emotes**: Renderização em tempo real de emotes nativos da Twitch, Kick, além de suportar extensões populares como **7TV e BTTV**.
- **🔔 Notificações Visuais**: Alertas em formato de banner animado quando novos espectadores entram na live.
- **🛡️ Ferramentas de Moderação**: Sistema de *Blacklist* para censurar automaticamente palavras indesejadas.
- **⏳ Controle de Leitura**: Sistema de atraso e espaçamento de mensagens para facilitar a leitura em chats muito movimentados.
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

Na primeira execução, o sistema gerará automaticamente o arquivo `settings.json` contendo suas preferências. Você pode editá-lo diretamente ou através da aba de configurações dentro da própria interface:

```json
{
    "twitch": "seu_canal_twitch",
    "tiktok": "seu_canal_tiktok",
    "kick": "seu_canal_kick",
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
        "system": "#333333"
    }
}
```

## 🎮 Comandos e Atalhos (Hotkeys)

### Atalhos de Teclado (Padrão)
- `Ctrl + Shift + H`: Mostrar/Esconder janela do chat
- `Ctrl + Shift + C`: Limpar o histórico do chat

### Comandos de Texto (No input do chat)
- `/clear` - Limpa todas as mensagens da tela
- `/config` - Abre a janela de configurações da aplicação

---

## ⚠️ Limitações Conhecidas (API de Terceiros)

**TikTok Live:**
Pode ocorrer uma perda de aproximadamente **15% das mensagens** de usuários específicos. Isso não é um erro da aplicação, mas sim uma limitação técnica:
1. A biblioteca de integração (`TikTokLive`) utiliza um proxy externo (`eulerstream.com`) para manter a conexão WebSocket.
2. Este proxy/API do TikTok muitas vezes filtra usuários que estão com restrições na conta (shadow ban) ou utilizando versões não homologadas do app.
- *Recomendação:* Esteja ciente dessa limitação atual das APIs públicas do TikTok para desenvolvedores terceiros.

---

## 🏗️ Arquitetura do Sistema

A aplicação foi desenhada com foco em performance e concorrência:
- **Fluxo de Mensagens**: O `ChatManager` inicializa instâncias isoladas (`handlers`) para cada plataforma. Os handlers conectam-se às APIs e enviam sinais (Thread-safe) para o PyQt6 renderizar na interface.
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
*Ou utilizando diretamente o PyInstaller:*
```bash
pyinstaller FuriousMultiChatPro.spec
```

---

<div align="center">
  <p>Criado com 💜 para a comunidade de streamers.</p>
  <p><b>Propriedade de Furious Multi Chat Pro</b></p>
</div>
