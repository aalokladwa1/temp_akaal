import os
import re
import ast

roots = ['akaalIPC', 'akaalPipeline', 'akaalEngine']
findings = []

patterns = [
    (re.compile(r'verify\s*=\s*False', re.IGNORECASE), 'verify=False'),
    (re.compile(r'CERT_NONE', re.IGNORECASE), 'CERT_NONE'),
    (re.compile(r'BEGIN (?:RSA |EC )?PRIVATE KEY', re.IGNORECASE), 'hardcoded private key'),
    (re.compile(r'\b(?:fake|mock|dummy|placeholder)\b', re.IGNORECASE), 'mock/fake/dummy word'),
    (re.compile(r'NotImplementedError'), 'NotImplementedError'),
    (re.compile(r'spiffe://(?![a-z0-9])', re.IGNORECASE), 'spiffe literal pattern'),
]

for root in roots:
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith('.py'):
                path = os.path.join(dirpath, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    lines = fp.readlines()
                    for idx, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if stripped.startswith('#') or stripped.startswith('*'):
                            continue
                        for regex, desc in patterns:
                            if regex.search(stripped):
                                findings.append((path, idx, desc, stripped))

print(f"Total findings across {roots}: {len(findings)}")
for path, idx, desc, text in findings:
    print(f"[{desc}] {path}:{idx} -> {text[:140]}")
