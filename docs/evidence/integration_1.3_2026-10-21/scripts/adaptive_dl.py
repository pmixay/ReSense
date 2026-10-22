"""Resumable ranged download that adapts its chunk to what Drive serves (quota page = HTML, not the range)."""
import os, subprocess, sys, time
urls, out, total = sys.argv[1].split('|'), sys.argv[2], int(sys.argv[3]); k = 0
lo, hi, ch = 256 << 10, 64 << 20, 8 << 20
part = out + ".part"
while True:
    have = os.path.getsize(out) if os.path.exists(out) else 0
    if have >= total:
        break
    end = min(have + ch, total) - 1
    r = subprocess.run(["curl", "-fsSL", "-m", "600", "-r", f"{have}-{end}", "-o", part, urls[k % len(urls)]])
    ok = r.returncode == 0 and os.path.getsize(part) == end - have + 1 and b"<!DOCTYPE" not in open(part, "rb").read(15)
    if ok:
        with open(out, "ab") as f, open(part, "rb") as p:
            f.write(p.read())
        print(time.strftime("%H:%M:%S"), os.path.getsize(out), f"chunk {ch >> 10} KB", flush=True)
        ch = min(ch * 2, hi)
    else:
        print(time.strftime("%H:%M:%S"), f"refused at {have}, chunk {ch >> 10} KB, url {k % len(urls)}", flush=True)
        k += 1
        # one attempt per WAIT seconds while refused (every request counts against the Drive quota)
        time.sleep(int(os.environ.get("WAIT", "900")))
os.path.exists(part) and os.remove(part)
print("DONE", flush=True)
