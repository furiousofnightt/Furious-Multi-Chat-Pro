# Planejamento: Bot de Voz Neural (TTS) - v4.1

Este documento detalha a implementação do sistema de Text-to-Speech (TTS) do **Furious Multi Chat Pro**. A partir da v4.1, o sistema suporta **dois motores de voz** selecionáveis pelo usuário na interface de configurações.

---

## Arquitetura: O Motor de Voz (`utils/tts_engine.py`)

### Motores Disponíveis

| Motor | Biblioteca | Qualidade | Requer Internet | Vozes por Plataforma |
|-------|-----------|-----------|-----------------|----------------------|
| **Microsoft Edge (Neural)** | `edge-tts` | Alta (Neural Azure) | Sim | Sim (Antônio/Francisca/Thalita) |
| **Google TTS (Alternativo)** | `gtts` | Média (Google Translate) | Sim | Não (pt-BR único) |

### Por que dois motores? — Contexto Histórico e Resolução (out/2026)
Em outubro de 2026, a Microsoft desativou a síntese WebSocket no endpoint legado `speech.platform.bing.com` (retornando `403 WSServerHandshakeError`), migrando o Edge 155+ para `api.msedgeservices.com/tts/cognitiveservices/websocket/v1`. 

**Resoluções implementadas no Furious Multi Chat Pro:**
1. **Patch Nativo do Edge TTS**: O `utils/tts_engine.py` redireciona automaticamente o `WSS_URL` para o novo endpoint `api.msedgeservices.com` com `Ocp-Apim-Subscription-Key`, reativando **100% das vozes neurais (Antônio, Francisca e Thalita)** sem esperar nova release do PyPI.
2. **Google TTS como Contingência Permanente**: O motor `gtts` permanece ativo como alternativa selecionável na interface, garantindo redundância total caso haja qualquer instabilidade futura na infraestrutura da Microsoft.

---

## Dependências Necessárias

- **`edge-tts`**: Motor principal — vozes neurais Microsoft Azure gratuitas via browser spoofing.
- **`gtts`**: Motor alternativo — Google Translate TTS (voz pt-BR única, estável).
- **`pygame-ce`**: Reprodução de áudio via `pygame.mixer` com controle de volume independente.
- **`tempfile`**: Arquivos `.mp3` temporários criados e destruídos automaticamente.

---

## Arquitetura Interna do `TTSManager`

```
add_message(user, text, platform)
    → TextCleaner.clean()           # Remove HTML, links, emojis, spam
    → asyncio.run_coroutine_threadsafe(_download_and_queue)
        → lê config: tts_engine
        ├── "edge"   → _download_edge(text, voice)   # Motor Edge original
        └── "google" → executor(_download_gtts, text) # Motor Google (síncrono em thread)
    → queue.append(temp_mp3_path)
    → QTimer(300ms) → _check_queue() → pygame.mixer.Sound.play()
```

### Proteções Implementadas
- **Fila anti-raid**: Máximo 50 mensagens em fila + downloads protegidos por semáforo.
- **Mute instantâneo**: `Ctrl+M` limpa fila + para áudio atual.
- **Try-Catch total**: Qualquer falha de rede ou API é silenciada — o chat visual nunca é afetado.
- **Descarte on-mute**: Se o usuário mutar durante o download, o arquivo é descartado antes de entrar na fila.

---

## Interface de Configurações

Na aba **Voz do Bot (TTS)** em Configurações:

1. **Ativar Leitura de Chat (TTS)** — checkbox global
2. **Motor de Voz** — combo:
   - `Microsoft Edge (Neural)` → salva `tts_engine: "edge"`
   - `Google TTS (Alternativo)` → salva `tts_engine: "google"`
3. **Volume da Voz** — slider 0–100%
4. **Vozes por Plataforma** *(visível apenas no modo Edge)*:
   - Twitch → padrão: Antônio (Masculino)
   - TikTok → padrão: Francisca (Feminina)
   - Kick → padrão: Thalita (Feminina)
   - YouTube → padrão: Antônio (Masculino)

> **Nota**: No modo Google, as vozes por plataforma ficam ocultas automaticamente pois o gTTS usa uma única voz pt-BR.

---

## Funcionalidades de Inteligência (TextCleaner)

- **Filtro de Spam Dinâmico**: `kkkkkk` → `kkk`, `AAAAAAA` → `AAA`
- **Ignorar Links**: URLs → "link enviado"
- **Blacklist**: Palavras cadastradas nas configurações são removidas do áudio
- **Limite de 500 chars**: Segurança para mensagens excessivamente longas
- **Sanitização SSML**: `&` → ` e `, apóstrofos normalizados

---

## Plano de Execução — Status

### Fase 1: Fundação do Motor ✅ Concluída
- [x] `utils/tts_engine.py` criado
- [x] Download assíncrono com `tempfile`
- [x] Player via `pygame.mixer` com fallback para `pygame.music`

### Fase 2: Interface e Configurações ✅ Concluída
- [x] Seção "Voz do Bot (TTS)" nas configurações
- [x] Seletor de motor (Edge / Google) com show/hide dinâmico
- [x] Controle de volume e vozes por plataforma

### Fase 3: Inteligência e Robustez ✅ Concluída
- [x] `TextCleaner` com limpeza HTML, links, spam e blacklist
- [x] Hotkey `Ctrl+M` para mute/clear instantâneo
- [x] Motor Google TTS como fallback permanente (v4.1)

### Fase 4: Futura (opcional)
- [ ] SFX sonoros para presentes/eventos
- [ ] Leitura de boas-vindas ao entrar na live
- [ ] Suporte a múltiplos idiomas no motor Google

---

## Medidas de Estabilidade

> [!CAUTION]
> O motor de voz opera em modo Try-Catch total. Se qualquer áudio falhar ou a internet oscilar, o sistema pula para a próxima mensagem sem afetar o desempenho visual do chat.

> [!TIP]
> Se o motor Edge apresentar erro 403 (Microsoft atualizou servidores), trocar para **Google TTS** nas configurações resolve imediatamente sem reiniciar o bot.

---

**Versão Atual**: v4.1 (Dual Engine — Edge + Google)
**Última Atualização**: Outubro 2026
**Responsável**: FuriousOfNight / Agente de IA


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
