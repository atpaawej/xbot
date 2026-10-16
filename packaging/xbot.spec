# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

block_cipher = None

# Root directory of xbot repo
repo_root = Path.cwd().resolve()
src_dir = repo_root / "src"

# Collect hidden modules for packages that do dynamic loading
hiddenimports = [
    *collect_submodules("xbot"),
    *collect_submodules("anthropic"),
    *collect_submodules("tinyfish"),
    *collect_submodules("InquirerPy"),
    *collect_submodules("prompt_toolkit"),
    *collect_submodules("rich"),
    *collect_submodules("pydantic"),
    *collect_submodules("pydantic_core"),
    *collect_submodules("dotenv"),
    *collect_submodules("openai"),
    *collect_submodules("httpx"),
]

# Collect package data files and package metadata
datas = [
    *collect_data_files("anthropic"),
    *collect_data_files("tinyfish"),
    *collect_data_files("InquirerPy"),
    *copy_metadata("xbot"),
    *copy_metadata("anthropic"),
    *copy_metadata("tinyfish"),
    *copy_metadata("inquirerpy"),
    *copy_metadata("prompt_toolkit"),
    *copy_metadata("pydantic"),
]

# Exclude unnecessary development and GUI modules to optimize bundle size
excludes = [
    "pytest",
    "pytest_asyncio",
    "tkinter",
    "matplotlib",
    "scipy",
    "IPython",
]

a = Analysis(
    [str(src_dir / "xbot" / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="xbot",
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
