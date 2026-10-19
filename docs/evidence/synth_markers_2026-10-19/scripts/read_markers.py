"""Read the organizers' /synthetic_obstacle_markers (visualization_msgs/MarkerArray) and the cloud stamps from one
marked synthetic bag (rosbag2 sqlite), with no ROS installation (rosbags typestore, ROS 2 Humble).

Writes <out>.jsonl, one line per marker message: bag time, header stamp, and every marker (ns, id, type, action,
frame_id, position, orientation, scale, color, text, line-point bounds), and <out>_clouds.jsonl, one line per
PointCloud2 message: index, bag time, header stamp, frame_id, width x height, SHA-256 of the raw CDR bytes.

    python read_markers.py <bag dir or .db3> <out prefix>
"""
import glob
import hashlib
import json
import os
import sqlite3
import sys

from rosbags.typesys import Stores, get_typestore

TS = get_typestore(Stores.ROS2_HUMBLE)
TYPES = {0: "ARROW", 1: "CUBE", 2: "SPHERE", 3: "CYLINDER", 4: "LINE_STRIP", 5: "LINE_LIST", 6: "CUBE_LIST",
         7: "SPHERE_LIST", 8: "POINTS", 9: "TEXT_VIEW_FACING", 10: "MESH_RESOURCE", 11: "TRIANGLE_LIST"}


def _apply(q, t, p):
    """Rotate p by the unit quaternion q (x, y, z, w) and add the translation t: the marker's pose."""
    x, y, z, w = q.x, q.y, q.z, q.w
    if x == y == z == 0.0 and w == 0.0:
        w = 1.0                                   # an all-zero quaternion means identity in RViz
    px, py, pz = p
    # v' = v + 2w (u x v) + 2 u x (u x v), u = (x, y, z)
    cx, cy, cz = y * pz - z * py, z * px - x * pz, x * py - y * px
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (px + 2 * (w * cx + ccx) + t.x, py + 2 * (w * cy + ccy) + t.y, pz + 2 * (w * cz + ccz) + t.z)


def stamp(h):
    return h.stamp.sec + h.stamp.nanosec * 1e-9


def main():
    src, out = sys.argv[1], sys.argv[2]
    db3 = src if src.endswith(".db3") else sorted(glob.glob(os.path.join(src, "*.db3")))[0]
    con = sqlite3.connect(f"file:{db3}?mode=ro", uri=True)
    topics = {tid: (name, typ) for tid, name, typ in con.execute("SELECT id, name, type FROM topics")}
    print("topics:", topics)
    n_m = n_c = 0
    with open(out + ".jsonl", "w") as fm, open(out + "_clouds.jsonl", "w") as fc:
        q = "SELECT topic_id, timestamp, data FROM messages ORDER BY timestamp, id"
        for tid, ts, data in con.execute(q):
            name, typ = topics[tid]
            if typ == "visualization_msgs/msg/MarkerArray":
                msg = TS.deserialize_cdr(data, typ)
                markers = []
                for m in msg.markers:
                    pts = [_apply(m.pose.orientation, m.pose.position, (p.x, p.y, p.z))
                           for p in m.points]                                   # marker frame -> header frame
                    markers.append({
                        "ns": m.ns, "id": int(m.id), "type": TYPES.get(int(m.type), int(m.type)), "action": int(m.action),
                        "frame_id": m.header.frame_id, "stamp": round(stamp(m.header), 6),
                        "pos": [round(m.pose.position.x, 4), round(m.pose.position.y, 4), round(m.pose.position.z, 4)],
                        "quat": [round(m.pose.orientation.x, 5), round(m.pose.orientation.y, 5),
                                 round(m.pose.orientation.z, 5), round(m.pose.orientation.w, 5)],
                        "scale": [round(m.scale.x, 4), round(m.scale.y, 4), round(m.scale.z, 4)],
                        "color": [round(m.color.r, 3), round(m.color.g, 3), round(m.color.b, 3), round(m.color.a, 3)],
                        "text": m.text, "n_points": len(pts),
                        "pts_min": [round(min(c), 3) for c in zip(*pts)] if pts else None,
                        "pts_max": [round(max(c), 3) for c in zip(*pts)] if pts else None,
                        "lifetime": m.lifetime.sec + m.lifetime.nanosec * 1e-9,
                    })
                fm.write(json.dumps({"i": n_m, "bag_t": ts / 1e9, "markers": markers}) + "\n")
                n_m += 1
            elif typ == "sensor_msgs/msg/PointCloud2":
                msg = TS.deserialize_cdr(data, typ)
                fc.write(json.dumps({"i": n_c, "bag_t": ts / 1e9, "stamp": round(stamp(msg.header), 6),
                                     "frame_id": msg.header.frame_id, "w": int(msg.width), "h": int(msg.height),
                                     "fields": [f.name for f in msg.fields],
                                     "sha256": hashlib.sha256(data).hexdigest()}) + "\n")
                n_c += 1
    print(f"{db3}: {n_m} marker messages, {n_c} clouds")


if __name__ == "__main__":
    main()
