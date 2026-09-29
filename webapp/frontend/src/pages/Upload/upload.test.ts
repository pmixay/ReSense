import { describe, expect, it } from 'vitest';
import type { ServerEntry } from '../../api/types';
import { cloudBytes, demoBytes, framesToProcess, processSeconds } from './estimate';
import { guessKind } from './kinds';
import { cloudTopics, isRecordingEntry, recordingMeta } from './recording';
import { demoProgress } from './useDemo';

describe('guessKind', () => {
  it('recognises the accepted inputs from their paths', () => {
    expect(guessKind(['ride.zip']).kind).toBe('zip');
    expect(guessKind(['bag/metadata.yaml', 'bag/bag_0.db3']).kind).toBe('rosbag2');
    expect(guessKind(['bag/metadata.yaml', 'bag/bag_0.mcap']).kind).toBe('rosbag2');
    expect(guessKind(['bag_0.mcap']).kind).toBe('mcap');
    expect(guessKind(['bag_0.DB3']).kind).toBe('db3');
    expect(guessKind(['results.jsonl']).kind).toBe('jsonl');
    expect(guessKind(['frames/000001.npy', 'frames/000002.npz']).kind).toBe('npy');
  });
  it('flags labels files and unknown files as not a recording', () => {
    expect(guessKind(['doubleT_obstacle.json'])).toMatchObject({ kind: 'labels', ok: false });
    expect(guessKind(['notes.txt'])).toMatchObject({ kind: 'unknown', ok: false, label: 'формат не распознан' });
    expect(guessKind([])).toMatchObject({ kind: 'unknown', ok: false });
  });
});

describe('processing estimates', () => {
  it('frames after the step, capped by the limit (as the backend counts frames_total)', () => {
    expect(framesToProcess(201)).toBe(201);
    expect(framesToProcess(201, 2)).toBe(101);
    expect(framesToProcess(201, 3, 10)).toBe(64);
    expect(framesToProcess(201, 1, 0, 50)).toBe(50);
    expect(framesToProcess(null)).toBeNull();
  });
  it('time at ~10 frames/s, clouds up to 3000 frames × 30 000 points × 8 bytes', () => {
    expect(processSeconds(150)).toBe(15);
    expect(cloudBytes(100)).toBe(100 * (30000 * 8 + 8));
    expect(cloudBytes(10000)).toBe(3000 * (30000 * 8 + 8));
    expect(demoBytes(15)).toBe(15 * 33 * 1024 * 1024);
  });
});

describe('demo progress', () => {
  it('estimates from the elapsed time until the server reports, capped below done', () => {
    expect(demoProgress(5, 10, null)).toEqual({ fraction: 0.5, etaS: 5 });
    expect(demoProgress(30, 10, null)).toEqual({ fraction: 0.95, etaS: 0 });
  });
  it('uses the server fraction and derives the time left from it', () => {
    expect(demoProgress(4, 10, 0.25)).toEqual({ fraction: 0.25, etaS: 12 });
  });
});

describe('recordings and server entries', () => {
  it('lists PointCloud2 topics and a Russian meta line', () => {
    const rec = {
      topics: [
        { name: '/lidar_points', type: 'sensor_msgs/msg/PointCloud2', count: 201 },
        { name: '/imu', type: 'sensor_msgs/msg/Imu', count: 2000 },
      ],
      n_frames: 201,
      duration_s: 20.4,
      size_bytes: 4.5 * 1024 ** 3,
    };
    expect(cloudTopics(rec)).toEqual(['/lidar_points']);
    expect(recordingMeta(rec).replace(/\u00a0/g, ' ')).toBe('201 кадр · 20,4 с · 4,5 ГБ');
    expect(recordingMeta({ n_frames: null, duration_s: null, size_bytes: 0 })).toBe('');
  });
  it('knows which server entries are recordings', () => {
    const e = (x: Partial<ServerEntry>): ServerEntry => ({ name: 'x', path: 'x', type: 'dir', size_bytes: 0, is_bag: false, is_npy_dir: false, ...x });
    expect(isRecordingEntry(e({ is_bag: true }))).toBe(true);
    expect(isRecordingEntry(e({ is_npy_dir: true }))).toBe(true);
    expect(isRecordingEntry(e({}))).toBe(false);
    expect(isRecordingEntry(e({ type: 'file', name: 'run.jsonl' }))).toBe(true);
    expect(isRecordingEntry(e({ type: 'file', name: 'metadata.yaml' }))).toBe(true);
    expect(isRecordingEntry(e({ type: 'file', name: 'readme.txt' }))).toBe(false);
  });
});
