# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('ui', 'ui'), ('core', 'core'), ('chat_handlers', 'chat_handlers'), ('utils', 'utils'), ('assets', 'assets')]
binaries = []
hiddenimports = ['httpx', 'websockets', 'certifi', 'betterproto', 'pyee', 'typing_extensions', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg', 'keyboard', 'twitchio', 'kickpython', 'edge_tts', 'pygame', 'curl_cffi', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'win32crypt']
tmp_ret = collect_all('PyQt6.QtWebEngineWidgets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt6.QtWebEngineCore')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL', 'unittest', 'pydoc', 'doctest', 'difflib', 'ftplib', 'imaplib', 'poplib', 'smtplib', 'telnetlib', 'xmlrpc'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FuriousMultiChatPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icone.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FuriousMultiChatPro',
)
