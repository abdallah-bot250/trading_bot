from pathlib import Path


BAD = {"\u00d8", "\u00d9", "\u00c3", "\u00c2", "\u00e2", "\ufffd"} | {chr(i) for i in range(0x80, 0xA0)}
EXTENSIONS = {".py", ".html", ".js", ".css"}


def main():
    hits = []
    for path in Path(".").rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(char in line for char in BAD):
                hits.append((str(path), line_no, line[:160]))
                break

    for filename, line_no, line in hits:
        print(f"{filename}:{line_no}:{line}")
    print(f"COUNT={len(hits)}")


if __name__ == "__main__":
    main()
