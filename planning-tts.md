# Planejamento: Bot de Voz Neural (TTS) - v4.0

Este documento detalha a implementação de um sistema de Text-to-Speech (TTS) de alta fidelidade para o **Furious Multi Chat Pro**, utilizando vozes neurais gratuitas da Microsoft via `edge-tts`. O objetivo é criar um assistente de voz "Plug-and-Play" que seja independente de plataforma e extremamente estável.

## Arquitetura: O Motor de Voz ("The Engine")

Para garantir que a implementação seja cirúrgica e não afete a estabilidade da v3.5, criaremos um novo módulo isolado: `utils/tts_engine.py`.

### 1. Dependências Necessárias
*   **`edge-tts`**: Biblioteca principal para gerar os áudios neurais (Azure).
*   **`pygame`**: Módulo `pygame.mixer` para reprodução simultânea e controle de volume independente.
*   **`tempfile`**: Para garantir que os arquivos de áudio temporários sejam criados e destruídos com segurança no diretório de sistema.

### 2. O Gerenciador de Voz (`TTSManager`)
Uma classe `QObject` que gerenciará todo o ciclo de vida da voz:
- **Fila de Mensagens (`collections.deque`)**: Armazena as mensagens. Sistema de "Proteção contra Raids" (limita o tamanho da fila a 10 mensagens para não acumular áudio infinito).
- **Vozes por Plataforma (Diferenciação)**:
    - **TikTok**: Voz Feminina 1 (Ex: Francisca).
    - **Twitch**: Voz Masculina 1 (Ex: Antonio).
    - **Kick**: Voz Feminina 2 (Ex: Thalita).
    - *Isso ajuda o streamer a saber de onde vem a mensagem sem olhar para a tela.*
- **Efeitos Sonoros (SFX) de Alerta**: Pequenos sons (bips) antes de ler presentes ou eventos importantes.

## Integração Cirúrgica (Mínimo Impacto)

A integração no `ui/main_window.py` será feita em apenas dois pontos:

1.  **Inicialização**: No final do `__init__`, carregamos o `TTSManager`.
2.  **Conexão de Sinais**: Conectamos o sinal `message_received` do MainWindow.
    - O `TTSManager` terá uma função que "limpa" o HTML (remove tags `<img>`) antes de enviar o texto puro para o sintetizador.

## Funcionalidades de Inteligência Avançada (Novas Melhorias)

Para que o bot seja profissional e útil em transmissões reais:

- **Filtro de Spam Dinâmico**: Detecta textos repetidos (ex: "kkkkkkkkkkk" ou "AAAAAA") e reduz para uma leitura curta.
- **Ignorar Links**: URLs não serão lidas ("Usuário enviou um link").
- **Leitura de Alertas de Entrada**: Opcional para ler a frase "Bem-vindo, fulano!" quando o banner de entrada for ativado.
- **Atalho de Limpeza (Hotkey)**: Um atalho de teclado global (Ex: `Ctrl+M`) para silenciar o bot e limpar a fila instantaneamente caso o chat esteja sendo "flopado".
- **Botão de Mudo no Cabeçalho**: Ícone de alto-falante ao lado do ID da sala para controle rápido.

## Plano de Execução (Passo a Passo)

### Fase 1: Fundação do Motor
- [ ] Criar `utils/tts_engine.py`.
- [ ] Implementar a lógica de download assíncrono do áudio com `tempfile`.
- [ ] Implementar o player de áudio multi-thread via `pygame.mixer`.

### Fase 2: Interface e Configurações
- [ ] Adicionar ícone de "Voz" no cabeçalho do `MainWindow`.
- [ ] Criar aba de "Voz" nas configurações para selecionar vozes por plataforma e volume.

### Fase 3: Regras e Inteligência
- [ ] Implementar o `TextCleaner` para limpar HTML e gerenciar spam.
- [ ] Adicionar lógica de SFX para presentes.
- [ ] Integrar com o `JoinNotificationBanner` para leitura de boas-vindas.

## Medidas de Estabilidade (Rollback)

> [!CAUTION]
> O motor de voz operará em modo "Try-Catch" total. Se qualquer áudio falhar ou a internet oscilar, o sistema pula para a próxima mensagem sem afetar o desempenho visual do chat, que é a prioridade absoluta.

---
**Status Recomendado**: v4.0 (Voz Inteligente e Acessibilidade)
**Responsável**: Agente de IA / Desenvolvedor
