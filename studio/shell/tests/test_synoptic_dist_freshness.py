"""The Synoptic editor Studio serves must be the one in src/: a dist/
older than the sources is rebuilt, not served (user report 2026-09-18 -
fixes made in src/ never reached the running editor)."""
import os
import time

from studio.shell.synoptic_panel import dist_is_stale, newest_source_mtime


def _touch(path, when):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (when, when))


def test_a_missing_or_older_dist_is_stale_and_a_fresh_one_is_not(tmp_path):
    root = tmp_path / "synoptic"
    dist = root / "dist"
    now = time.time()
    _touch(root / "src" / "components" / "Canvas.tsx", now - 100)
    _touch(root / "package.json", now - 200)
    assert dist_is_stale(dist, root)                      # nothing built yet
    _touch(dist / "index.html", now - 50)
    assert not dist_is_stale(dist, root)                  # built after the last source change
    _touch(root / "src" / "store" / "workspaceSlice.ts", now - 10)
    assert newest_source_mtime(root) == os.stat(root / "src" / "store" / "workspaceSlice.ts").st_mtime
    assert dist_is_stale(dist, root)                      # a source edited after the build
    _touch(dist / "index.html", now)
    assert not dist_is_stale(dist, root)
    _touch(root / "vite.config.ts", now + 5)              # config counts as a source too
    assert dist_is_stale(dist, root)
