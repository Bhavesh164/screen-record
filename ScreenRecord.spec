# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import os
import shutil
import sys


ffmpeg_binary = os.environ.get("SCREEN_RECORD_FFMPEG_BIN") or shutil.which("ffmpeg")
if not ffmpeg_binary:
    raise SystemExit(
        "ffmpeg was not found on PATH. Install it or set SCREEN_RECORD_FFMPEG_BIN before building."
    )


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[(ffmpeg_binary, ".")],
    datas=[("assets/captokey.png", "assets")],
    hiddenimports=[
        "pynput",
        "pynput.keyboard",
        "pynput.mouse",
        "pynput._util",
        "mss",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ],
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
    [],
    exclude_binaries=True,
    name="CaptoKey",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity="-",
    entitlements_file="macos/CaptoKey.entitlements",
    icon="assets/captokey.icns",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CaptoKey",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CaptoKey.app",
        bundle_identifier="com.kilo.captokey",
        icon="assets/captokey.icns",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
            "NSScreenCaptureUsageDescription": "CaptoKey needs screen recording access to capture your screen.",
        },
    )
