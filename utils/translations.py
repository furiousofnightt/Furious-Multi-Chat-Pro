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
        "glassmorphism_label": "Efeito Vidro / Blur Nativo (Glassmorphism - Win 11 / Win 10)",
        "bg_opacity_label": "Opacidade do Fundo (Fundo Escuro Translúcido):",
        "text_opacity_label": "Opacidade do Texto / Mensagens do Chat:",
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

        # Sections
        "connections_section": "Conexões",
        "general_section": "Geral",
        "tts_section": "Voz do Bot (TTS)",

        # Tooltips & Hints - Config Window
        "glassmorphism_tooltip": "Ativa desfoque nativo (Mica/Acrylic no Win 11 ou Acrylic escuro no Win 10)",
        "reconnect_tooltip": "Reconectar {label}",
        "hotkey_press_keys": "Clique e pressione as teclas...",
        "hotkey_capturing": "⏳ Pressione as teclas...",
        "placeholder_username": "SeuArrobaAqui (sem @)",

        # TTS (Text-to-Speech)
        "tts_enable_label": "Ativar Leitura de Chat (TTS)",
        "tts_engine_label": "Motor de Voz:",
        "tts_engine_edge": "Microsoft Edge (Neural)",
        "tts_engine_google": "Google TTS (Alternativo)",
        "google_tts_info": "Google: voz única (pt-BR), ignora seleção de voz por plataforma",
        "tts_volume_label": "Volume da Voz",
        "voice_antonio": "Antônio (Masculino)",
        "voice_francisca": "Francisca (Feminina)",
        "voice_thalita": "Thalita (Feminina)",

        # TikTok Login
        "tiktok_connected_status": "TikTok: Conectado",
        "tiktok_not_connected_status": "TikTok: Não conectado",
        "tiktok_login_btn": "Fazer Login no TikTok",
        "tiktok_connected_btn": "Conectado",
        "tiktok_disconnect_title": "Desconectar do TikTok?",
        "tiktok_disconnect_msg": "Você já está conectado.\n\nDeseja remover a conta e desconectar?\n(Lives +18 perderão o horário real)",
        "tiktok_why_login_title": "Por que fazer login no TikTok?",
        "tiktok_why_login_text": (
            "<b>O login no TikTok é opcional.</b><br><br>"
            "<b>🕐 Cronômetro preciso:</b> Necessário para o relógio mostrar o tempo total da live "
            "em transmissões com restrição de idade (+18) ou caso você conecte atrasado. "
            "Sem o login, o relógio começa sempre do <b>00:00:00</b> no momento em que você conectar.<br><br>"
            "<b>👥 Aba de Espectadores Online:</b> Com o login ativo, uma aba dedicada exibe "
            "em tempo real <b>todos os usuários presentes na sua live</b> — com foto de perfil, "
            "nome, @username e pontos de contribuição. "
            "Ideal para agradecer a todos no encerramento da live lendo os nomes.<br><br>"
            "<b>Recomendado:</b> use uma conta secundária do TikTok para login, nunca a conta principal.<br><br>"
            "<i>🔒 <b>Sua Privacidade:</b> Não salvamos sua senha. Os dados de login ficam apenas neste computador, em um arquivo local criptografado pelo próprio windows.</i>"
        ),
        "continue_btn": "Continuar",
        "cancel_btn": "Cancelar",
        "tiktok_login_success": "Login no TikTok realizado com sucesso!\nSuas lives +18 agora vão mostrar o horário real.",
        "tiktok_login_error_webengine": "PyQt6-WebEngine não está instalado.\nInstale com: pip install PyQt6-WebEngine\n\n{error}",

        # Main Window - Header & Tooltips
        "tooltip_views_primary": "Views (Baseado na plataforma primária)",
        "tooltip_total_views_ttk": "Total de Views Acumulados (TikTok)",
        "tooltip_uptime": "Tempo de Live",
        "tooltip_likes": "Total de curtidas (Corações)",
        "tooltip_viewers_page": "Ver Espectadores Online (TikTok)",
        "tooltip_chat_page": "Voltar ao Chat",
        "tooltip_settings": "Configurações (Ctrl+Alt+S)",
        "tooltip_pin": "Fixar janela por cima",
        "tooltip_pinned": "Janela TRAVADA (Não move) 📌",
        "tooltip_unpinned": "Janela DESTRAVADA",
        "tooltip_close": "Sair do Aplicativo Completamente",
        "bot_voice_status": "🔊 Voz do Bot {status}!",
        "bot_voice_enabled": "Ativada",
        "bot_voice_disabled": "Desativada",
        "ghost_mode_status": "Modo Fantasma {status}!",
        "ghost_mode_enabled": "Ativado (Mouse ignora o chat)",
        "ghost_mode_disabled": "Desativado (Mouse interage com o chat)",

        # Main Window - Online Viewers Page
        "btn_back_to_chat": " Voltar ao Chat",
        "btn_sync": " Sincronizar",
        "btn_syncing": " Sincronizando...",
        "tooltip_sync_viewers": "Sincronizar espectadores online da live agora",
        "tooltip_font_decrease": "Diminuir tamanho da fonte dos usuários",
        "tooltip_font_increase": "Aumentar tamanho da fonte dos usuários",
        "viewers_online_format": "{count} online (TikTok)",
        "viewers_empty": "Nenhum espectador na lista no momento.\nOs usuários aparecerão aqui durante a live.",
        "tiktok_not_configured_title": "TikTok não configurado",
        "tiktok_not_configured_desc": "Nenhum canal TikTok está configurado.\n\nAbra as Configurações e insira o\n@username do canal para conectar.",
        "tiktok_not_configured_hint": "Configurações → campo TikTok → @username",
        "tiktok_login_required_title": "Login TikTok necessário",
        "tiktok_login_required_desc": "A aba de espectadores online mostra\ntodos os usuários presentes na sua live.\n\nPara acessar, faça login com qualquer\nconta TikTok nas Configurações.",
        "tiktok_login_required_hint": "Configurações → aba TikTok → Fazer Login",
        "btn_open_settings": "⚙  Abrir Configurações",

        # Context Menu & Tray
        "menu_settings": "Configurações",
        "menu_clear_chat": "Limpar Chat",
        "menu_exit": "Sair",
        "tray_show_chat": "Mostrar Chat",
        "tray_clear_chat": "Limpar Chat",
        "tray_quit_app": "Fechar App Completamente",
        "tray_running_bg": "O chat continua rodando em segundo plano.",
        "tooltip_exit_quick": "Sair do Aplicativo Completamente",
        "placeholder_command": "Comando... (Esc para sair)",
        "system_initialized": "🚀 Furious Multi Chat Pro Inicializado!",

        # TikTok WebEngine Login Dialog
        "tiktok_dialog_title": "Login TikTok — Furious Multi Chat",
        "tiktok_dialog_header": "Faça login no TikTok para ativar lives +18",
        "tiktok_dialog_waiting": "Aguardando login...",
        "tiktok_login_detecting": "Login detectado! Salvando...",
        "tiktok_login_instruction": "Faça o login normalmente — detectaremos automaticamente.",
        "tiktok_login_loading_session": "Carregando sessão...",
    },
    "en": {
        # Config Window
        "config_title": "Furious Config",
        "twitch_label": "Twitch @Username:",
        "tiktok_label": "TikTok @Username:",
        "kick_label": "Kick @Username:",
        "youtube_label": "YouTube @Username:",
        "glassmorphism_label": "Native Blur / Glass Effect (Glassmorphism - Win 11 / Win 10)",
        "bg_opacity_label": "Background Opacity (Dark Translucent):",
        "text_opacity_label": "Chat Text / Messages Opacity:",
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

        # Sections
        "connections_section": "Connections",
        "general_section": "General",
        "tts_section": "Bot Voice (TTS)",

        # Tooltips & Hints - Config Window
        "glassmorphism_tooltip": "Enables native blur (Mica/Acrylic on Win 11 or Dark Acrylic on Win 10)",
        "reconnect_tooltip": "Reconnect {label}",
        "hotkey_press_keys": "Click and press keys...",
        "hotkey_capturing": "⏳ Press keys...",
        "placeholder_username": "YourUsernameHere (without @)",

        # TTS (Text-to-Speech)
        "tts_enable_label": "Enable Chat Reading (TTS)",
        "tts_engine_label": "Voice Engine:",
        "tts_engine_edge": "Microsoft Edge (Neural)",
        "tts_engine_google": "Google TTS (Alternative)",
        "google_tts_info": "Google: single voice (pt-BR), ignores per-platform voice selection",
        "tts_volume_label": "Voice Volume",
        "voice_antonio": "Antônio (Male)",
        "voice_francisca": "Francisca (Female)",
        "voice_thalita": "Thalita (Female)",

        # TikTok Login
        "tiktok_connected_status": "TikTok: Connected",
        "tiktok_not_connected_status": "TikTok: Not connected",
        "tiktok_login_btn": "Log In to TikTok",
        "tiktok_connected_btn": "Connected",
        "tiktok_disconnect_title": "Disconnect from TikTok?",
        "tiktok_disconnect_msg": "You are already connected.\n\nDo you want to remove your account and disconnect?\n(18+ streams will lose accurate uptime)",
        "tiktok_why_login_title": "Why log in to TikTok?",
        "tiktok_why_login_text": (
            "<b>TikTok login is optional.</b><br><br>"
            "<b>🕐 Accurate Uptime:</b> Required for the timer to display total live stream uptime "
            "on age-restricted (18+) broadcasts or if you connect after the stream has started. "
            "Without login, the timer always starts at <b>00:00:00</b> when you connect.<br><br>"
            "<b>👥 Online Viewers Tab:</b> With login active, a dedicated tab displays in real-time "
            "<b>all users currently in your live stream</b> — with profile pictures, names, @usernames, "
            "and contribution scores. Perfect for thanking everyone at the end of the stream.<br><br>"
            "<b>Recommended:</b> Use a secondary TikTok account to log in, never your primary account.<br><br>"
            "<i>🔒 <b>Your Privacy:</b> We do not save your password. Login data stays on this computer only, in a local file encrypted natively by Windows.</i>"
        ),
        "continue_btn": "Continue",
        "cancel_btn": "Cancel",
        "tiktok_login_success": "TikTok login successful!\nYour 18+ streams will now display accurate uptime.",
        "tiktok_login_error_webengine": "PyQt6-WebEngine is not installed.\nInstall with: pip install PyQt6-WebEngine\n\n{error}",

        # Main Window - Header & Tooltips
        "tooltip_views_primary": "Views (Based on primary platform)",
        "tooltip_total_views_ttk": "Total Cumulative Views (TikTok)",
        "tooltip_uptime": "Stream Uptime",
        "tooltip_likes": "Total Likes (Hearts)",
        "tooltip_viewers_page": "View Online Viewers (TikTok)",
        "tooltip_chat_page": "Back to Chat",
        "tooltip_settings": "Settings (Ctrl+Alt+S)",
        "tooltip_pin": "Keep window on top",
        "tooltip_pinned": "Window LOCKED (Pinned) 📌",
        "tooltip_unpinned": "Window UNLOCKED",
        "tooltip_close": "Quit Application Completely",
        "bot_voice_status": "🔊 Bot Voice {status}!",
        "bot_voice_enabled": "Enabled",
        "bot_voice_disabled": "Disabled",
        "ghost_mode_status": "Ghost Mode {status}!",
        "ghost_mode_enabled": "Enabled (Mouse ignores chat)",
        "ghost_mode_disabled": "Disabled (Mouse interacts with chat)",

        # Main Window - Online Viewers Page
        "btn_back_to_chat": " Back to Chat",
        "btn_sync": " Sync",
        "btn_syncing": " Syncing...",
        "tooltip_sync_viewers": "Sync live online viewers now",
        "tooltip_font_decrease": "Decrease user font size",
        "tooltip_font_increase": "Increase user font size",
        "viewers_online_format": "{count} online (TikTok)",
        "viewers_empty": "No viewers on the list right now.\nUsers will appear here during the live stream.",
        "tiktok_not_configured_title": "TikTok Not Configured",
        "tiktok_not_configured_desc": "No TikTok channel is configured.\n\nOpen Settings and enter the channel\n@username to connect.",
        "tiktok_not_configured_hint": "Settings → TikTok field → @username",
        "tiktok_login_required_title": "TikTok Login Required",
        "tiktok_login_required_desc": "The online viewers tab displays\nall users present in your live stream.\n\nTo access it, log in with any\nTikTok account in Settings.",
        "tiktok_login_required_hint": "Settings → TikTok tab → Log In",
        "btn_open_settings": "⚙  Open Settings",

        # Context Menu & Tray
        "menu_settings": "Settings",
        "menu_clear_chat": "Clear Chat",
        "menu_exit": "Exit",
        "tray_show_chat": "Show Chat",
        "tray_clear_chat": "Clear Chat",
        "tray_quit_app": "Quit Application Completely",
        "tray_running_bg": "Chat continues running in the background.",
        "tooltip_exit_quick": "Quit Application Completely",
        "placeholder_command": "Command... (Esc to exit)",
        "system_initialized": "🚀 Furious Multi Chat Pro Initialized!",

        # TikTok WebEngine Login Dialog
        "tiktok_dialog_title": "TikTok Login — Furious Multi Chat",
        "tiktok_dialog_header": "Log in to TikTok to enable 18+ streams",
        "tiktok_dialog_waiting": "Waiting for login...",
        "tiktok_login_detecting": "Login detected! Saving...",
        "tiktok_login_instruction": "Log in normally — we will detect it automatically.",
        "tiktok_login_loading_session": "Loading session...",
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
