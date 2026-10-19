# FAQ - Perguntas Frequentes

## Geral

### O que é o Furious Multi Chat Pro?

Uma aplicação desktop para streamers que permite visualizar e exibir chat de múltiplas plataformas (Twitch, TikTok, Kick) em uma única interface flutuante e personalizável, com estatísticas em tempo real, bot de voz neural e proteção de dados.

### Quais plataformas são suportadas?

- **Twitch**: Via conexão IRC direta (anônima, sem precisar de conta)
- **TikTok**: Via biblioteca TikTokLive (WebSocket)
- **Kick**: Via biblioteca kickpython (WebSocket)

### É gratuito?

Sim, projeto de código aberto.

---

## Instalação

### Como instalar?

1. Ter Python 3.12+ instalado no sistema
2. Clonar/baixar o projeto
3. `pip install -r requirements.txt`
4. `python run.py`

Ou baixar o executável pronto disponível no site.

### Posso usar sem Python?

Sim. Ao baixar o executável (`.exe`) no site oficial, não é necessário ter Python instalado.

---

## Configuração

### Como configurar minhas contas?

1. Execute o programa
2. Clique no botão de engrenagem (⚙️)
3. Preencha os campos:
   - Twitch: nome do canal (ex: `alanzoka`)
   - TikTok: nome do usuário (ex: `virginia`)
   - Kick: nome do canal (ex: `xqc`)
4. Salve

### O arquivo settings.json é seguro?

**Quase tudo** no arquivo é seguro de compartilhar — apenas nomes de canais e preferências visuais. **Porém**, o campo `tiktok_session_id` é um token sensível de acesso à conta TikTok.

Para protegê-lo, o aplicativo usa **criptografia DPAPI do Windows**. O valor aparece como `"DPAPI:AQAAANCMnd8..."` no arquivo — isso significa que ele está criptografado e **só pode ser lido pelo usuário Windows que o gerou**. Nunca compartilhe o arquivo `settings.json` contendo um `tiktok_session_id`.

### Por que o tiktok_session_id aparece como "DPAPI:..."?

Isso é esperado e correto! É a criptografia automática do aplicativo protegendo seu token de sessão do TikTok. Se você abrir o `settings.json` e ver essa sequência, significa que está funcionando corretamente. Ver: [Segurança dos Dados](#segurança-dos-dados).

### Posso usar só uma plataforma?

Sim. Deixe os outros campos vazios nas configurações.

---

## Funcionalidades

### O que são os números no topo da janela?

A barra de estatísticas mostra, da esquerda para direita:

- 👁️ **Viewers Online** (olho azul): Espectadores ativos na live agora. Ao passar o mouse, mostra por plataforma.
- 👤 **Total de Views** (bonequinho azul): Total de visualizações acumuladas desde o início da live (somente TikTok).
- 🕐 **Uptime** (relógio): Tempo de transmissão em andamento.
- ❤️ **Curtidas** (coração): Total de curtidas acumuladas (somente TikTok).

### O que significa o tooltip de viewers mostrar "0" colorido vs "Offline"?

- **Número colorido** (ex: "16"): Plataforma conectada com espectadores.
- **"0" colorido**: Plataforma **conectada**, mas sem espectadores no momento.
- **"Offline" cinza**: Plataforma **desconectada** ou não configurada.

Isso evita confusão de achar que o app não conectou quando na verdade a live acabou de começar sem viewers ainda.

### O que é Glassmorphism?

Efeito visual de vidro fosco (blur + transparência). Disponível no Windows 11. Deixa a janela com aparência moderna e translúcida. No Windows 10, funciona apenas transparência básica.

### Como funciona o sistema de hotkeys?

Atalhos de teclado que funcionam mesmo quando o programa não está focado:
- **Ctrl+Shift+H**: Mostrar/Esconder janela
- **Ctrl+Shift+C**: Limpar chat
- **Ctrl+M**: Ativar/Desativar bot de voz (TTS)

### Posso mudar as hotkeys?

Sim. Vá em Configurações → Comportamento → Atalhos de Teclado.

### O que é o "Atraso para Leitura"?

Adiciona delay entre mensagens (em segundos). Útil se você quer ler cada mensagem sem pressa em chats movimentados.

### O que é a Blacklist?

Lista de palavras que serão censuradas no chat (substituídas por `*****`). Configure em Configurações → Comportamento. O filtro usa boundary regex — a palavra "anal" na blacklist NÃO censura a palavra "canal".

---

## Segurança dos Dados

### O que é o tiktok_session_id?

É um token de acesso à conta TikTok necessário para a live do TikTok ser capturada de forma confiável. Ele é obtido ao fazer login pelo próprio aplicativo (aba Configurações → TikTok).

### Alguém pode roubar minha sessão do TikTok se pegar meu settings.json?

**Não**, desde que esteja numa máquina diferente. O token é criptografado usando a **DPAPI (Data Protection API)** do Windows, vinculada ao usuário logado. Se o arquivo for copiado para outro computador (inclusive por vírus), o dado criptografado é inútil.

### O que acontece se eu mudar de computador?

O aplicativo não conseguirá descriptografar o token antigo (esse é o comportamento correto de segurança). Você precisará fazer o login novamente pelo aplicativo para gerar um novo token na nova máquina.

---

## Problemas Conhecidos

### Mensagens do TikTok não aparecem (usuários específicos)

**Causa**: Limitação do servidor de proxy usado pela biblioteca TikTokLive. Cerca de 10-15% dos usuários podem ter mensagens que não chegam ao aplicativo, mesmo estando visíveis no TikTok Live Studio.

**Solução**: Não há solução no momento. É uma limitação técnica documentada.

**Ver detalhes**: `docs/TIKTOK-LIMITACOES.md`

### Emotes não aparecem

**Possíveis causas**:
1. Sem conexão com internet (emotes são baixados em tempo real)
2. Emote específico não existe no cache de terceiros
3. Erro no download temporário

**Solução**: Verifique conexão. Emotes são baixados e cacheados automaticamente.

### Janela não fica transparente

**Causa**: No Windows 11 o desfoque Glassmorphism (Mica/Acrylic) é nativo. No Windows 10, você pode ativar o **Fundo Escuro Translúcido** e regular a **Opacidade do Fundo** de forma independente.

**Solução**: Abra as Configurações (ícone da engrenagem) e ajuste o controle deslizante de **Opacidade do Fundo** para o valor desejado (ex: 70%). Se estiver no Windows 10 e quiser desfoque acrílico, certifique-se de que a opção de transparência do Windows está ligada em *Configurações do Windows > Personalização > Cores*.

### Hotkeys não funcionam

**Possíveis causas**:
1. Outro programa usa a mesma combinação de teclas
2. Falta de permissões de administrador
3. Teclado com layout diferente

**Solução**: Tente outra combinação de teclas nas configurações.

### TikTok desconecta com "Rate Limit"

**Causa**: Muitas tentativas de conexão em curto período.

**Solução**: Aguarde 16-24 horas antes de tentar novamente.

---

## Uso

### Como usar como overlay no OBS?

1. Configure a janela para "Always on Top" (botão 📌)
2. Ajuste opacidade para ~85%
3. Posicione sobre o jogo/aplicação
4. Use "Window Capture" no OBS se quiser capturar só o chat

### Posso clicar através da janela?

Sim. Ative "Click-through" nas configurações. A janela ficará transparente a cliques do mouse.

### Como limpar o chat?

- Hotkey: **Ctrl+Shift+C**
- Comando: `/clear` (digitando no campo de texto do chat)
- Botão 🗑️ na barra de botões

---

## 👥 Espectadores Online (TikTok)

### Como funciona a aba de Espectadores Online?
O aplicativo possui uma visualização dedicada acessível pelo botão de alternância no header. Ela consulta a API oficial de audiência do TikTok a cada 4 segundos e exibe todos os usuários conectados na sua live com foto de perfil, nome, @username, pontuação de contribuição e numeração sequencial (#1 a #N). **Todos os dados são 100% em tempo real** — a aba não mantém cache, então ela sempre reflete o estado atual da live.

### Para que serve o botão "↺ Sincronizar"?
O botão força uma consulta imediata à API do TikTok fora do ciclo automático de 4 segundos. É útil quando:
- A aba ficou vazia após horas de live (o loop interno parou por queda momentânea de conexão WebSocket).
- Você quer confirmar quem está online agora antes de se despedir.

Após clicar, o botão fica desabilitado por 2,5 segundos para evitar excesso de requisições. O label ao lado mostra a hora da última atualização recebida.

### A aba ficou vazia no meio da live — o que fazer?
Clique em **↺ Sincronizar**. Isso força uma requisição fresca diretamente na API sem precisar fechar e reabrir o aplicativo. Se o problema persistir, a conexão WebSocket com o TikTok pode ter sido encerrada — nesse caso, reinicie a conexão nas Configurações (alterando e salvando o canal TikTok).

### Por que é necessário login no TikTok para ver os espectadores online?
A rota de audiência em tempo real (`/webcast/ranklist/online_audience/`) do TikTok é um endpoint restrito que exige um cookie de sessão válido (`sessionid`). Sem login, o app desativa o loop automaticamente para evitar bloqueios por taxa de requisições (429/403) e exibe um card orientando a fazer login nas Configurações.

### Por que o número de "Online" no topo pode ser maior do que a lista de perfis exibidos?
O contador "X online" representa o total absoluto de pessoas conectadas na sala do TikTok. A lista detalhada exibe os espectadores que estão navegando logados em suas contas do TikTok. Usuários anônimos (sem conta aberta no navegador/app ou navegando em modo privado) são contabilizados no total geral, mas não possuem perfil individual para ser listado.

### Como aumentar ou diminuir a fonte na lista de espectadores?
No topo da aba de espectadores, clique nos botões **A-** (diminui a fonte) e **A+** (aumenta a fonte). O ajuste é aplicado instantaneamente em todos os cards sem recarregar a lista.

---

## Técnico

### Por que mensagens do TikTok às vezes não aparecem?

A biblioteca TikTokLive depende de um servidor de proxy externo (`eulerstream.com`). Ver documentação completa em `docs/TIKTOK-LIMITACOES.md`.

### O programa coleta meus dados?

Não. Todas as conexões são diretas com as plataformas. Nenhum dado é enviado para servidores terceiros além das conexões necessárias com TikTok/Twitch/Kick e o servidor de proxy EulerStream (necessário para TikTok).

### Como reportar bugs?

1. Verifique `crash_log.txt` na pasta do programa
2. Anote os passos para reproduzir
3. Verifique se é um problema conhecido nesta FAQ
4. Descreva o comportamento esperado vs atual com logs do console

---

## Outros

### Posso mudar as cores das plataformas?

Sim. Configurações → Aparência → Cores das plataformas.

### Posso mudar a fonte?

Sim. Configurações → Aparência → Fonte do Chat.

### O programa fecha sozinho!

Verifique `crash_log.txt` na pasta do programa. Pode ser erro não tratado (ex: `settings.json` corrompido).

### Perdi minhas configurações!

Se o `settings.json` estiver corrompido, delete-o e o aplicativo recriará com valores padrão. Você precisará refazer a configuração.

### Posso usar em Linux/Mac?

Teoricamente sim (Python é multiplataforma), mas:
- Glassmorphism só funciona no Windows 11
- DPAPI (`win32crypt`) é exclusivo do Windows — a criptografia do session_id não funcionará
- Hotkeys globais podem variar
- Não testado ativamente
