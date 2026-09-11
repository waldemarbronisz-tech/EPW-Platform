"""Generates studio/shell/identity/*.png and *.ico - task "fix/project-
format-integrity" point 4 ("tożsamość wizualna"). Run manually
(`python generate_identity.py` from this directory) whenever the
identity assets need to change; the files themselves are committed and
loaded from disk by studio/main.py (app icon) and studio/tools/
register_file_type.py (file icon) - neither regenerates them at
runtime, same "script in repo, artifacts are the source of truth"
convention studio/shell/icons/generate_icons.py and studio/shell/help/
generate_help.py already established.

SOURCE: runtime/epw_os/resources/about_logo.png (READ ONLY - GRANICE:
runtime/ never touched, only read here). That file is a large,
detailed illustration (two mascot characters, a Win98 desktop mockup)
built for an About-dialog-sized display, not for a 16px icon - most of
it turns to unrecognizable mush at icon sizes. The one element that
survives down to 16-32px is the navy "EPW / ENTRY GATE SYSTEM" plaque
at its center: bold, high-contrast, blocky lettering. Both assets
below are built from a crop of THAT plaque (_EPW_LETTERS_CROP below,
found by inspecting the source image directly - not guessed), not
redrawn from scratch and not a shrunk version of the whole illustration.

STYLE, deliberately DIFFERENT from studio/shell/icons/'s own 16x16
Win98-manner toolbar set: those are hard-pixel, no-antialiasing by an
explicit, repeated instruction for THAT specific context (period-
accurate toolbar buttons). A file/app icon is a modern Windows shell
icon, rendered by Explorer/the taskbar at high DPI - smooth scaling is
the correct, expected look there (Windows' own system icons are not
pixel-art either), so QPainter's antialiasing stays ON here, the one
deliberate exception to this whole session's own pixel-art rule,
because the CONTEXT is different, not because the rule was forgotten.

ICO FORMAT: Qt's own ICO writer, tested empirically, does not reliably
emit multiple embedded sizes into one file (repeated QImageWriter.
write() calls silently keep only the last one - confirmed by reading
the result back and finding a single frame). GRANICE forbids adding
Pillow as a new dependency for this. The ICO container format is
simple and well-documented (a directory of PNG-compressed entries,
supported natively since Windows Vista) - _write_ico() below hand-
assembles one with the stdlib `struct` module, no new dependency.
"""
import os
import struct

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(OUT_DIR, "..", "..", ".."))
SOURCE_LOGO = os.path.join(REPO_ROOT, "runtime", "epw_os", "resources", "about_logo.png")

# Found by inspecting runtime/epw_os/resources/about_logo.png directly
# (1254x1254) - the WHOLE navy plaque (top/bottom pinstripes, "EPW",
# the "ENTRY GATE SYSTEM" tagline), not just the lettering. First
# attempt cropped the letters alone and pasted them onto a hand-picked
# navy QColor for the surrounding badge - the two navies didn't match
# (the real plaque's own background is a different shade), leaving a
# visible rectangular seam. Second attempt used a looser crop of the
# whole plaque but still caught a few pixels of the plaque's own OUTER
# grey bezel/frame on the right edge (verified: sampling pixelColor()
# along each edge showed grey ~x370-392, clean navy only up to ~x365) -
# visible as a thin grey sliver once scaled up. This crop is trimmed
# to land inside the navy interior on all four sides (verified the
# same way, sampled pixel by pixel, not guessed) - self-consistent
# navy background, no seam, no stray bezel pixels.
_EPW_PLAQUE_CROP = (470, 242, 355, 168)  # x, y, w, h

SIZES = (16, 32, 48, 256)


def _load_epw_crop() -> QImage:
    source = QImage(SOURCE_LOGO)
    if source.isNull():
        raise SystemExit(f"Could not read source logo at {SOURCE_LOGO!r} - is runtime/ present?")
    x, y, w, h = _EPW_PLAQUE_CROP
    return source.copy(x, y, w, h)


def _draw_plaque(painter: QPainter, rect: QRectF, epw_crop: QImage, border: bool = True):
    """Fills `rect` (rounded) by fitting the WHOLE `epw_crop` inside it
    (KeepAspectRatio - the plaque is ~2:1, rect is often square, so
    "cover" would crop real letters off the sides; tried that first,
    reverted - see this module's own docstring) and filling whatever
    margin is left with a color SAMPLED from the crop's own corner
    pixel (guaranteed to match - definitely background, never a
    letter), not a hand-picked QColor guess (that mismatch is exactly
    what the first version of this function got wrong)."""
    radius = rect.height() * 0.12
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    background = epw_crop.pixelColor(0, 0)
    painter.fillPath(path, background)

    painter.save()
    painter.setClipPath(path)
    scaled = epw_crop.scaled(
        max(1, round(rect.width())), max(1, round(rect.height())),
        Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
    )
    dx = rect.x() + (rect.width() - scaled.width()) / 2
    dy = rect.y() + (rect.height() - scaled.height()) / 2
    painter.drawImage(QPointF(dx, dy), scaled)
    painter.restore()

    if border:
        pen = painter.pen()
        pen.setColor(QColor(220, 220, 220))
        pen.setWidthF(max(1.0, rect.height() * 0.015))
        painter.setPen(pen)
        painter.drawPath(path)


def _render_app_icon(size: int, epw_crop: QImage) -> QImage:
    """The application icon (task 4.2) - the EPW plaque filling a
    rounded square, edge to edge (task: "Wyprowadź z logo")."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    margin = max(1, round(size * 0.04))
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    _draw_plaque(painter, rect, epw_crop)
    painter.end()
    return img


def _render_file_icon(size: int, epw_crop: QImage) -> QImage:
    """The .epw project-file icon (task 4.3) - a document silhouette
    (same folded-top-right-corner shape as studio/shell/icons/new.png,
    redrawn here at real size instead of upscaled) with the EPW plaque
    inset in its lower two-thirds - "ma się kojarzyć z DOKUMENTEM, nie
    z programem" (must read as a DOCUMENT, not the program) is exactly
    why this is a page shape carrying the badge, not the badge alone."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    margin_x = size * 0.14
    margin_y = size * 0.06
    fold = size * 0.22
    page = QRectF(margin_x, margin_y, size - 2 * margin_x, size - 2 * margin_y)

    path = QPainterPath()
    path.moveTo(page.left(), page.top())
    path.lineTo(page.right() - fold, page.top())
    path.lineTo(page.right(), page.top() + fold)
    path.lineTo(page.right(), page.bottom())
    path.lineTo(page.left(), page.bottom())
    path.closeSubpath()
    painter.fillPath(path, QColor(255, 255, 255))
    painter.setPen(QColor(30, 30, 30))
    painter.setPen(painter.pen())
    pen = painter.pen()
    pen.setWidthF(max(1.0, size * 0.012))
    painter.setPen(pen)
    painter.drawPath(path)

    fold_path = QPainterPath()
    fold_path.moveTo(page.right() - fold, page.top())
    fold_path.lineTo(page.right() - fold, page.top() + fold)
    fold_path.lineTo(page.right(), page.top() + fold)
    fold_path.closeSubpath()
    painter.fillPath(fold_path, QColor(210, 210, 210))
    painter.drawPath(fold_path)

    # The EPW badge, inset in the page's lower two-thirds.
    badge_rect = QRectF(
        page.left() + page.width() * 0.12,
        page.top() + page.height() * 0.40,
        page.width() * 0.76,
        page.height() * 0.42,
    )
    _draw_plaque(painter, badge_rect, epw_crop)

    # A few "text lines" below the badge, same convention studio/shell/
    # icons/generate_icons.py's own icon_new() already uses for "this is
    # a document with content", scaled to size.
    line_y = badge_rect.bottom() + page.height() * 0.06
    line_h = max(1.0, size * 0.02)
    for i in range(2):
        y = line_y + i * (line_h * 2.2)
        if y + line_h > page.bottom() - page.height() * 0.04:
            break
        painter.fillRect(QRectF(page.left() + page.width() * 0.18, y, page.width() * 0.5, line_h), QColor(160, 160, 160))

    painter.end()
    return img


def _image_to_png_bytes(img: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def _write_ico(path: str, images_by_size: dict):
    """Hand-assembled ICO container (PNG-compressed entries, native
    since Windows Vista) - see this module's own docstring for why Qt's
    own writer isn't used. `images_by_size`: {size: QImage}, largest
    last is NOT required (order in the file is irrelevant to Windows,
    which picks by requested size) but kept sorted here for a
    deterministic, diffable file."""
    sizes = sorted(images_by_size.keys())
    entries = []
    blobs = []
    offset = 6 + 16 * len(sizes)  # ICONDIR header + one ICONDIRENTRY per image
    for size in sizes:
        blob = _image_to_png_bytes(images_by_size[size])
        blobs.append(blob)
        dim_byte = 0 if size >= 256 else size  # 0 means "256" in ICO's own convention
        entries.append(struct.pack(
            "<BBBBHHII",
            dim_byte, dim_byte,  # width, height
            0, 0,                 # color count, reserved
            1, 32,                # planes, bit count
            len(blob), offset,
        ))
        offset += len(blob)

    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(sizes)))  # ICONDIR: reserved, type=1 (icon), count
        for entry in entries:
            f.write(entry)
        for blob in blobs:
            f.write(blob)


def generate_all():
    epw_crop = _load_epw_crop()

    app_images = {size: _render_app_icon(size, epw_crop) for size in SIZES}
    file_images = {size: _render_file_icon(size, epw_crop) for size in SIZES}

    for size, img in app_images.items():
        img.save(os.path.join(OUT_DIR, f"app_icon_{size}.png"), "PNG")
    for size, img in file_images.items():
        img.save(os.path.join(OUT_DIR, f"file_icon_{size}.png"), "PNG")

    _write_ico(os.path.join(OUT_DIR, "app_icon.ico"), app_images)
    _write_ico(os.path.join(OUT_DIR, "file_icon.ico"), file_images)

    print(f"generated app_icon_{{{','.join(map(str, SIZES))}}}.png + app_icon.ico")
    print(f"generated file_icon_{{{','.join(map(str, SIZES))}}}.png + file_icon.ico")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    generate_all()
