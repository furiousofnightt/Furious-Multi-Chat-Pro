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
        '--onefile',         # Um único executável
        '--clean',           # Limpar cache do build
        '--noconfirm',       # Sobrescrever sem perguntar
        console_flag,        # Console ou Windowed
        '--icon=assets/icone.ico',
        
        # Dependências Ocultas
        '--hidden-import=httpx',
        '--hidden-import=websockets',
        '--hidden-import=certifi',
        '--hidden-import=betterproto',
        '--hidden-import=pyee',
        '--hidden-import=typing_extensions',
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
        '--uac-admin',                      # Força modo Administrador no .exe

        # Incluir pastas externas (Dados)
        '--add-data=ui;ui',
        '--add-data=core;core',
        '--add-data=chat_handlers;chat_handlers',
        '--add-data=utils;utils',
        '--add-data=assets;assets',
        
        # Otimizações
        '--noupx',                          # UPX às vezes quebra algumas DLLs de rede
    ]
    
    PyInstaller.__main__.run(params)
    print(f"\n✅ Compilação concluída! O executável está na pasta 'dist/{app_name}.exe'")

if __name__ == "__main__":
    build_exe()
