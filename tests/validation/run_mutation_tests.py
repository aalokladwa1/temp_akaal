"""
Akaal — Mutation Testing Runner
================================
Automates Stage 4 validation by programmatically mutating comparison and validation logic,
running unit tests, and verifying that every mutation is detected (killed) by the test suite.
"""

import os
import shutil
import subprocess
import sys

# Paths to core components
BASE_DIR = r"c:\Users\LENOVO\Downloads\temp_akaal-main"
ENGINE_PATH = os.path.join(BASE_DIR, "akaal", "core", "comparison", "engine.py")
VALIDATOR_PATH = os.path.join(BASE_DIR, "akaal", "core", "comparison", "validator.py")
SERIALIZER_PATH = os.path.join(BASE_DIR, "akaal", "core", "comparison", "serializer.py")
COLUMN_COMPARER_PATH = os.path.join(BASE_DIR, "akaal", "core", "comparison", "comparers", "column.py")

MUTATIONS = [
    {
        "name": "Mutation 1: Disable Engine Difference Sorting",
        "file": ENGINE_PATH,
        "original": "sorted_differences = sorted(raw_differences, key=diff_sort_key)",
        "mutated": "sorted_differences = list(raw_differences)",
    },
    {
        "name": "Mutation 2: Bypass Validator Global Unique Names Check",
        "file": VALIDATOR_PATH,
        "original": "global_names.add(pk_name)",
        "mutated": "pass",
    },
    {
        "name": "Mutation 3: Disable Column Type Mismatch Detection",
        "file": COLUMN_COMPARER_PATH,
        "original": "type_mismatch = not are_types_equivalent(",
        "mutated": "type_mismatch = False\n        if False: not are_types_equivalent(",
    },
    {
        "name": "Mutation 4: Allow Deserializing Report Major Version > 1",
        "file": SERIALIZER_PATH,
        "original": "if major_ver > 1:",
        "mutated": "if False:",
    },
]


def run_tests() -> bool:
    """Runs the unit tests and returns True if all tests PASS (mutation survived), False otherwise (killed)."""
    try:
        result = subprocess.run(
            ["py", "-m", "unittest", "tests/unit/test_schema_comparison.py"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False  # Timeout implies infinite loop, mutation killed


def main():
    print("=== Starting Schema Comparison Engine Mutation Testing ===")
    
    # 1. Verify baseline tests pass before mutations
    print("\nVerifying baseline tests...")
    if not run_tests():
        print("Error: Baseline tests are failing! Fix tests before running mutation tests.")
        sys.exit(1)
    print("Baseline tests passed cleanly.")

    success = True
    killed_count = 0
    survived_mutations = []

    for m in MUTATIONS:
        name = m["name"]
        file_path = m["file"]
        orig_text = m["original"]
        mut_text = m["mutated"]

        # Backup file
        backup_path = file_path + ".bak"
        shutil.copyfile(file_path, backup_path)

        try:
            # Read, replace, and write
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if orig_text not in content:
                print(f"\n[ERROR] Target text not found in {os.path.basename(file_path)} for: {name}")
                success = False
                continue

            content_mutated = content.replace(orig_text, mut_text)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_mutated)

            # Run tests
            survived = run_tests()
            
            if survived:
                print(f"\n[SURVIVED] {name}")
                print(f"  -> Original: {orig_text.strip()}")
                print(f"  -> Mutated : {mut_text.strip()}")
                survived_mutations.append(name)
                success = False
            else:
                print(f"[KILLED]   {name}")
                killed_count += 1

        finally:
            # Restore file
            if os.path.exists(backup_path):
                shutil.copyfile(backup_path, file_path)
                os.remove(backup_path)

    print("\n" + "="*50)
    print("MUTATION TESTING SUMMARY")
    print("="*50)
    print(f"Total Mutations Run: {len(MUTATIONS)}")
    print(f"Mutations Killed   : {killed_count}")
    print(f"Mutations Survived : {len(survived_mutations)}")
    
    if success:
        print("SUCCESS: 100% Mutation Kill Rate achieved!")
        sys.exit(0)
    else:
        print("FAILURE: Some mutations survived. Test suite requires hardening.")
        sys.exit(1)


if __name__ == "__main__":
    main()
