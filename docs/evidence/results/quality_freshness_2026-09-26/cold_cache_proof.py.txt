import ctypes, json, mmap, os
from pathlib import Path
libc=ctypes.CDLL(None, use_errno=True)
libc.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
results=[]
for p in Path('/home/resense/data/for_hackathon/doubleT_obstacle').glob('*.db3'):
    fd=os.open(p,os.O_RDONLY)
    os.fsync(fd)
    size=os.fstat(fd).st_size
    os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
    mapping=mmap.mmap(fd,size,access=mmap.ACCESS_COPY)
    buffer=(ctypes.c_char*size).from_buffer(mapping)
    pages=(size+mmap.PAGESIZE-1)//mmap.PAGESIZE
    resident=(ctypes.c_ubyte*pages)()
    if libc.mincore(ctypes.addressof(buffer),size,resident): raise OSError(ctypes.get_errno(),'mincore')
    count=sum(bool(x & 1) for x in resident)
    results.append({'file':p.name,'bytes':size,'pages':pages,'resident_pages':count,'resident_fraction':count/pages})
    del buffer
    mapping.close()
    os.close(fd)
print(json.dumps(results,indent=2))
if any(r['resident_fraction'] > .01 for r in results): raise SystemExit('cold-cache condition not met')
