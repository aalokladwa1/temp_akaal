import ast
import os
import sys

AKAAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "akaal"))

PLATFORM_DIRS = {
    "platform1_streaming": "streaming",
    "platform2_orchestration": "orchestration",
    "platform3_integrity": "data_integrity",
    "platform4_schema": "schema",
    "platform5_resilience": "resilience_eng",
    "platform6_governance": "governance",
    "platform7_advisory": "advisory",
    "platform8_reliability": "operational_reliability",
    "platform9_recovery": "recovery_intelligence",
    "platform10_trust": "trust_certification",
    "platform11_foundation": "platform",
}

FACADE_DIR = os.path.join(AKAAL_ROOT, "api", "facades")

def analyze_facade_purity():
    violations = []
    if not os.path.exists(FACADE_DIR):
        return [f"Facade directory missing: {FACADE_DIR}"]
    
    for root, _, files in os.walk(FACADE_DIR):
        for f in files:
            if f.endswith(".py") and not f.startswith("__"):
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8") as file:
                    tree = ast.parse(file.read(), filename=filepath)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.For, ast.While)):
                        violations.append(f"Facade {f}:{node.lineno} contains iterative control flow logic (For/While loop)")
    return violations

def analyze_boundary_imports():
    violations = []
    platform_module_names = set(PLATFORM_DIRS.values())
    
    for p_key, p_dir in PLATFORM_DIRS.items():
        dir_path = os.path.join(AKAAL_ROOT, p_dir)
        if not os.path.exists(dir_path):
            continue
        
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py"):
                    filepath = os.path.join(root, f)
                    with open(filepath, "r", encoding="utf-8") as file:
                        try:
                            tree = ast.parse(file.read(), filename=filepath)
                        except Exception as e:
                            violations.append(f"AST Parse Error in {filepath}: {e}")
                            continue
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            parts = node.module.split(".")
                            if len(parts) >= 2 and parts[0] == "akaal":
                                target_module = parts[1]
                                if target_module in platform_module_names and target_module != p_dir:
                                    if "facade" not in parts and "facades" not in parts:
                                        violations.append(
                                            f"Direct cross-platform import violation in {os.path.relpath(filepath, AKAAL_ROOT)}:{node.lineno} -> imported {node.module}"
                                        )
    return violations

def main():
    print("=== STARTING AKAAL PLATFORM BOUNDARY & FACADE AST AUDIT ===")
    facade_violations = analyze_facade_purity()
    boundary_violations = analyze_boundary_imports()
    
    all_violations = facade_violations + boundary_violations
    
    print(f"Facade Purity Violations: {len(facade_violations)}")
    for v in facade_violations:
        print(f"  [FACADE VIOLATION] {v}")
        
    print(f"Direct Cross-Platform Boundary Violations: {len(boundary_violations)}")
    for v in boundary_violations:
        print(f"  [BOUNDARY VIOLATION] {v}")
        
    if all_violations:
        print("\n[FAIL] Boundary Audit Failed with violations.")
        sys.exit(1)
    else:
        print("\n[OK] 100% Facade Purity and Zero Direct Cross-Platform Imports Verified!")
        sys.exit(0)

if __name__ == "__main__":
    main()
