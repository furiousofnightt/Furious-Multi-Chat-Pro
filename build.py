import PyInstaller.__main__
import os
import sys
import subprocess

def build_exe():
    print("📦 Iniciando compilação do Furious Multi Chat Pro [V2 - Estabilizada]...")
    
    # Nome do projeto
    app_name = "FuriousMultiChatPro"
    
    # Tentar fechar o app se estiver aberto para evitar erro de permissão
    try:
        if sys.platform == "win32":
            subprocess.run(['taskkill', '/F', '/IM', f'{app_name}.exe', '/T'], 
                           capture_output=True, text=True)
    except:
        pass
    
    # Script principal
    main_script = "main.py"
    
    # DEBUG: Mude para True se precisar ver erros no terminal do .exe
    DEBUG = False
    console_flag = '--console' if DEBUG else '--windowed'

    # Comandos do PyInstaller
    params = [
        main_script,
        f'--name={app_name}',
        '--onedir',          # Formato de pasta (abertura instantânea)
        '--clean',           # Limpar cache do build
        '--noconfirm',       # Sobrescrever sem perguntar
        console_flag,        # Console ou Windowed
        '--icon=assets/icone.ico',
        # '--uac-admin',  # Removido: causa lentidão no startup (prompt UAC + el evação)
        
        # Dependências Ocultas
        '--hidden-import=httpx',
        '--hidden-import=websockets',
        '--hidden-import=certifi',
        '--hidden-import=betterproto',
        '--hidden-import=pyee',
        '--hidden-import=typing_extensions',
        '--hidden-import=TikTokLive',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtSvg',
        '--hidden-import=keyboard',
        '--hidden-import=twitchio',
        '--hidden-import=kickpython',
        '--hidden-import=edge_tts',
        '--hidden-import=pygame',
        '--hidden-import=curl_cffi',
        '--hidden-import=PyQt6.QtWebEngineWidgets',
        '--hidden-import=PyQt6.QtWebEngineCore',
        '--hidden-import=win32crypt',
        '--hidden-import=gtts',
        '--hidden-import=gtts.tts',
        '--hidden-import=gtts.lang',
        '--hidden-import=requests',
        '--hidden-import=urllib3',
        '--hidden-import=charset_normalizer',
        '--hidden-import=click',

        # Inclui as DLLs e recursos do WebEngine no executável
        '--collect-all=PyQt6.QtWebEngineWidgets',
        '--collect-all=PyQt6.QtWebEngineCore',
        '--collect-all=gtts',

        # Incluir pastas externas (Dados)
        '--add-data=ui;ui',
        '--add-data=core;core',
        '--add-data=chat_handlers;chat_handlers',
        '--add-data=utils;utils',
        '--add-data=assets;assets',
        
        # Otimizações de startup — excluir apenas módulos confirmados como não usados
        '--noupx',           # UPX quebra algumas DLLs de rede
        '--exclude-module=tkinter',
        '--exclude-module=_tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=scipy',
        '--exclude-module=PIL',
        '--exclude-module=unittest',
        '--exclude-module=pydoc',
        '--exclude-module=doctest',
        '--exclude-module=difflib',
        '--exclude-module=ftplib',
        '--exclude-module=imaplib',
        '--exclude-module=poplib',
        '--exclude-module=smtplib',
        '--exclude-module=telnetlib',
        '--exclude-module=xmlrpc',
    ]
    
    PyInstaller.__main__.run(params)
    print(f"\n✅ Compilação concluída! O executável está na pasta 'dist/{app_name}.exe'")

if __name__ == "__main__":
    build_exe()
