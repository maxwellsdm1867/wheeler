"""Dependency scanner: parse Python scripts to extract imports, data file refs, and function calls.

Uses stdlib ``ast`` to statically analyse a script. No execution needed.
Returns a structured dependency map that can be used for graph integration
(linking Analysis nodes to Dataset nodes, etc.).
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# File extensions that indicate data files when found in string literals
_DATA_EXTENSIONS = frozenset({
    ".mat", ".h5", ".hdf5", ".csv", ".tsv", ".npy", ".npz",
    ".json", ".parquet", ".feather", ".pkl", ".pickle",
    ".xlsx", ".xls", ".tif", ".tiff", ".fits",
})

# Function names that typically load data files (module.func patterns)
_DATA_LOAD_FUNCTIONS = frozenset({
    "pd.read_csv", "pd.read_excel", "pd.read_parquet", "pd.read_hdf",
    "pd.read_json", "pd.read_feather", "pd.read_pickle", "pd.read_table",
    "np.load", "np.loadtxt", "np.genfromtxt", "np.fromfile",
    "scipy.io.loadmat", "h5py.File",
    "open",
})

# Common aliases for modules whose function calls we track
_MODULE_ALIASES: dict[str, str] = {
    "pandas": "pd",
    "numpy": "np",
    "scipy": "scipy",
    "h5py": "h5py",
    "matplotlib": "plt",
    "matplotlib.pyplot": "plt",
}


@dataclass
class DependencyMap:
    """Structured result of scanning a Python script."""

    script_path: str
    imports: list[str] = field(default_factory=list)
    data_files: list[dict[str, str]] = field(default_factory=list)
    function_calls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "script_path": self.script_path,
            "imports": self.imports,
            "data_files": self.data_files,
            "function_calls": self.function_calls,
        }


def _resolve_alias(aliases: dict[str, str], name: str) -> str:
    """Expand a local alias to its canonical module name.

    Given aliases {"pd": "pandas"} and name "pd", returns "pandas".
    Returns the name unchanged if no alias mapping exists.
    """
    return aliases.get(name, name)


_MAX_PATH_LENGTH = 512  # Guard against false positives from long strings


def _looks_like_file_path(s: str) -> bool:
    """Heuristic: does this string look like a data file path?"""
    if not s or len(s) > _MAX_PATH_LENGTH:
        return False
    # Must have a recognisable data extension
    suffix = Path(s).suffix.lower()
    return suffix in _DATA_EXTENSIONS


def _is_data_load_call(func_str: str) -> bool:
    """Check if a function call string matches a known data-loading pattern."""
    return func_str in _DATA_LOAD_FUNCTIONS


class _ImportVisitor(ast.NodeVisitor):
    """Walk AST and collect imports, data file references, and function calls."""

    def __init__(self) -> None:
        self.imports: list[str] = []
        self.data_files: list[dict[str, str]] = []
        self.function_calls: list[str] = []
        # Track local aliases: alias -> canonical module name
        self.aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
            if alias.asname:
                self.aliases[alias.asname] = alias.name
            else:
                # Top-level name is usable directly
                top = alias.name.split(".")[0]
                self.aliases[top] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module:
            self.imports.append(module)
        for alias in node.names:
            full = f"{module}.{alias.name}" if module else alias.name
            local = alias.asname or alias.name
            self.aliases[local] = full
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_str = self._call_name(node.func)
        if func_str:
            # Expand aliases for matching
            canonical = self._expand_call(func_str)
            self.function_calls.append(canonical)

            # Check if this is a data-loading call — extract file path from first arg
            if _is_data_load_call(canonical):
                self._extract_file_arg(node, canonical)

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Catch string literals that look like file paths."""
        if isinstance(node.value, str) and _looks_like_file_path(node.value):
            self.data_files.append({
                "path": node.value,
                "context": "string_literal",
            })
        self.generic_visit(node)

    def _call_name(self, node: ast.expr) -> str | None:
        """Extract dotted name from a call target (e.g. pd.read_csv -> 'pd.read_csv')."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            if parent:
                return f"{parent}.{node.attr}"
        return None

    def _expand_call(self, func_str: str) -> str:
        """Expand first segment using known aliases.

        'pd.read_csv' -> 'pd.read_csv' (we keep short canonical forms)
        'pandas.read_csv' -> 'pd.read_csv' if pandas->pd mapping exists
        """
        parts = func_str.split(".", 1)
        first = parts[0]
        canonical_module = self.aliases.get(first, first)

        # Map to short alias if we know one
        short = _MODULE_ALIASES.get(canonical_module, first)
        if len(parts) == 1:
            return short
        return f"{short}.{parts[1]}"

    def _extract_file_arg(self, node: ast.Call, func_name: str) -> None:
        """If the first positional argument is a string literal, record it as a data file."""
        if node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                # Already caught by visit_Constant, but add context about the loader
                path = first.value
                # Update existing entry or add new one
                for entry in self.data_files:
                    if entry["path"] == path:
                        entry["context"] = func_name
                        return
                self.data_files.append({"path": path, "context": func_name})


def scan_script(script_path: str | Path) -> DependencyMap:
    """Parse a Python script and return its dependency map.

    Args:
        script_path: Path to a .py file.

    Returns:
        DependencyMap with imports, data_files, and function_calls.

    Raises:
        FileNotFoundError: if the file does not exist.
        SyntaxError: if the file cannot be parsed.
    """
    path = Path(script_path)
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    visitor = _ImportVisitor()
    visitor.visit(tree)

    # Deduplicate imports while preserving order
    seen_imports: set[str] = set()
    unique_imports: list[str] = []
    for imp in visitor.imports:
        if imp not in seen_imports:
            seen_imports.add(imp)
            unique_imports.append(imp)

    # Deduplicate data files by path
    seen_paths: set[str] = set()
    unique_data: list[dict[str, str]] = []
    for entry in visitor.data_files:
        if entry["path"] not in seen_paths:
            seen_paths.add(entry["path"])
            unique_data.append(entry)

    # Deduplicate function calls while preserving order
    seen_calls: set[str] = set()
    unique_calls: list[str] = []
    for call in visitor.function_calls:
        if call not in seen_calls:
            seen_calls.add(call)
            unique_calls.append(call)

    return DependencyMap(
        script_path=str(path),
        imports=unique_imports,
        data_files=unique_data,
        function_calls=unique_calls,
    )
