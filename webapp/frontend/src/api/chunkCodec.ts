// Preparing upload chunks (runs in a Web Worker, or inline where there is none): read a slice of
// the file, compress it with gzip when asked (CompressionStream, native zlib) and give its CRC-32
// over the raw bytes, which the server checks (webapp/API.md, «Recordings»: X-Content-CRC32).
// A gzip body carries that CRC in its trailer, so only raw chunks are summed here in JS.

// slice-by-8 CRC-32 (IEEE 802.3, the zlib.crc32 / gzip one): ~0.7 GB/s in V8
const TABLE = (() => {
  const t = new Int32Array(8 * 256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  for (let n = 0; n < 256; n += 1) {
    let c = t[n];
    for (let s = 1; s < 8; s += 1) {
      c = t[c & 255] ^ (c >>> 8);
      t[s * 256 + n] = c;
    }
  }
  return t;
})();

/** CRC-32 of `bytes`, continuing from `crc` (pass the previous result to chain). Unsigned. */
export function crc32(bytes: Uint8Array, crc = 0): number {
  const t = TABLE;
  let c = ~crc;
  let i = 0;
  const n = bytes.length;
  for (; i + 8 <= n; i += 8) {
    const a = (bytes[i] | (bytes[i + 1] << 8) | (bytes[i + 2] << 16) | (bytes[i + 3] << 24)) ^ c;
    const b = bytes[i + 4] | (bytes[i + 5] << 8) | (bytes[i + 6] << 16) | (bytes[i + 7] << 24);
    c =
      t[1792 + (a & 255)] ^
      t[1536 + ((a >>> 8) & 255)] ^
      t[1280 + ((a >>> 16) & 255)] ^
      t[1024 + (a >>> 24)] ^
      t[768 + (b & 255)] ^
      t[512 + ((b >>> 8) & 255)] ^
      t[256 + ((b >>> 16) & 255)] ^
      t[b >>> 24];
  }
  for (; i < n; i += 1) c = t[(c ^ bytes[i]) & 255] ^ (c >>> 8);
  return ~c >>> 0;
}

export const crcHex = (crc: number): string => crc.toString(16).padStart(8, '0');

/** gzip in this context (Chrome 80+, Firefox 113+, Safari 16.4+, Node 18+). */
export function canGzip(): boolean {
  try {
    return typeof CompressionStream === 'function' && !!new CompressionStream('gzip');
  } catch {
    return false;
  }
}

async function gzipBytes(bytes: Uint8Array): Promise<ArrayBuffer> {
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(new CompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}

/** The CRC-32 and the length of the raw data, from a gzip member's 8-byte trailer. */
export function gzipTrailer(gz: ArrayBuffer): { crc: number; size: number } {
  const v = new DataView(gz, gz.byteLength - 8, 8);
  return { crc: v.getUint32(0, true), size: v.getUint32(4, true) };
}

export interface PreparedChunk {
  body: ArrayBuffer; // what goes on the wire
  encoding: 'identity' | 'gzip';
  crc: number; // CRC-32 of the raw bytes
  rawSize: number;
  /** time spent reading + summing / compressing (ms) */
  codecMs: number;
}

/** Reads `blob[start, end)` and prepares it for sending. With `gzip`, a body that does not shrink
 *  is sent raw (its CRC computed then). */
export async function prepareChunk(blob: Blob, start: number, end: number, gzip: boolean): Promise<PreparedChunk> {
  const t0 = performance.now();
  const raw = new Uint8Array(await blob.slice(start, end).arrayBuffer());
  if (gzip && raw.length > 0) {
    const gz = await gzipBytes(raw);
    if (gz.byteLength < raw.length) {
      const { crc } = gzipTrailer(gz);
      return { body: gz, encoding: 'gzip', crc, rawSize: raw.length, codecMs: performance.now() - t0 };
    }
  }
  const crc = crc32(raw);
  return { body: raw.buffer as ArrayBuffer, encoding: 'identity', crc, rawSize: raw.length, codecMs: performance.now() - t0 };
}

const PROBE = 1024 * 1024;

/** A cheap identity of a file's content for resuming: size + CRC-32 of its first and last MiB. A
 *  different file under the same name makes the server start that file over. */
export async function fingerprint(blob: Blob): Promise<string> {
  const head = new Uint8Array(await blob.slice(0, PROBE).arrayBuffer());
  const tail = blob.size > PROBE ? new Uint8Array(await blob.slice(Math.max(PROBE, blob.size - PROBE)).arrayBuffer()) : new Uint8Array(0);
  return `${blob.size.toString(16)}-${crcHex(crc32(head))}-${crcHex(crc32(tail))}`;
}
