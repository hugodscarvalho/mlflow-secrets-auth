"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

# Get the project root (two levels up from this script)
root = Path(__file__).parent.parent.parent
src = root / "src"

# Store navigation items
nav_items = []

# Generate documentation pages for each Python module
for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
    elif parts[-1] == "__main__":
        continue

    # Skip empty parts (happens when __init__.py is processed and parts become empty)
    if not parts:
        continue

    nav[parts] = doc_path.as_posix()
    nav_items.append((parts, doc_path.as_posix()))

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

# Create the navigation summary manually
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    # First try the official method
    try:
        nav_content = list(nav.build_literate_nav())
        if nav_content:
            nav_file.writelines(nav_content)
        else:
            msg = "Empty navigation content"
            raise ValueError(msg)
    except:  # noqa: E722
        # Fallback to manual navigation
        if nav_items:
            for parts, doc_path in sorted(nav_items):
                level = len(parts)
                indent = "  " * (level - 1)
                title = parts[-1].replace("_", " ").title()
                nav_file.write(f"{indent}* [{title}]({doc_path})\n")

# Copy top-level changelog.md into the docs output (visible to MkDocs)
changelog_src = root / "CHANGELOG.md"
changelog_dest = Path("changelog.md")

if changelog_src.exists():
    with mkdocs_gen_files.open(changelog_dest, "w") as fd:
        fd.write(changelog_src.read_text())
        mkdocs_gen_files.set_edit_path(changelog_dest, changelog_src.relative_to(root))
