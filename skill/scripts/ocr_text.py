#!/usr/bin/env python3
"""
ocr_text.py — Multi-backend OCR with automatic fallback.

Backend priority:
  macOS:   Vision Framework → Tesseract
  Windows: Tesseract (WinRT OCR reserved for future)
  Linux:   Tesseract

Usage:
    $PY ocr_text.py --app "AppName" --python $PY [--region-label LABEL] [--backend auto]
    $PY ocr_text.py --image /path/to/capture.png --python $PY [--backend vision]
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None

ROOT = Path(__file__).resolve().parent

# Mapping of locale prefixes to tesseract language codes
_LOCALE_TO_TESS = {
    "zh-Hans": "chi_sim", "zh-Hant": "chi_tra", "zh": "chi_sim",
    "ja": "jpn", "ko": "kor", "ar": "ara", "hi": "hin",
    "th": "tha", "vi": "vie", "ru": "rus", "de": "deu",
    "fr": "fra", "es": "spa", "pt": "por", "it": "ita",
}


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def run_json(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


# ─────────────────────────────────────────────
# Backend availability checks
# ─────────────────────────────────────────────

def _vision_available():
    """Check if macOS Vision Framework is available."""
    if platform.system().lower() != "darwin":
        return False
    try:
        import Vision  # noqa: F401
        return True
    except ImportError:
        return False


def _tesseract_available():
    """Check if Tesseract OCR is available."""
    if Image is None:
        return False
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False


def choose_backend(requested):
    """Choose the best available backend.

    Returns (backend_name, error_or_None).
    """
    system = platform.system().lower()

    if requested == "vision":
        if _vision_available():
            return "vision", None
        return None, "vision_unavailable"

    if requested == "tesseract":
        if _tesseract_available():
            return "tesseract", None
        return None, "tesseract_unavailable"

    # auto: try Vision first on macOS, then Tesseract
    if system == "darwin" and _vision_available():
        return "vision", None
    if _tesseract_available():
        return "tesseract", None

    # Nothing available
    if system == "darwin":
        return None, "no_ocr_backend: install pyobjc-framework-Vision (pip) or tesseract (brew)"
    return None, "no_ocr_backend: install tesseract"


# ─────────────────────────────────────────────
# Tesseract backend (original implementation)
# ─────────────────────────────────────────────

def _get_installed_tess_langs():
    try:
        p = subprocess.run(["tesseract", "--list-langs"],
                           capture_output=True, text=True, timeout=5)
        lines = (p.stderr + "\n" + p.stdout).strip().splitlines()
        langs = set()
        for line in lines:
            s = line.strip()
            if s and not s.startswith("List of") and "/" not in s:
                langs.add(s)
        return langs
    except Exception:
        return set()


def auto_detect_tess_lang():
    installed = _get_installed_tess_langs()
    parts = ["eng"]
    system = platform.system().lower()
    locale_langs = []
    _UNDERSCORE_LOCALE = {
        "zh_CN": "chi_sim", "zh_TW": "chi_tra",
        "ja_JP": "jpn", "ko_KR": "kor",
    }
    if system == "darwin":
        try:
            p = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                               capture_output=True, text=True, timeout=5)
            if p.returncode == 0:
                locale_langs = re.findall(r'"([^"]+)"', p.stdout)
        except Exception:
            pass
    elif system == "windows":
        try:
            import locale as _locale
            def_locale = _locale.getlocale()
            if def_locale and def_locale[0]:
                locale_langs.append(def_locale[0])
        except Exception:
            pass
    else:
        for env_var in ["LANG", "LANGUAGE", "LC_ALL"]:
            val = os.environ.get(env_var, "")
            if val:
                locale_langs.append(val.split(".")[0])

    for lang in locale_langs:
        for prefix, tess_code in _LOCALE_TO_TESS.items():
            if lang.startswith(prefix) and tess_code in installed and tess_code not in parts:
                parts.append(tess_code)
                break
        for prefix, tess_code in _UNDERSCORE_LOCALE.items():
            if lang.startswith(prefix) and tess_code in installed and tess_code not in parts:
                parts.append(tess_code)
                break
    return "+".join(parts)


def extract_text_tesseract(image_path, min_conf, lang):
    import pytesseract  # type: ignore
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang=lang)
    boxes = []
    for i in range(len(data.get("text", []))):
        text = (data["text"][i] or "").strip()
        conf_raw = data.get("conf", ["-1"])[i]
        try:
            conf = float(conf_raw)
        except Exception:
            conf = -1.0
        if not text or conf < min_conf:
            continue
        x = int(data["left"][i])
        y = int(data["top"][i])
        w = int(data["width"][i])
        h = int(data["height"][i])
        boxes.append({
            "text": text, "confidence": conf,
            "box": {"x": x, "y": y, "width": w, "height": h},
        })
    return boxes


# ─────────────────────────────────────────────
# Vision backend
# ─────────────────────────────────────────────

def extract_text_vision(image_path, min_conf, lang_str):
    """Run Vision OCR. Returns boxes in same format as Tesseract backend."""
    from vision_ocr import ocr_image, auto_detect_vision_langs

    if lang_str and lang_str != "auto":
        languages = [l.strip() for l in lang_str.split(",")]
    else:
        languages = auto_detect_vision_langs()

    # Use fast mode for interactive targeting (147ms vs 700ms)
    boxes_raw, err = ocr_image(image_path, languages, level="fast", dpi_scale=1.0)
    if err:
        return []

    boxes = []
    for b in boxes_raw:
        if b["confidence"] < min_conf:
            continue
        boxes.append({
            "text": b["text"],
            "confidence": b["confidence"],
            "box": b["pixel_box"],  # pixel coords for consistency
        })
    return boxes


# ─────────────────────────────────────────────
# DPI detection
# ─────────────────────────────────────────────

def _detect_dpi_scale(python_exec):
    try:
        desktop_ops = ROOT / "desktop_ops.py"
        screen = run_json([python_exec, str(desktop_ops), "screen-size"])
        logical_w = screen.get("width", 0)
        if logical_w <= 0:
            return 1.0
        tmp = tempfile.mktemp(prefix="dpi-probe-", suffix=".png")
        run_json([python_exec, str(desktop_ops), "screenshot", "--output", tmp])
        img = Image.open(tmp)
        pixel_w = img.width
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass
        if pixel_w > 0 and logical_w > 0:
            ratio = pixel_w / logical_w
            return round(ratio * 2) / 2
    except Exception:
        pass
    return 1.0


# ─────────────────────────────────────────────
# Region capture (shared by both backends)
# ─────────────────────────────────────────────

def capture_region(app, region_label, python_exec):
    desktop_ops = ROOT / "desktop_ops.py"
    window_regions = ROOT / "window_regions.py"

    bounds = run_json([python_exec, str(desktop_ops), "front-window-bounds", "--app", app])
    if region_label:
        region_out = run_json([
            python_exec, str(window_regions),
            "--window-x", str(bounds["x"]),
            "--window-y", str(bounds["y"]),
            "--window-width", str(bounds["width"]),
            "--window-height", str(bounds["height"]),
            "--label", region_label,
        ])
        region = region_out["region"]["absolute"]
    else:
        region = {
            "x": bounds["x"], "y": bounds["y"],
            "width": bounds["width"], "height": bounds["height"],
        }

    output = tempfile.mktemp(prefix="ocr-region-", suffix=".png")
    cap = run_json([
        python_exec, str(desktop_ops), "capture-region",
        "--x", str(region["x"]), "--y", str(region["y"]),
        "--width", str(region["width"]), "--height", str(region["height"]),
        "--output", output,
    ])
    return {
        "bounds": bounds, "region": region,
        "capture": cap, "image": output,
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--app")
    ap.add_argument("--region-label")
    ap.add_argument("--python", default="python3")
    ap.add_argument("--min-conf", type=float, default=40.0)
    ap.add_argument("--lang", default="auto",
                     help="Language code. For Tesseract: eng+chi_sim. "
                          "For Vision: zh-Hans,en-US. 'auto' = detect.")
    ap.add_argument("--backend", choices=["auto", "vision", "tesseract"],
                     default="auto",
                     help="OCR backend. 'auto' = Vision on macOS, Tesseract elsewhere.")
    args = ap.parse_args()

    # Choose backend
    backend, backend_err = choose_backend(args.backend)
    if backend_err:
        jprint({"ok": False, "error": backend_err})
        return

    # Resolve language
    lang = args.lang
    if backend == "tesseract" and lang == "auto":
        lang = auto_detect_tess_lang()

    # Source: image file or app window capture
    source = {"type": "image", "image": args.image}
    capture = None
    region = None
    bounds = None
    image_path = args.image

    if not image_path:
        if not args.app:
            jprint({"ok": False, "error": "image_or_app_required"})
            return
        capture = capture_region(args.app, args.region_label, args.python)
        image_path = capture["image"]
        region = capture["region"]
        bounds = capture["bounds"]
        source = {"type": "capture", "app": args.app,
                  "region_label": args.region_label, "image": image_path}

    # Run OCR with chosen backend
    if backend == "vision":
        boxes = extract_text_vision(image_path, args.min_conf, lang)
    else:
        boxes = extract_text_tesseract(image_path, args.min_conf, lang)

    # DPI scale for coordinate conversion
    dpi_scale = _detect_dpi_scale(args.python)

    def scale_box(b):
        return {
            "x": int(b["x"] / dpi_scale),
            "y": int(b["y"] / dpi_scale),
            "width": max(1, int(b["width"] / dpi_scale)),
            "height": max(1, int(b["height"] / dpi_scale)),
        }

    if region:
        offset_x = region["x"]
        offset_y = region["y"]
        scaled_boxes = []
        for box in boxes:
            pixel_box = box["box"]
            logical_box = scale_box(pixel_box)
            scaled_boxes.append({
                "text": box["text"],
                "confidence": box["confidence"],
                "pixel_box": pixel_box,
                "box": logical_box,
                "abs_box": {
                    "x": logical_box["x"] + offset_x,
                    "y": logical_box["y"] + offset_y,
                    "width": logical_box["width"],
                    "height": logical_box["height"],
                },
            })
        boxes = scaled_boxes
    else:
        scaled_boxes = []
        for box in boxes:
            pixel_box = box["box"]
            logical_box = scale_box(pixel_box)
            scaled_boxes.append({
                "text": box["text"],
                "confidence": box["confidence"],
                "pixel_box": pixel_box,
                "box": logical_box,
            })
        boxes = scaled_boxes

    jprint({
        "ok": True,
        "backend": backend,
        "source": source,
        "lang": lang,
        "dpi_scale": dpi_scale,
        "bounds": bounds,
        "region": region,
        "boxes": boxes,
    })


if __name__ == "__main__":
    main()
