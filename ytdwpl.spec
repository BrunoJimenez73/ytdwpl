# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\bruno\\documentos\\ytdwpl\\app\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\bruno\\documentos\\ytdwpl\\bin', 'bin'), ('C:\\Users\\bruno\\documentos\\ytdwpl\\app', 'app')],
    hiddenimports=['app.db', 'app.core.models', 'app.core.downloader', 'app.core.queue', 'app.ui.layout', 'app.ui.queue_table', 'app.ui.progress_card', 'app.ui.add_dialog'],
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
    name='ytdwpl',
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
