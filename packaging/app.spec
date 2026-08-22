# PyInstaller spec for the packaged macOS app. Build with:
#   pyinstaller packaging/app.spec
#
# onedir (not onefile): no self-extraction step at launch, and if something
# breaks on a Mac nobody has locally, an unpacked dir under
# dist/FantasyDraftAssistant/ is far easier to debug remotely (e.g. over
# screen-share) than one opaque single-file blob.

import os

block_cipher = None
REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(REPO_ROOT, "packaging", "launcher.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=[
        (os.path.join(REPO_ROOT, "project", "webapp", "static"), os.path.join("project", "webapp", "static")),
        (os.path.join(REPO_ROOT, "project", "data", "cleaned_data.csv"), os.path.join("project", "data")),
    ],
    hiddenimports=[
        # uvicorn lazy-imports its backends; PyInstaller's static analysis
        # misses them without this.
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FantasyDraftAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    windowed=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="FantasyDraftAssistant",
)

app = BUNDLE(
    coll,
    name="FantasyDraftAssistant.app",
    bundle_identifier="com.fantasydraftassistant.app",
)
