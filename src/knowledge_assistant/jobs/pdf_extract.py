"""PDF -> markdown, run in a child process so a parser crash fails one job, not the server.

Default engine is PyMuPDF (fast, small). docling is optional (`pip install knowledge-assistant[docling]`)
and gives better tables/layout at the cost of a large install.

Usage as a script (what the parent spawns):  python -m knowledge_assistant.jobs.pdf_extract <pdf> <engine>
Prints markdown to stdout.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def extract_markdown(pdf_path: Path, engine: str = "pymupdf") -> str:
    if engine == "docling":
        from docling.document_converter import DocumentConverter

        return DocumentConverter().convert(str(pdf_path)).document.export_to_markdown()
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf_path))


def extract_in_subprocess(pdf_path: Path, engine: str = "pymupdf", timeout_s: int = 600) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "knowledge_assistant.jobs.pdf_extract", str(pdf_path), engine],
        capture_output=True, text=True, timeout=timeout_s,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError(f"PDF extraction failed (exit {proc.returncode}): {' | '.join(tail)}")
    return proc.stdout


if __name__ == "__main__":
    sys.stdout.write(extract_markdown(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "pymupdf"))
