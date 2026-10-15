import { describe, expect, it } from 'vitest';
import { canGzip, crc32, crcHex, fingerprint, gzipTrailer, prepareChunk } from './chunkCodec';
import { CompressionPolicy, MAX_RATIO, PROBE_EVERY } from './compressionPolicy';

const enc = (s: string) => new TextEncoder().encode(s);

async function gunzip(buf: ArrayBuffer): Promise<Uint8Array> {
  const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function noise(n: number, seed = 1): Uint8Array {
  const out = new Uint8Array(n);
  let x = seed;
  for (let i = 0; i < n; i += 1) {
    x = (x * 1103515245 + 12345) >>> 0;
    out[i] = x >>> 24;
  }
  return out;
}

describe('crc32', () => {
  it('is the zlib / gzip CRC-32', () => {
    expect(crcHex(crc32(enc('123456789')))).toBe('cbf43926');
    expect(crc32(new Uint8Array(0))).toBe(0);
    expect(crcHex(crc32(enc('The quick brown fox jumps over the lazy dog')))).toBe('414fa339');
  });

  it('chains over pieces and handles every tail length', () => {
    const data = noise(1037);
    const whole = crc32(data);
    expect(crc32(data.subarray(500), crc32(data.subarray(0, 500)))).toBe(whole);
    // the slice-by-8 loop and the byte loop agree for lengths around a multiple of 8
    for (let n = 0; n < 20; n += 1) {
      const d = data.subarray(0, n);
      let c = 0;
      for (const b of d) c = crc32(new Uint8Array([b]), c);
      expect(crc32(d)).toBe(c);
    }
  });
});

describe('prepareChunk', () => {
  it('gzips what shrinks, with the CRC of the raw bytes from the trailer', async () => {
    expect(canGzip()).toBe(true);
    const raw = enc('lidar '.repeat(20000));
    const blob = new Blob([new Uint8Array(100), raw as BlobPart]);
    const c = await prepareChunk(blob, 100, 100 + raw.length, true);
    expect(c.encoding).toBe('gzip');
    expect(c.body.byteLength).toBeLessThan(raw.length / 10);
    expect(c.rawSize).toBe(raw.length);
    expect(c.crc).toBe(crc32(raw));
    expect(gzipTrailer(c.body)).toEqual({ crc: crc32(raw), size: raw.length });
    expect(await gunzip(c.body)).toEqual(raw);
  });

  it('sends raw what does not shrink, or when not asked', async () => {
    const raw = new Uint8Array(70000);
    for (let i = 0; i < raw.length; i += 65536) crypto.getRandomValues(raw.subarray(i, i + 65536));
    const blob = new Blob([raw as BlobPart]);
    for (const gzip of [true, false]) {
      const c = await prepareChunk(blob, 0, raw.length, gzip);
      expect(c.encoding).toBe('identity');
      expect(new Uint8Array(c.body)).toEqual(raw);
      expect(c.crc).toBe(crc32(raw));
    }
  });

  it('fingerprints size, head and tail', async () => {
    const a = noise(3 * 1024 * 1024, 1);
    const b = a.slice();
    b[b.length - 1] ^= 1; // a different tail
    const c = a.slice();
    c[1024 * 1024 + 5] ^= 1; // the middle: not seen (cheap on purpose)
    const fa = await fingerprint(new Blob([a as BlobPart]));
    expect(fa).toMatch(/^300000-[0-9a-f]{8}-[0-9a-f]{8}$/);
    expect(await fingerprint(new Blob([b as BlobPart]))).not.toBe(fa);
    expect(await fingerprint(new Blob([c as BlobPart]))).toBe(fa);
    expect(await fingerprint(new Blob([enc('small')]))).toMatch(/^5-[0-9a-f]{8}-00000000$/);
  });
});

describe('CompressionPolicy', () => {
  const MB = 1024 * 1024;

  it('measures first, then compresses on a slow link and not on a fast one', () => {
    const slow = new CompressionPolicy(true, 3);
    expect(slow.next()).toBe(true); // nothing known: try
    slow.compressed(8 * MB, 5.2 * MB, 400); // ratio 0.65, 20 MB/s per worker
    slow.sent(5.2 * MB, 1300, 3); // 12 MB/s on the link (100 Mbit/s)
    expect(slow.wins()).toBe(true);
    expect(slow.next()).toBe(true);

    const fast = new CompressionPolicy(true, 3);
    fast.compressed(8 * MB, 5.2 * MB, 400);
    fast.sent(8 * MB, 70, 1); // ~115 MB/s: the codec (60 MB/s) would hold it back
    expect(fast.wins()).toBe(false);
    const picks = Array.from({ length: PROBE_EVERY }, () => fast.next());
    expect(picks.filter(Boolean)).toHaveLength(1); // one probe now and then
    expect(picks[PROBE_EVERY - 1]).toBe(true);
  });

  it('stops for data that does not shrink and when disabled', () => {
    const p = new CompressionPolicy(true, 4);
    p.compressed(8 * MB, 8 * MB, 300);
    expect(p.stats.ratio).toBeGreaterThan(MAX_RATIO);
    expect(p.wins()).toBe(false);
    expect(new CompressionPolicy(false, 4).next()).toBe(false);
  });
});
