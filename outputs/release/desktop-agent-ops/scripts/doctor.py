#!/usr/bin/env python3
import importlib.util
import json
import os
import platform
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESKTOP_OPS = ROOT / 'desktop_ops.py'

from resolve_python import resolve_python, PERMISSION_HOME
PERMISSION_STATE = PERMISSION_HOME / "permissions.json"

PY = resolve_python()


def check_mod(name):
    return importlib.util.find_spec(name) is not None


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        'ok': p.returncode == 0,
        'code': p.returncode,
        'stdout': p.stdout.strip(),
        'stderr': p.stderr.strip(),
    }


if __name__ == "__main__":
    report = {
        'platform': platform.system().lower(),
        'python': PY,
        'deps': {
            'pyautogui': run([PY, '-c', 'import pyautogui; print("ok")'])['ok'],
            'PIL': run([PY, '-c', 'from PIL import Image; print("ok")'])['ok'],
            'pytesseract': run([PY, '-c', 'import pytesseract; print("ok")'])['ok'],
            'cv2': run([PY, '-c', 'import cv2; print("ok")'])['ok'],
            'pyatspi': run([PY, '-c', 'import pyatspi; print("ok")'])['ok'],
            'powershell_bin': shutil.which('powershell') is not None or shutil.which('pwsh') is not None,
            'tesseract_bin': shutil.which('tesseract') is not None,
        },
        'permissions': {
            'state_file': str(PERMISSION_STATE),
            'completed': False,
        },
        'checks': {}
    }

    try:
        if PERMISSION_STATE.exists():
            state = json.loads(PERMISSION_STATE.read_text())
            report['permissions']['completed'] = bool(state.get('completed'))
            report['permissions']['state'] = state
    except Exception:
        report['permissions']['error'] = 'permission_state_read_failed'

    report['checks']['frontmost'] = run([PY, str(DESKTOP_OPS), 'frontmost'])
    report['checks']['screenshot'] = run([PY, str(DESKTOP_OPS), 'screenshot'])
    report['checks']['mouse_position_before'] = run([PY, str(DESKTOP_OPS), 'mouse-position'])
    report['checks']['move'] = run([PY, str(DESKTOP_OPS), 'move', '--x', '400', '--y', '400', '--duration', '0.1'])
    report['checks']['mouse_position_after'] = run([PY, str(DESKTOP_OPS), 'mouse-position'])

    # --- OCR backend checks ---
    ocr = {'vision': False, 'tesseract': False, 'vision_boxes': 0, 'tesseract_boxes': 0}

    # Check Vision OCR (macOS)
    if platform.system().lower() == 'darwin':
        vision_check = run([PY, '-c', 'import Vision; print("ok")'])
        ocr['vision'] = vision_check['ok']
        # Live test: if screenshot succeeded, try Vision OCR on it
        screenshot_result = report['checks'].get('screenshot', {})
        if ocr['vision'] and screenshot_result.get('ok'):
            try:
                ss_out = json.loads(screenshot_result.get('stdout', '{}'))
                ss_path = ss_out.get('output', ss_out.get('path', ''))
                if ss_path and Path(ss_path).exists():
                    vision_ocr_script = ROOT / 'vision_ocr.py'
                    r = run([PY, str(vision_ocr_script), '--image', ss_path, '--level', 'fast'])
                    if r['ok']:
                        try:
                            vdata = json.loads(r['stdout'])
                            ocr['vision_boxes'] = len(vdata.get('boxes', []))
                        except Exception:
                            pass
            except Exception:
                pass

    # Check Tesseract OCR
    tess_ok = report['deps'].get('pytesseract', False) and report['deps'].get('tesseract_bin', False)
    ocr['tesseract'] = tess_ok
    if tess_ok:
        # Check installed languages
        tess_langs = run(['tesseract', '--list-langs'])
        if tess_langs['ok']:
            lines = (tess_langs['stderr'] + '\n' + tess_langs['stdout']).strip().splitlines()
            lang_list = [l.strip() for l in lines if l.strip() and not l.strip().startswith('List of') and '/' not in l.strip()]
            ocr['tesseract_langs'] = lang_list[:20]  # first 20
            ocr['tesseract_lang_count'] = len(lang_list)
            # Check if CJK langs are available
            cjk = [l for l in lang_list if l in ('chi_sim', 'chi_tra', 'jpn', 'kor')]
            ocr['tesseract_cjk'] = cjk if cjk else 'none installed'

    report['ocr'] = ocr

    # --- Summary ---
    all_deps_ok = all(report['deps'].values())
    any_ocr_ok = ocr['vision'] or ocr['tesseract']
    screenshot_ok = report['checks'].get('screenshot', {}).get('ok', False)

    report['summary'] = {
        'deps_ok': all_deps_ok,
        'screenshot_ok': screenshot_ok,
        'ocr_available': any_ocr_ok,
        'ocr_working': ocr.get('vision_boxes', 0) > 0 or ocr.get('tesseract', False),
        'recommended_backend': 'vision' if ocr['vision'] else ('tesseract' if ocr['tesseract'] else 'none'),
    }

    if not any_ocr_ok:
        report['summary']['fix'] = (
            'No OCR backend available. '
            'macOS: pip install pyobjc-framework-Vision (recommended) or brew install tesseract. '
            'Linux/Windows: install tesseract and pip install pytesseract.'
        )

    if report['platform'] == 'windows':
        report['summary']['windows_uia_note'] = (
            'Windows UI Automation may fail against elevated targets if this process runs at a lower privilege level.'
        )
    if report['platform'] == 'linux':
        report['summary']['linux_atspi_note'] = (
            'GNOME structured accessibility targeting requires AT-SPI bindings such as pyatspi.'
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
