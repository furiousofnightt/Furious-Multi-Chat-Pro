# Sistema de Tradução Centralizado
# Suporta múltiplos idiomas: português (pt-br) e inglês (en)

TRANSLATIONS = {
    "pt-br": {
        # Config Window
        "config_title": "Furious Config",
        "twitch_label": "Twitch @Username:",
        "tiktok_label": "TikTok @Username:",
        "kick_label": "Kick @Username:",
        "youtube_label": "YouTube @Username:",
        "glassmorphism_label": "Ativar Efeito Vidro Translúcido (Glassmorphism - Win11)",
        "opacity_label": "Opacidade da Janela:",
        "delay_label": "Atraso p/ Leitura (Lentidão das mensagens):",
        "language_label": "Idioma / Language:",
        "blacklist_label": "Palavras Bloqueadas (Digite e aperte Espaço/Enter):",
        "blacklist_placeholder": "Adicionar palavra...",
        "save_btn": "Salvar Configurações",
        "quit_btn": "Sair do Aplicativo Completamente",
        "confirm_quit_title": "Encerrar App",
        "confirm_quit_msg": "Deseja realmente encerrar o aplicativo e parar todos os chats?",
        
        # Appearance
        "appearance_section": "APARÊNCIA E ESTILO",
        "font_label": "Fonte do Chat:",
        "font_size_label": "Tamanho da Fonte:",
        "twitch_color_label": "Cor Twitch:",
        "tiktok_color_label": "Cor TikTok:",
        "kick_color_label": "Cor Kick:",
        "youtube_color_label": "Cor YouTube:",
        "pick_color": "Escolher Cor",
        
        # System Messages - Twitch
        "twitch_connect_attempt": "Sistema",
        "twitch_connected": "Conectado ao canal #{}",
        "twitch_disconnected": "Conexão Twitch perdida ({}). Reconectando em 30s...",
        "twitch_reconnect": "Reconectando em 30s...",
        
        # System Messages - TikTok
        "tiktok_connect_attempt": "Sistema",
        "tiktok_attempting": "Tentando conectar ao TikTok: {username}...",
        "tiktok_connected": "Conectado ao TikTok: {username}",
        "tiktok_disconnected": "Conexão com TikTok encerrada. Tentando reconectar...",
        "tiktok_error": "TikTok desconectado ({error}).",
        "tiktok_offline": "📴 TikTok: Canal '@{username}' está offline no momento. Parando reconexão.",
        "tiktok_not_found": "❌ TikTok: Usuário '@{username}' não encontrado ou nunca foi ao vivo. Verifique o nome digitado.",
        "tiktok_rate_limited": "⚠️ RATE LIMIT ATIVADO para {username}!\nLimite de requisições foi excedido.\nAguarde ~16-24 horas para tentar novamente.\nErro: {error}",
        
        
        # System Messages - Kick
        "kick_connect_attempt": "Sistema",
        "kick_connecting": "Conectando ao canal {}...",
        "kick_disconnected": "Conexão com Kick encerrada. Tentando reconectar em 30s...",
        "kick_error": "Erro no Kick: {}. Reconectando em 30s...",
        
        # Chat Actions - TikTok
        "gift_sent": "<img src='gift.svg' width='18' height='18'> enviou {} {}!",
        "gift_sent_multiple": "<img src='gift.svg' width='18' height='18'> enviou {} {} x{}!",
        "follow_started": "<img src='follow.svg' width='18' height='18'> começou a seguir!",
        "share_transmitted": "<img src='share.svg' width='18' height='18'> compartilhou a transmissão!",
        "user_joined": "{} entrou na live!",
        # Novos eventos: fã-clube, super fã, conquistas
        "fan_club_joined": "{} entrou para o Fã-clube! 🎉",
        "fan_club_months": "{} {} no Fã-clube! 🎂",
        "super_fan_became": "{} se tornou Super Fã! ⭐",
        "super_fan_joined": "{} (Super Fã) entrou na live! ⭐",

        # System Messages - General
        "system_label": "Sistema",
        "chat_cleared": "Chat limpo!",
        
        # Hotkeys
        "hotkeys_section": "Atalhos de Teclado (Hotkeys)",
        "hotkeys_hint": "Clique no campo e pressione a combinação. ESC cancela.",
        "hotkey_toggle": "Mostrar/Esconder Chat:",
        "hotkey_clear": "Limpar Chat:",
        "hotkey_clickthrough": "Modo Fantasma:",
        "info_toggle": "Oculta ou exibe a janela do chat na tela.",
        "info_clear": "Apaga todas as mensagens atuais do chat na sua tela.",
        "info_clickthrough": "Faz o chat ignorar o mouse, evitando cliques\nacidentais enquanto joga. Aperte novamente para desativar.",
    },
    "en": {
        # Config Window
        "config_title": "Furious Config",
        "twitch_label": "Twitch @Username:",
        "tiktok_label": "TikTok @Username:",
        "kick_label": "Kick @Username:",
        "youtube_label": "YouTube @Username/URL:",
        "glassmorphism_label": "Enable Glassmorphism Effect (Glassmorphism - Win11)",
        "opacity_label": "Window Opacity:",
        "delay_label": "Message Delay (Slowness):",
        "language_label": "Language / Idioma:",
        "blacklist_label": "Blocked Words (Type and press Space/Enter):",
        "blacklist_placeholder": "Add word...",
        "save_btn": "Save Settings",
        "quit_btn": "Quit Application Completely",
        "confirm_quit_title": "Quit App",
        "confirm_quit_msg": "Do you really want to quit the application and stop all chats?",
        
        # Appearance
        "appearance_section": "APPEARANCE & STYLE",
        "font_label": "Chat Font:",
        "font_size_label": "Font Size:",
        "twitch_color_label": "Twitch Color:",
        "tiktok_color_label": "TikTok Color:",
        "kick_color_label": "Kick Color:",
        "youtube_color_label": "YouTube Color:",
        "pick_color": "Pick Color",
        
        # System Messages - Twitch
        "twitch_connect_attempt": "System",
        "twitch_connected": "Connected to channel #{}",
        "twitch_disconnected": "Twitch connection lost ({}). Reconnecting in 30s...",
        "twitch_reconnect": "Reconnecting in 30s...",
        
        # System Messages - TikTok
        "tiktok_connect_attempt": "System",
        "tiktok_attempting": "Attempting to connect to TikTok: {username}...",
        "tiktok_connected": "Connected to TikTok: {username}",
        "tiktok_disconnected": "TikTok connection closed. Attempting to reconnect...",
        "tiktok_error": "TikTok disconnected ({error}).",
        "tiktok_offline": "📴 TikTok: Channel '@{username}' is currently offline. Stopping reconnection.",
        "tiktok_not_found": "❌ TikTok: User '@{username}' was not found or has never gone live. Please check the username.",
        "tiktok_rate_limited": "⚠️ RATE LIMIT ACTIVATED for {username}!\nRequest limit exceeded.\nWait ~16-24 hours to try again.\nError: {error}",
        
        
        # System Messages - Kick
        "kick_connect_attempt": "System",
        "kick_connecting": "Connecting to channel {}...",
        "kick_disconnected": "Kick connection closed. Trying to reconnect in 30s...",
        "kick_error": "Kick error: {}. Reconnecting in 30s...",
        
        # Chat Actions - TikTok
        "gift_sent": "<img src='gift.svg' width='18' height='18'> sent {} {}!",
        "gift_sent_multiple": "<img src='gift.svg' width='18' height='18'> sent {} {} x{}!",
        "follow_started": "<img src='follow.svg' width='18' height='18'> followed!",
        "share_transmitted": "<img src='share.svg' width='18' height='18'> shared the stream!",
        "user_joined": "{} joined the live!",
        # New events: fan club, super fan, achievements
        "fan_club_joined": "{} joined the Fan Club! 🎉",
        "fan_club_months": "{} {} in the Fan Club! 🎂",
        "super_fan_became": "{} became a Super Fan! ⭐",
        "super_fan_joined": "{} (Super Fan) joined the live! ⭐",

        # System Messages - General
        "system_label": "System",
        "chat_cleared": "Chat cleared!",
        
        # Hotkeys
        "hotkeys_section": "Keyboard Shortcuts (Hotkeys)",
        "hotkeys_hint": "Click the field and press the combo. ESC cancels.",
        "hotkey_toggle": "Show/Hide Chat:",
        "hotkey_clear": "Clear Chat:",
        "hotkey_clickthrough": "Ghost Mode:",
        "info_toggle": "Hides or shows the chat window on the screen.",
        "info_clear": "Clears all current messages from the chat on your screen.",
        "info_clickthrough": "Makes the chat ignore the mouse, preventing accidental\nclicks while playing. Press the shortcut again to disable.",
    }
}

def get_translation(key, language="pt-br", *args, **kwargs):
    """
    Obtém uma string traduzida.
    
    Args:
        key (str): Chave da tradução
        language (str): Idioma (pt-br ou en)
        *args: Argumentos posicionais para formatação
        **kwargs: Argumentos nomeados para formatação
        
    Returns:
        str: String traduzida e formatada
    """
    # Validar idioma
    if language not in TRANSLATIONS:
        language = "pt-br"
    
    # Obter tradução
    translation = TRANSLATIONS[language].get(key, key)
    
    # Formatar se há argumentos
    try:
        if args:
            return translation.format(*args)
        elif kwargs:
            return translation.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        # Se falhar na formatação, retorna a string sem formatação
        pass
    
    return translation

def set_ui_language(window, settings_manager):
    """
    Aplica o idioma salvo à interface do window.
    
    Args:
        window: QWidget ou QDialog
        settings_manager: SettingsManager instance
    """
    lang = settings_manager.settings.get("language", "pt-br")
    # Esta função será customizada por cada janela conforme necessário
    pass

def get_available_languages():
    """Retorna lista de idiomas disponíveis"""
    return list(TRANSLATIONS.keys())

def get_language_display_name(lang_code):
    """Retorna nome de exibição do idioma"""
    names = {
        "pt-br": "Português (Brasil)",
        "en": "English"
    }
    return names.get(lang_code, lang_code)
