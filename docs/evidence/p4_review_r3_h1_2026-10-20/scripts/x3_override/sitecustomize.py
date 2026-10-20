"""X3 switch override for scripts/robustness_battery.py, which has no --set: passed as --resource-adapter, this
directory is on every worker's PYTHONPATH, so Python imports this module at start-up. When P4_X3_SET holds
"section.key=value[;section.key=value]" it wraps DetectorConfig.from_yaml (the only way judge_runner.NodeReplica
reads configs/default.yaml) to apply those values after loading, exactly as regression_gate.py --set and
falcon_trace.py --set do, and writes one line per load to stderr (the worker's process.log). No detector file
is changed; without P4_X3_SET it does nothing."""
import os
import sys

_SET = os.environ.get("P4_X3_SET", "")
if _SET:
    import yaml
    from resense.config import DetectorConfig

    _load = DetectorConfig.from_yaml.__func__

    def _from_yaml(cls, path):
        cfg = _load(cls, path)
        for item in filter(None, _SET.split(";")):
            key, value = item.split("=", 1)
            section, name = key.split(".", 1)
            obj = getattr(cfg, section)
            if not hasattr(obj, name):
                raise KeyError(f"unknown parameter {key}")
            setattr(obj, name, yaml.safe_load(value))
            sys.stderr.write(f"P4_X3_SET applied: {key} = {getattr(obj, name)!r} (from {path})\n")
        return cfg

    DetectorConfig.from_yaml = classmethod(_from_yaml)
