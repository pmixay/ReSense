// The facts of «О системе»: the decisions, the pipeline stations, the headline results (README
// «Результаты», measured in-sample), the quick-start commands (README «Кратко для жюри»), links and
// the team. Static on purpose: the numbers are the project's evidence, not something this server
// measures; the stand's own versions and features come from GET /api/system.
import type { Decision } from '../../api/types';
import type { IconName } from '../../components';

export const REPO_URL = 'https://github.com/pmixay/ReSense';
export const GUIDE_URL = 'https://resense.gitbook.io/resense-docs/';
export const WEBAPP_URL = 'http://localhost:8080';

const blob = (path: string) => `${REPO_URL}/blob/main/${path}`;

// ---------------------------------------------------------------- decisions

export interface DecisionInfo {
  decision: Decision;
  /** the rule, for the «?» */
  rule: string;
  /** the ROS topic value */
  topic: string;
}

/** As a driver reads them: from «all clear» to «cannot see» (the node's priority order is in the
 *  «решение» station's help). */
export const DECISION_INFO: readonly DecisionInfo[] = [
  { decision: 'GO', topic: 'GO', rule: 'Препятствие не обнаружено. Дальность контроля — /resense/clear_distance: это оценка, а не гарантия.' },
  {
    decision: 'CAUTION',
    topic: 'CAUTION',
    rule: 'Подсказка, не тревога: объект у габарита снаружи или за доверенной дальностью, известная инфраструктура тоннеля, сниженная исправность.',
  },
  { decision: 'STOP', topic: 'STOP', rule: 'Тревога: подтверждённое препятствие в габарите 2,1 × 3,0 м. Расстояние до него — /resense/nearest_distance.' },
  { decision: 'FAULT', topic: 'FAULT', rule: 'Входа нет (до первого кадра или дольше 0,5 с без кадров) либо ему нельзя доверять.' },
];

// ---------------------------------------------------------------- pipeline

export interface Station {
  key: string;
  name: string;
  /** the one number of the station, Benzin under the name */
  value?: string;
  icon: IconName;
  help: string;
}

export const STATIONS: readonly Station[] = [
  {
    key: 'decode',
    name: 'декодирование',
    value: '10 Гц',
    icon: 'zip',
    help: 'Облако PointCloud2 читается прямо из сериализованных байтов, без лишних копий. Подходит любая пара топик / frame id.',
  },
  {
    key: 'calib',
    name: 'калибровка',
    icon: 'ruler',
    help: 'Крепление лидара уточняется по рельсам: наклон и высота датчика — на каждой записи заново.',
  },
  {
    key: 'track',
    name: 'модель пути',
    icon: 'rails',
    help: 'Полотно, головки рельсов, ось пути и её кривизна по стенам: коридор следует изгибам тоннеля. Без карты.',
  },
  {
    key: 'gauge',
    name: 'габарит',
    value: '2,1 × 3,0 м',
    icon: 'gauge',
    help: 'Габарит поезда от организаторов протягивается вдоль оси: 1,05 м в каждую сторону, 0,12–3,0 м над головкой рельса. Зона предупреждения — ещё 0,35 м.',
  },
  {
    key: 'cluster',
    name: 'кластеризация',
    icon: 'cube',
    help: 'Точки внутри габарита группируются (DBSCAN, радиус растёт с дальностью). Колонны, грани стен, провода и знаки узнаются по сигнатурам — это ВНИМАНИЕ, не СТОП.',
  },
  {
    key: 'tracking',
    name: 'трекинг',
    value: '0,5 с',
    icon: 'target',
    help: 'Объект, который держится внутри габарита 0,5 с, подтверждается. Небольшая обученная модель может задержать сомнительный дальний СТОП не больше чем на 10 кадров, но никогда не отменяет его.',
  },
  {
    key: 'decision',
    name: 'решение',
    icon: 'stop-octagon',
    help: 'СТОП при подтверждённом препятствии; иначе ОШИБКА, если входу нельзя доверять; иначе ВНИМАНИЕ; иначе СВОБОДНО. Топики /resense/decision и /resense/nearest_distance.',
  },
];

// ---------------------------------------------------------------- results

export interface ResultFact {
  key: string;
  label: string;
  value: string;
  unit?: string;
  sub: string;
  /** the caveat, for the «?» */
  help: string;
  mark?: 'stop' | 'good';
  variant?: 'light' | 'dark' | 'green';
}

/** README «Результаты» (independent assessment 28.09 and the team's 4-core VM; in-sample). */
export const RESULTS: readonly ResultFact[] = [
  {
    key: 'obstacle',
    label: 'Реальное препятствие',
    value: '55,5–56,6',
    unit: 'м',
    sub: 'СТОП 193 из 201 кадра',
    mark: 'stop',
    help: 'doubleT_obstacle: человек на пути. СТОП с первого кадра в габарите до конца записи, без пропусков; разметка 55,4–56,6 м. В выборке: правила настраивались на этой записи.',
  },
  {
    key: 'false',
    label: 'Ложные СТОП',
    value: '2,3',
    unit: 'на км',
    sub: '20 мин · 13 км',
    help: '20-минутная поездка без препятствий, 11 271 кадр: 30 эпизодов СТОП, 1,5 % кадров. В выборке. ВНИМАНИЕ на пустом пути бывает часто (35–69 % кадров).',
  },
  {
    key: 'synthetic',
    label: 'Синтетика',
    value: '8 из 8',
    sub: 'СТОП в габарите',
    mark: 'good',
    variant: 'green',
    help: '10 объектов организаторов, построенных лучевым методом (1 510 кадров): СТОП для всех 8 внутри габарита, куб снаружи — ни разу. Синтетика, в выборке; малые объекты подтверждаются на 30–56 м.',
  },
  {
    key: 'latency',
    label: 'Задержка p95',
    value: '81',
    unit: 'мс',
    sub: 'сквозная, ROS в Docker',
    variant: 'dark',
    help: 'От плеера бэга до результата, облака 360° по 24 МБ, 4-ядерная ВМ: p95 81–82 мс; декодирование + обнаружение — 63–72 мс.',
  },
  {
    key: 'rate',
    label: 'Частота',
    value: '10',
    unit: 'кадр/с',
    sub: 'меньше 1 ядра CPU',
    help: 'Лидар даёт 10 кадров в секунду — нода обрабатывает каждый, занимая меньше одного ядра CPU на 4-ядерной ВМ. Без GPU.',
  },
  {
    key: 'reach',
    label: 'Лидар видит',
    value: '≈ 210',
    unit: 'м',
    sub: 'по 13 759 кадрам',
    help: 'Ни одного отражения дальше ~210 м ни в одном из 13 759 кадров: 300 м этому лидару недостижимы. Поэтому шкалы дальности на сайте — до 210 м.',
  },
];

// ---------------------------------------------------------------- quick start

export interface Command {
  cmd: string;
  /** what the step does, for the step's tooltip */
  what: string;
}

/** README «Кратко для жюри», steps 1–5 (step 0, the UDP buffer, is in the card's «?»). */
export const ROS_COMMANDS: readonly Command[] = [
  { cmd: 'docker load -i resense-image-<версия>.tar.gz', what: 'Один раз, без интернета: образ из архива' },
  { cmd: 'docker run --rm -it --net=host --ipc=host resense', what: 'Консоль 1: нода' },
  { cmd: 'ros2 bag play <бэг> --delay 3 --read-ahead-queue-size 10', what: 'Консоль 2: проиграть запись' },
  { cmd: 'ros2 topic echo /resense/decision --field data', what: 'Консоль 3: GO | CAUTION | STOP | FAULT' },
  { cmd: 'ros2 topic echo /resense/nearest_distance --field data', what: 'Расстояние до препятствия, м; −1 — нет' },
];

export const UDP_BUFFER_CMD = 'sudo sysctl -w net.core.rmem_max=33554432';
export const WEBAPP_CMD = 'scripts/run_webapp.sh';

// ---------------------------------------------------------------- links

export interface DocLink {
  key: string;
  label: string;
  href: string;
  icon: IconName;
  help: string;
}

export const LINKS: readonly DocLink[] = [
  { key: 'guide', label: 'Руководство', href: GUIDE_URL, icon: 'info', help: 'Руководство пользователя на GitBook: установка, запуск, параметры ноды, топики и JSON статуса.' },
  { key: 'arch', label: 'Архитектура', href: blob('docs/ARCHITECTURE.md'), icon: 'layers', help: 'docs/ARCHITECTURE.md: нода, модули детектора, потоки данных, известные ограничения.' },
  { key: 'algo', label: 'Алгоритм', href: blob('docs/ALGORITHM.md'), icon: 'rails', help: 'docs/ALGORITHM.md: модель пути, габарит, кластеризация, трекинг — с математикой и параметрами.' },
  { key: 'exp', label: 'Эксперименты', href: blob('docs/EXPERIMENTS.md'), icon: 'chart', help: 'docs/EXPERIMENTS.md: дальность, задержка, частота кадров, ложные тревоги — полные таблицы.' },
  {
    key: 'legacy',
    label: 'Прежний дашборд',
    href: `${REPO_URL}/tree/main/web`,
    icon: 'bars',
    help: 'web/index.html — дашборд без сборки: откройте файл в браузере. Работает с rosbridge и с results.jsonl.',
  },
];

// ---------------------------------------------------------------- team

export interface Member {
  id: string;
  role: string;
  /** what they are responsible for, for the «?» */
  owns: string;
  captain?: boolean;
}

export const TEAM: readonly Member[] = [
  {
    id: 'P1',
    role: 'Аналитик, ROS 2',
    captain: true,
    owns: 'Капитан. Требования, архитектура, нода, Docker, CI и релиз, протокол оценки, связь с организаторами.',
  },
  { id: 'P2', role: 'Разработчик UI', owns: 'RViz, Foxglove, веб-дашборд, инструмент разметки; питч и видео.' },
  { id: 'P3', role: 'Компьютерное зрение', owns: 'Детектор: модель пути, габарит, кластеризация, трекинг, подавление ложных тревог, производительность.' },
  { id: 'P4', role: 'Данные и метрики', owns: 'Инструменты для данных, синтетические препятствия, метки, метрики, тесты.' },
];

// ---------------------------------------------------------------- the stand (GET /api/system)

export type FeatureKey = 'rosbags' | 'open3d' | 'native_kernels' | 'clouds';

export const FEATURES: readonly { key: FeatureKey; label: string; help: string }[] = [
  { key: 'rosbags', label: 'Бэги ROS 2', help: 'Пакет rosbags: чтение записей .db3 и .mcap без ROS.' },
  { key: 'native_kernels', label: 'Ядра C++', help: 'Необязательные ядра на C++: побитово те же результаты, детектор примерно вдвое быстрее.' },
  { key: 'open3d', label: 'open3d', help: 'Установлен open3d (для инструментов и тестов; детектору не обязателен).' },
  { key: 'clouds', label: 'Облака для 3D', help: 'Прогоны сохраняют прореженные облака точек для плеера и 3D-вида.' },
];

/** "1.0.0" → "v1.0.0" (a version that already starts with v is kept). */
export function fmtVersion(v: string | null | undefined): string {
  const s = (v ?? '').trim();
  if (!s) return '—';
  return /^v/i.test(s) ? s : `v${s}`;
}
