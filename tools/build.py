#!/usr/bin/env python3
"""Build both languages and check all local links, including JSON downloads."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for name in ("href", "src"):
            if name in attrs:
                self.links.append(attrs[name])


def check_links(site):
    pages, failures = {}, []
    for path in site.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text())
        pages[path.resolve()] = parser
    for path, parser in pages.items():
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or link.startswith("/"):
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(site.resolve()) or not target.exists():
                failures.append(f"{path.relative_to(site)}: {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                failures.append(f"{path.relative_to(site)}: missing anchor {link}")
    if failures:
        raise SystemExit("Broken site links:\n" + "\n".join(failures))
    print(f"PASS local links and anchors across {len(pages)} HTML pages")


def main():
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tools",
                    "-p", "test_*.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "tools/validate.py"], cwd=ROOT, check=True)
    for config in ("mkdocs.yml", "mkdocs.en.yml"):
        subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict", "--clean", "--config-file", config], cwd=ROOT, check=True)
    site = ROOT / "build/site"
    shutil.copytree(ROOT / "build/en", site / "en")
    (site / ".nojekyll").touch()
    check_links(site)


if __name__ == "__main__":
    main()
