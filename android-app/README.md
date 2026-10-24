# 奇境王冠·新版（Android）

这是一个独立的离线 Android WebView 应用。应用名称为“奇境王冠·新版”，包名为 `com.qijingwangguan.mobile`，因此会和旧版 `com.qijingwangguan.game` 并排安装。

APK 内包含游戏运行所需的 `index.html`、`css/`、`js/` 和 `assets/`，可离线游玩。安装包不含 个人凭据、本地代理或测试文件。游戏运行时使用全屏横屏布局。

## 构建

需要 JDK 17+ 和 Android SDK Platform/Build Tools 36。设置 `ANDROID_SDK_ROOT` 后，在项目根目录运行：

```powershell
./android-app/build-apk.ps1
```

生成的签名调试 APK 在 `output/android/WonderlandCrown-New.apk`。个人签名保存在忽略提交的 `wonderland-crown-debug.keystore`，让后续版本能更新同一个新版应用。脚本可传入 `-AdbDevice <设备序列号>`，用于构建后安装到指定手机；安装前会核对旧游戏 `com.qijingwangguan.game` 仍在设备上。

## GitHub Release（2026.10.24）

Release 安装包从 UI 主线生成，版本名 2026.10.24，版本号 20261024。沿用已有的个人调试签名和包名 com.qijingwangguan.mobile，可更新之前安装的“奇境王冠·新版”，与旧包 com.qijingwangguan.game 继续并存。APK 为完整离线动物版，无需账号与个人 API 配置。

工作区中没有原签名时，使用 `-SigningKey <本机已有签名文件路径>` 指定原签名，不能生成新签名后声称可覆盖旧包。可通过 `-VersionCode`、`-VersionName` 设置后续发布版本；签名文件不提交到 GitHub。

发布前核对 APK 内全部游戏文件与 UI 运行文件一致，检查版本/横屏/最低 Android 版本/无网络权限、APK 签名，以及签名证书与上一版相同。Release 同时附带 SHA256 校验文件。
