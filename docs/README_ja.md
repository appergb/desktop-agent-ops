<div align="center">

# 🖥️ Desktop Agent Ops

**AIエージェント向けクロスプラットフォームデスクトップGUI自動化スキル**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/対応-macOS%20%7C%20Windows%20%7C%20Linux-blue.svg)](../README.md#-supported-platforms)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org)
[![Release](https://img.shields.io/github/v/release/appergb/desktop-agent-ops)](https://github.com/appergb/desktop-agent-ops/releases)

**[English](../README.md)** | **[中文](README_zh.md)** | **[日本語](README_ja.md)**

</div>

---

## 📖 Desktop Agent Ops とは？

Desktop Agent Ops は、Claude Code・Codex・GPT などの AI エージェントが**デスクトップアプリケーションを見て、理解し、操作できる**ようにする AI エージェントスキルです。

**画面観察**から**正確なクリック**までの完全なパイプラインを提供し、誤ったUI要素をクリックすることを防ぐ安全機構を内蔵しています。

### 主な機能

| 機能 | 説明 |
|------|------|
| 🔍 **ウィンドウスコープ OCR** | 対象アプリのウィンドウ内のみを OCR スキャン — 別アプリのボタンを誤クリックしない |
| 🎯 **OCR ファースト** | テキスト内容で UI 要素を検索。座標の推測ではない |
| 📐 **DPI 自動対応** | Retina/HiDPI スケーリングを全プラットフォームで自動検出 |
| 🌐 **多言語 OCR** | システム言語を自動検出し、対応する Tesseract 言語パックをインストール |
| ⌨️ **CJK テキスト入力** | クリップボード貼り付けによる確実な日本語・中国語・韓国語入力 |
| 🔧 **ワンコマンドセットアップ** | `first_run_setup.py` が初回使用時にすべてを自動インストール |
| 🖱️ **17 種の操作** | スクリーンショット、クリック、入力、スクロール、ドラッグ、ホットキーなど |

---

## ⚡ クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/appergb/desktop-agent-ops.git
cd desktop-agent-ops

# ワンコマンドセットアップ（すべての依存関係を自動インストール）
python3 skill/scripts/first_run_setup.py

# 準備状態を確認
python3 skill/scripts/first_run_setup.py --check
```

### 使用例

```bash
# 📸 スクリーンショット
$PY skill/scripts/desktop_ops.py screenshot --output screen.png

# 🔍 アプリウィンドウ内のテキストを検索
$PY skill/scripts/target_resolver.py --app "Safari" --text "検索" --python $PY

# 🖱️ クリック
$PY skill/scripts/desktop_ops.py click --x 450 --y 520

# ⌨️ テキスト入力（日本語対応）
$PY skill/scripts/desktop_ops.py type --text "こんにちは世界"
```

---

## 🎯 ターゲティングパイプライン（6ステップ）

```
1. 対象アプリにフォーカス → 最前面に表示
2. ウィンドウ境界を取得   → 正確な位置とサイズ
3. ウィンドウ領域のみキャプチャ
4. ウィンドウ内で OCR（DPI 自動スケーリング）
5. ターゲット位置を検証（ウィンドウ範囲内か確認）
6. 検証後にクリック
```

---

## 📄 ライセンス

[MIT License](../LICENSE)

---

<div align="center">

**デスクトップアプリを見て操作する必要がある AI エージェントのために。**

[⬆ トップへ戻る](#-desktop-agent-ops) | [English](../README.md) | [中文](README_zh.md)

</div>
