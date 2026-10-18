// The real node's status via rosbridge. roslib is imported lazily so it only lands in the chunk of
// the page that connects.
import type { LiveMessage } from './types';
import { isStatus } from './status';
import { STATUS_TOPIC, rosbridgeUrl } from './ws';

export interface RosStatusHandlers {
  onMessage(msg: LiveMessage): void;
  onConnection?(): void;
  onClose?(): void;
  onError?(message: string): void;
}

export interface RosStatusSubscription {
  close(): void;
}

export async function subscribeRosStatus(url: string = rosbridgeUrl(), h: RosStatusHandlers): Promise<RosStatusSubscription> {
  const ROSLIB = await import('roslib');
  const ros = new ROSLIB.Ros({});
  ros.on('connection', () => h.onConnection?.());
  ros.on('close', () => h.onClose?.());
  ros.on('error', () => h.onError?.('Нет связи с узлом ROS (rosbridge)'));
  const topic = new ROSLIB.Topic<{ data: string }>({ ros, name: STATUS_TOPIC, messageType: 'std_msgs/msg/String' });
  topic.subscribe((m) => {
    try {
      const status: unknown = JSON.parse(m.data);
      if (!isStatus(status)) throw new Error('Invalid status');
      h.onMessage(status);
    } catch {
      h.onError?.('Некорректное сообщение узла');
    }
  });
  ros.connect(url).catch(() => h.onError?.('Нет связи с узлом ROS (rosbridge)'));
  return {
    close() {
      topic.unsubscribe();
      ros.close();
    },
  };
}
