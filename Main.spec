# -*- mode: python ; coding: utf-8 -*-
# One-directory build: starts much faster than --onefile because nothing has
# to be self-extracted to %TEMP% on every launch. CI zips the dist folder.

a = Analysis(
    ['Main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Stdlib/test machinery the app never touches; keeps the bundle smaller.
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'lib2to3',
        'tkinter.test',
        'xmlrpc',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RevolutExpenses',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX makes antivirus scans slower and triggers more false positives.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RevolutExpenses',
)
