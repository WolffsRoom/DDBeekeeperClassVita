# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui\\dd_beekeeper_vita_gui.py'],
    pathex=['patcher'],
    binaries=[],
    datas=[('patcher\\translations.json', 'patcher'), ('assets\\darkest_dungeon_logo.png', 'assets'), ('assets\\image.ico', 'assets')],
    hiddenimports=['dd_beekeeper_vita_patcher'],
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
    name='DDBeekeeperClassVita',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\image.ico'],
)
