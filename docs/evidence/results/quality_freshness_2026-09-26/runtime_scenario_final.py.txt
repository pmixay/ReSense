"""Stock Humble/Fast DDS real-node functional trial; no timing performance conclusion."""
import hashlib, json, os, pathlib, time
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import String
from resense_ros.detector_node import DetectorNode, SourceInfoExecutor
root = pathlib.Path('/evidence')
rclpy.init(args=['--ros-args', '-p', 'freshness_mode:=replay', '-p', 'auto_discover:=false'])
node = DetectorNode()
probe = Node('freshness_scenario')
pub = probe.create_publisher(PointCloud2, '/lidar_points', 40)
alt = probe.create_publisher(PointCloud2, '/sensing/lidar/hesai128/pointcloud', 40)
rows=[]
probe.create_subscription(String, '/resense/status', lambda m: rows.append(json.loads(m.data)), 1000)
executor = SourceInfoExecutor()
executor.add_node(node)
executor.add_node(probe)
scenes = np.load(root/'scenes.npz')
phase='startup'
def spin(duration):
    deadline=time.monotonic()+duration
    while time.monotonic()<deadline:
        executor.spin_once(timeout_sec=min(.01, max(0, deadline-time.monotonic())))
def publish(stamp, scene='clear', publisher=pub, frame='lidar'):
    xyz=scenes[scene]
    data=np.zeros(len(xyz), dtype=[('x','f4'),('y','f4'),('z','f4'),('intensity','f4')])
    data['x'],data['y'],data['z']=xyz.T
    data['intensity']=20.0
    msg=PointCloud2(height=1,width=len(data),is_dense=True,is_bigendian=False,point_step=16,row_step=16*len(data))
    msg.header.frame_id=frame
    ns=round(stamp*1e9)
    msg.header.stamp.sec,msg.header.stamp.nanosec=divmod(ns,10**9)
    msg.fields=[PointField(name=n,offset=4*i,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(('x','y','z','intensity'))]
    msg.data=data.tobytes()
    publisher.publish(msg)
def batch(stamps, **kwargs):
    start=len(rows)
    for s in stamps:
        publish(s,**kwargs)
        spin(.1)
    spin(.05)
    return rows[start:]
def frames(items): return [x for x in items if x.get('snapshot_kind')=='frame']
checks=[]
def check(name, condition):
    checks.append({'name':name,'passed':bool(condition)})
    if not condition: raise AssertionError(name)
try:
    spin(1)
    startup=frames(batch([20+.1*i for i in range(6)]))
    check('first frame epoch invalid', startup[0]['freshness']['reason']=='epoch_unconfirmed')
    check('steady historical replay becomes current with publication UTC', any(x['freshness']['valid'] and x['decision']=='GO' and x['freshness']['acquisition_age_s'] is None for x in startup))
    begin=len(rows)
    for i in range(7): publish(20.6+.1*i)
    time.sleep(.7) # messages are published, but executor is intentionally stalled
    spin(.45)
    stalled=frames(rows[begin:])
    check('later DDS backlog fails closed on source age', bool(stalled) and all(x['decision']!='GO' for x in stalled) and any(x['freshness']['reason']=='source_stale' for x in stalled))
    recovered=frames(batch([21.3+.1*i for i in range(5)]))
    check('fresh progression recovers', any(x['decision']=='GO' and x['freshness']['valid'] for x in recovered))
    begin=len(rows)
    spin(.65)
    check('pause expires GO', any(x.get('snapshot_kind')=='watchdog' and x['decision']=='FAULT' for x in rows[begin:]))
    resumed=frames(batch([21.8+.1*i for i in range(4)]))
    check('resume first frame invalid then recovers', resumed[0]['decision']=='FAULT' and any(x['decision']=='GO' for x in resumed[1:]))
    begin=len(rows)
    for i in range(7):
        publish(22.2+.1*i)
        time.sleep(.002)
    spin(.4)
    burst=frames(rows[begin:])
    check('current burst cannot GO while behind', bool(burst) and all(x['decision']!='GO' for x in burst if x['freshness']['queue_lag_s']>1e-6))
    stop=frames(batch([22.9+.1*i for i in range(14)],scene='obstacle'))
    check('detector STOP on synthetic obstacle fixture', any(x['decision']=='STOP' for x in stop))
    begin=len(rows)
    spin(1.1)
    check('watchdog preserves STOP with invalid monitoring', any(x.get('snapshot_kind')=='watchdog' and x['decision']=='STOP' and x['stop_held'] and not x['freshness']['valid'] for x in rows[begin:]))
    switched=frames(batch([5+.1*i for i in range(6)],publisher=alt,frame='another_lidar'))
    check('input switch first frame retains STOP', switched[0]['stop_held'] and not switched[0]['freshness']['valid'])
    check('fresh clear switched recording releases STOP', any(x['decision']=='GO' and not x['stop_held'] for x in switched[1:]))
    jumped=frames(batch([1+.1*i for i in range(4)],publisher=alt,frame='another_lidar'))
    check('backward jump invalidates epoch', jumped[0]['decision']=='FAULT' and any(x['decision']=='GO' for x in jumped[1:]))
    check('no invalid GO anywhere', all(x['decision']!='GO' or x['freshness']['valid'] and x['freshness']['go_allowed'] for x in rows))
    check('invalid monitored range always zero', all(x['freshness']['valid'] or x['clear_distance']==0 for x in rows))
    from check_dry_run import freshness_failures
    check('final metadata and strict runtime contract', not freshness_failures(frames(rows)))
finally:
    (root/'runtime_stock_final_status.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    result={'checks':checks,'passed':bool(checks) and all(x['passed'] for x in checks), 'frames':len(frames(rows)),
            'snapshots':len(rows)-len(frames(rows)), 'stock_profile':not os.environ.get('FASTRTPS_DEFAULT_PROFILES_FILE'),
            'rmw':os.environ.get('RMW_IMPLEMENTATION'),
            'node_sha256':hashlib.sha256(pathlib.Path('/opt/resense/ros2_ws/src/resense_ros/resense_ros/detector_node.py').read_bytes()).hexdigest()}
    (root/'runtime_stock_final_result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    executor.shutdown()
    node.destroy_node(); probe.destroy_node(); rclpy.shutdown()
