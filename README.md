# 🧪 Pipeek

**Pipeek** is a **fast, stream-based CLI tool** for searching digit or byte patterns inside **large text files** or **compressed archives** — designed with performance and flexibility in mind.

> ⚠️ **Note**
> This project is a work in progress. Some features are still under development. Bug reports and contributions are welcome!

---

## 📦 Installation

> **Requirements**: Python **3.8+**

Install from [PyPI](https://pypi.org/project/pipeek):

```bash
pip install pipeek
```

To install from source (for development):

```bash
git clone https://github.com/danilopatrial/pipeek.git
cd pipeek
pip install -e .
```

---

## 🚀 Quick Start

See the available commands and options:

```bash
pipeek --help
```

Search for a pattern:

```bash
pipeek needle 42 ./data/
```

You can use it on single files, multiple files, or entire folders — including compressed formats like `.gz`, `.bz2`, `.xz`, and `.lzma`.

---

## ⚙️ Configuration

Pipeek uses a configuration file stored in your system’s config directory:

* **Linux/macOS**: `~/.config/pipeek/config.json`
* **Windows**: `%APPDATA%\pipeek\config.json`

To open the config file in your editor (default is `nvim`):

```bash
pipeek conf
```

Specify a different editor:

```bash
pipeek conf -e code
```

Restore default settings:

```bash
pipeek conf --restore
```

---

## 💡 Features

* 🔍 Stream-based search: optimized for **low memory usage**
* 🗜️ Supports compressed files: `.gz`, `.bz2`, `.xz`, `.lzma`
* 🧠 Configurable buffer size, max matches, and context window
* 📁 Accepts multiple files and directories
* 📋 Saves search logs to `pipeek.log` in the config directory
* 🖍️ Optional colored output (via `colorama`)
* 🧪 Easily extensible and built with readability in mind

---

## 📚 Command Overview

All commands support `--help` for usage instructions:

```bash
pipeek conf --help
pipeek needle --help
```

### 🔎 Search for a Pattern

```bash
pipeek needle 31415 data.txt
```

Search through a directory recursively:

```bash
pipeek needle 42 ./data/
```

Force reading as gzip:

```bash
pipeek needle 2718 compressed.gz --force-gzip
```

---

[MIT License](LICENSE) © 2025 [Danilo Patrial](https://github.com/danilopatrial)
