#!/usr/bin/env python3
"""
vision_ocr.py — macOS Vision Framework OCR backend.

Uses Apple's VNRecognizeTextRequest to perform OCR on screenshots.
No Tesseract dependency needed. Superior CJK handling (no character splitting).

Usage:
    python3 vision_ocr.py --image /path/to/screenshot.png [--lang zh-Hans,en-US] [--level fast]

Output (JSON):
    {
      "ok": true,
      "backend": "vision",
      "lang": ["zh-Hans", "en-US"],
      "boxes": [
        {
          "text": "发送",
          "confidence": 0.98,
          "box": { "x": 100, "y": 200, "width": 50, "height": 20 },
          "pixel_box": { "x": 200, "y": 400, "width": 100, "height": 40 }
        }
      ]
    }

Falls back gracefully:
  - If not macOS → ok:false, error:"macos_only"
  - If pyobjc-framework-Vision not installed → ok:false, error:"vision_unavailable"
"""
import argparse
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Locale prefix → Vision language code
_LOCALE_TO_VISION = {
    "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "zh": "zh-Hans",
    "ja": "ja-JP", "ko": "ko-KR",
    "ru": "ru-RU", "uk": "uk-UA", "th": "th-TH",
    "de": "de-DE", "fr": "fr-FR", "es": "es-ES",
    "pt": "pt-BR", "it": "it-IT",
}


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def _check_available():
    """Check if Vision framework is available. Returns error string or None."""
    if platform.system().lower() != "darwin":
        return "macos_only"
    try:
        import Vision  # noqa: F401
        import Quartz  # noqa: F401
        return None
    except ImportError:
        return "vision_unavailable"


def auto_detect_vision_langs():
    """Detect Vision OCR languages from system locale. Always includes en-US."""
    import subprocess, re
    langs = ["en-US"]
    try:
        p = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                           capture_output=True, text=True, timeout=5)
        if p.returncode == 0:
            locale_langs = re.findall(r'"([^"]+)"', p.stdout)
            for lang in locale_langs:
                for prefix, vision_code in _LOCALE_TO_VISION.items():
                    if lang.startswith(prefix) and vision_code not in langs:
                        langs.append(vision_code)
                        break
    except Exception:
        pass
    # If system is Chinese but not detected, add zh-Hans as safe default
    if len(langs) == 1:
        langs.append("zh-Hans")
    return langs


def ocr_image(image_path, languages=None, level="fast", dpi_scale=1.0):
    """
    Run Vision OCR on an image file.

    Args:
        image_path: Path to image file
        languages: List like ['zh-Hans', 'en-US']. None = auto-detect.
        level: 'fast' or 'accurate'
        dpi_scale: DPI scale factor for coordinate conversion

    Returns:
        List of box dicts with text, confidence, box (logical), pixel_box (raw)
    """
    import Vision
    import Quartz
    from Foundation import NSURL

    input_url = NSURL.fileURLWithPath_(image_path)

    # Get image dimensions
    cg_source = Quartz.CGImageSourceCreateWithURL(input_url, None)
    if cg_source is None:
        return None, "image_load_failed"
    cg_image = Quartz.CGImageSourceCreateImageAtIndex(cg_source, 0, None)
    if cg_image is None:
        return None, "image_decode_failed"
    img_w = Quartz.CGImageGetWidth(cg_image)
    img_h = Quartz.CGImageGetHeight(cg_image)

    # Collect results via completion handler
    results_holder = []
    error_holder = []

    def on_complete(request, error):
        if error:
            error_holder.append(str(error))
            return
        for obs in request.results():
            candidates = obs.topCandidates_(1)
            if not candidates:
                continue
            text = candidates[0].string()
            confidence = candidates[0].confidence()
            bbox = obs.boundingBox()

            # Vision: normalized (0-1), origin bottom-left
            # Convert to pixel coords, origin top-left
            px_x = bbox.origin.x * img_w
            px_y = (1.0 - bbox.origin.y - bbox.size.height) * img_h
            px_w = bbox.size.width * img_w
            px_h = bbox.size.height * img_h

            pixel_box = {
                "x": int(round(px_x)),
                "y": int(round(px_y)),
                "width": max(1, int(round(px_w))),
                "height": max(1, int(round(px_h))),
            }

            # Logical coords (divide by DPI scale)
            logical_box = {
                "x": int(pixel_box["x"] / dpi_scale),
                "y": int(pixel_box["y"] / dpi_scale),
                "width": max(1, int(pixel_box["width"] / dpi_scale)),
                "height": max(1, int(pixel_box["height"] / dpi_scale)),
            }

            results_holder.append({
                "text": text,
                "confidence": round(confidence * 100, 1),  # 0-100 scale like Tesseract
                "box": logical_box,
                "pixel_box": pixel_box,
            })

    # Build request
    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(on_complete)
    rec_level = 0 if level == "accurate" else 1
    request.setRecognitionLevel_(rec_level)

    # Try revision 3 (macOS 14+, best CJK)
    try:
        request.setRevision_(3)
    except Exception:
        pass

    if languages:
        request.setRecognitionLanguages_(languages)

    # Execute
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(input_url, {})
    success, err = handler.performRequests_error_([request], None)
    if not success:
        return None, f"vision_request_failed: {err}"
    if error_holder:
        return None, error_holder[0]

    return results_holder, None


def detect_dpi_scale(python_exec):
    """Detect DPI scale factor. Reuses desktop_ops screen-size logic."""
    import subprocess, tempfile
    try:
        desktop_ops = ROOT / "desktop_ops.py"
        p = subprocess.run([python_exec, str(desktop_ops), "screen-size"],
                           capture_output=True, text=True, check=True)
        screen = json.loads(p.stdout)
        logical_w = screen.get("width", 0)
        if logical_w <= 0:
            return 1.0

        tmp = tempfile.mktemp(prefix="dpi-probe-", suffix=".png")
        p = subprocess.run([python_exec, str(desktop_ops), "screenshot", "--output", tmp],
                           capture_output=True, text=True, check=True)
        from PIL import Image
        img = Image.open(tmp)
        pixel_w = img.width
        Path(tmp).unlink(missing_ok=True)

        if pixel_w > 0 and logical_w > 0:
            return round((pixel_w / logical_w) * 2) / 2
    except Exception:
        pass
    return 1.0


def main():
    ap = argparse.ArgumentParser(description="macOS Vision Framework OCR")
    ap.add_argument("--image", required=True, help="Path to image file")
    ap.add_argument("--lang", default="auto",
                     help="Comma-separated Vision language codes (e.g. zh-Hans,en-US). "
                          "'auto' detects from system locale.")
    ap.add_argument("--level", choices=["fast", "accurate"], default="fast",
                     help="Recognition level: fast (~150ms) or accurate (~700ms)")
    ap.add_argument("--python", default="python3",
                     help="Python executable for DPI detection")
    ap.add_argument("--dpi-scale", type=float, default=0,
                     help="Override DPI scale (0 = auto-detect)")
    args = ap.parse_args()

    err = _check_available()
    if err:
        jprint({"ok": False, "error": err, "backend": "vision"})
        return

    # Resolve languages
    if args.lang == "auto":
        languages = auto_detect_vision_langs()
    else:
        languages = [l.strip() for l in args.lang.split(",")]

    # Resolve DPI
    dpi_scale = args.dpi_scale if args.dpi_scale > 0 else detect_dpi_scale(args.python)

    boxes, ocr_err = ocr_image(args.image, languages, args.level, dpi_scale)
    if ocr_err:
        jprint({"ok": False, "error": ocr_err, "backend": "vision"})
        return

    jprint({
        "ok": True,
        "backend": "vision",
        "lang": languages,
        "level": args.level,
        "dpi_scale": dpi_scale,
        "boxes": boxes,
    })


if __name__ == "__main__":
    main()
