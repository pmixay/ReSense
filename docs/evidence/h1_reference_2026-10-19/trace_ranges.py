"""Reuse the unchanged raw-result/assignment audit on the new H1 candidate."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('h1_d_trace', ROOT / 'docs/evidence/h1_axis_range_2026-10-19/trace_ranges.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

if __name__ == '__main__':
    driver.main()
