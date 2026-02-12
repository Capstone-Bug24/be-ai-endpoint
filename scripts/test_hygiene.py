#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable


@dataclass
class Counters:
    tests_total: int = 0
    duplicate_groups_total: int = 0
    duplicate_tests_total: int = 0
    no_assert_tests_total: int = 0
    trivial_assert_true_total: int = 0


def _iter_test_functions(path: Path) -> Iterable[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            yield node


def _has_assert(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
    return False


def _is_trivial_assert_true(node: ast.FunctionDef) -> bool:
    asserts = [child for child in ast.walk(node) if isinstance(child, ast.Assert)]
    if len(asserts) != 1:
        return False
    expr = asserts[0].test
    return isinstance(expr, ast.Constant) and expr.value is True


def analyze(test_root: Path) -> Counters:
    counters = Counters()
    body_hashes: dict[str, int] = {}

    for py_file in sorted(test_root.rglob("test_*.py")):
        for func in _iter_test_functions(py_file):
            counters.tests_total += 1
            if not _has_assert(func):
                counters.no_assert_tests_total += 1
            if _is_trivial_assert_true(func):
                counters.trivial_assert_true_total += 1

            body_key = ast.dump(ast.Module(body=func.body, type_ignores=[]), include_attributes=False)
            body_hashes[body_key] = body_hashes.get(body_key, 0) + 1

    for count in body_hashes.values():
        if count > 1:
            counters.duplicate_groups_total += 1
            counters.duplicate_tests_total += count
    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple test hygiene gate")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-duplicate-groups", type=int, default=0)
    parser.add_argument("--max-no-assert", type=int, default=0)
    parser.add_argument("--max-trivial-assert-true", type=int, default=0)
    parser.add_argument("--test-root", default="tests")
    args = parser.parse_args()

    root = Path(args.test_root)
    counters = analyze(root)

    print("== Test Hygiene Report ==")
    print(f"tests_total={counters.tests_total}")
    print(f"duplicate_groups_total={counters.duplicate_groups_total}")
    print(f"duplicate_tests_total={counters.duplicate_tests_total}")
    print(f"no_assert_tests_total={counters.no_assert_tests_total}")
    print(f"trivial_assert_true_total={counters.trivial_assert_true_total}")

    if not args.strict:
        return 0

    fail = False
    if counters.duplicate_groups_total > args.max_duplicate_groups:
        fail = True
    if counters.no_assert_tests_total > args.max_no_assert:
        fail = True
    if counters.trivial_assert_true_total > args.max_trivial_assert_true:
        fail = True
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
