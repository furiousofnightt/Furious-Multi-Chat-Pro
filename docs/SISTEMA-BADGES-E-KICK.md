# Sistema de Badges e Conexão em Tempo Real da Kick

Este documento detalha o funcionamento técnico da integração com a **Kick** e o **Sistema Unificado de Badges** em todas as plataformas suportadas pelo Furious Multi Chat Pro.

---

## 1. Recuperação e Nova Arquitetura do Chat da Kick

### O Problema Legado
Anteriormente, a conexão com o chat da Kick utilizava a biblioteca `kickpython`, que se conectava ao WebSocket do **Pusher** (`wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679`).
Recentemente, a Kick desativou permanentemente essa chave e cluster do Pusher, resultando em:
* Conexões sendo derrubadas instantaneamente pelo servidor (`WebSocket connection closed`).
* O aplicativo mostrava que o canal estava conectado e contava espectadores (porque viewers usam a API REST `/api/v2/channels/...`), mas **nenhuma mensagem de chat chegava**.

### A Nova Solução Oficial (Centrifugo)
Através de engenharia reversa do frontend moderno da Kick (Next.js/Turbopack), mapeamos a nova arquitetura oficial de mensageria em tempo real:
1. **Infraestrutura**: A Kick migrou para servidores **Centrifugo PRO** (`wss://realtime.us-west-2.platform.kick.com/connection/websocket`).
2. **Chat Público sem Login**: Para receber o chat público, não é necessário fazer login com conta nem utilizar tokens OAuth.
3. **Fluxo de Conexão**:
   * **Passo 1**: Requisição `GET https://kick.com/api/v2/channels/{username}` (usando `curl_cffi` com impersonate Chrome para contornar proteções Cloudflare) para obter o `chatroom_id` e a lista de `subscriber_badges`.
   * **Passo 2**: Requisição `POST https://web.kick.com/api/v1/realtime/auth/connection` com header `x-app-platform: web` e body `{"client_id": "<uuid>"}`. A Kick retorna um token JWT público de visitante (Guest Token).
   * **Passo 3**: Abertura de WebSocket direto em `wss://realtime.us-west-2.platform.kick.com/connection/websocket`.
   * **Passo 4**: Envio do handshake inicial Centrifugo:
     ```json
     {"id": 1, "connect": {"token": "<guest_jwt_token>"}}
     ```
   * **Passo 5**: Subscrição no canal do chatroom:
     ```json
     {"id": 2, "subscribe": {"channel": "chatrooms.<chatroom_id>.v2"}}
     ```
4. **Tratamento de Keep-Alive e Conexão Ininterrupta**:
   * O Centrifugo envia quadros de ping `{}` a cada 25 segundos. O cliente responde com `{}` (pong), mantendo o socket sempre ativo.
   * O Centrifugo suporta mensagens agrupadas em lote (NDJSON delimitado por `\n`), que são devidamente fatiadas e processadas.
   * **Renovação Proativa (`refresh`)**: O token JWT possui validade de 45 minutos (TTL de 2700s). Para evitar desconexões periódicas, uma rotina assíncrona executa 5 minutos antes da expiração (aos 40 minutos), gera um novo token e envia o comando nativo:
     ```json
     {"id": 999, "refresh": {"token": "<novo_token>"}}
     ```
     O Centrifugo prorroga a sessão sem fechar o WebSocket, garantindo uma conexão que roda por dias a fio sem piscar.

---

## 2. Sistema Unificado de Badges (`BadgeManager`)

O `BadgeManager` (`utils/badge_manager.py`) centraliza e padroniza a conversão de distintivos e insígnias de todas as redes em HTML limpo com imagens originais.

### 2.1. Badges da Kick

A Kick utiliza um modelo misto de insígnias:
1. **Badges Tradicionais (`identity.badges`)**:
   * **Inscritos do Canal (`subscriber`)**: Cada canal possui distintivos próprios para cada meta de meses (1 mês, 2 meses, 3 meses, 6 meses, 12 meses, etc.). Essas imagens são obtidas diretamente da API do canal (`subscriber_badges`) e baixadas localmente com cache inteligente. Se o canal não possuir emblemas próprios, o sistema utiliza o vetor oficial `kick_subscriber.svg`.
   * **Badges Globais / Staff / Moderação**: Extraímos os vetores SVG oficiais idênticos aos usados no site da Kick:
     * `kick_moderator.svg`: O clássico martelo ciano com gradiente e moldura arredondada da Kick.
     * `kick_vip.svg`: A coroa dourada/laranja VIP.
     * `kick_verified.svg`: Selo de verificado oficial.
     * `kick_broadcaster.svg`: Distintivo do criador/dono da transmissão.
     * `kick_founder.svg`, `kick_og.svg`, `kick_bot.svg`, `kick_staff.svg`, `kick_sub_gifter.svg`.
2. **Badges V2 (`identity.badges_v2`)**:
   * A Kick agora atribui insígnias com URLs diretas na CDN (`https://ext.cdn.kick.com/chat/badges/...`).
   * Inclui **Nível de Chat** (`level`, ex: nível 24, 33, 99) e distintivos especiais (`kick_founder22`, etc.), renderizados com qualidade total ao lado do nome do usuário.

---

### 2.2. Badges do TikTok

No TikTok, o sistema organiza os emblemas em duas seções: **Prefixos** (à esquerda do nome) e **Sufixos** (à direita do nome).

1. **Moderador do TikTok (Correção de Duplicação)**:
   * **Problema Anterior**: O evento transmitia a flag de moderador com o texto `"Moderator"`. O renderizador antigo criava uma *pill* azul com diamante e texto, outra *pill* cinza com texto, e no final ainda inseria um SVG de escudo, triplicando a badge na tela.
   * **Correção Atual**:
     * Moderador agora tem tratamento isolado: exibe **estritamente o ícone oficial do TikTok** (18x18), **sem texto** `"Moderator"` e sem formato de pílula esticada.
     * Controle anti-duplicação (`added_mod`): o ícone é desenhado apenas uma vez.
     * O fallback SVG local só entra em ação se a API do TikTok não enviar nenhum ícone oficial na lista de badges.
2. **Novo Doador / New Gifter (Correção de Duplicação)**:
   * **O Problema**: A API do TikTok Webcast transmite a insígnia de primeiro recarregamento (`FIRST_RECHARGE`, scene_val 2) em duas versões simultâneas na mesma mensagem: uma versão legada/compatibilidade (texto puro `"New gifter"` sem ícone nem cores) e uma versão estilizada moderna (`combine`, com ícone CDN de caixinha de presentes 🎁 e fundo cinza escuro). O renderizador acabava processando as duas entradas: a versão legada caía no fallback com diamante azul, enquanto a versão moderna gerava a caixinha cinza, duplicando a insígnia na tela.
   * **A Correção**:
     * Detecção dedicada para `FIRST_RECHARGE` / `"New gifter"` / `"Novo doador"`.
     * Padronização na pílula azul oficial com ícone de Diamante: `[💎 New gifter]`.
     * Trava anti-duplicação (`added_new_gifter` e `seen_texts`): a versão repetida (caixinha cinza) é sumariamente descartada.
3. **Pílulas Dinâmicas (Gifter / Nível e Fã-Clube)**:
   * **Nível de Doador (`pay_grade`)**: Renderiza a pílula colorida conforme o nível (azul, roxo, rosa, dourado) com o número exato do doador (ex: `▲ 3`).
   * **Fã-Clube (`fans_club`)**: Pílula marrom com ícone de coração e nome ou nível do fã-clube (ex: `EQPA`, `Lv.10`).
   * **Top Gifter Rank**: Exibido como sufixo à direita do nome (ex: `Nº 1`, `Nº 2`, `Nº 3`).

---

### 2.3. Badges da Twitch

1. **Catálogo Oficial GQL**:
   * O `BadgeManager` consulta a API GraphQL pública da Twitch (`https://gql.twitch.tv/gql`) para baixar o catálogo oficial de badges do streamer (incluindo todas as fases de assinante, badges VIP, moderador, fundador, etc.).
2. **Cache Local**:
   * Os ícones PNG originais de 18x18 da Twitch são cacheados localmente.
   * Caso a rede ainda não tenha concluído o download, SVGs locais funcionam como fallback instantâneo.

---

### 2.4. Badges do YouTube

1. **Membros do Canal (Sponsors)**:
   * O selo personalizado de membro configurado pelo canal no YouTube é extraído e renderizado na resolução nativa.
2. **Moderador e Streamer**:
   * Moderadores recebem a chave inglesa oficial.
   * Donos do canal recebem o ícone de streamer/owner.
