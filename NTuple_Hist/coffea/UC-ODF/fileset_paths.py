"""Relocate the ntuple paths of a coffea fileset to a local directory."""

from pathlib import Path


def relocate_fileset(dataset, ntuple_dir):
    """
    Return a copy of ``dataset`` whose files all live directly under ``ntuple_dir``.

    The dataset JSON in the repo records the absolute paths of the ntuples at the
    site that produced it. Keeping only each file's name lets any site point the
    same JSON at its own copy of the ntuples. Per-file entries (``num_entries``,
    ``steps``, ...) and the dataset metadata are carried over unchanged.

    Args:
        dataset: One dataset entry with a ``files`` mapping of path -> file info
        ntuple_dir: Directory holding the ntuples at this site

    Raises:
        ValueError: If two source files share a name, since they would collapse
            into a single entry.
    """
    ntuple_dir = Path(ntuple_dir)
    files = {}
    for old_path, file_info in dataset["files"].items():
        name = Path(old_path).name
        new_path = str(ntuple_dir / name)
        if new_path in files:
            raise ValueError(f"Duplicate file name in fileset: {name}")
        files[new_path] = file_info
    return {**dataset, "files": files}
