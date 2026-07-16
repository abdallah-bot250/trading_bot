from pathlib import Path


BAD = (
    "\u00c3\u0192",
    "\u00c3\u201a",
    "\u00c3\u00a2",
    "\u00c3\u00b0",
    "\u00f0\u0178",
    "\u00e2\u0153",
    "\u00e2\u009d",
    "\u0393",
    "\u00ef\u00bf\u00bd",
    "\ufffd",
)
EXTENSIONS = {".py", ".html", ".js", ".css"}


def main():
    hits = []
    for path in Path(".").rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(marker in line for marker in BAD):
                hits.append((str(path), line_no, line[:160]))
                break

    for filename, line_no, line in hits:
        print(f"{filename}:{line_no}:{line}")
    print(f"COUNT={len(hits)}")


if __name__ == "__main__":
    main()
