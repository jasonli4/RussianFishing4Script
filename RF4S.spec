# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('rf4s/config/config.yaml', 'rf4s/config')],
    hiddenimports=['rf4s.auth', 'rf4s.auth.device', 'rf4s.auth.crypto', 'rf4s.auth.client', 'rf4s.auth.manager', 'Crypto.Cipher', 'Crypto.Util.Padding', 'Cryptodome.Cipher', 'Cryptodome.Util.Padding', 'pyautogui', 'pyscreeze', 'psutil', 'requests', 'yaml', 'yacs', 'rich', 'pynput', 'keyboard', 'cv2', 'PIL', 'PIL.Image', 'matplotlib', 'discord_webhook', 'win32api', 'win32con', 'win32gui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RF4S',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
