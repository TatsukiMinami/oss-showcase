#!/usr/bin/env python3
"""cluster-apps/portal/server.py を configmap.yaml に埋め込み、app.yaml の Deployment にハッシュを付ける

ConfigMap だけが変わっても Pod は作り直されず、古いコードが動き続ける。
Pod のテンプレートにハッシュを付け、コードが変わったら作り直させる。

使い方: python scripts/render_portal.py          # 書き出す
        python scripts/render_portal.py --check  # 揃っていなければ失敗する。CI で使う
"""
import hashlib
import re
import sys
from pathlib import Path

import yaml

DIR = Path(__file__).resolve().parent.parent / "cluster-apps/portal"
KEY = "showcase.cloudnativedays.jp/server-sha256"


class Literal(yaml.SafeDumper):
    pass


Literal.add_representer(str, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def render() -> dict[Path, str]:
    src = (DIR / "server.py").read_text()
    digest = hashlib.sha256(src.encode()).hexdigest()
    cm = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "portal"}, "data": {"server.py": src}}
    configmap = "# scripts/render_portal.py が server.py から作る。手で書き換えない\n" + yaml.dump(cm, Dumper=Literal, sort_keys=False, allow_unicode=True)
    app = re.sub(rf"({re.escape(KEY)}: )\S+", rf"\g<1>{digest}", (DIR / "app.yaml").read_text())
    return {DIR / "configmap.yaml": configmap, DIR / "app.yaml": app}


if __name__ == "__main__":
    stale = [p for p, text in render().items() if not p.exists() or p.read_text() != text]
    if "--check" in sys.argv:
        for p in stale:
            print(f"::error::{p.relative_to(DIR.parent.parent)}: server.py と揃っていません。python scripts/render_portal.py を実行してください")
        sys.exit(1 if stale else 0)
    for p, text in render().items():
        p.write_text(text)
