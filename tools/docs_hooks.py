"""Publish the canonical contract files in both language builds."""
from pathlib import Path
import shutil
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parent.parent


def on_files(files, config):
    for directory in ("contracts", "assets"):
        for source in sorted((ROOT / directory).rglob("*")):
            if source.is_file():
                files.append(File(source.relative_to(ROOT).as_posix(), str(ROOT),
                                  config["site_dir"], config["use_directory_urls"]))
    return files


def on_post_build(config):
    # Search is deliberately a small full-text scan: CJK and protocol tokens
    # must work without a Node-only segmenter or an external search service.
    shutil.copyfile(ROOT / "assets/search-worker.js", Path(config["site_dir"]) / "search/worker.js")
