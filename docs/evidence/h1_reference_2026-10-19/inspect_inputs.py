"""Read-only raw-bag topic inventory, independent of decoded cache metadata."""
import json
import argparse
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
BAGS = [
    Path('/tmp/opencode/resense-b4-data/for_hackathon/roundT_squareT_pressureGate_squareT/roundT_squareT_pressureGate_squareT_0.db3'),
    Path('/tmp/opencode/resense-b4-data/for_hackathon/roundT_pressureGate_roundT/roundT_pressureGate_roundT_0.db3'),
    Path('/tmp/opencode/l16-s3/falcon_test_second_dark/falcon_test_second_dark_0.db3'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'raw-topic-inventory.json')
    args = parser.parse_args()
    report = []
    for path in BAGS:
        with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as connection:
            rows = connection.execute('SELECT t.name,t.type,COUNT(m.id) FROM topics t LEFT JOIN messages m ON m.topic_id=t.id GROUP BY t.id').fetchall()
            total = connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
            orphan = connection.execute('SELECT COUNT(*) FROM messages m LEFT JOIN topics t ON m.topic_id=t.id WHERE t.id IS NULL').fetchone()[0]
        assert any(kind == 'sensor_msgs/msg/PointCloud2' and count > 0 for _, kind, count in rows)
        assert total == sum(count for _, _, count in rows) + orphan
        report.append(dict(path=str(path), total_messages=total, orphan_messages=orphan,
                           topics=[dict(name=name, type=kind, messages=count) for name, kind, count in rows]))
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
