from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_HTML = ROOT / "源代码" / "游戏源代码.html"
RELEASE_DIR = ROOT / "release"
ENTRY_NAME = "奇境王冠.html"
ZIP_PATH = ROOT / "奇境王冠_mobile.zip"

RESOURCES = [
    ("image", ROOT / "源代码/assets/fairy-garden-battlefield-v1.png", "assets/images/fairy-garden-battlefield-v1.png", ["./assets/fairy-garden-battlefield-v1.png"]),
    ("image", ROOT / "源代码/assets/fairy-castle-gate-v1.png", "assets/images/fairy-castle-gate-v1.png", ["./assets/fairy-castle-gate-v1.png"]),
    ("image", ROOT / "源代码/assets/fairy-road-stone-texture-v1.png", "assets/images/fairy-road-stone-texture-v1.png", ["./assets/fairy-road-stone-texture-v1.png"]),
    ("image", ROOT / "源代码/assets/fairy-cannon-barrel-v1.png", "assets/images/fairy-cannon-barrel-v1.png", ["./assets/fairy-cannon-barrel-v1.png"]),
    ("audio", ROOT / "音效/BGM/BGM .ogg", "assets/audio/BGM.ogg", ["../音效/BGM/BGM%20.ogg"]),
    ("audio", ROOT / "音效/加农炮/单发/cannon1.mp3", "assets/audio/cannon1.mp3", ["../音效/加农炮/单发/cannon1.mp3"]),
    ("audio", ROOT / "音效/加农炮/连发/explosions.mp3", "assets/audio/explosions.mp3", ["../音效/加农炮/连发/explosions.mp3"]),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build() -> None:
    if not SOURCE_HTML.is_file():
        raise FileNotFoundError(SOURCE_HTML)
    missing = [str(source) for _, source, _, _ in RESOURCES if not source.is_file()]
    if missing:
        raise FileNotFoundError("缺少发布资源:\n" + "\n".join(missing))

    if RELEASE_DIR.exists():
        resolved = RELEASE_DIR.resolve()
        if resolved.parent != ROOT.resolve() or resolved.name != "release":
            raise RuntimeError(f"拒绝清理异常目录: {resolved}")
        shutil.rmtree(resolved)
    (RELEASE_DIR / "assets/images").mkdir(parents=True)
    (RELEASE_DIR / "assets/audio").mkdir(parents=True)
    (RELEASE_DIR / "assets/data").mkdir(parents=True)

    html = SOURCE_HTML.read_text(encoding="utf-8")
    html = re.sub(r'^<link rel="preload"[^>]+>\s*$', '', html, flags=re.MULTILINE)
    manifest: list[dict[str, object]] = []
    for kind, source, release_path, references in RESOURCES:
        target = RELEASE_DIR / release_path
        shutil.copy2(source, target)
        embedded = data_uri(source)
        hits = 0
        for reference in references:
            if source.name == "fairy-road-stone-texture-v1.png":
                css_reference = f"url('{reference}')"
                css_hits = html.count(css_reference)
                html = html.replace(css_reference, "var(--release-road-image)")
                hits += css_hits
            hits += html.count(reference)
            html = html.replace(reference, embedded)
        if source.name == "fairy-road-stone-texture-v1.png":
            html = html.replace(
                "</head>", f"<style>:root{{--release-road-image:url('{embedded}')}}</style>\n</head>", 1
            )
        if hits == 0:
            raise RuntimeError(f"源码没有引用预期资源: {source.name}")
        manifest.append({
            "type": kind,
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "release": release_path,
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
            "source_reference_count": hits,
            "embedded_in_html": True,
        })

    fonts = [
        "Microsoft YaHei / Microsoft YaHei UI（系统字体）",
        "Segoe UI Emoji / Apple Color Emoji / Noto Color Emoji（系统 Emoji 字体）",
        "system-ui（系统回退字体）",
    ]
    manifest_doc = {
        "entry": ENTRY_NAME,
        "self_contained_entry": True,
        "resources": manifest,
        "fonts": fonts,
        "external_network_dependencies": [],
        "json_runtime_dependencies": [],
    }
    (RELEASE_DIR / "assets/data/resource-manifest.json").write_text(
        json.dumps(manifest_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RELEASE_DIR / ENTRY_NAME).write_text(html, encoding="utf-8")
    (RELEASE_DIR / "README.txt").write_text(
        "奇境王冠 手机发布包\n"
        "====================\n\n"
        "Android：解压整个 ZIP，点击 奇境王冠.html，选择 Chrome 等现代浏览器打开。\n"
        "iPhone/iPad：解压到‘文件’，用支持本地 HTML 的浏览器打开；Safari 对本地文件全屏和横屏锁定有限制。\n"
        "首次触摸页面会初始化声音并尝试播放 BGM。进入战场或点击‘进入横屏模式’会请求全屏和横屏。\n"
        "奇境王冠.html 已内嵌全部图片和音频；assets 目录保留独立资源和校验清单，便于检查。\n"
        "不要在压缩包内直接预览，请先完整解压。\n\n"
        "重新构建：在项目根目录执行 python build_release.py\n",
        encoding="utf-8",
    )

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(RELEASE_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(RELEASE_DIR).as_posix())

    print(f"[PASS] 发布目录: {RELEASE_DIR}")
    print(f"[PASS] 手机发布包: {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes)")
    print(f"[PASS] 资源数量: {len(RESOURCES)}，入口已完全内嵌资源")


if __name__ == "__main__":
    build()
