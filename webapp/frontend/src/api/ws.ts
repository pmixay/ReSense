// WebSocket helpers for the live page: the backend's replay simulation (/api/live/sim) and the
// real node's rosbridge (ws://<host>:9090, topic /resense/status, std_msgs/String JSON).
import type { LiveCommand, LiveMessage } from './types';

export interface LiveSimParams {
  runId: string;
  speed?: number; // 0.25..10
  loop?: boolean;
}

/** ws(s)://<page host>/api/live/sim?run_id=…&speed=…&loop=… (relative to the page origin, so the
 *  Vite proxy and the production server both work). */
export function liveSimUrl({ runId, speed = 1, loop = false }: LiveSimParams, origin: Location | URL = window.location): string {
  const proto = origin.protocol === 'https:' ? 'wss:' : 'ws:';
  const qs = new URLSearchParams({ run_id: runId, speed: String(clampSpeed(speed)), loop: String(loop) });
  return `${proto}//${origin.host}/api/live/sim?${qs.toString()}`;
}

export function clampSpeed(speed: number): number {
  return Math.min(10, Math.max(0.25, Number.isFinite(speed) ? speed : 1));
}

/** Default rosbridge address: the page's host, port 9090. */
export function rosbridgeUrl(host?: string, origin: Location | URL = window.location): string {
  const proto = origin.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${host || origin.hostname}:9090`;
}

export const STATUS_TOPIC = '/resense/status';

export interface LiveSocket {
  send(cmd: LiveCommand): void;
  close(): void;
  readonly socket: WebSocket;
}

export interface LiveHandlers {
  onMessage(msg: LiveMessage): void;
  onOpen?(): void;
  onClose?(ev: CloseEvent): void;
  onError?(message: string): void;
}

/** Opens the simulation socket; malformed messages are reported via onError and skipped. */
export function openLiveSim(params: LiveSimParams, h: LiveHandlers): LiveSocket {
  const socket = new WebSocket(liveSimUrl(params));
  socket.onopen = () => h.onOpen?.();
  socket.onclose = (ev) => h.onClose?.(ev);
  socket.onerror = () => h.onError?.('Соединение с эфиром прервано');
  socket.onmessage = (ev) => {
    if (typeof ev.data !== 'string') return;
    try {
      h.onMessage(JSON.parse(ev.data) as LiveMessage);
    } catch {
      h.onError?.('Некорректное сообщение эфира');
    }
  };
  return {
    socket,
    send(cmd) {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(cmd));
    },
    close() {
      socket.close();
    },
  };
}
