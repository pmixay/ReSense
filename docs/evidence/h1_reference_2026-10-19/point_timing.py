"""Inspect original per-point timing fields, not the reduced decoded cache."""
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/resense_ros'))
from resense_ros.fastcloud import parse_pointcloud2  # noqa: E402


def main():
    inventory = json.loads((Path(__file__).parent / 'raw-topic-inventory-checked.json').read_text())
    report = []
    for bag in inventory:
        path = Path(bag['path'])
        with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as connection:
            payload = connection.execute("SELECT m.data FROM messages m JOIN topics t ON m.topic_id=t.id WHERE t.type='sensor_msgs/msg/PointCloud2' ORDER BY m.timestamp LIMIT 1").fetchone()[0]
        msg = parse_pointcloud2(payload)
        row = dict(bag=str(path), point_step=msg.point_step, fields=[dict(name=f.name, offset=f.offset,
            datatype=f.datatype) for f in msg.fields], timing={})
        for field in msg.fields:
            if field.name.lower() in ['t', 'time', 'timestamp', 'offset_time']:
                types = {1: 'i1', 2: 'u1', 3: '<i2', 4: '<u2', 5: '<i4', 6: '<u4', 7: '<f4', 8: '<f8'}
                dtype = np.dtype(dict(names=['value'], formats=[types[field.datatype]], offsets=[field.offset], itemsize=msg.point_step))
                values = np.frombuffer(msg.data, dtype=dtype)['value']
                finite = values[np.isfinite(values)]
                row['timing'][field.name] = dict(min=float(finite.min()), max=float(finite.max()),
                    distinct=int(np.unique(finite).size), sample=finite[::max(1, len(finite) // 8)].tolist())
        report.append(row)
    with (Path(__file__).parent / 'point-timing.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
