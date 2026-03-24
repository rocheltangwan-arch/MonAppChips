[app]
# --- Informations de base ---
title = Gestion Chips
package.name = gestionchips
package.domain = org.projet

# --- Fichiers à inclure ---
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 0.1

# --- CONFIGURATION CRUCIALE (ANTI-ERREUR 3.12) ---
# On utilise Python 3.10 et des versions de Kivy/KivyMD ultra-stables
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,sqlite3
# --- Affichage ---
orientation = landscape
fullscreen = 0

# --- Android Spécifique ---
# On cible une version d'Android moderne mais compatible
android.api = 31
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a

# Autorisations pour que ta base de données fonctionne
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET
android.accept_sdk_license = True

# --- Configuration du Build ---
[buildozer]
log_level = 2
warn_on_root = 1
