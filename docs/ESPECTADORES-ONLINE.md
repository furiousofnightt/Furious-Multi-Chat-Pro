# Aba de Espectadores Online (TikTok) - Documentação Técnica

## 1. Visão Geral

A aba de **Espectadores Online** permite que o streamer visualize em tempo real a lista completa de todos os usuários logados presentes na transmissão do TikTok. O foco é permitir a leitura dos nomes para agradecimentos individuais durante ou no encerramento da live.

---

## 2. Arquitetura e Fluxo de Dados

```
[TikTok Webcast API]
         │  GET /webcast/ranklist/online_audience/ (a cada 4s)
         ▼
[TikTokHandler._sync_online_audience_loop] (Asyncio)
         │  viewers_list_updated.emit(viewers_list)
         ▼
[ChatWindow.update_tiktok_viewers] (Thread Principal Qt)
         │
         ▼
[OnlineViewersListWidget.set_viewers]
         ├── Atualização in-place se a lista não mudou de ordem (zero lag)
         └── Reconstrução dos cards se houve novos usuários ou reordenação
                 ▼
         [ViewerCardWidget] (Avatar + #Rank + Nickname + @username + Pontos)
```

---

## 3. Componentes da Interface

### 3.1. `OnlineViewersListWidget` (`ui/main_window.py`)
- Página gerenciada pelo `QStackedWidget` da janela principal (Index 1).
- Header contendo:
  - Botão de voltar ao chat.
  - Título com contador de espectadores (`X online (TikTok)`).
  - Botões de ajuste rápido de fonte (`A-` e `A+`).
- ScrollArea com renderização suave e transparente (efeito Glassmorphism).

### 3.2. `ViewerCardWidget` (`ui/main_window.py`)
- Card individual de espectador contendo:
  - **Badge de numeração**: `#1`, `#2`, `#N` para todos os usuários da lista (inclusive os com 0 pontos).
  - **Foto de perfil circular**: Download assíncrono com cache Base64 local.
  - **Nome e @username**: Formatados via RichText com suporte a escalonamento dinâmico.
  - **Badge de pontuação**: `X pts` estilizado com gradiente.

---

## 4. Controle Dinâmico de Fonte

A classe `ViewerCardWidget` possui a variável de controle `_font_size` (padrão: 15px).
- **Botão `A-`**: Reduz a fonte em 1px (mínimo de 10px).
- **Botão `A+`**: Aumenta a fonte em 1px (máximo de 24px).
- O método `OnlineViewersListWidget.adjust_font_size()` atualiza todos os cards instantaneamente sem recarregar a lista da API.

---

## 5. Proteções de Autenticação & Rate Limit

1. **Early-Exit sem `sessionid`**:
   - Se o usuário não tiver realizado login nas Configurações, o loop encerra imediatamente sem disparar nenhuma requisição HTTP.
   - Isso elimina riscos de banimento ou erro `HTTP 429` (Too Many Requests).
2. **Tratamento de Sessão Expirada (`401` / `403`)**:
   - Caso o token expire, o loop entra em pausa de 30 segundos entre verificações.
3. **Cards Informativos (Banners de Estado)**:
   - Sem Login: Banner orientando a fazer login nas Configurações, com botão de atalho `⚙ Abrir Configurações`.
   - Sem Canal: Banner indicando que nenhum canal TikTok foi configurado.
