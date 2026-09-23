"""Strip frontmatter/markdown from corpus/docs files and chunk into paragraphs.

Each chunk keeps the source file's "title" and "ms.date" frontmatter fields
alongside it, since downstream steps will need that metadata.
"""
import argparse
import glob
import re

import yaml

CORPUS_DIR = "corpus/docs"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?", re.DOTALL)

# Markdown syntax to strip from the body, applied in order.
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HEADER_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
BOLD_ITALIC_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|_)(.+?)\1")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?", re.MULTILINE)
LIST_MARKER_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+", re.MULTILINE)
HR_RE = re.compile(r"^\s*([-*_]\s*){3,}\s*$", re.MULTILINE)
TABLE_PIPE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ADMONITION_RE = re.compile(r"\[!(NOTE|WARNING|TIP|IMPORTANT|CAUTION)\]", re.IGNORECASE)


def split_frontmatter(text):
    """Return (metadata dict, body text) for a markdown file's contents."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw_yaml = match.group(1)
    body = text[match.end():]
    try:
        metadata = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body


def strip_markdown(body):
    """Remove common markdown syntax, leaving plain prose."""
    text = CODE_BLOCK_RE.sub(" ", body)
    text = IMAGE_RE.sub(r"\1", text)
    text = LINK_RE.sub(r"\1", text)
    text = INLINE_CODE_RE.sub(r"\1", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = HEADER_RE.sub("", text)
    text = BLOCKQUOTE_RE.sub("", text)
    text = ADMONITION_RE.sub("", text)
    text = LIST_MARKER_RE.sub("", text)
    text = HR_RE.sub("", text)
    text = TABLE_PIPE_RE.sub("", text)
    text = BOLD_ITALIC_RE.sub(r"\2", text)
    return text


MIN_CHUNK_WORDS = 6


def chunk_paragraphs(text):
    """Split cleaned body text into paragraph-level chunks.

    Very short fragments (mostly leftover headers, once ``#`` markers are
    stripped) are merged into the paragraph that follows them so the header
    text isn't lost. A short fragment with no following paragraph (e.g. the
    last line in a file) is dropped instead.
    """
    raw_chunks = re.split(r"\n\s*\n", text)
    collapsed_chunks = []
    for raw in raw_chunks:
        collapsed = re.sub(r"\s+", " ", raw).strip()
        if collapsed:
            collapsed_chunks.append(collapsed)

    chunks = []
    pending = None
    for chunk in collapsed_chunks:
        if pending:
            chunk = f"{pending} {chunk}"
            pending = None
        if len(chunk.split()) < MIN_CHUNK_WORDS:
            pending = chunk
        else:
            chunks.append(chunk)
    # A trailing short fragment with nothing after it has nowhere to merge.
    return chunks


def process_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    metadata, body = split_frontmatter(text)
    cleaned = strip_markdown(body)
    paragraphs = chunk_paragraphs(cleaned)
    title = metadata.get("title")
    ms_date = metadata.get("ms.date")
    return [
        {"title": title, "ms.date": ms_date, "text": p, "source": path}
        for p in paragraphs
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N files (default: process the whole corpus).",
    )
    args = parser.parse_args()

    files = sorted(glob.glob(f"{CORPUS_DIR}/**/*.md", recursive=True))
    if args.limit is not None:
        files = files[: args.limit]
    print(f"Processing {len(files)} files from {CORPUS_DIR}\n")

    all_chunks = []
    for path in files:
        all_chunks.extend(process_file(path))

    print(f"Total chunks produced: {len(all_chunks)}\n")

    print("=== Example chunks ===\n")
    for chunk in all_chunks[:3]:
        print(f"Source: {chunk['source']}")
        print(f"Title: {chunk['title']}")
        print(f"ms.date: {chunk['ms.date']}")
        print(f"Text: {chunk['text']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
