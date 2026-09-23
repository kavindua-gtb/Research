import os

CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")


def main():
    md_files = []
    for root, _dirs, files in os.walk(CORPUS_DIR):
        for name in files:
            if name.lower().endswith(".md"):
                md_files.append(os.path.join(root, name))

    print(f"Total markdown (.md) files found: {len(md_files)}")
    print("Example files:")
    for path in md_files[:3]:
        print(f"  {path}")


if __name__ == "__main__":
    main()
