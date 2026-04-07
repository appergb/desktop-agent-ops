#!/usr/bin/env python3
import argparse
import json
import sys


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def candidate_points(x, y, width, height, inset=12):
    # Clamp inset to prevent inverted coordinates on small elements
    effective_inset_x = min(inset, width // 2)
    effective_inset_y = min(inset, height // 2)
    left = x + effective_inset_x
    right = x + width - effective_inset_x
    top = y + effective_inset_y
    bottom = y + height - effective_inset_y
    cx = x + width // 2
    cy = y + height // 2
    return [
        {"label": "center", "x": cx, "y": cy},
        {"label": "upper_middle", "x": cx, "y": top + max(0, (cy - top) // 2)},
        {"label": "lower_middle", "x": cx, "y": cy + max(0, (bottom - cy) // 2)},
        {"label": "left_middle", "x": left, "y": cy},
        {"label": "right_middle", "x": right, "y": cy},
    ]


def region_from_window(x, y, width, height, anchor, dx=0, dy=0, rw=None, rh=None):
    if anchor == "bottom_input":
        return {
            "x": x + int(width * 0.28) + dx,
            "y": y + int(height * 0.80) + dy,
            "width": rw or int(width * 0.66),
            "height": rh or int(height * 0.16),
            "label": "bottom_input",
        }
    if anchor == "left_sidebar_top":
        return {
            "x": x + dx,
            "y": y + int(height * 0.08) + dy,
            "width": rw or int(width * 0.28),
            "height": rh or int(height * 0.25),
            "label": "left_sidebar_top",
        }
    if anchor == "top_search":
        return {
            "x": x + int(width * 0.02) + dx,
            "y": y + int(height * 0.03) + dy,
            "width": rw or int(width * 0.24),
            "height": rh or int(height * 0.08),
            "label": "top_search",
        }
    jprint({"ok": False, "error": f"unsupported anchor: {anchor}",
            "supported": ["bottom_input", "left_sidebar_top", "top_search"]})
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("candidate-points")
    p1.add_argument("--x", type=int, required=True)
    p1.add_argument("--y", type=int, required=True)
    p1.add_argument("--width", type=int, required=True)
    p1.add_argument("--height", type=int, required=True)
    p1.add_argument("--inset", type=int, default=12)

    p2 = sub.add_parser("region-from-window")
    p2.add_argument("--x", type=int, required=True)
    p2.add_argument("--y", type=int, required=True)
    p2.add_argument("--width", type=int, required=True)
    p2.add_argument("--height", type=int, required=True)
    p2.add_argument("--anchor", required=True)
    p2.add_argument("--dx", type=int, default=0)
    p2.add_argument("--dy", type=int, default=0)
    p2.add_argument("--rw", type=int)
    p2.add_argument("--rh", type=int)

    args = ap.parse_args()
    if args.cmd == "candidate-points":
        points = candidate_points(args.x, args.y, args.width, args.height, args.inset)
        jprint({"ok": True, "points": points})
    else:
        region = region_from_window(args.x, args.y, args.width, args.height, args.anchor, args.dx, args.dy, args.rw, args.rh)
        jprint({"ok": True, "region": region})


if __name__ == "__main__":
    main()
