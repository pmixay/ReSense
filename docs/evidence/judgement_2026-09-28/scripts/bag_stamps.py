"""Receive time and header stamp of every message of the named bags, read straight from sqlite (the
first 16 bytes of each CDR blob), so a node capture can be mapped to bag frame indices.

    DATA=/home/user/data python bag_stamps.py doubleT_obstacle roundT_doubleT > bag_stamps.json
"""
import glob
import json
import os
import sqlite3
import struct
import sys

DATA = os.environ.get("DATA", "/home/user/data")


def stamps(bag: str) -> list:
    db = glob.glob(f"{DATA}/for_hackathon/{bag}/*.db3")[0]
    rows = sqlite3.connect(db).execute("select timestamp, substr(data, 1, 16) from messages order by timestamp")
    out = []
    for ts, blob in rows:
        sec, nsec = struct.unpack_from("<iI", blob, 4)
        out.append([ts * 1e-9, sec + nsec * 1e-9])
    return out


if __name__ == "__main__":
    json.dump({bag: stamps(bag) for bag in sys.argv[1:]}, sys.stdout)
