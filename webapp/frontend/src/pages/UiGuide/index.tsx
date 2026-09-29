// /_ui — the living style guide: every component of the kit in its states (visual review; not in the nav).
import { useState, type ReactNode } from 'react';
import {
  Button,
  Card,
  Chip,
  DecisionChip,
  DecisionLegend,
  DecisionStrip,
  EmptyState,
  ErrorBanner,
  Field,
  GoodMark,
  Help,
  ICON_NAMES,
  Icon,
  IconButton,
  KpiTile,
  PageHeader,
  PipelineLine,
  ProgressBar,
  Segmented,
  Select,
  Sparkline,
  Spinner,
  Stepper,
  StopMark,
  TextInput,
  Toggle,
  Tooltip,
} from '../../components';
import { ApiError } from '../../api/client';
import { decisionCounts } from '../../lib/decisions';
import { fmtBytes, fmtDuration, fmtFrames, fmtMeters, fmtMs, fmtRelDate } from '../../lib/format';
import { doubleT, doubleTLabels, newData, roundT, sparkValues } from './samples';
import styles from './UiGuide.module.css';

const SWATCHES: [string, string][] = [
  ['--red', '#E4000D'],
  ['--red-deep', '#B0000A'],
  ['--red-tint', '#FCE6E7'],
  ['--bg / --well', '#F5F3F0'],
  ['--well-2', '#EDE9E4'],
  ['--hair', '#E7E2DB'],
  ['--hair-2', '#D9D3CB'],
  ['--ink', '#16151A'],
  ['--go', '#12A150'],
  ['--go-deep', '#0B7A3B'],
  ['--caution', '#FFB300'],
  ['--stop', '#D0001B'],
  ['--fault', '#5B4E9C'],
  ['--night', '#05070D'],
];

function Section({ title, children, help }: { title: string; children: ReactNode; help?: string }) {
  return (
    <Card title={title} help={help} className={styles.section}>
      {children}
    </Card>
  );
}

function Row({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <div className={styles.row}>
      {label && <span className={styles.rowLabel}>{label}</span>}
      <div className={styles.rowBody}>{children}</div>
    </div>
  );
}

export default function UiGuide() {
  const [seg, setSeg] = useState<'file' | 'server' | 'demo'>('file');
  const [segSm, setSegSm] = useState<'cab' | 'top' | 'back'>('cab');
  const [tg, setTg] = useState(true);
  const [tg2, setTg2] = useState(false);
  const [step, setStep] = useState(1);
  const [pts, setPts] = useState(30000);
  const [sel, setSel] = useState('standard');
  const [txt, setTxt] = useState('doubleT_obstacle');
  const [ph, setPh] = useState(112);
  const [ph2, setPh2] = useState(4000);

  return (
    <>
      <PageHeader
        title="Компоненты"
        docTitle="Компоненты"
        station="settings"
        chips={
          <>
            <Chip variant="outline">«Линия»</Chip>
            <Chip variant="outline">/_ui — не в навигации</Chip>
          </>
        }
        actions={
          <>
            <Button variant="outline" icon="home" to="/">
              Главная
            </Button>
            <Button variant="primary" icon="play">
              Главное действие
            </Button>
          </>
        }
      />

      <div className={styles.cols}>
        <Section title="Цвета">
          <div className={styles.swatches}>
            {SWATCHES.map(([name, hex]) => (
              <div key={name} className={styles.swatch}>
                <span style={{ background: hex }} />
                <b>{name}</b>
                <small>{hex}</small>
              </div>
            ))}
            <div className={styles.swatch}>
              <span style={{ background: 'var(--stop) var(--hatch)' }} />
              <b>STOP + штриховка</b>
              <small>45°, белая</small>
            </div>
          </div>
        </Section>

        <Section title="Шрифты">
          <div className={styles.type}>
            <div className={styles.t1}>Benzin 800 · 34</div>
            <div className={styles.t2}>Benzin 700 · заголовок карточки 15</div>
            <div className={styles.t3}>
              55,6<small>м</small>
            </div>
            <div className={styles.t4}>Montserrat 800 · навигация, кнопки 14</div>
            <div className={styles.t5}>Montserrat 600 · подписи 12,5 · 11 271 кадр · 4,5 ГБ</div>
            <div className={styles.t6}>
              {fmtMeters(54.94)} · {fmtMs(72.4)} · {fmtDuration(20.43)} · {fmtDuration(84)} · {fmtDuration(1200)} · {fmtBytes(4.5 * 1024 ** 3)} · {fmtFrames(11271)} ·{' '}
              {fmtRelDate(new Date())}
            </div>
          </div>
        </Section>
      </div>

      <Section title="Кнопки" help="primary — только главное действие страницы (бренд-красный); остальное — dark / outline / ghost.">
        <Row label="варианты">
          <Button variant="primary" icon="play">
            Обработать
          </Button>
          <Button variant="dark" icon="play">
            Открыть плеер
          </Button>
          <Button variant="outline" icon="compare">
            Сравнить
          </Button>
          <Button variant="ghost" icon="download">
            Скачать
          </Button>
          <Button variant="dark" iconRight="arrow-right">
            Дальше
          </Button>
        </Row>
        <Row label="размеры">
          <Button variant="primary" size="lg" icon="play">
            Большая
          </Button>
          <Button variant="dark" size="md" icon="upload">
            Средняя
          </Button>
          <Button variant="outline" size="sm" iconRight="arrow-right">
            Малая
          </Button>
        </Row>
        <Row label="состояния">
          <Button variant="primary" loading>
            Загрузка
          </Button>
          <Button variant="dark" loading>
            Сохраняем
          </Button>
          <Button variant="outline" loading>
            Проверяем
          </Button>
          <Button variant="primary" disabled icon="play">
            Недоступно
          </Button>
          <Button variant="outline" disabled>
            Недоступно
          </Button>
        </Row>
        <div className={styles.onRed}>
          <Button variant="light" size="lg" icon="upload">
            Загрузить запись
          </Button>
          <Button variant="ghost-light" size="lg" icon="sparkle">
            Демо
          </Button>
          <Help tone="light">Подсказка на красном фоне.</Help>
        </div>
      </Section>

      <div className={styles.cols}>
        <Section title="Кнопки-иконки">
          <Row label="варианты">
            <IconButton icon="arrow-right" label="Открыть" />
            <IconButton icon="pause" label="Пауза" variant="white" />
            <IconButton icon="x" label="Отменить" variant="outline" />
            <IconButton icon="arrow-right" label="Открыть прогон" variant="dark" tooltip />
            <IconButton icon="retry" label="Повторить" variant="fault" tooltip />
            <IconButton icon="trash" label="Удалить" />
            <IconButton icon="play" label="Играть" variant="red" />
            <IconButton icon="loop" label="Повтор" active />
          </Row>
          <Row label="размеры">
            <IconButton icon="settings" label="xs" size="xs" />
            <IconButton icon="settings" label="sm" size="sm" />
            <IconButton icon="settings" label="md" size="md" />
            <IconButton icon="settings" label="lg" size="lg" variant="white" />
            <IconButton icon="settings" label="Загрузка" loading />
            <IconButton icon="settings" label="Недоступно" disabled />
          </Row>
        </Section>

        <Section title="Метки">
          <Row label="chip">
            <Chip>2 готово</Chip>
            <Chip variant="outline">детектор v1.0.0</Chip>
            <Chip variant="ink">1 в работе</Chip>
            <Chip variant="red">пресет</Chip>
            <Chip dot="var(--fault)">1 ошибка</Chip>
            <Chip variant="outline" icon="server">
              свободно 312 ГБ
            </Chip>
            <Chip size="sm" variant="outline" dot="var(--go)">
              онлайн
            </Chip>
          </Row>
          <Row label="решения">
            <DecisionChip decision="GO" />
            <DecisionChip decision="CAUTION" />
            <DecisionChip decision="STOP" />
            <DecisionChip decision="FAULT" />
            <DecisionChip decision="GO" label="БЕЗ СТОП" />
          </Row>
          <Row label="размеры">
            <DecisionChip decision="STOP" size="sm" />
            <DecisionChip decision="STOP" size="lg" extra="с кадра 8 · 55,6 м" />
            <DecisionChip decision="STOP" size="xl" pulse />
          </Row>
        </Section>
      </div>

      <Section title="Решения по кадрам" help="Полоса рисуется на canvas: по одной колонке на кадр или пиксель, самое тяжёлое решение побеждает. Клик и перетаскивание — перемотка, стрелки — по кадру.">
        <div className={styles.stripHead}>
          <span className={styles.rowLabel}>doubleT_obstacle · 201 кадр · метки, плейхед, разметка, ось</span>
          <DecisionLegend counts={decisionCounts(doubleT)} labelsCount={doubleTLabels.filter(Boolean).length} />
        </div>
        <DecisionStrip
          decisions={doubleT}
          height={44}
          radius={14}
          markers={[
            { pos: 8, label: 'кадр 8 · СТОП', tone: 'stop', align: 'start' },
            { pos: 111, label: '111', tone: 'go' },
            { pos: 117, label: '117', tone: 'caution' },
            { pos: 197, label: '197', tone: 'caution' },
          ]}
          playhead={ph}
          onSeek={setPh}
          labels={doubleTLabels}
          ticks
          tickUnit="кадр"
        />
        <div className={styles.stripGap} />
        <span className={styles.rowLabel}>new_data · 11 271 кадр (биннинг до пикселя), с ошибками и плейхедом</span>
        <DecisionStrip decisions={newData} height={26} radius={8} playhead={ph2} onSeek={setPh2} ticks posLabel={(p) => String(p)} />
        <div className={styles.stripGap} />
        <div className={styles.miniStrips}>
          <DecisionStrip decisions={doubleT} height={22} />
          <DecisionStrip decisions={roundT} height={22} />
          <DecisionStrip decisions={newData} height={22} />
          <DecisionStrip decisions="" height={22} />
        </div>
      </Section>

      <div className={styles.cols}>
        <Section title="Поля">
          <div className={styles.formGrid}>
            <Field label="Пресет" help="Набор параметров детектора — см. «Параметры».">
              {() => (
                <Select
                  label="Пресет"
                  icon="sliders"
                  value={sel}
                  onChange={setSel}
                  options={[
                    { value: 'standard', label: 'Базовый · v1.0' },
                    { value: 'fast', label: 'Быстрый' },
                  ]}
                />
              )}
            </Field>
            <Field label="Шаг кадров" help={<><b>1</b> — каждый кадр, как на поезде. <b>2</b> и больше — быстрее, но решения реже.</>}>
              <Stepper label="Шаг кадров" value={step} onChange={setStep} min={1} max={50} />
            </Field>
            <Field label="Точек в облаке">
              <Stepper label="Точек в облаке" value={pts} onChange={setPts} min={5000} max={120000} step={5000} />
            </Field>
            <Field label="Для плеера">
              <Toggle label="Облака точек" checked={tg} onChange={setTg} />
            </Field>
            <Field label="Название">{(id) => <TextInput id={id} icon="edit" value={txt} onChange={(e) => setTxt(e.target.value)} />}</Field>
            <Field label="Скорость" error="Больше 30 м/с не бывает">
              {(id) => <TextInput id={id} value="42" suffix="м/с" invalid readOnly />}
            </Field>
            <Field label="Поиск">{(id) => <TextInput id={id} icon="search" placeholder="запись или пресет" />}</Field>
            <Field label="Переключатель">
              <div className={styles.inline}>
                <Toggle ariaLabel="Выключено" checked={tg2} onChange={setTg2} />
                <Toggle ariaLabel="Включено" checked onChange={() => undefined} />
                <Toggle ariaLabel="Недоступно" checked={false} onChange={() => undefined} disabled />
              </div>
            </Field>
          </div>
          <Row label="segmented">
            <Segmented
              label="Источник"
              value={seg}
              onChange={setSeg}
              options={[
                { value: 'file', label: 'Файл', icon: 'file' },
                { value: 'server', label: 'Папка на сервере', icon: 'server' },
                { value: 'demo', label: 'Демо-запись', icon: 'sparkle' },
              ]}
            />
          </Row>
          <Row>
            <Segmented
              label="Вид"
              size="sm"
              tone="white"
              value={segSm}
              onChange={setSegSm}
              options={[
                { value: 'cab', label: 'Кабина', icon: 'train' },
                { value: 'top', label: 'Сверху' },
                { value: 'back', label: 'Сзади' },
              ]}
            />
          </Row>
        </Section>

        <Section title="Подсказки" help="«?» открывается наведением и фокусом с клавиатуры, Escape закрывает; одна подсказка на экране.">
          <Row label="позиции">
            <Tooltip content="Сверху" placement="top" width="auto">
              <Button variant="outline" size="sm">
                top
              </Button>
            </Tooltip>
            <Tooltip content="Снизу" placement="bottom" width="auto">
              <Button variant="outline" size="sm">
                bottom
              </Button>
            </Tooltip>
            <Tooltip content="Слева" placement="left" width="auto">
              <Button variant="outline" size="sm">
                left
              </Button>
            </Tooltip>
            <Tooltip content="Справа" placement="right" width="auto">
              <Button variant="outline" size="sm">
                right
              </Button>
            </Tooltip>
          </Row>
          <Row label="открыта">
            <span className={styles.tipDemo}>
              Итог
              <Help placement="bottom-start" defaultOpen width={260}>
                Детектор против разметки:
                <br />
                <b>верно</b> — СТОП на объекте,
                <br />
                <b>ложный СТОП</b> — на пустом пути.
              </Help>
            </span>
          </Row>
          <div className={styles.tipSpace} />
        </Section>
      </div>

      <Section title="Карточки и показатели">
        <div className={styles.cardsRow}>
          <Card title="Карточка" help="Заголовок Benzin 700 · 15, «?» и действия справа." actions={<Button variant="outline" size="sm" iconRight="arrow-right">Все</Button>} className={styles.demoCard}>
            <span className={styles.meta}>Белая карточка, радиус 28.</span>
          </Card>
          <Card title="Тёмная" variant="dark" help="Подсказка на тёмном." className={styles.demoCard}>
            <span className={styles.meta}>ink-фон, белый текст.</span>
          </Card>
          <Card title="Главное действие" variant="red" className={styles.demoCard}>
            <span className={styles.meta}>Градиент бренда, только CTA.</span>
          </Card>
          <Card title="Колодец" variant="well" className={styles.demoCard}>
            <span className={styles.meta}>well-фон внутри карточек.</span>
          </Card>
        </div>
        <div className={styles.kpiRow}>
          <KpiTile label="Кадров" value="201" sub="10 Гц" />
          <KpiTile label="Длительность" value="20,4" unit="с" sub="4,5 ГБ облаков" />
          <KpiTile label="Первый СТОП" icon={<StopMark />} help="Кадр 8 — первый, где человек входит в габарит." value="55,6" unit="м" sub="кадр 8 · задержка 0" />
          <KpiTile label="p95 задержка" variant="dark" value="72" unit="мс" sub="сквозная 81 мс" />
          <KpiTile label="Ложные тревоги" variant="green" value="0" after={<GoodMark />} sub="против разметки" />
          <KpiTile label="Загрузка CPU" viz={<Sparkline values={sparkValues} height={46} />} value="0,7" unit="ядра" sub="из 4" />
        </div>
      </Section>

      <div className={styles.cols}>
        <Section title="Обработка" help="Мини-линия этапов детектора: пройдено, текущий (вращается), впереди.">
          <div className={styles.pipes}>
            <PipelineLine current={3} />
            <PipelineLine current={1} compact failed />
            <PipelineLine current={6} compact />
          </div>
          <Row label="прогресс">
            <div className={styles.bars}>
              <ProgressBar value={0.64} height={14} />
              <ProgressBar value={0.2} />
              <ProgressBar value={null} height={8} label="Подготовка" />
            </div>
          </Row>
        </Section>
        <Section title="Состояния">
          <div className={styles.states}>
            <Row label="spinner">
              <Spinner />
              <Spinner size={28} />
              <span className={styles.darkDot}>
                <Spinner tone="light" />
              </span>
            </Row>
            <ErrorBanner error={new ApiError('Топик облака не найден', 422)} onRetry={() => undefined} />
            <ErrorBanner error={new ApiError('Бэкенд недоступен — проверьте, что сервер запущен', 0)} compact />
            <div className={styles.emptyBox}>
              <EmptyState icon="list" title="Прогонов пока нет" action={<Button variant="dark" icon="upload">Загрузить запись</Button>}>
                Загрузите запись или создайте демо.
              </EmptyState>
            </div>
          </div>
        </Section>
      </div>

      <Section title="Иконки">
        <div className={styles.icons}>
          {ICON_NAMES.map((n) => (
            <div key={n} className={styles.icon}>
              <Icon name={n} size={22} />
              <small>{n}</small>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
