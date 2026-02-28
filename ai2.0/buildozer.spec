[app]

title = 旮旯GAME
package.name = gala_game
package.domain = org.gala
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,ttf,otf
version = 1.0.0
requirements = python3,kivy,kivy_deps.sdl2,kivy_deps.glew,pillow,aiohttp,sqlite3,jieba
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.entrypoint = org.kivy.android.PythonActivity
android.allow_backup = True
android.archs = arm64-v8a,armeabi-v7a
p4a.bootstrap = sdl2
p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1

[app:android]

# 添加必要的权限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA

# 添加元数据
android.meta_data = com.google.android.gms.car.application=com.google.android.gms.car.notification.CarApp

# 图标
icon.filename = %(source.dir)s/icon.png

# 启动画面
presplash.filename = %(source.dir)s/presplash.png
presplash.color = #FFFFFF
