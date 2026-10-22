import sys, zstandard
zstandard.ZstdDecompressor().copy_stream(sys.stdin.buffer, sys.stdout.buffer, read_size=1 << 20, write_size=1 << 20)
