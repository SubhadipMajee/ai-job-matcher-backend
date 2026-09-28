"""
diff_engine.py — compute a structured diff between the original and
tailored resume so the frontend can render a side-by-side view.

Returns a list of chunks, each with:
  { "type": "added" | "removed" | "unchanged", "text": "..." }

Uses Python's built-in difflib — no new packages needed.
"""

import difflib


def compute_diff(original: str, tailored: str) -> list[dict]:
    """
    Compare original and tailored resume text line by line.

    Returns a list of dicts the frontend can render directly:
      - "unchanged" lines appear in both versions (grey/normal)
      - "removed"   lines were in the original but dropped (red)
      - "added"     lines are new in the tailored version (green)
    """
    original_lines = original.splitlines(keepends=True)
    tailored_lines = tailored.splitlines(keepends=True)

    differ = difflib.ndiff(original_lines, tailored_lines)

    chunks = []
    for line in differ:
        # ndiff prefixes each line with a 2-char code:
        #   "  " = unchanged, "- " = removed, "+ " = added, "? " = hint (skip)
        code = line[:2]
        text = line[2:]

        if code == "  ":
            chunks.append({"type": "unchanged", "text": text.rstrip("\n")})
        elif code == "- ":
            chunks.append({"type": "removed", "text": text.rstrip("\n")})
        elif code == "+ ":
            chunks.append({"type": "added", "text": text.rstrip("\n")})
        # "? " lines are alignment hints from ndiff — skip them

    return chunks


def diff_summary(chunks: list[dict]) -> dict:
    """
    Quick stats about what changed.

    Returns:
      { "lines_added": int, "lines_removed": int, "lines_unchanged": int }
    """
    added     = sum(1 for c in chunks if c["type"] == "added")
    removed   = sum(1 for c in chunks if c["type"] == "removed")
    unchanged = sum(1 for c in chunks if c["type"] == "unchanged")
    return {
        "lines_added":     added,
        "lines_removed":   removed,
        "lines_unchanged": unchanged,
    }
