"""Kiểm tra quy tắc độc lập: mỗi tính năng chỉ được import stdlib, contracts/, shared/ và chính nó.

Nếu một tính năng import tính năng khác, lõi (services/), hoặc server, test này sẽ FAIL.
Chạy:  python tests/test_isolation.py
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALLOWED_TOP = {"contracts", "shared"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield 0, a.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


class IsolationTests(unittest.TestCase):
    def test_features_depend_only_on_contracts_shared_and_stdlib(self):
        violations = []
        for folder in sorted((ROOT / "features").iterdir()):
            if not folder.is_dir():
                continue
            own = f"features.{folder.name}"
            for path in folder.glob("*.py"):
                for level, mod in _imports(path):
                    if level > 0:  # import tương đối: chỉ được trong cùng folder
                        continue
                    top = mod.split(".")[0]
                    if top in sys.stdlib_module_names or top in ALLOWED_TOP:
                        continue
                    if mod == own or mod.startswith(own + "."):
                        continue
                    violations.append(f"{path.relative_to(ROOT)} -> {mod}")
        self.assertEqual(violations, [], "tính năng import phụ thuộc không được phép")

    def test_contracts_and_shared_do_not_depend_on_features_or_core(self):
        violations = []
        for pkg in ("contracts", "shared"):
            for path in (ROOT / pkg).glob("*.py"):
                for level, mod in _imports(path):
                    if level == 0 and mod.split(".")[0] in ("features", "services", "server"):
                        violations.append(f"{path.relative_to(ROOT)} -> {mod}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
