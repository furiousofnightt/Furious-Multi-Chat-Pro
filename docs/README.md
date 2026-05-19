# Documentação do Furious Multi Chat Pro

Esta pasta contém toda a documentação técnica e de usuário do projeto.

## 📚 Documentos Disponíveis

### Para Usuários Finais

| Documento | Descrição | Público |
|-----------|-----------|---------|
| [FAQ.md](FAQ.md) | Perguntas frequentes e dúvidas comuns | Usuários |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Guia de resolução de problemas | Usuários e Suporte |

### Para Desenvolvedores

| Documento | Descrição | Público |
|-----------|-----------|---------|
| [ARQUITETURA.md](ARQUITETURA.md) | Arquitetura do sistema, fluxos de dados, threading | Desenvolvedores |
| [API-REFERENCE.md](API-REFERENCE.md) | Referência completa de classes e métodos | Desenvolvedores |
| [GUIA-DESENVOLVIMENTO.md](GUIA-DESENVOLVIMENTO.md) | Como configurar ambiente, contribuir, adicionar features | Desenvolvedores |
| [TIKTOK-LIMITACOES.md](TIKTOK-LIMITACOES.md) | Documentação técnica detalhada sobre limitações do TikTok | Desenvolvedores e Usuários Avançados |

## 🗺️ Mapa de Documentação

### Quero usar o programa

1. Leia o [FAQ.md](FAQ.md) — respostas rápidas
2. Se tiver problemas, consulte [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Quero entender como funciona

1. Leia [ARQUITETURA.md](ARQUITETURA.md) — visão geral técnica
2. Consulte [API-REFERENCE.md](API-REFERENCE.md) — detalhes de implementação

### Quero contribuir/modificar

1. Leia [GUIA-DESENVOLVIMENTO.md](GUIA-DESENVOLVIMENTO.md) — setup do ambiente
2. Consulte [ARQUITETURA.md](ARQUITETURA.md) — entender a estrutura
3. Use [API-REFERENCE.md](API-REFERENCE.md) — referência de código

### Quero entender o problema do TikTok

1. Leia [TIKTOK-LIMITACOES.md](TIKTOK-LIMITACOES.md) — explicação completa

## 📖 Resumo por Tópico

### Conexões
- **Twitch**: IRC direto — ARQUITETURA.md seção "TwitchHandler"
- **TikTok**: WebSocket via proxy — TIKTOK-LIMITACOES.md
- **Kick**: WebSocket direto — ARQUITETURA.md seção "KickHandler"

### Interface
- **Glassmorphism**: FAQ.md, TROUBLESHOOTING.md
- **Hotkeys**: API-REFERENCE.md (HotkeyManager)
- **Emotes**: ARQUITETURA.md seção "Emoticons"

### Desenvolvimento
- **Adicionar plataforma**: GUIA-DESENVOLVIMENTO.md
- **Sinais PyQt6**: ARQUITETURA.md seção "Threading Model"
- **Build**: GUIA-DESENVOLVIMENTO.md seção "Build e Distribuição"

### Problemas
- **Mensagens faltando**: TIKTOK-LIMITACOES.md
- **Crashes**: TROUBLESHOOTING.md
- **Performance**: TROUBLESHOOTING.md seção "Problemas de Performance"

## 🔗 Documentos Relacionados

- [README principal](../README.md) — Visão geral do projeto
- [Planejamento do projeto](../planejamento_projeto.md) — Roadmap e funcionalidades planejadas
- [Sugestões de upgrade](../sugestoes_upgrade.md) — Ideias futuras

## 📝 Convenções

- Documentação técnica em Markdown (.md)
- Código inline com backticks: `ChatManager`
- Referências cruzadas com links relativos
- Emojis para categorização visual

## 🔄 Atualizações

Esta documentação deve ser mantida atualizada quando:
- Novas funcionalidades são adicionadas
- Arquitetura muda significativamente
- Bugs conhecidos são descobertos/documentados
- APIs de bibliotecas de terceiros mudam

---

Última atualização: Abril 2025
