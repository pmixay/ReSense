import json, os, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init()
n = Node('freshness_metadata_probe')
p = n.create_publisher(String, '/freshness_metadata_probe', 10)
s = n.create_subscription(String, '/freshness_metadata_probe', lambda msg: None, 10)
time.sleep(1)
rows = []
for i in range(3):
    before = time.time_ns()
    p.publish(String(data=str(i)))
    deadline = time.monotonic() + 3
    got = None
    while got is None and time.monotonic() < deadline:
        with s.handle:
            got = s.handle.take_message(s.msg_type, s.raw)
        if got is None:
            time.sleep(.01)
    assert got is not None, 'message not delivered'
    msg, info = got
    after = time.time_ns()
    source = info.get('source_timestamp', 0)
    assert msg.data == str(i)
    assert before <= source <= after, (before, source, after)
    rows.append({'value': msg.data, 'before_ns': before, 'after_ns': after,
                 'source_timestamp_ns': source, 'received_timestamp_ns': info.get('received_timestamp'),
                 'age_ms': (after-source)/1e6})
    time.sleep(.1)
print(json.dumps({'rmw': os.environ.get('RMW_IMPLEMENTATION'), 'stock_profile': not os.environ.get('FASTRTPS_DEFAULT_PROFILES_FILE'), 'rows': rows, 'passed': True}, indent=2))
n.destroy_node()
rclpy.shutdown()
