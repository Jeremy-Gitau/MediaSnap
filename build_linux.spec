# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for MediaSnap Linux build.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect hidden imports
hidden_imports = [
    # Core Python modules
    'asyncio',
    'sqlite3',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    
    # MediaSnap modules
    'mediasnap',
    'mediasnap.core',
    'mediasnap.core.app_service',
    'mediasnap.core.auth_helpers',
    'mediasnap.core.download_controller',
    'mediasnap.core.downloader',
    'mediasnap.core.exceptions',
    'mediasnap.core.facebook_scraper',
    'mediasnap.core.linkedin_downloader',
    'mediasnap.core.rate_limiter',
    'mediasnap.core.scraper',
    'mediasnap.core.youtube_downloader',
    'mediasnap.core.scrapers',
    'mediasnap.core.scrapers.graphql_scraper',
    'mediasnap.core.scrapers.html_scraper',
    'mediasnap.models',
    'mediasnap.models.data_models',
    'mediasnap.models.schema',
    'mediasnap.storage',
    'mediasnap.storage.database',
    'mediasnap.storage.repository',
    'mediasnap.ui',
    'mediasnap.ui.async_bridge',
    'mediasnap.ui.login_dialog',
    'mediasnap.ui.main_window',
    'mediasnap.ui.styles',
    'mediasnap.utils',
    'mediasnap.utils.config',
    'mediasnap.utils.logging',
    
    # Third-party modules
    'instaloader',
    'instaloader.structures',
    'requests',
    'ttkbootstrap',
    'yt_dlp',
    'sqlalchemy',
    'sqlalchemy.ext',
    'sqlalchemy.ext.asyncio',
    'aiosqlite',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.backends',
    'facebook_scraper',
    'aiohttp',
    'typing_extensions',
    '_tkinter',
]

# Collect all submodules from key packages
hidden_imports += collect_submodules('ttkbootstrap')
hidden_imports += collect_submodules('instaloader')
hidden_imports += collect_submodules('yt_dlp')
hidden_imports += collect_submodules('sqlalchemy')
hidden_imports += collect_submodules('aiosqlite')

# Collect data files
datas = []
datas += collect_data_files('ttkbootstrap')
datas += collect_data_files('instaloader')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'setuptools',
    ],
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
    name='MediaSnap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console for GUI app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
