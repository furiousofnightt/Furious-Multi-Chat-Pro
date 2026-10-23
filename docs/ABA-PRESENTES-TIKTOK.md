# Aba de Presentes da Live (TikTok) — Documentação Técnica

## 1. Visão Geral

A aba de **Presentes da Live** é uma página dedicada dentro do `QStackedWidget` da janela principal (Index 2). Ela registra e exibe todos os presentes (`GiftEvent`) recebidos durante uma transmissão do TikTok, organizados em ordem cronológica (mais antigos no topo, mais recentes embaixo), com scroll automático para o último.

O objetivo é resolver um problema prático: como o chat do TikTok sobe muito rápido durante lives movimentadas, era difícil visualizar presentes que foram enviados. A aba de presentes funciona como um histórico permanente da sessão.

---

## 2. Arquitetura e Fluxo de Dados

```
[TikTok GiftEvent — WebSocket via TikTokLive]
         |  event.streaking == False  (aguarda fim da rajada)
         v
[TikTokHandler.on_gift(event)] (Asyncio)
         |  message_received.emit(...)      -> Chat normal (texto)
         |  gift_received.emit(gift_data)   -> Aba de presentes (dict)
         v
[ChatManager — conectado via h.gift_received.connect(self.window.add_gift)]
         v
[ChatWindow.add_gift(gift_data)]
         |  Incrementa badge de notificacao se nao estiver na aba
         v
[LiveGiftsListWidget.add_gift(gift_data)]
         |  Remove placeholder se for o primeiro presente
         |  Cria LiveGiftCardWidget e adiciona ao final da lista
         |  Instala eventFilter e mouseTracking no novo card
         |  Auto-scroll para o ultimo presente apos 50ms
         v
[LiveGiftCardWidget] (Avatar + Nome + @arroba + "enviou X" + Icone + xN + tempo relativo)
```

### Estrutura do `gift_data` (dict emitido pelo sinal)

| Campo           | Tipo    | Descricao                                          |
|-----------------|---------|---------------------------------------------------|
| `user`          | `str`   | Nickname do usuario                                |
| `display_id`    | `str`   | @username do TikTok                               |
| `author_display`| `str`   | HTML com avatar + badges + nome (para o chat)      |
| `avatar_html`   | `str`   | HTML com imagem base64 do avatar                   |
| `prefix_badges` | `str`   | HTML com badges antes do nome (Mod, Top 1, etc.)   |
| `suffix_badges` | `str`   | HTML com badges apos o nome (Fa-Clube, etc.)       |
| `gift_name`     | `str`   | Nome do presente (ex: "Rose", "TikTok")            |
| `gift_count`    | `int`   | Quantidade enviada na rajada                        |
| `diamond_count` | `int`   | Valor em diamantes por unidade                     |
| `icon_html`     | `str`   | HTML com imagem base64 do icone do presente         |
| `platform`      | `str`   | Sempre "tiktok"                                   |
| `timestamp`     | `float` | time.time() no momento do evento                   |

---

## 3. Componentes da Interface

### 3.1. `LiveGiftCardWidget` (`ui/main_window.py`)

Card individual de presente. Altura fixa de 70px.

**Layout interno (horizontal):**
1. **Avatar circular** (36x36px): carregado do `avatar_html` base64 via `make_circular_pixmap_from_bytes()`. Fallback: inicial do nome em fundo dourado.
2. **Box de informacao** (coluna, expande):
   - `name_lbl`: Badges do usuario (`prefix_badges` e `suffix_badges`) + Nome (14px, branco, bold).
   - `handle_lbl`: `@arroba` (11px, branco `#ffffff`).
   - `desc_lbl`: "enviou **NomePresente**" (13px, dourado) + `💎 N` em negrito extra (13px, ciano `#00e6e6`, `font-weight: 900`, `Segoe UI Black`) se `diamond_count > 0`.
3. **Box direita** (coluna, alinhada a direita):
   - Icone do presente (24x24px): carregado do `icon_html` base64. Fallback: `gift_tab.svg`.
   - Badge `xN` com gradiente laranja -> dourado e numeros em bold extra (`font-weight: 900`, branco).
   - Label de tempo relativo: "agora mesmo", "ha X min", "ha Xh", "ha Xd".

**Cache de avatares:** `LiveGiftCardWidget._avatar_cache` e um dict de classe (compartilhado entre todos os cards) que mapeia `display_id -> QPixmap` circular. Evita reprocessamento de base64 para o mesmo usuario.

**Variavel de fonte:** `LiveGiftCardWidget._font_size = 14` (px) controla o nome do usuario.

#### Metodo `update_relative_time(lang="pt-br")`
Atualiza o label de tempo com base em `time.time() - self.timestamp`:

| Intervalo | Texto (pt-br)  |
|-----------|---------------|
| < 60s     | "agora mesmo" |
| 1-59 min  | "ha X min"    |
| 1-23h     | "ha Xh"       |
| >= 1 dia  | "ha Xd"       |

---

### 3.2. `LiveGiftsListWidget` (`ui/main_window.py`)

Pagina completa da aba de presentes (Index 2 do `QStackedWidget`).

**Elementos do header:**
- **Voltar**: emite `back_requested` -> volta para o chat (Index 0).
- **Limpar**: chama `clear_gifts()` manualmente.
- **Icone + contador**: exibe "X presentes recebidos" (ou 0).

**Scroll Area:** configurada com `setWidgetResizable(True)` e scrollbar vertical estilizada (cor dourada).

**Timer de tempos relativos:** `QTimer` de 30 segundos que chama `_refresh_relative_times()` -> itera por todos os `_cards` e chama `update_relative_time(lang)`.

**Alinhamento:** `AlignBottom` — quando ha poucos itens, ficam ancorados na parte inferior. Novos presentes sao adicionados ao final (`addWidget`) e o scroll vai automaticamente para baixo.

#### Sinais emitidos
| Sinal           | Quando                       |
|----------------|------------------------------|
| `back_requested` | Usuario clica em Voltar     |

#### Metodo `add_gift(gift_data)`
1. Se `_cards` estiver vazio, limpa o placeholder da lista.
2. Cria um `LiveGiftCardWidget`.
3. Instala `installEventFilter(chat_window)` e `setMouseTracking(True)` no card e em todos os seus filhos via `findChildren(QWidget)` — **essencial para o resize da janela funcionar sobre os cards**.
4. Adiciona ao final do layout e da lista `_cards`.
5. Remove o card mais antigo se `len(_cards) > 200`.
6. Apos 50ms, auto-scroll para o final via `QTimer.singleShot`.

#### Metodo `clear_gifts()`
Zera `_total_gifts_count`, limpa `_cards` e chama `show_empty_placeholder()`.

---

### 3.3. Botao da Header (`gifts_btn`) — `ChatWindow`

Botao de icone `gift_tab.svg` no header da janela principal, posicionado apos o botao de espectadores.

**Comportamento de notificacao:**
- Quando um presente e recebido e o usuario **nao** esta na aba de presentes, o botao recebe uma borda dourada (presentes nao lidos).
- Ao clicar no botao e entrar na aba, o badge e o estilo sao resetados (`_unread_gifts = 0`).

---

## 4. Sinal `gift_received` (`BaseChatHandler`)

Declarado em `chat_handlers/base_handler.py`:

```python
gift_received = pyqtSignal(dict)
# {user, display_id, author_display, avatar_html, prefix_badges, suffix_badges,
#  gift_name, gift_count, diamond_count, icon_html, platform, timestamp}
```

Emitido por `TikTokHandler.on_gift()` **apenas** quando `event.streaking == False` (fim de uma rajada de presentes). Presentes enviados em rajada rapida sao agrupados e exibidos como um unico evento com a contagem total (`gift_count`).

---

## 5. Conexao do Sinal no `ChatManager`

O sinal e conectado tanto no `start_all()` quanto no `restart_platform("tiktok")`:

```python
if hasattr(self.window, "add_gift"):
    h.gift_received.connect(self.window.add_gift)
```

**Motivo de estar em ambos os lugares:** `restart_platform` e chamado quando o usuario troca o canal TikTok nas configuracoes — sem a conexao la, presentes nao chegariam a aba apos um restart de plataforma.

---

## 6. Sessao e Reconexao

| Evento                              | Comportamento da aba                                               |
|-------------------------------------|--------------------------------------------------------------------|
| `start_all()` (nova sessao)         | `clear_gifts()` e chamado -> aba zerada                           |
| Reconexao automatica do WebSocket   | Presentes **mantidos** — `clear_gifts` so e chamado em `start_all`|
| `restart_platform("tiktok")`        | Aba **nao** e limpa — presentes da sessao anterior permanecem     |

---

## 7. Assets Criados

| Arquivo                   | Uso                                                              |
|--------------------------|------------------------------------------------------------------|
| `assets/gift_tab.svg`    | Icone do botao no header e fallback do icone do presente no card|
| `assets/gift_empty.svg`  | Imagem do placeholder quando nao ha presentes na aba            |
| `assets/gift_sparkle.svg`| Decorativo (disponivel para uso futuro)                         |

---

## 8. Traducoes (`utils/translations.py`)

Chaves adicionadas (PT-BR / EN):

| Chave                | PT-BR                        | EN                    |
|----------------------|-----------------------------|-----------------------|
| `tooltip_gifts_page` | "Presentes da Live"         | "Live Gifts"          |
| `btn_back_to_chat`   | "Voltar"                    | "Back"                |
| `btn_clear_gifts`    | "Limpar"                    | "Clear"               |
| `tooltip_clear_gifts`| "Limpar lista de presentes" | "Clear gifts list"    |
| `gifts_count_format` | "X presentes recebidos"     | "X gifts received"    |
| `gifts_empty`        | "Nenhum presente recebido ainda..." | "No gifts received yet..." |
| `gift_time_now`      | "agora mesmo"               | "just now"            |
| `gift_time_min`      | "ha X min"                  | "Xm ago"              |
| `gift_time_hour`     | "ha Xh"                     | "Xh ago"              |
| `gift_time_day`      | "ha Xd"                     | "Xd ago"              |

---

## 9. Resize da Janela na Aba de Presentes

O redimensionamento da janela funciona via `eventFilter` no `ChatWindow`. Para que funcione sobre todos os widgets filhos:

1. **`setMouseTracking(True)`** na `gifts_page` e seus filhos diretos (`scroll_area`, `viewport`, `list_container`).
2. **`installEventFilter(chat_window)`** nos mesmos widgets.
3. **Por card**: ao criar cada `LiveGiftCardWidget` em `add_gift()`, o codigo itera `card.findChildren(QWidget)` instalando mouseTracking e eventFilter em todos os filhos internos (labels, boxes). Necessario porque os cards cobrem toda a area de conteudo e bloqueiam os eventos de borda sem isso.

---

## 10. Diagnostico / Troubleshooting

| Sintoma                                        | Causa provavel                               | Solucao                                                          |
|------------------------------------------------|----------------------------------------------|------------------------------------------------------------------|
| Presentes no chat mas nao na aba               | `gift_received` nao conectado                | Verificar `chat_manager.py`: `start_all` e `restart_platform`   |
| Aba exibe presentes mas nao rola para o ultimo | Auto-scroll nao disparando                   | Verificar `QTimer.singleShot(50ms)` no `add_gift`               |
| Janela nao redimensiona sobre os cards         | Cards sem eventFilter                        | Verificar bloco `findChildren(QWidget)` no `add_gift`           |
| Tempo relativo nao atualiza                    | Timer de 30s nao iniciou                     | Verificar `self.time_update_timer.start(30000)` no `__init__`   |
| Presentes aparecem duplicados                  | `event.streaking` nao filtrado               | Verificar `if event.streaking: return` em `on_gift`             |
| Aba aparece vazia mesmo recebendo presentes    | `gifts_page` nao encontrado no ChatWindow    | Verificar atributo `self.gifts_page` apos `stacked_widget` init |
