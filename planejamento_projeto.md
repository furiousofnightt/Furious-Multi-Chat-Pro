# Planejamento do Projeto: Furious Multi Chat Pro (Chat Robusto Multi-Plataforma)

Este documento detalha o plano de desenvolvimento para um aplicativo de chat transparente e moderno, capaz de sincronizar mensagens do Twitch, YouTube, TikTok e Kick em tempo real.

## 1. Visão Geral
O objetivo é criar uma alternativa superior ao TransparentTwitchChat, com suporte a múltiplas plataformas, interface moderna, leve e de fácil configuração. O usuário precisará apenas inserir os usernames (@) de seus perfis para que o app sincronize automaticamente os chats e eventos.

## 2. Tecnologias Utilizadas
- **Linguagem:** Python 3.11+
- **Interface Gráfica (Frontend):** PyQt6 (para alta performance, transparência nativa e suporte a janelas "sempre no topo").
- **Motor de Renderização:** PyQt6 WebEngine (opcional, para renderização rica de emotes e mensagens) ou QLabels otimizados.
- **Conectividade (APIs/Websockets):**
  - **Twitch:** `TwitchIO` (Alta performance via Websockets).
  - **YouTube:** `pytchat` (Leve, não requer chave de API oficial para leitura).
  - **TikTok:** `TikTokLive` (Conexão direta com o serviço de WebCast do TikTok).
  - **Kick:** `kickpython` ou integração via Websocket direto.
- **Empacotamento:** `PyInstaller` ou `Nuitka` para gerar um executável `.exe` único e portátil.

## 3. Funcionalidades Principais
### 🎉 Sincronização Inteligente
- O usuário configura apenas o @ de cada plataforma.
- O app detecta quando uma live está online e inicia a captura das mensagens.
- Consolidação de todas as mensagens em uma única lista cronológica.

### ✨ Interface Moderna e Transparente
- Janela sem bordas (frameless) e transparente.
- Opção de "Click-through" (clicar através da tela para não atrapalhar o jogo).
- Customização de opacidade, fontes e cores.
- Ícones de plataforma (badges) ao lado do nome do usuário para identificar a origem da mensagem.

### 🌍 Internacionalização
- Suporte nativo a Português (PT-BR) e Inglês (EN).

### ⚙️ Configurações e Instalação
- Interface de configuração intuitiva.
- Instalador rápido e leve, opcional-com opção de versão portátil.

## 4. Etapas de Desenvolvimento

### Fase 1: Arquitetura e Interface Base
1.  Setup do ambiente Python e estrutura de pastas.
2.  Criação da janela principal transparente com PyQt6.
3.  Implementação do sistema de temas e transparência ajustável.

### Fase 2: Módulos de Chat (Backend)
1.  **Twitch:** Integração com Websockets para chat e eventos (sub, bits, etc).
2.  **YouTube:** Implementação do scraper `pytchat` para mensagens em tempo real.
3.  **TikTok:** Integração com `TikTokLive` para capturar comentários e presentes (gifts).
4.  **Kick:** Conexão com a rede de chat do Kick.com.

### Fase 3: Lógica de Sincronização
1.  Criação de um "Manager" central que gerencia as múltiplas conexões.
2.  Normalização dos dados (transformar todas as mensagens/eventos em um formato comum).
3.  Sistema de cache de ícones e emotes para performance.

### Fase 4: Interface de Configuração e Polimento
1.  Criação da aba de configurações (Inputs para os @ das plataformas).
2.  Implementação de filtros de chat e comandos básicos.
3.  Ajustes de UI/UX (Animações suaves de entrada de mensagens).

### Fase 5: Compilação e Distribuição
1.  Otimização do código para reduzir o tamanho do executável.
2.  Criação do instalador usando Inno Setup ou similar.
3.  Testes de compatibilidade em Windows 10/11.

## 5. Próximos Passos
1.  Aprovação deste plano pelo usuário.
2.  Início da Fase 1 (Interface Base).
