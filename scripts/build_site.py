#!/usr/bin/env python3
"""Build the iPad web apps site: one folder per app, plus a start page.

usage: build_site.py <apps.json> <unzipped_root> <dl_root> <out_dir>

  <unzipped_root>/<id>/   the unpacked upstream zip of each app
  <dl_root>/<id>/TAG      the release tag that zip came from

The upstream files (index.html, the .js and .wasm) are copied unchanged. Only index.html gets
a few extra lines (manifest link, home-screen icon, touch settings, language fix, offline
cache registration), and a sw.js, manifest and icons are added next to it.
"""
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
ICONS = ROOT / "icons"

# Upstream files that are not part of the running app: left in the site (licences must stay)
# but not downloaded into the offline cache.
NOT_PRECACHED_NAMES = {"README.md", "HOSTING.md", "ASSETS.md", "NOTICE", "sw.js", ".nojekyll"}
NOT_PRECACHED_PREFIXES = ("LICENSE", "licenses/")
# Host-specific rule files that do nothing on GitHub Pages.
REMOVED = {"_headers", ".htaccess"}
# Precompressed copies for servers that can serve them; GitHub Pages compresses by itself.
REMOVED_SUFFIXES = (".gz", ".br")
# A file name with a 16-hex-digit content hash never changes under the same name.
HASHED = re.compile(r"[0-9a-f]{16}")

HEAD_TEMPLATE = """  <link rel="manifest" href="./manifest.webmanifest">
  <link rel="apple-touch-icon" href="./icons/icon-180.png">
{apple_meta}  <style>
    /* iPad: no page bounce, text selection or callout; the app takes the touch gestures. */
    html, body {{ overscroll-behavior: none; -webkit-user-select: none; user-select: none;
      -webkit-touch-callout: none; -webkit-tap-highlight-color: transparent; }}
    canvas {{ touch-action: none; }}
  </style>
  <script>
    // The web builds have no Korean font, so a Korean interface shows empty boxes.
    // Report English to the app in that case; other languages are left alone.
    (function () {{
      try {{
        var first = (navigator.languages && navigator.languages[0]) || navigator.language || '';
        if (/^ko/i.test(first)) {{
          var langs = ['en-US', 'en'];
          Object.defineProperty(navigator, 'languages', {{ get: function () {{ return langs; }}, configurable: true }});
          Object.defineProperty(navigator, 'language', {{ get: function () {{ return langs[0]; }}, configurable: true }});
        }}
      }} catch (e) {{}}
    }})();
  </script>
  <script>
    // Offline use: cache the app after it has started, and ask the browser to keep it.
    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', function () {{
        navigator.serviceWorker.register('./sw.js').catch(function () {{}});
        try {{ if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); }} catch (e) {{}}
      }});
    }}
  </script>
"""

# PhotoCraft's menu bar (File, Edit...) ignores finger and Pencil taps: it only opens for a mouse.
# Taps inside the top bar are handed to the app as mouse input instead. The rest is untouched.
MENUBAR_FIX = """  <script>
    (function () {
      var active = false;
      function forward(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        if (e.pointerType === 'mouse' || !e.isTrusted) return;
        if (e.type === 'pointerdown') active = e.clientY < __PX__;
        if (!active) return;
        e.stopImmediatePropagation(); e.preventDefault();
        e.target.dispatchEvent(new PointerEvent(e.type, {
          bubbles: true, cancelable: true, composed: true, clientX: e.clientX, clientY: e.clientY,
          pointerId: 1, pointerType: 'mouse', isPrimary: true,
          button: e.type === 'pointermove' ? -1 : 0, buttons: e.type === 'pointerup' ? 0 : 1 }));
        if (e.type === 'pointerup' || e.type === 'pointercancel') active = false;
      }
      ['pointerdown', 'pointermove', 'pointerup', 'pointercancel'].forEach(function (k) {
        window.addEventListener(k, forward, true);
      });
      ['touchstart', 'touchmove', 'touchend'].forEach(function (k) {
        window.addEventListener(k, function (e) {
          var t = e.touches[0] || e.changedTouches[0];
          if (t && t.clientY < __PX__) e.stopImmediatePropagation();
        }, true);
      });
    })();
  </script>
"""

LANDING = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>ArtCraft for iPad</title>
  <style>
    body {{ margin: 0; background: #1b1c1f; color: #e6e6e8; font: 16px/1.5 -apple-system, system-ui, sans-serif; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 32px 16px 48px; }}
    h1 {{ font-size: 24px; margin: 0 0 4px; }}
    p.lead {{ color: #a9a9ae; margin: 0 0 24px; }}
    a.card {{ display: flex; gap: 16px; align-items: center; padding: 14px 16px; margin-bottom: 12px;
      background: #26272b; border-radius: 14px; color: inherit; text-decoration: none; }}
    a.card img {{ width: 56px; height: 56px; border-radius: 13px; }}
    a.card b {{ display: block; font-size: 18px; }}
    a.card span {{ color: #a9a9ae; font-size: 14px; }}
    a.card small {{ color: #7c7c82; }}
    .note {{ color: #a9a9ae; font-size: 14px; margin-top: 24px; }}
  </style>
</head>
<body>
  <main>
    <h1>ArtCraft for iPad</h1>
    <p class="lead">앱을 눌러 열고, 공유 → 홈 화면에 추가를 하세요.</p>
{cards}    <p class="note">인터넷이 되는 곳에서 각 앱을 홈 화면 아이콘으로 한 번 실행하고 1~2분 기다리면 오프라인에서도 열립니다.
      새 버전은 인터넷이 될 때 앱을 열면 받아지고, 다음 실행부터 적용됩니다.</p>
  </main>
</body>
</html>
"""

CARD = """    <a class="card" href="./{id}/"><img src="./{id}/icons/icon-192.png" alt=""><div><b>{name}</b><span>{description}</span><br><small>{tag}</small></div></a>
"""


def find_site_root(unzipped: Path) -> Path:
    candidates = [p.parent for p in unzipped.rglob("index.html")]
    if len(candidates) != 1:
        sys.exit(f"{unzipped}: expected exactly one index.html, found {len(candidates)}")
    return candidates[0]


def apple_meta_for(page: str, name: str) -> str:
    wanted = [
        ("apple-mobile-web-app-capable", "yes"),
        ("mobile-web-app-capable", "yes"),
        ("apple-mobile-web-app-title", name),
        ("apple-mobile-web-app-status-bar-style", "black"),
    ]
    lines = ""
    for key, value in wanted:
        if f'name="{key}"' not in page:
            lines += f'  <meta name="{key}" content="{html.escape(value)}">\n'
    return lines


def list_files(out: Path) -> list[str]:
    files = []
    for path in sorted(out.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out).as_posix()
        if path.name in NOT_PRECACHED_NAMES or rel.startswith(NOT_PRECACHED_PREFIXES):
            continue
        files.append(rel)
    return files


def build_app(app: dict, unzipped: Path, tag: str, out_root: Path) -> None:
    app_id, name = app["id"], app["name"]
    src = find_site_root(unzipped)
    out = out_root / app_id
    shutil.copytree(src, out)
    for removed in REMOVED:
        (out / removed).unlink(missing_ok=True)
    for path in list(out.rglob("*")):
        if path.is_file() and path.name.endswith(REMOVED_SUFFIXES):
            path.unlink()

    index = out / "index.html"
    page = index.read_text(encoding="utf-8")
    if "</head>" not in page:
        sys.exit(f"{app_id}: index.html has no </head>; the upstream page changed, update build_site.py")
    if "manifest.webmanifest" in page:
        sys.exit(f"{app_id}: index.html is already patched")
    head = HEAD_TEMPLATE.format(apple_meta=apple_meta_for(page, name))
    menubar = app.get("menubar_touch_px")
    if menubar:
        head += MENUBAR_FIX.replace("__PX__", str(int(menubar)))
    index.write_text(page.replace("</head>", head + "</head>", 1), encoding="utf-8")

    manifest = {
        "name": name, "short_name": name, "start_url": "./", "scope": "./",
        "display": "standalone", "orientation": "any",
        "background_color": "#1b1c1f", "theme_color": app.get("color", "#1b1c1f"),
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.copytree(ICONS / app_id, out / "icons")

    files = list_files(out)
    static = ["./" + f for f in files if HASHED.search(Path(f).name)]
    page_files = ["./"] + ["./" + f for f in files if not HASHED.search(Path(f).name)]

    # Fingerprint of everything that can change under an unchanged name. It goes into sw.js,
    # so any change to the page, the glue or an icon makes browsers install a new version.
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.encode() + b"\0")
        if f"./{f}" not in static:
            digest.update((out / f).read_bytes() + b"\0")
    build_id = digest.hexdigest()[:12]

    sw = (TEMPLATES / "sw.template.js").read_text(encoding="utf-8")
    for key, value in {
        "__APP__": app_id, "__TAG__": tag, "__BUILD__": build_id,
        "__STATIC_FILES__": json.dumps(static, indent=2),
        "__PAGE_FILES__": json.dumps(page_files, indent=2),
    }.items():
        sw = sw.replace(key, value)
    (out / "sw.js").write_text(sw, encoding="utf-8")

    size = sum((out / f).stat().st_size for f in files)
    print(f"{name} {tag} (build {build_id}): {len(static)} hashed + {len(page_files)} page files, {size / 1e6:.1f} MB")


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    apps_json, unzipped_root, dl_root, out_dir = (Path(a) for a in sys.argv[1:])
    apps = json.loads(apps_json.read_text(encoding="utf-8"))
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    cards = ""
    for app in apps:
        tag = (dl_root / app["id"] / "TAG").read_text(encoding="utf-8").strip()
        build_app(app, unzipped_root / app["id"], tag, out_dir)
        cards += CARD.format(id=app["id"], name=html.escape(app["name"]),
                             description=html.escape(app.get("description", "")), tag=html.escape(tag))
    (out_dir / "index.html").write_text(LANDING.format(cards=cards), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
