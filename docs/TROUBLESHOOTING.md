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
ping google.com
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

**Causas comuns**: Canal IRC inativo, timeout de inatividade, instabilidade na rede

**Soluções**:
- Normal — reconexão automática a cada 30s está funcionando
- Verificar se canal existe e está digitado corretamente (sem `#`)
- Testar em canal mais ativo

**Logs esperados**:
```
⚠️ Conexão Twitch perdida (timeout). Reconectando em 30s...
✅ Conectado ao canal #xqc
```

---

### TikTok: "Rate Limit Ativado"

**Causa**: Muitas tentativas de conexão em curto período.

**Solução**: Aguarde **16-24 horas** sem tentar conectar.

**Prevenção**: Configure corretamente na primeira vez; evite reconectar repetidamente para testar.

---

### TikTok: Conecta mas não recebe mensagens

**Sintomas**: Bolinha verde, mas chat vazio mesmo com mensagens no app.

**Diagnóstico**:
1. Verificar se live está pública
2. Confirmar se há pessoas mandando mensagens
3. Verificar logs — deve aparecer `[TikTok] Usuário: mensagem`

**Soluções**:
1. Verificar se username está correto (sem `@`)
2. Aguardar 10-20 segundos (demora para iniciar)
3. Tentar desconectar e reconectar

---

### Kick: Não conecta

**Soluções**:
1. Verificar instalação: `pip install kickpython`
2. Confirmar nome do canal (sem `https://`)
3. Testar canal diferente

---

### YouTube: Chat conecta, mas visualizações ficam presas em 0

**Causas comuns**:
O YouTube muda regularmente a maneira como exibe o número de visualizações na tela, o que faz a captura das visualizações via HTML ser frágil. 

**Solução (Interna)**:
A aplicação agora possui 3 métodos diferentes para tentar extrair e exibir os viewers: `runs`, `simpleText` ou `concurrentViewers`. Caso o app pare de contar os views permanentemente, significa que o YouTube alterou todo o HTML estrutural. Neste caso, o desenvolvedor precisa analisar o source da página e adaptar o `youtube_handler.py`.

---

---

### Janela não aparece / Invisível

**Causas**: Opacidade 0%, janela fora da tela, click-through ativado

**Soluções**:
1. Pressionar **Ctrl+Shift+H** (toggle visibilidade)
2. Deletar `settings.json` para resetar posição/opacidade
3. Verificar se não está minimizado no tray (ícone na barra do sistema)

---

### Viewers continuam na tela após desconectar a plataforma (Viewers Fantasmas)

**Causa (Resolvida)**:
Anteriormente, o reset granular dos chats na página de configurações não estava resetando a última contagem enviada pela plataforma. Se o YouTube ou Kick era desabilitado nas configurações, a contagem na tela não baixava para 0.

**Solução**: 
Esta questão foi consertada a nível de código no `chat_manager.py` durante o fechamento dinâmico (no método `restart_platform()`). Agora, remover o nome e clicar em salvar zera obrigatoriamente os viewers dessa plataforma para evitar vestígios.

---

### Glassmorphism não funciona

**Causa**: Requer Windows 11 com compositor DWM ativo.

- Windows 10: Glassmorphism **não funciona**
- Windows 11: Deve funcionar normalmente

**Soluções**:
1. Atualizar para Windows 11
2. Verificar se efeitos visuais estão ativados em Configurações do Windows
3. Usar opacidade normal como fallback

---

### Fontes não carregam

**Diagnóstico** — Verificar logs ao iniciar:
```
✅ Fonte carregada: Inter.ttf (Inter, Inter Thin...)
❌ Falha ao carregar fonte: Nome.ttf
```

**Soluções**:
1. Verificar se pasta `assets/fonts/` existe com os arquivos `.ttf`
2. Verificar permissões de leitura da pasta

---

### Erro "PyQt6-WebEngine não está instalado"

**Causa**: Este erro aparece quando `QWebEngineWidgets` é importado **depois** que o `QApplication` já foi criado. Não é falta de instalação.

**Verificação**:
```bash
py -m pip show PyQt6-WebEngine
```

**Solução** (para desenvolvedores): Garantir que `main.py` importa `QWebEngineView` **antes** de criar `QApplication`:
```python
from PyQt6.QtWidgets import QApplication
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # ANTES do QApplication!
except ImportError:
    pass
app = QApplication(sys.argv)  # Agora pode criar
```

---

## Problemas de Chat/Mensagens

### Mensagens aparecem duplicadas

**Causas**: Handler duplicado, reconexão sem limpar fila

**Soluções**:
1. Reiniciar programa completamente
2. Verificar se não há múltiplas instâncias rodando

---

### Emotes aparecem como texto

**Soluções**:
1. Aguardar download (pode demorar alguns segundos na primeira vez)
2. Verificar pasta temporária: `%TEMP%\furious_chat_emotes_*`
3. Para emotes de terceiros (7TV/BTTV): verificar se nome está correto

---

### Mensagens do TikTok faltando

Ver detalhes em `docs/TIKTOK-LIMITACOES.md`

**Resumo**: ~10-15% de mensagens podem ser perdidas. Problema no servidor de proxy externo (EulerStream), não no código da aplicação.

---

### Filtro de blacklist não funciona

**Verificação**:
1. Confirmar que palavra está na lista (Configurações)
2. O filtro é case-insensitive mas respeita boundary de palavras (não censura substrings)

**Soluções**:
1. Recarregar configurações (reiniciar)
2. Verificar se não há espaços extras na palavra cadastrada

---

## Problemas de Performance

### Programa lento/travando

**Soluções**:
1. Aumentar delay entre mensagens (Configurações)
2. Limpar chat periodicamente (Ctrl+Shift+C)
3. Verificar se antivírus não está escaneando a pasta do app
4. Fechar outros programas pesados

---

### Consumo alto de RAM

**Causas**: Cache de emotes muito grande, mensagens acumulando na UI

**Soluções**:
1. Limpar chat periodicamente (Ctrl+Shift+C)
2. Reiniciar programa a cada algumas horas em sessões longas

---

## Erros Específicos

### `ImportError: No module named 'PyQt6'`
```bash
py -m pip install -r requirements.txt
```

---

### `win32crypt` não encontrado no executável

**Causa**: Compilado sem `--hidden-import=win32crypt`

**Solução**: Usar o `build.py` do projeto que já inclui essa flag. Não compilar manualmente sem verificar as flags.

---

### `tiktok_session_id` retorna vazio / erro ao descriptografar

**Causa**: O token foi gerado em outra máquina ou conta Windows diferente.

**Solução**: No aplicativo, ir em Configurações → TikTok → fazer login novamente para gerar um novo token nesta máquina.

---

### Crash ao iniciar

**Soluções**:
1. Verificar `crash_log.txt` para stack trace
2. Deletar `settings.json` (pode estar corrompido)
3. Verificar se Python 3.12+ está instalado
4. Reinstalar dependências:
   ```bash
   py -m pip install --force-reinstall -r requirements.txt
   ```

---

### `settings.json` corrompido

**Solução**:
```powershell
# Deletar arquivo de settings
del settings.json

# Ou renomear para backup
ren settings.json settings.json.bak
```

O programa recriará com defaults na próxima execução.

---

## Debug Avançado

### Habilitar logs detalhados

```python
# chat_handlers/tiktok_handler.py
print(f"[DEBUG] Evento recebido: {type(event).__name__}")
print(f"[DEBUG] Conteúdo: {getattr(event, 'content', 'N/A')}")
```

### Verificar arquivo de crash

```bash
type crash_log.txt
```

### Salvar todos os logs em arquivo

```bash
py run.py > app_log.txt 2>&1
```

---

## Recuperação

### Reset completo

Se tudo falhar:

1. Fechar programa
2. Deletar `settings.json`
3. Limpar pasta temporária: `%TEMP%\furious_chat_emotes_*`
4. Reiniciar computador
5. Executar novamente

---

## Reportar Problema

Se nenhuma solução funcionar:

1. **Coletar informações**:
   - Versão do Windows
   - Versão do Python: `py --version`
   - Logs do console
   - Conteúdo de `crash_log.txt` (se existir)

2. **Descrever**:
   - Passos exatos para reproduzir
   - Comportamento esperado vs atual
   - Se é consistente ou intermitente

---

## Checklist de Verificação

Antes de reportar bug:

- [ ] Programa na versão mais recente
- [ ] Dependências instaladas (`py -m pip install -r requirements.txt`)
- [ ] Reiniciado após instalação
- [ ] Testado em canal diferente
- [ ] Verificado logs para erros específicos
- [ ] Testado com `settings.json` padrão (deletar e recriar)
- [ ] Windows atualizado
- [ ] Sem outros programas interferindo (overlay, capture, etc.)
