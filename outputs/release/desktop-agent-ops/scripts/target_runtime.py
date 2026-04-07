#!/usr/bin/env python3
"""Pure targeting helpers shared by the resolver runtime."""

import re


def normalize_text(text):
    return re.sub(r"\s+", "", str(text or "").strip().lower())


def match_text(text, query, mode):
    if not query:
        return False
    source_text = str(text or "")
    if not source_text:
        return False

    normalized_text = normalize_text(source_text)
    normalized_query = normalize_text(query)

    if mode == "exact":
        return normalized_text == normalized_query
    if mode == "regex":
        return re.search(query, source_text, flags=re.IGNORECASE) is not None
    return normalized_query in normalized_text


def merge_adjacent_boxes(boxes, query, max_gap=30):
    """Merge adjacent OCR boxes when their combined text matches the query."""
    if not boxes or not query:
        return []

    normalized_query = normalize_text(query)
    sorted_boxes = sorted(
        boxes,
        key=lambda box: (
            (box.get("abs_box") or box.get("box", {})).get("y", 0),
            (box.get("abs_box") or box.get("box", {})).get("x", 0),
        ),
    )

    merged_matches = []
    consumed = set()
    limit = len(normalized_query) + 3

    for start in range(len(sorted_boxes)):
        if start in consumed:
            continue

        combined_text = ""
        combined_boxes = []
        for end in range(start, min(start + limit, len(sorted_boxes))):
            box = sorted_boxes[end]
            absolute_box = box.get("abs_box") or box.get("box", {})

            if combined_boxes:
                previous_box = combined_boxes[-1].get("abs_box") or combined_boxes[-1].get("box", {})
                previous_right = previous_box.get("x", 0) + previous_box.get("width", 0)
                current_left = absolute_box.get("x", 0)
                y_diff = abs(absolute_box.get("y", 0) - previous_box.get("y", 0))
                if current_left - previous_right > max_gap or y_diff > absolute_box.get("height", 20):
                    break

            combined_text += box.get("text", "")
            combined_boxes.append(box)

            if normalized_query not in normalize_text(combined_text):
                continue

            all_absolute_boxes = [item.get("abs_box") or item.get("box", {}) for item in combined_boxes]
            min_x = min(item.get("x", 0) for item in all_absolute_boxes)
            min_y = min(item.get("y", 0) for item in all_absolute_boxes)
            max_x = max(item.get("x", 0) + item.get("width", 0) for item in all_absolute_boxes)
            max_y = max(item.get("y", 0) + item.get("height", 0) for item in all_absolute_boxes)
            avg_confidence = sum(item.get("confidence", 0) for item in combined_boxes) / len(combined_boxes)
            merged_matches.append({
                "text": combined_text,
                "confidence": avg_confidence,
                "abs_box": {
                    "x": min_x,
                    "y": min_y,
                    "width": max_x - min_x,
                    "height": max_y - min_y,
                },
            })

            for index in range(start, end + 1):
                consumed.add(index)
            break

    return merged_matches


def choose_best(results):
    candidates = []
    for result in results:
        if not result.get("ok"):
            continue
        candidates.extend(result.get("matches", []))

    if not candidates:
        return None

    return sorted(candidates, key=lambda candidate: candidate.get("confidence", 0.0), reverse=True)[0]
