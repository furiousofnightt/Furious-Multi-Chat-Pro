# Guia de Desenvolvimento

## Configuração do Ambiente

### 1. Instalação do Python

Requer Python 3.12 ou superior.

### 2. Criar Virtual Environment (Recomendado)

```bash
cd chat-geral-ttk-twitch-kick
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Testar Instalação

```bash
python run.py
```

## Estrutura de Desenvolvimento

### Fluxo de Trabalho

1. **Fazer alterações** nos arquivos Python
2. **Testar** executando `python run.py`
3. **Verificar logs** no console
4. **Build** (se necessário): `python build.py`

### Pastas Importantes

```
chat-geral-ttk-twitch-kick/
├── chat_handlers/      # Adicionar novas plataformas aqui
├── core/              # Lógica de negócio central
├── ui/                # Interfaces PyQt6
├── utils/             # Funções auxiliares
├── assets/            # Recursos (ícones, fontes)
└── docs/              # Documentação
```

## Adicionando uma Nova Plataforma

### Passo 1: Criar Handler

Criar arquivo em `chat_handlers/`:

```python
# chat_handlers/newplatform_handler.py
from .base_handler import BaseChatHandler

class NewPlatformHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "newplatform"
    
    def start(self):
        self.is_running = True
        # Implementar lógica
        pass
    
    def stop(self):
        self.is_running = False
        pass
```

### Passo 2: Adicionar ao ChatManager

Editar `core/chat_manager.py`:

```python
from chat_handlers.newplatform_handler import NewPlatformHandler

# Em start_all():
if self.settings.settings.get("newplatform"):
    h = NewPlatformHandler(self.settings.settings["newplatform"])
    h.set_language(lang)
    h.message_received.connect(self.on_message_received)
    h.start()
    self.handlers.append(h)
```

### Passo 3: Adicionar UI

Editar `ui/config_window.py` para adicionar campo de input.

### Passo 4: Adicionar Traduções

Editar `utils/translations.py`:

```python
"pt-br": {
    "newplatform_connect_attempt": "Sistema",
    "newplatform_connected": "Conectado à NewPlatform: {}",
    # ...
}
```

## Convenções de Código

### Estilo

- **PEP 8** para Python
- **Docstrings** em métodos públicos
- **Type hints** quando apropriado

### Sinais PyQt6

Sempre usar `pyqtSignal` para comunicação entre threads:

```python
class MyHandler(BaseChatHandler):
    message_received = pyqtSignal(str, str, str)  # (user, text, platform)
    
    def some_method(self):
        # Thread segura
        self.message_received.emit("user", "msg", "platform")
```

### Tratamento de Erros

```python
try:
    # Código que pode falhar
    pass
except SpecificException as e:
    print(f"⚠️ Erro específico: {e}")
except Exception as e:
    print(f"💥 Erro inesperado: {e}")
```

### Logging

Usar prints para debug (console):

```python
print(f"✅ Sucesso: {mensagem}")
print(f"⚠️ Aviso: {mensagem}")
print(f"❌ Erro: {mensagem}")
print(f"💥 Erro crítico: {mensagem}")
```

## Debugging

### Logs Importantes

Execute com redirecionamento para salvar logs:

```bash
python run.py > app_log.txt 2>&1
```

### Erros Comuns

#### `ImportError: No module named 'PyQt6'`
```bash
pip install PyQt6
```

#### `KeyError: 'twitch'`
Settings não carregou corretamente. Deletar `settings.json` para recriar.

#### Conexão TikTok sempre falha
Verificar se `tiktok.eulerstream.com` está acessível:
```bash
ping tiktok.eulerstream.com
```

### Debug de Mensagens

Habilitar debug no handler:

```python
# Em tiktok_handler.py
print(f"[DEBUG] Evento recebido: {event}")
```

## Build e Distribuição

### Criar Executável

```bash
python build.py
```

Ou manualmente:

```bash
pyinstaller FuriousMultiChatPro.spec
```

Output em `dist/FuriousMultiChatPro/`

### Arquivos Necessários para Distribuição

- `FuriousMultiChatPro.exe`
- `assets/` (com fontes e ícones)
- `settings.json` (opcional, será criado)

## Testes

### Testes Manuais

1. **Conexão**: Verificar se todas as plataformas conectam
2. **Mensagens**: Enviar mensagens em cada plataforma
3. **Emotes**: Testar emotes de diferentes fontes
4. **Hotkeys**: Verificar atalhos globais
5. **Configurações**: Salvar/recarregar settings
6. **Reconexão**: Desconectar e reconectar manualmente

### Checklist de Release

- [ ] Testar em Windows 10 e 11
- [ ] Verificar glassmorphism (se Win11)
- [ ] Testar todas as plataformas
- [ ] Verificar tamanho do build
- [ ] Testar instalador (se houver)

## Contribuição

### Processo

1. Criar branch para feature: `git checkout -b feature/nova-funcionalidade`
2. Fazer commits com mensagens claras
3. Testar exaustivamente
4. Documentar no README/docs

### Padrões de Commit

```
feat: Adicionar suporte a nova plataforma X
fix: Corrigir reconexão automática do Twitch
docs: Atualizar documentação de arquitetura
refactor: Melhorar performance do ChatManager
```

## Recursos Úteis

### Documentação PyQt6
- https://doc.qt.io/qtforpython-6/

### Bibliotecas de Terceiros
- TikTokLive: https://github.com/isaackogan/TikTokLive
- kickpython: (verificar documentação)

### Comunidades
- Discord de desenvolvedores do projeto
- Issues no GitHub

## Dúvidas Frequentes (Dev)

### Como funciona o sistema de emotes?

1. Emotes externos são baixados via HTTP
2. Salvos em pasta temporária local
3. Convertidos para URL `file:///`
4. Exibidos via HTML `<img>` no QLabel

### Por que usar thread separada para TikTok/Kick?

Ambos usam `asyncio`. PyQt6 tem seu próprio event loop. A solução é criar uma thread dedicada com event loop asyncio separado.

### Como adicionar suporte a mais idiomas?

1. Adicionar traduções em `utils/translations.py`
2. Adicionar opção no `ConfigWindow`
3. Usar `get_translation(key, lang)` em toda UI

### Posso usar PyQt5 em vez de PyQt6?

Não recomendado. PyQt6 tem melhor suporte a DPI alto, glassmorphism, e é o futor do projeto.
