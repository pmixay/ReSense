// Decoder of the RSC1 binary point cloud (webapp/API.md, little-endian):
//   "RSC1" · uint32 n · int16[n·3] xyz in centimetres (vehicle frame, X forward, Y left, Z up)
//   · uint8[n] intensity · uint8[n] flags (bit0 corridor, bit1 confirmed gauge object box, bit2 advisory box)

export const RSC1_MAGIC = 'RSC1';
export const FLAG_CORRIDOR = 1;
export const FLAG_OBJECT = 2;
export const FLAG_WARNING = 4;

export interface DecodedCloud {
  n: number;
  positions: Float32Array; // n·3, metres
  intensity: Uint8Array; // n
  flags: Uint8Array; // n
}

export class CloudFormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CloudFormatError';
  }
}

const LITTLE_ENDIAN = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;

export function decodeRSC1(input: ArrayBuffer | ArrayBufferView): DecodedCloud {
  const bytes =
    input instanceof ArrayBuffer ? new Uint8Array(input) : new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
  if (bytes.byteLength < 8) throw new CloudFormatError('Облако повреждено: нет заголовка');
  const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
  if (magic !== RSC1_MAGIC) throw new CloudFormatError('Облако в неизвестном формате');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const n = view.getUint32(4, true);
  const need = 8 + n * 8; // 6 bytes xyz + 1 intensity + 1 flags
  if (bytes.byteLength < need) throw new CloudFormatError('Облако повреждено: данные обрезаны');

  const positions = new Float32Array(n * 3);
  const xyzOffset = bytes.byteOffset + 8;
  if (LITTLE_ENDIAN && xyzOffset % 2 === 0) {
    const raw = new Int16Array(bytes.buffer, xyzOffset, n * 3);
    for (let i = 0; i < raw.length; i += 1) positions[i] = raw[i] / 100;
  } else {
    for (let i = 0; i < n * 3; i += 1) positions[i] = view.getInt16(8 + i * 2, true) / 100;
  }
  const iOff = 8 + n * 6;
  // copies, so the caller may drop the response buffer
  const intensity = bytes.slice(iOff, iOff + n);
  const flags = bytes.slice(iOff + n, iOff + 2 * n);
  return { n, positions, intensity, flags };
}

/** Encoder (tests, fixtures): positions in metres, clipped to the int16 centimetre range. */
export function encodeRSC1(positions: ArrayLike<number>, intensity?: ArrayLike<number>, flags?: ArrayLike<number>): ArrayBuffer {
  const n = Math.floor(positions.length / 3);
  const buf = new ArrayBuffer(8 + n * 8);
  const view = new DataView(buf);
  const u8 = new Uint8Array(buf);
  for (let i = 0; i < 4; i += 1) u8[i] = RSC1_MAGIC.charCodeAt(i);
  view.setUint32(4, n, true);
  for (let i = 0; i < n * 3; i += 1) {
    const cm = Math.max(-32768, Math.min(32767, Math.round(positions[i] * 100)));
    view.setInt16(8 + i * 2, cm, true);
  }
  const iOff = 8 + n * 6;
  for (let i = 0; i < n; i += 1) {
    u8[iOff + i] = intensity ? Math.max(0, Math.min(255, Math.round(intensity[i]))) : 0;
    u8[iOff + n + i] = flags ? flags[i] & 0xff : 0;
  }
  return buf;
}

/** Counts of flagged points (for legends / HUD). */
export function flagCounts(flags: Uint8Array): { corridor: number; object: number; warning: number } {
  let corridor = 0;
  let object = 0;
  let warning = 0;
  for (let i = 0; i < flags.length; i += 1) {
    const f = flags[i];
    if (f & FLAG_CORRIDOR) corridor += 1;
    if (f & FLAG_OBJECT) object += 1;
    if (f & FLAG_WARNING) warning += 1;
  }
  return { corridor, object, warning };
}
