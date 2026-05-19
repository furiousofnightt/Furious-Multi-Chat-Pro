# Troubleshooting - Resolução de Problemas

## Índice
1. [Problemas de Conexão](#problemas-de-conexão)
2. [Problemas de Interface](#problemas-de-interface)
3. [Problemas de Chat/Mensagens](#problemas-de-chatmensagens)
4. [Problemas de Performance](#problemas-de-performance)
5. [Erros Específicos](#erros-específicos)

---

## Problemas de Conexão

### Nenhuma plataforma conecta

**Sintomas**: Todas as bolinhas de status ficam vermelhas.

**Diagnóstico**:
```bash
# Testar conexão com internet
ping google.com

# Verificar se é problema de DNS
nslookup tiktok.com
nslookup twitch.tv
```

**Soluções**:
1. Verificar conexão com internet
2. Desativar VPN/proxy temporariamente
3. Verificar firewall (permitir Python)
4. Testar um canal popular conhecido (ex: `xqc` na Twitch)

---

### Twitch: Conexão cai frequentemente

**Sintomas**: Bolinha alterna verde/vermelho, mensagens "Reconectando..."

**Causas comuns**:
- Canal IRC inativo (sem mensagens)
- Timeout de inatividade
- Instabilidade na rede

**Soluções**:
1. Normal — reconexão automática a cada 30s está funcionando
2. Verificar se canal existe e está digitado corretamente
3. Testar em canal mais ativo

**Logs esperados**:
```
⚠️ Conexão Twitch perdida (timeout). Reconectando em 30s...
✅ Conectado ao canal #xqc
```

---

### TikTok: "Rate Limit Ativado"

**Sintomas**: Mensagem de erro sobre limite de requisições.

**Causa**: Muitas tentativas de conexão em curto período.

**Solução**:
1. Aguarde **16-24 horas** sem tentar conectar
2. Verificar se username está correto antes de tentar
3. Evitar reconectar múltiplas vezes seguidas

**Prevenção**:
- Configure corretamente na primeira vez
- Não fique reconectando repetidamente para testar

---

### TikTok: Conecta mas não recebe mensagens

**Sintomas**: Bolinha verde, mas chat vazio mesmo com mensagens no app.

**Diagnóstico**:
1. Verificar se live está pública (não privada)
2. Confirmar se há pessoas mandando mensagens
3. Verificar logs — deve aparecer `[TikTok] Usuário: mensagem`

**Soluções**:
1. Verificar se username está correto (sem @)
2. Aguardar 10-20 segundos (demora para iniciar)
3. Tentar desconectar e reconectar

---

### Kick: Não conecta

**Sintomas**: Status permanece vermelho.

**Diagnóstico**:
```python
# Verificar se kickpython está instalado
pip list | grep kick
```

**Soluções**:
1. Verificar instalação: `pip install kickpython`
2. Confirmar nome do canal (sem https://)
3. Testar canal diferente

---

## Problemas de Interface

### Janela não aparece / Invisível

**Sintomas**: Programa executa mas não vê janela.

**Causas**:
- Opacidade 0%
- Janela fora da tela
- Click-through ativado

**Soluções**:
1. Pressionar **Ctrl+Shift+H** (toggle visibilidade)
2. Deletar `settings.json` para resetar posição/opacidade
3. Verificar se não está minimizado no tray

---

### Glassmorphism não funciona

**Sintomas**: Sem efeito de blur/vidro, apenas transparência simples.

**Causa**: Requer Windows 11 com compositor DWM ativo.

**Verificação**:
- Windows 10: Glassmorphism NÃO funciona
- Windows 11: Deve funcionar
- Tema clássico/básico: Pode não funcionar

**Soluções**:
1. Atualizar para Windows 11
2. Verificar se efeitos visuais estão ativados:
   ```
   Configurações → Sistema → Multitarefa → Efeitos visuais
   ```
3. Usar opacidade normal como fallback

---

### Fontes não carregam

**Sintomas**: Texto aparece em fonte padrão do sistema.

**Diagnóstico**:
Verificar logs ao iniciar:
```
✅ Fonte carregada: Inter.ttf (Inter, Inter Thin...)
❌ Falha ao carregar fonte: Nome.ttf
```

**Soluções**:
1. Verificar se pasta `assets/fonts/` existe
2. Confirmar que arquivos .ttf estão presentes
3. Verificar permissões de leitura

---

### Janela não fixa "Always on Top"

**Sintomas**: Outras janelas passam por cima.

**Soluções**:
1. Clicar no botão de alfinete (📌)
2. Ou usar menu de contexto → "Fixar no Topo"
3. Alguns jogos em fullscreen podem sobrepor (comportamento normal)

---

## Problemas de Chat/Mensagens

### Mensagens aparecem duplicadas

**Sintomas**: Mesma mensagem 2+ vezes.

**Causas**:
- Handler duplicado
- Reconexão sem limpar fila
- Bug específico de plataforma

**Soluções**:
1. Reiniciar programa completamente
2. Verificar se não há múltiplas instâncias rodando
3. Para TikTok: reiniciar conexão (limitação conhecida)

---

### Emotes aparecem como texto

**Sintomas**: `:)` ou `KEKW` aparecem em vez das imagens.

**Diagnóstico**:
1. Verificar conexão com internet
2. Verificar logs de download de emotes
3. Verificar se emote existe no cache

**Soluções**:
1. Aguardar download (pode demorar alguns segundos na primeira vez)
2. Verificar pasta temporária: `%TEMP%/furious_chat_emotes_*`
3. Para emotes de terceiros (7TV/BTTV): verificar se nome está correto

---

### Mensagens do TikTok faltando

**Sintomas**: Mensagens de usuários específicos nunca aparecem.

**Detalhes completos**: Ver `docs/TIKTOK-LIMITACOES.md`

**Resumo**:
- ~15% de mensagens podem ser perdidas
- Problema no servidor de proxy, não nosso código
- Não há solução imediata

**Workaround**:
- Aceitar limitação
- Informar viewers que chat pode ter delay/perda

---

### Filtro de blacklist não funciona

**Sintomas**: Palavras da lista aparecem sem censura.

**Verificação**:
1. Confirmar que palavra está na lista (Configurações)
2. Testar com palavra simples (ex: "teste")
3. Verificar case: filtro é case-insensitive

**Soluções**:
1. Recarregar configurações (reiniciar)
2. Verificar se não há espaços extras na palavra
3. Testar em plataforma diferente

---

### Notificações de entrada não aparecem

**Sintomas**: Usuários entram mas não vejo banner "X entrou na live!".

**Causas**:
- Evento de join não suportado na plataforma
- Fila de notificações travada
- Banner desabilitado (se houver opção)

**Soluções**:
1. Verificar se plataforma suporta eventos de join
2. Reiniciar programa
3. Verificar logs para `user_joined` signals

---

## Problemas de Performance

### Programa lento/travando

**Sintomas**: Interface congelando, delay nas mensagens.

**Diagnóstico**:
1. Verificar uso de CPU/RAM (Gerenciador de Tarefas)
2. Verificar se há muitas mensagens (flood)
3. Verificar se emotes estão carregando

**Soluções**:
1. Aumentar delay entre mensagens (Configurações)
2. Limpar chat periodicamente
3. Verificar se antivirus não está escaneando
4. Fechar outros programas pesados

---

### Consumo alto de RAM

**Sintomas**: Uso de memória crescendo indefinidamente.

**Causas**:
- Cache de emotes muito grande
- Fuga de memória em handlers
- Mensagens acumulando na UI

**Soluções**:
1. Limpar chat periodicamente (Ctrl+Shift+C)
2. Reiniciar programa a cada algumas horas
3. Verificar se pasta temporária de emotes está limpa

---

### CPU alto

**Sintomas**: Processo Python consumindo muita CPU.

**Causas**:
- Loop de reconexão rápida demais
- Processamento excessivo de mensagens
- Animações pesadas

**Soluções**:
1. Verificar logs de reconexão (deve ser a cada 30s, não mais rápido)
2. Desativar glassmorphism se não necessário
3. Reduzir taxa de atualização se houver

---

## Erros Específicos

### "Erro de Importação"

```
❌ Erro de Importação: No module named 'PyQt6'
```

**Solução**:
```bash
pip install -r requirements.txt
```

---

### "Erro de Conexão" genérico

```
⚠️ Erro ao parar handler tiktok: <erro>
```

**Normal**: Erros ao parar handlers são esperados durante shutdown.

**Preocupante**: Se ocorrer durante operação normal, verificar:
1. Conexão com internet
2. Status dos servidores das plataformas

---

### Crash ao iniciar

**Sintomas**: Programa fecha imediatamente, `crash_log.txt` criado.

**Soluções**:
1. Verificar `crash_log.txt` para stack trace
2. Deletar `settings.json` (pode estar corrompido)
3. Verificar se Python 3.12+ está instalado
4. Reinstalar dependências:
   ```bash
   pip install --force-reinstall -r requirements.txt
   ```

---

### "Settings.json corrompido"

**Sintomas**: Erro ao ler configurações, comportamento inesperado.

**Solução**:
```bash
# Deletar arquivo de settings
del settings.json

# Ou renomear para backup
ren settings.json settings.json.bak
```

O programa recriará com defaults na próxima execução.

---

## Debug Avançado

### Habilitar logs detalhados

Para investigar problemas, adicione prints nos handlers:

```python
# chat_handlers/tiktok_handler.py
print(f"[DEBUG] Evento recebido: {type(event).__name__}")
print(f"[DEBUG] Conteúdo: {getattr(event, 'content', 'N/A')}")
```

### Verificar arquivo de crash

```bash
# Conteúdo de crash_log.txt
type crash_log.txt
```

### Testar conectividade

```bash
# Testar IRC Twitch
telnet irc.chat.twitch.tv 6667

# Testar API TikTok
curl https://tiktok.eulerstream.com/webcast/fetch/?client=ttlive-python&room_id=123
```

---

## Recuperação

### Reset completo

Se tudo falhar:

1. Fechar programa
2. Deletar `settings.json`
3. Limpar pasta temporária: `%TEMP%/furious_chat_emotes_*`
4. Reiniciar computador
5. Executar novamente

---

## Reportar Problema

Se nenhuma solução funcionar:

1. **Coletar informações**:
   - Versão do Windows
   - Versão do Python: `python --version`
   - Logs do console (copiar do início ao erro)
   - Conteúdo de `crash_log.txt` (se existir)

2. **Descrever**:
   - Passos exatos para reproduzir
   - Comportamento esperado vs atual
   - Se é consistente ou intermitente

3. **Testes feitos**:
   - Lista de soluções tentadas
   - Resultado de cada uma

---

## Checklist de Verificação

Antes de reportar bug:

- [ ] Programa atualizado (última versão)
- [ ] Dependências instaladas corretamente
- [ ] Reiniciado após instalação
- [ ] Testado em canal diferente
- [ ] Verificado logs para erros específicos
- [ ] Testado com settings padrão (sem personalizações)
- [ ] Windows atualizado
- [ ] Sem outros programas interferindo (overlay, capture, etc)
