#!/usr/bin/env python3
"""Windows UI Automation provider."""

import json
import os
import platform
import re
import shutil
import subprocess


POWERSHELL_QUERY = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$appName = $env:DESKTOP_AGENT_OPS_UIA_APP
$maxDepth = [int]$env:DESKTOP_AGENT_OPS_UIA_MAX_DEPTH

function Get-Rect($element) {
  try {
    $rect = $element.Current.BoundingRectangle
    if ($rect.Width -le 0 -or $rect.Height -le 0) { return $null }
    return @{
      left = [int][Math]::Round($rect.Left)
      top = [int][Math]::Round($rect.Top)
      width = [int][Math]::Round($rect.Width)
      height = [int][Math]::Round($rect.Height)
    }
  } catch { return $null }
}

function Export-Element($element, $depth) {
  $rect = Get-Rect $element
  $controlType = $null
  try { $controlType = $element.Current.ControlType.ProgrammaticName } catch {}
  if ($controlType -and $controlType.Contains('.')) {
    $controlType = $controlType.Split('.')[-1]
  }
  return @{
    depth = $depth
    name = $element.Current.Name
    control_type = $controlType
    class_name = $element.Current.ClassName
    automation_id = $element.Current.AutomationId
    is_enabled = $element.Current.IsEnabled
    has_keyboard_focus = $element.Current.HasKeyboardFocus
    is_offscreen = $element.Current.IsOffscreen
    rect = $rect
  }
}

function Walk($walker, $element, $depth, $maxDepth, $results) {
  if ($depth -gt $maxDepth) { return }
  $results.Add((Export-Element $element $depth)) | Out-Null
  $child = $walker.GetFirstChild($element)
  while ($child -ne $null) {
    Walk $walker $child ($depth + 1) $maxDepth $results
    $child = $walker.GetNextSibling($child)
  }
}

$root = [System.Windows.Automation.AutomationElement]::RootElement
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
$target = $null

foreach ($candidate in $windows) {
  try {
    $name = $candidate.Current.Name
    if ($name -and $name.ToLower().Contains($appName.ToLower())) {
      $target = $candidate
      break
    }
  } catch {}
}

if ($target -eq $null) {
  @{
    ok = $false
    error = "app_not_found"
    app = $appName
  } | ConvertTo-Json -Depth 6 -Compress
  exit 0
}

$results = New-Object System.Collections.ArrayList
Walk $walker $target 0 $maxDepth $results

@{
  ok = $true
  app = $target.Current.Name
  element_count = $results.Count
  elements = $results
} | ConvertTo-Json -Depth 8 -Compress
"""


def _permission_error(hint, error):
    return {
        "ok": False,
        "platform": "windows",
        "backend": "uia",
        "error": error,
        "hint": hint,
        "matches": [],
    }


def _normalize_text(value):
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _match_text(value, query, mode):
    if not query:
        return False
    text = str(value or "")
    if not text:
        return False
    if mode == "regex":
        return re.search(query, text, flags=re.IGNORECASE) is not None
    normalized_text = _normalize_text(text)
    normalized_query = _normalize_text(query)
    if mode == "exact":
        return normalized_text == normalized_query
    return normalized_query in normalized_text


def _normalize_element(raw):
    rect = raw.get("rect") or {}
    left = int(rect.get("left", 0))
    top = int(rect.get("top", 0))
    width = int(rect.get("width", 0))
    height = int(rect.get("height", 0))
    element = {
        "role": raw.get("control_type"),
        "title": raw.get("name"),
        "description": None,
        "value": None,
        "automation_id": raw.get("automation_id"),
        "class_name": raw.get("class_name"),
        "states": {
            "enabled": bool(raw.get("is_enabled", False)),
            "focused": bool(raw.get("has_keyboard_focus", False)),
            "selected": False,
            "visible": not bool(raw.get("is_offscreen", False)),
            "offscreen": bool(raw.get("is_offscreen", False)),
        },
    }
    if width > 0 and height > 0:
        element["position"] = {"x": left, "y": top}
        element["size"] = {"w": width, "h": height}
    return element


def _normalize_match(raw):
    left = int(raw.get("left", 0))
    top = int(raw.get("top", 0))
    width = int(raw.get("width", 0))
    height = int(raw.get("height", 0))
    return {
        "text": raw.get("name") or raw.get("automation_id") or raw.get("class_name") or "",
        "role": raw.get("control_type"),
        "x": int(left + width / 2),
        "y": int(top + height / 2),
        "width": width,
        "height": height,
        "confidence": 1.0,
        "source": "accessibility",
        "label": f'uia:{raw.get("control_type", "")}:{raw.get("name", "")}',
    }


def _run_powershell(app_name, max_depth):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return _permission_error("uia_unavailable", "powershell_missing")
    env = {
        **os.environ,
        "DESKTOP_AGENT_OPS_UIA_APP": app_name,
        "DESKTOP_AGENT_OPS_UIA_MAX_DEPTH": str(max_depth),
    }
    try:
        proc = subprocess.run(
            [powershell, "-NoProfile", "-Command", POWERSHELL_QUERY],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return _permission_error("uia_unavailable", "uia_query_timeout")
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if stderr and ("Access is denied" in stderr or "denied" in stderr.lower()):
        return _permission_error("windows_uipi_blocked", "uia_access_denied")
    if proc.returncode != 0:
        return _permission_error("uia_unavailable", stderr or "uia_query_failed")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return _permission_error("uia_unavailable", "uia_output_parse_failed")


def run_windows_uia_query(app_name, text=None, text_match="contains", max_depth=6):
    if platform.system().lower() != "windows":
        return {"ok": False, "platform": platform.system().lower(), "error": "windows_only", "matches": []}

    raw = _run_powershell(app_name, max_depth)
    if not raw.get("ok"):
        return raw

    normalized_elements = []
    normalized_matches = []
    for element in raw.get("elements", []):
        normalized = _normalize_element(element)
        normalized_elements.append(normalized)
        rect = element.get("rect") or {}
        if not rect or int(rect.get("width", 0)) <= 0 or int(rect.get("height", 0)) <= 0:
            continue
        candidates = [
            element.get("name"),
            element.get("automation_id"),
            element.get("class_name"),
        ]
        if any(_match_text(candidate, text, text_match) for candidate in candidates):
            normalized_matches.append(_normalize_match({
                "name": element.get("name"),
                "automation_id": element.get("automation_id"),
                "class_name": element.get("class_name"),
                "control_type": element.get("control_type"),
                "left": rect.get("left", 0),
                "top": rect.get("top", 0),
                "width": rect.get("width", 0),
                "height": rect.get("height", 0),
            }))

    return {
        "ok": True,
        "platform": "windows",
        "backend": "uia",
        "app": raw.get("app", app_name),
        "element_count": len(normalized_elements),
        "elements": normalized_elements,
        "matches": normalized_matches,
    }
