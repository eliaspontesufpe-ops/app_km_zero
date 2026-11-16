[app]
title = VôLanchar
package.name = volanchar
icon.filename = assets/icone_volanchar.png
package.domain = br.ufrpe.projetos
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,txt
version = 0.8.5
requirements = python3,kivy,plyer,pyjnius,pillow,openssl,certifi,requests,kivy_garden.mapview
orientation = portrait
fullscreen = 0
android.permissions = android.permission.INTERNET
android.minapi = 24
android.api = 36
android.ndk = 29
android.archs = arm64-v8a
android.allow_backup = False
# Biblioteca 21.6 mantém o login legado; a 22 removeu essas classes.
android.gradle_dependencies = com.google.android.gms:play-services-auth:21.6.0
p4a.branch = develop
android.extra_manifest_application_arguments = manifest_extra.xml
[buildozer]
log_level = 2
warn_on_root = 1
