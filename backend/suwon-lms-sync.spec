# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — `pyinstaller suwon-lms-sync.spec` 으로 빌드.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hidden = []
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("apscheduler")
hidden += collect_submodules("watchdog")
hidden += collect_submodules("pystray")
hidden += collect_submodules("PIL")
hidden += collect_submodules("sqlmodel")
hidden += collect_submodules("pydantic")
hidden += collect_submodules("app")

datas = []
# 프론트 정적 파일, 실행 파일 옆 frontend/prototype 으로 패키징
datas += [
    ("../frontend/prototype/index.html", "frontend/prototype"),
    ("../frontend/prototype/course.html", "frontend/prototype"),
    ("../frontend/prototype/settings.html", "frontend/prototype"),
    ("../frontend/prototype/styles.css", "frontend/prototype"),
    ("../frontend/prototype/shared.js", "frontend/prototype"),
    ("../frontend/prototype/dashboard.js", "frontend/prototype"),
    ("../frontend/prototype/course.js", "frontend/prototype"),
    ("../frontend/prototype/settings.js", "frontend/prototype"),
]


a = Analysis(
    ["app/tray.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PySide6", "PyQt5", "PyQt6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="suwon-lms-sync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name="suwon-lms-sync",
)
