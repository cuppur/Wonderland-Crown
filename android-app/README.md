# 奇境王冠·新版（Android）

这是一个独立的离线 Android WebView 应用。应用名称为“奇境王冠·新版”，包名为 `com.qijingwangguan.mobile`，因此会和旧版 `com.qijingwangguan.game` 并排安装。

APK 内包含游戏运行所需的 `index.html`、`css/`、`js/` 和 `assets/`，可离线游玩。安装包不含 EVA API 密钥、本地代理或测试文件。游戏运行时使用全屏横屏布局。

## 构建

需要 JDK 17+ 和 Android SDK Platform/Build Tools 36。设置 `ANDROID_SDK_ROOT` 后，在项目根目录运行：

```powershell
./android-app/build-apk.ps1
```

生成的签名调试 APK 在 `output/android/WonderlandCrown-New.apk`。个人签名保存在忽略提交的 `wonderland-crown-debug.keystore`，让后续版本能更新同一个新版应用。脚本可传入 `-AdbDevice <设备序列号>`，用于构建后安装到指定手机；安装前会核对旧游戏 `com.qijingwangguan.game` 仍在设备上。
