import { describe, expect, it } from 'vitest';
import { CloudFormatError, FLAG_CORRIDOR, FLAG_OBJECT, FLAG_WARNING, decodeRSC1, encodeRSC1, flagCounts } from './cloud';

// A buffer written the way resense_web.clouds writes it (struct '<4sI', int16 cm, uint8, uint8).
function pythonLike(points: [number, number, number][], inten: number[], flags: number[]): ArrayBuffer {
  const n = points.length;
  const buf = new ArrayBuffer(8 + n * 8);
  const v = new DataView(buf);
  'RSC1'.split('').forEach((c, i) => v.setUint8(i, c.charCodeAt(0)));
  v.setUint32(4, n, true);
  points.flat().forEach((m, i) => v.setInt16(8 + 2 * i, Math.round(m * 100), true));
  inten.forEach((x, i) => v.setUint8(8 + 6 * n + i, x));
  flags.forEach((x, i) => v.setUint8(8 + 7 * n + i, x));
  return buf;
}

describe('RSC1', () => {
  it('decodes metres, intensity and flags', () => {
    const buf = pythonLike([[55.61, -0.42, 1.07], [-3.5, 12.25, -1.62], [327.67, -327.68, 0]], [12, 255, 0], [
      FLAG_CORRIDOR | FLAG_OBJECT, 0, FLAG_WARNING,
    ]);
    const c = decodeRSC1(buf);
    expect(c.n).toBe(3);
    const exp = [55.61, -0.42, 1.07, -3.5, 12.25, -1.62, 327.67, -327.68, 0];
    Array.from(c.positions).forEach((v, i) => expect(v).toBeCloseTo(exp[i], 4));
    expect(Array.from(c.intensity)).toEqual([12, 255, 0]);
    expect(Array.from(c.flags)).toEqual([3, 0, 4]);
    expect(flagCounts(c.flags)).toEqual({ corridor: 1, object: 1, warning: 1 });
  });
  it('round-trips the encoder and accepts an offset view', () => {
    const pos = [1, 2, 3, -4.56, 0.01, 99.99];
    const buf = encodeRSC1(pos, [1, 2], [0, 7]);
    const padded = new Uint8Array(buf.byteLength + 3);
    padded.set(new Uint8Array(buf), 3); // odd offset: the DataView path
    const c = decodeRSC1(new Uint8Array(padded.buffer, 3, buf.byteLength));
    Array.from(c.positions).forEach((v, i) => expect(v).toBeCloseTo(pos[i], 4));
    expect(Array.from(c.flags)).toEqual([0, 7]);
  });
  it('decodes an empty cloud', () => {
    const c = decodeRSC1(encodeRSC1([]));
    expect(c.n).toBe(0);
    expect(c.positions.length).toBe(0);
  });
  it('rejects bad input with Russian messages', () => {
    expect(() => decodeRSC1(new ArrayBuffer(4))).toThrow(CloudFormatError);
    const bad = encodeRSC1([1, 2, 3]);
    new Uint8Array(bad)[0] = 88;
    expect(() => decodeRSC1(bad)).toThrow('неизвестном формате');
    const short = encodeRSC1([1, 2, 3, 4, 5, 6]).slice(0, 20);
    expect(() => decodeRSC1(short)).toThrow('обрезаны');
  });
});
