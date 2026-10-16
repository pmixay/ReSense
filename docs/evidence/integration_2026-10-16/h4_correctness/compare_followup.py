"""Compare retained target measurements with the now import-compatible control."""
from pathlib import Path

source = Path('/review/compare_scenes.py').read_text()
old = "data = {name:json.loads((out/(name+'.json')).read_text()) for name in ('target_on','target_off','control')}"
new = "data = {name:json.loads(((out if name == 'control' else Path('/review/run-002'))/(name+'.json')).read_text()) for name in ('target_on','target_off','control')}"
assert source.count(old) == 1
exec(compile(source.replace(old,new),'/review/compare_scenes.py:retained-target-inputs','exec'))
