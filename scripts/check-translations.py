#!/usr/bin/env python3
"""Validate catalog keys and interpolation placeholders without dependencies."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1] / 'locales'
reference = json.loads((root / 'en.json').read_text(encoding='utf-8'))
errors = []
for file in sorted(root.glob('*.json')):
    try:
        catalog = json.loads(file.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        errors.append(f'{file.name}: {exc}')
        continue
    missing = sorted(reference.keys() - catalog.keys())
    extra = sorted(catalog.keys() - reference.keys())
    if missing: errors.append(f'{file.name}: missing keys: {missing}')
    if extra: errors.append(f'{file.name}: unknown keys: {extra}')
    for key in reference.keys() & catalog.keys():
        value = catalog[key]
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{file.name}: empty or non-text value: {key}')
            continue
        if set(re.findall(r'\{(\w+)\}', value)) != set(re.findall(r'\{(\w+)\}', reference[key])):
            errors.append(f'{file.name}: incorrect placeholders: {key}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'Validated {len(list(root.glob("*.json")))} catalogs, {len(reference)} keys each.')
