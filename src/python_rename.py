from pathlib import Path

def prompt_yes_no(old_path: Path, new_path: Path) -> str:
    print("\nRename?")
    print(f"OLD: {old_path}")
    print(f"NEW: {new_path}")

    while True:
        choice = input("Proceed? [y]es / [n]o / [q]uit: ").strip().lower()
        if choice in {"y", "yes"}:
            return "yes"
        if choice in {"n", "no", ""}:
            return "no"
        if choice in {"q", "quit"}:
            return "quit"
        print("Please enter y, n, or q.")


def main() -> None:
    root = Path.cwd()

    print(f"Scanning for Python files under: {root}")

    candidates = []

    for path in root.rglob("*.py"):
        if "-" in path.name:
            new_name = path.stem.replace("-", "_") + path.suffix
            new_path = path.with_name(new_name)
            candidates.append((path, new_path))

    if not candidates:
        print("\nNo .py files with '-' in the filename were found.")
        return

    renamed = []
    skipped = []
    failed = []

    for old_path, new_path in candidates:
        if old_path == new_path:
            skipped.append((old_path, new_path, "No change needed"))
            continue

        if new_path.exists():
            print("\nCannot rename because target already exists:")
            print(f"OLD: {old_path}")
            print(f"NEW: {new_path}")
            skipped.append((old_path, new_path, "Target already exists"))
            continue

        choice = prompt_yes_no(old_path, new_path)

        if choice == "quit":
            skipped.append((old_path, new_path, "User quit"))
            break

        if choice == "no":
            skipped.append((old_path, new_path, "User skipped"))
            continue

        try:
            old_path.rename(new_path)
            print("Renamed.")
            renamed.append((old_path, new_path))
        except Exception as exc:
            print(f"Failed: {exc}")
            failed.append((old_path, new_path, str(exc)))

    print("\nSummary")
    print("-------")
    print(f"Files found: {len(candidates)}")
    print(f"Renamed:     {len(renamed)}")
    print(f"Skipped:     {len(skipped)}")
    print(f"Failed:      {len(failed)}")

    if renamed:
        print("\nRenamed files:")
        for old_path, new_path in renamed:
            print(f"- {old_path} -> {new_path}")

    if skipped:
        print("\nSkipped files:")
        for old_path, new_path, reason in skipped:
            print(f"- {old_path} -> {new_path} ({reason})")

    if failed:
        print("\nFailed files:")
        for old_path, new_path, reason in failed:
            print(f"- {old_path} -> {new_path} ({reason})")


if __name__ == "__main__":
    main()