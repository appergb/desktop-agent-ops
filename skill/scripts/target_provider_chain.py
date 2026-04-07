#!/usr/bin/env python3
"""Provider wrappers and orchestration for target resolution."""

import json
import subprocess

from target_runtime import match_text, merge_adjacent_boxes


AX_MIN_ELEMENTS = 10


def run_json(cmd):
    process = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(process.stdout)


def accessibility_provider(args, root):
    if not args.text:
        return {"name": "accessibility", "ok": False, "error": "text_query_required"}

    accessibility_script = root / "accessibility_provider.py"
    if not accessibility_script.exists():
        return {"name": "accessibility", "ok": False, "error": "accessibility_provider_not_found"}

    try:
        cmd = [
            args.python,
            str(accessibility_script),
            "--app",
            args.app,
            "--text",
            args.text,
            "--text-match",
            args.text_match,
        ]
        output = run_json(cmd)
    except Exception as exc:
        return {"name": "accessibility", "ok": False, "error": str(exc)}

    if not output.get("ok"):
        return {
            "name": "accessibility",
            "ok": False,
            "error": output.get("error", "unknown"),
            "hint": output.get("hint"),
        }

    element_count = output.get("element_count", 0)
    matches = output.get("matches", [])
    if element_count < AX_MIN_ELEMENTS:
        return {
            "name": "accessibility",
            "ok": True,
            "degraded": True,
            "element_count": element_count,
            "matches": [],
            "reason": f"only {element_count} elements found, app likely hides accessibility tree",
        }

    return {
        "name": "accessibility",
        "ok": True,
        "degraded": False,
        "element_count": element_count,
        "matches": matches,
        "backend": output.get("backend"),
        "platform": output.get("platform"),
    }


def ocr_provider(args, root, region_label):
    if not args.text:
        return {"name": "ocr_text", "ok": False, "error": "text_query_required"}

    script = root / "ocr_text.py"
    try:
        cmd = [
            args.python,
            str(script),
            "--app",
            args.app,
            "--min-conf",
            str(args.ocr_min_conf),
            "--python",
            args.python,
        ]
        if region_label:
            cmd += ["--region-label", region_label]
        output = run_json(cmd)
    except Exception as exc:
        return {"name": "ocr_text", "ok": False, "error": str(exc)}

    if not output.get("ok"):
        return {"name": "ocr_text", "ok": False, "error": output.get("error")}

    backend = output.get("backend", "tesseract")
    matches = []

    for box in output.get("boxes", []):
        text = box.get("text", "")
        if not match_text(text, args.text, args.text_match):
            continue
        absolute_box = box.get("abs_box") or box.get("box") or {}
        x = absolute_box.get("x")
        y = absolute_box.get("y")
        width = absolute_box.get("width")
        height = absolute_box.get("height")
        if None in (x, y, width, height):
            continue
        confidence = float(box.get("confidence", 0.0))
        matches.append({
            "x": int(x + width / 2),
            "y": int(y + height / 2),
            "width": int(width),
            "height": int(height),
            "confidence": min(1.0, max(0.0, confidence / 100.0)),
            "label": f"text:{text}",
            "source": f"ocr_{backend}",
        })

    if not matches and args.text_match != "regex" and backend == "tesseract":
        merged = merge_adjacent_boxes(output.get("boxes", []), args.text)
        for match in merged:
            absolute_box = match["abs_box"]
            matches.append({
                "x": int(absolute_box["x"] + absolute_box["width"] / 2),
                "y": int(absolute_box["y"] + absolute_box["height"] / 2),
                "width": int(absolute_box["width"]),
                "height": int(absolute_box["height"]),
                "confidence": min(1.0, max(0.0, match["confidence"] / 100.0)),
                "label": f"text_merged:{match['text']}",
                "source": "ocr_tesseract_merged",
            })

    return {
        "name": "ocr_text",
        "ok": True,
        "backend": backend,
        "matches": matches,
        "source": output.get("source"),
        "region": output.get("region"),
    }


def template_provider(args, root, region_label):
    if not args.template:
        return {"name": "template_match", "ok": False, "error": "template_required"}

    script = root / "template_match.py"
    try:
        cmd = [
            args.python,
            str(script),
            "--app",
            args.app,
            "--template",
            args.template,
            "--threshold",
            str(args.template_threshold),
            "--max-matches",
            str(args.template_max_matches),
        ]
        if region_label:
            cmd += ["--region-label", region_label]
        output = run_json(cmd)
    except Exception as exc:
        return {"name": "template_match", "ok": False, "error": str(exc)}

    if not output.get("ok"):
        return {"name": "template_match", "ok": False, "error": output.get("error")}

    matches = []
    for match in output.get("matches", []):
        x = match["x"]
        y = match["y"]
        width = match["width"]
        height = match["height"]
        score = float(match.get("score", 0.0))
        matches.append({
            "x": int(x + width / 2),
            "y": int(y + height / 2),
            "width": int(width),
            "height": int(height),
            "confidence": min(1.0, max(0.0, score)),
            "label": "template_match",
            "source": "template_match",
        })

    return {
        "name": "template_match",
        "ok": True,
        "matches": matches,
        "source": output.get("source"),
        "region": output.get("region"),
    }


def heuristic_provider(args, root):
    if not args.label:
        return {"name": "heuristic_region", "ok": False, "error": "label_required"}

    script = root / "target_report.py"
    try:
        output = run_json([
            args.python,
            str(script),
            "--app",
            args.app,
            "--label",
            args.label,
            "--python",
            args.python,
        ])
    except Exception as exc:
        return {"name": "heuristic_region", "ok": False, "error": str(exc)}

    matches = []
    region_abs = output.get("region", {}).get("absolute", {})
    for candidate in output.get("candidates", []):
        matches.append({
            "x": candidate["x"],
            "y": candidate["y"],
            "width": region_abs.get("width", 0),
            "height": region_abs.get("height", 0),
            "confidence": 0.2,
            "label": f"heuristic:{candidate.get('label', 'unknown')}",
            "source": "heuristic_region",
        })

    return {"name": "heuristic_region", "ok": True, "matches": matches, "region": output.get("region")}


def run_provider_chain(args, root):
    providers = [item.strip() for item in args.providers.split(",") if item.strip()]
    results = []
    region_label = args.region_label or args.label

    for provider in providers:
        if provider == "accessibility":
            result = accessibility_provider(args, root)
            results.append(result)
            if result.get("ok") and not result.get("degraded") and result.get("matches"):
                break
            continue
        if provider == "ocr_text":
            result = ocr_provider(args, root, region_label)
            results.append(result)
            if result.get("ok") and result.get("matches"):
                break
            continue
        if provider == "template_match":
            result = template_provider(args, root, region_label)
            results.append(result)
            if result.get("ok") and result.get("matches"):
                break
            continue
        if provider == "heuristic_region":
            result = heuristic_provider(args, root)
            results.append(result)
            if result.get("ok") and result.get("matches"):
                break
            continue
        results.append({"name": provider, "ok": False, "error": "unknown_provider"})

    return results


__all__ = [
    "AX_MIN_ELEMENTS",
    "accessibility_provider",
    "ocr_provider",
    "template_provider",
    "heuristic_provider",
    "run_json",
    "run_provider_chain",
]
