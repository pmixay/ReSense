// The upload codec off the main thread: reads, compresses and sums chunks (chunkCodec.ts) so a
// 25 GB upload keeps the page responsive. Requests and answers are matched by `id`.
import { fingerprint, prepareChunk } from './chunkCodec';
import type { CodecRequest, CodecResponse } from './codec';

interface WorkerScope {
  onmessage: ((e: MessageEvent<CodecRequest>) => void) | null;
  postMessage(msg: CodecResponse, transfer?: Transferable[]): void;
}
const scope = self as unknown as WorkerScope;

scope.onmessage = async (e) => {
  const req = e.data;
  try {
    if (req.op === 'chunk') {
      const result = await prepareChunk(req.blob, req.start, req.end, req.gzip);
      scope.postMessage({ id: req.id, ok: true, chunk: result }, [result.body]);
    } else {
      scope.postMessage({ id: req.id, ok: true, fingerprint: await fingerprint(req.blob) });
    }
  } catch (err) {
    scope.postMessage({ id: req.id, ok: false, error: err instanceof Error ? err.message : String(err) });
  }
};
