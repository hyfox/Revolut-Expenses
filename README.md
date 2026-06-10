# Revolut → E‑conomic Connector

A small Python project that helps connect **Revolut Business** with the Danish accounting system **E‑conomic** (by Visma).
Maintained as a **hobby project by Albert Fox** (CEO of Performativ) and used internally at Performativ for more than a year.

The goal is to make reconciled bookkeeping with Revolut Business **fast, reproducible, and less painful**.
With this tool, we bring a full month of reconciled transactions into E‑conomic in about **1 hour total**.

---

## Features

* **Imports expenses from Revolut Business CSV exports**
* **Processes receipts/attachments** and maps them to E‑conomic entries
* **Interactive GUI** for stepping through bookkeeping tasks
* **Secure credential storage** via OS keychain (Windows Credential Manager or macOS Keychain)
* **Pushes data to E‑conomic REST API** with vouchers, VAT, contra accounts, and attachments
* **File renaming & cleanup** so your receipts match journal entries neatly

---

## How It Works

The project is split into two files:

* **`Main.py`**
  Provides a simple Tkinter GUI with buttons for each step:
  *Save credentials → Gather data → Load settings → Verify data → Ship to E‑conomic → Split files*

* **`Economic.py`**
  Handles the heavy lifting: reading CSVs, mapping accounts, preparing vouchers, calling E‑conomic APIs, and managing local file storage.

---

## Getting Started

### Option 1 — Windows, no Python required

1. Download `RevolutExpenses-windows.zip` from the [latest release](../../releases/latest).
2. Extract it anywhere (right‑click → *Extract All…*).
3. Open the extracted folder and double‑click `RevolutExpenses.exe`.

The app ships as a folder rather than a single `.exe` on purpose: a single‑file build has to unpack ~30 MB to a temp directory (and get rescanned by your antivirus) on every launch, which makes startup very slow.

> Windows SmartScreen may warn about an unsigned executable the first time — choose *More info → Run anyway*.

### Option 2 — Windows, run from source

1. Install [Python 3.9+](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"** during installation).
2. Clone or download this repository.
3. Double‑click **`run_windows.bat`**. It creates a local virtual environment, installs the dependencies, and launches the GUI.

### Option 3 — Any platform, manual

* Python 3.9+
* `tkinter` (usually bundled with Python)

```bash
pip install -r requirements.txt
python Main.py
```

### Setup

1. Launch the app (see above).

2. First step: **Save credentials**.
   You’ll be asked for your E‑conomic API AppSecretToken and Agreement Grant Token. These are stored securely in your OS keychain.

3. Export your **expenses.csv** from Revolut Business and place receipts in the same folder.

4. Click through the steps in the GUI to:

   * Load your settings JSON
   * Process expenses
   * Select the journal in E‑conomic
   * Ship entries + attachments

---

## Security Notes

* **No hardcoded tokens**: You must save your own tokens to your OS keychain.
* The `.exe` builds created with PyInstaller still contain your logic but not your secrets. Tokens remain safe in your OS credential store.

---

## Project Status

* This is **not an official Performativ product**.
* It’s a **hobby project**, built to scratch our own itch, and open‑sourced in case others find it useful.
* Used successfully for 12+ months at Performativ.

---

## Contributing

Contributions are very welcome!
Ideas include:

* Support for additional banks besides Revolut
* More automation of VAT mapping
* Better progress/error reporting in the GUI

Fork, improve, and submit a PR — or open an issue if you want to discuss improvements.

---

## Maintainer

**Albert Fox**
Founder & CEO, [Performativ](https://performativ.com)
Maintaining this project in his spare time — opinions and bugs are his own 😉