#!/usr/bin/env bash
# Builds MaxPlayer.apk (needs: aapt, dalvik-exchange, apksigner, zipalign, android.jar, javac)
set -euo pipefail
cd "$(dirname "$0")"
JAR=${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}
OUT=build; rm -rf $OUT; mkdir -p $OUT/classes $OUT/assets
cp ../mxplayer/{index.html,app.js,style.css,icon.svg,manifest.webmanifest} $OUT/assets/
javac -source 8 -target 8 -bootclasspath "$JAR" -d $OUT/classes src/com/maxplayer/app/*.java 2>&1 | grep -v warning || true
dalvik-exchange --dex --output=$OUT/classes.dex $OUT/classes
aapt package -f -M AndroidManifest.xml -S res -A $OUT/assets -I "$JAR" -F $OUT/unsigned.apk
(cd $OUT && zip -q -j unsigned.apk classes.dex)
zipalign -f 4 $OUT/unsigned.apk $OUT/aligned.apk
KS=${KEYSTORE:-$OUT/debug.keystore}
[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias key -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=MaxPlayer" 2>/dev/null
apksigner sign --ks "$KS" --ks-pass pass:android --key-pass pass:android --out MaxPlayer.apk $OUT/aligned.apk
apksigner verify MaxPlayer.apk && echo OK && ls -la MaxPlayer.apk
