param(
    [string]$Sdk = $env:ANDROID_SDK_ROOT,
    [string]$AdbDevice = ''
)

$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $appRoot
if (-not $Sdk) { $Sdk = $env:ANDROID_HOME }
if (-not $Sdk) { throw 'Set ANDROID_SDK_ROOT or ANDROID_HOME to the Android SDK directory.' }

$buildTools = Join-Path $Sdk 'build-tools/36.0.0'
$platform = Join-Path $Sdk 'platforms/android-36'
$aapt2 = Join-Path $buildTools 'aapt2.exe'
$androidJar = Join-Path $platform 'android.jar'
$javac = (Get-Command javac -ErrorAction Stop).Source
$jarTool = Join-Path (Split-Path -Parent $javac) 'jar.exe'
$keytool = Join-Path (Split-Path -Parent $javac) 'keytool.exe'
foreach ($required in @($aapt2, $androidJar, $jarTool, $keytool)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required Android build tool is missing: $required" }
}

$build = Join-Path $env:TEMP 'wonderland-crown-mobile-build'
$source = Join-Path $build 'source'
$res = Join-Path $source 'res'
$manifest = Join-Path $source 'AndroidManifest.xml'
$activitySource = Join-Path $source 'java/com/qijingwangguan/mobile/MainActivity.java'
$outDir = Join-Path $projectRoot 'output/android'
if (Test-Path -LiteralPath $build) { Remove-Item -LiteralPath $build -Recurse -Force }
New-Item -ItemType Directory -Force -Path $build, $source, $outDir | Out-Null
Copy-Item -LiteralPath (Join-Path $appRoot 'app/src/main/AndroidManifest.xml') -Destination $source -Force
Copy-Item -LiteralPath (Join-Path $appRoot 'app/src/main/java') -Destination $source -Recurse -Force
Copy-Item -LiteralPath (Join-Path $appRoot 'app/src/main/res') -Destination $source -Recurse -Force
$gameAssets = Join-Path $build 'assets/game'
if (Test-Path -LiteralPath $gameAssets) { Remove-Item -LiteralPath $gameAssets -Recurse -Force }
New-Item -ItemType Directory -Force -Path $gameAssets | Out-Null
foreach ($entry in @('index.html', 'css', 'js', 'assets')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $entry) -Destination $gameAssets -Recurse -Force
}

$compiledResources = Join-Path $build 'compiled-resources.zip'
$aaptApk = Join-Path $build 'app-unsigned.apk'
$generated = Join-Path $build 'generated'
$classes = Join-Path $build 'classes'
$classesJar = Join-Path $build 'classes.jar'
$dexDir = Join-Path $build 'dex'
$unsigned = Join-Path $build 'app-final-unsigned.apk'
$aligned = Join-Path $build 'app-aligned.apk'
$keystore = Join-Path $appRoot 'wonderland-crown-debug.keystore'
$finalApk = Join-Path $build 'WonderlandCrown-New.apk'
$deliverable = Join-Path $outDir 'WonderlandCrown-New.apk'
foreach ($path in @($generated, $classes, $dexDir)) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

& $aapt2 compile --dir $res -o $compiledResources
if ($LASTEXITCODE -ne 0) { throw "aapt2 resource compile failed ($LASTEXITCODE)" }
& $aapt2 link -o $aaptApk -I $androidJar --manifest $manifest --rename-manifest-package com.qijingwangguan.mobile --min-sdk-version 23 --target-sdk-version 35 --version-code 20261017 --version-name 2026.10.17 --java $generated -R $compiledResources --auto-add-overlay
if ($LASTEXITCODE -ne 0) { throw "aapt2 resource link failed ($LASTEXITCODE)" }

& $javac -encoding UTF-8 -source 8 -target 8 -Xlint:-options -Xlint:-deprecation -bootclasspath $androidJar -d $classes $activitySource (Join-Path $generated 'com/qijingwangguan/mobile/R.java')
if ($LASTEXITCODE -ne 0) { throw "javac failed ($LASTEXITCODE)" }
& $jarTool cf $classesJar -C $classes .
if ($LASTEXITCODE -ne 0) { throw "Packaging Java class files failed ($LASTEXITCODE)" }
& (Join-Path $buildTools 'd8.bat') --lib $androidJar --min-api 23 --output $dexDir $classesJar
if ($LASTEXITCODE -ne 0) { throw "d8 failed ($LASTEXITCODE)" }

Copy-Item -LiteralPath $aaptApk -Destination $unsigned -Force
& $jarTool uf $unsigned -C $dexDir classes.dex -C $build 'assets'
if ($LASTEXITCODE -ne 0) { throw "Adding game files to APK failed ($LASTEXITCODE)" }
& (Join-Path $buildTools 'zipalign.exe') -f -p 4 $unsigned $aligned
if ($LASTEXITCODE -ne 0) { throw "zipalign failed ($LASTEXITCODE)" }
if (-not (Test-Path -LiteralPath $keystore)) {
    & $keytool -genkeypair -keystore $keystore -storepass android -alias androiddebugkey -keypass android -dname 'CN=Android Debug,O=Android,C=US' -keyalg RSA -keysize 2048 -validity 10000
    if ($LASTEXITCODE -ne 0) { throw "Creating the personal debug key failed ($LASTEXITCODE)" }
}
& (Join-Path $buildTools 'apksigner.bat') sign --ks $keystore --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out $finalApk $aligned
if ($LASTEXITCODE -ne 0) { throw "APK signing failed ($LASTEXITCODE)" }

& (Join-Path $buildTools 'apksigner.bat') verify --verbose $finalApk
if ($LASTEXITCODE -ne 0) { throw "APK signature verification failed ($LASTEXITCODE)" }
Write-Host "Built APK: $finalApk"
Write-Host "Package: com.qijingwangguan.mobile"
Write-Host "The existing com.qijingwangguan.game package is untouched."
Copy-Item -LiteralPath $finalApk -Destination $deliverable -Force
Write-Host "Copied APK to: $deliverable"

if ($AdbDevice) {
    $adb = Join-Path $Sdk 'platform-tools/adb.exe'
    if (-not (Test-Path -LiteralPath $adb)) { throw "ADB was not found: $adb" }
    $installed = & $adb -s $AdbDevice shell pm list packages com.qijingwangguan.game
    if (-not ($installed -match 'package:com\.qijingwangguan\.game')) {
        throw 'Safety check failed: the existing Wonderland Crown app was not found; refusing installation.'
    }
    $newInstalled = & $adb -s $AdbDevice shell pm list packages com.qijingwangguan.mobile
    if ($newInstalled -match 'package:com\.qijingwangguan\.mobile') {
        & $adb -s $AdbDevice install -r $finalApk
    } else {
        & $adb -s $AdbDevice install $finalApk
    }
    if ($LASTEXITCODE -ne 0) { throw "Installing the separate APK failed ($LASTEXITCODE)" }
    Write-Host "Installed on device $AdbDevice without replacing the existing app."
}
