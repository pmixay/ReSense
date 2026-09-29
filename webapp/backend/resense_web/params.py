"""The detector parameters a jury member may tune from the web UI (``GET /api/presets/schema``),
their validation and the ``DetectorConfig`` of a preset: ``configs/default.yaml`` with the
preset's dotted overrides (``"tracking.confirm_time_s": 0.7``) applied through
``DetectorConfig.from_dict``. Defaults are read from that file at import, never hard-coded."""
from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path

import yaml

import resense
from resense.config import DetectorConfig

DEFAULT_CONFIG_PATH = Path(resense.__file__).resolve().parents[1] / "configs" / "default.yaml"

# (key, group, label, help, type, min, max, step, unit); the default comes from the config file
_SPECS = [
    ("sensor.min_range", "Датчик", "Ближняя граница точек",
     "Точки ближе этого расстояния отбрасываются: это нос поезда, грязь и капли на окне датчика. "
     "Больше — меньше помех, но длиннее слепая зона прямо перед поездом.",
     "float", 0.5, 10.0, 0.5, "м"),
    ("gauge.range_max", "Габарит", "Дальность контроля",
     "Дальше этого расстояния габарит не проверяется. Меньше — меньше ложных срабатываний вдали, "
     "но препятствие будет замечено позже.",
     "float", 30.0, 250.0, 10.0, "м"),
    ("gauge.warning_margin", "Габарит", "Ширина зоны предупреждения",
     "На сколько зона предупреждения шире габарита 2,1 м с каждой стороны. Объект в этой полосе "
     "даёт ВНИМАНИЕ, а не СТОП; шире — больше предупреждений.",
     "float", 0.0, 1.0, 0.05, "м"),
    ("gauge.edge_margin_per_100m", "Габарит", "Запас у края на 100 м",
     "Насколько объект должен зайти внутрь габарита от его края для СТОП, на каждые 100 м дальности "
     "(учёт неточности оси пути вдали). Больше — меньше ложных СТОП у стен, но позже реакция на "
     "объекты у края.",
     "float", 0.0, 0.5, 0.01, "м"),
    ("gauge.no_rail_range", "Габарит", "Дальность без найденных рельсов",
     "Если рельсы рядом с поездом не найдены (станции, съезды), объекты дальше этого расстояния дают "
     "только ВНИМАНИЕ. 0 — правило выключено.",
     "float", 0.0, 150.0, 5.0, "м"),
    ("cluster.eps", "Кластеризация", "Радиус объединения точек",
     "Точки ближе этого расстояния (у поезда; вдали радиус растёт) считаются одним объектом. Больше — "
     "объекты цельнее, но соседние предметы и стены могут слиться.",
     "float", 0.1, 1.0, 0.05, "м"),
    ("cluster.min_points", "Кластеризация", "Минимум точек объекта",
     "Сколько ячеек по 5 см должно быть в группе точек вблизи, чтобы она считалась объектом. Больше — "
     "меньше срабатываний на шум, но мелкие предметы могут пропасть.",
     "int", 2, 30, 1, "шт"),
    ("cluster.min_points_far", "Кластеризация", "Минимум точек вдали",
     "То же для объектов дальше 100 м, где точек на предмете мало. Больше — меньше ложных "
     "срабатываний вдали, но позднее обнаружение.",
     "int", 1, 20, 1, "шт"),
    ("cluster.max_extent", "Кластеризация", "Максимальный размер объекта",
     "Группы точек длиннее этого считаются конструкцией тоннеля, а не препятствием. Больше — "
     "длинные предметы не теряются, но возможны ложные СТОП на стенах.",
     "float", 2.0, 20.0, 0.5, "м"),
    ("tracking.confirm_time_s", "Трекинг", "Время подтверждения",
     "Сколько секунд объект должен наблюдаться в габарите до СТОП. Меньше — быстрее реакция, "
     "но больше ложных тревог от мелькающих помех.",
     "float", 0.0, 2.0, 0.1, "с"),
    ("tracking.confirm_hits", "Трекинг", "Кадров для подтверждения",
     "Минимум кадров подряд, в которых объект найден, до СТОП (вместе со временем подтверждения). "
     "Больше — надёжнее, но медленнее.",
     "int", 1, 10, 1, "кадр"),
    ("tracking.min_hit_fraction", "Трекинг", "Доля кадров с объектом",
     "Какая доля последних 10 кадров должна содержать объект, чтобы он оставался подтверждённым. "
     "Выше — мелькающие помехи отсеиваются сильнее, но прерывистые объекты тоже.",
     "float", 0.0, 1.0, 0.05, None),
    ("tracking.hold_misses", "Трекинг", "Удержание СТОП без объекта",
     "Сколько кадров СТОП держится, если объект на мгновение пропал из облака. Больше — меньше "
     "«миганий» решения, но дольше тревога после ухода объекта.",
     "int", 0, 5, 1, "кадр"),
    ("tracking.doubt_extra_hits", "Трекинг", "Ожидание при сомнении модели",
     "Сколько лишних кадров ждать, если обученная модель сомневается в далёком (дальше 25 м) "
     "объекте. 0 — модель не задерживает СТОП.",
     "int", 0, 30, 1, "кадр"),
    ("lowobj.enabled", "Низкие объекты", "Поиск низких предметов",
     "Искать предметы ниже габарита, лежащие на пути (от 10 см высотой). Выключение убирает "
     "ложные срабатывания на путевом оборудовании, но такие предметы не будут найдены.",
     "bool", None, None, None, None),
    ("lowobj.range_max", "Низкие объекты", "Дальность поиска низких предметов",
     "Дальше этого расстояния низкие предметы не ищутся: полотно видно под слишком острым углом. "
     "Больше — раньше обнаружение, но больше ложных тревог.",
     "float", 10.0, 100.0, 5.0, "м"),
    ("accumulation.enabled", "Накопление", "Накопление кадров",
     "Объединять несколько кадров для далёких объектов с учётом движения поезда. Работает, только "
     "если задана скорость поезда.",
     "bool", None, None, None, None),
    ("health.min_points", "Исправность", "Минимум точек в кадре",
     "Если в кадре меньше точек, вход считается неисправным (ОШИБКА). Меньше — терпимее к "
     "загрязнению датчика, но риск работать вслепую.",
     "int", 0, 100000, 1000, "шт"),
    ("health.min_visibility", "Исправность", "Минимальная видимость",
     "Если тоннель виден ближе этого расстояния, выдаётся ВНИМАНИЕ. Больше — "
     "осторожнее в поворотах и на станциях, но чаще ВНИМАНИЕ.",
     "float", 0.0, 200.0, 5.0, "м"),
    ("health.latency_budget_ms", "Исправность", "Бюджет задержки",
     "Если 95 % кадров обрабатываются дольше, в исправности появляется предупреждение. На решение "
     "СВОБОДНО / СТОП это не влияет.",
     "float", 20.0, 500.0, 10.0, "мс"),
]


@lru_cache(maxsize=1)
def _base_dict() -> dict:
    """The ``resense:`` dict of configs/default.yaml, or the code defaults without the file."""
    try:
        with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        d = raw.get("resense", raw)
        DetectorConfig.from_dict(copy.deepcopy(d))          # fail early on a broken file
        return d
    except (OSError, ValueError, KeyError, yaml.YAMLError):
        return json.loads(json.dumps(DetectorConfig().to_dict()))


def _build_specs() -> list[dict]:
    base = DetectorConfig.from_dict(copy.deepcopy(_base_dict()))
    out = []
    for key, group, label, help_, typ, lo, hi, step, unit in _SPECS:
        section, name = key.split(".", 1)
        value = getattr(getattr(base, section), name)
        spec = {"key": key, "group": group, "label": label, "help": help_, "type": typ,
                "default": {"float": float, "int": int, "bool": bool}[typ](value)}
        if typ != "bool":
            spec.update(min=lo, max=hi, step=step)
        if unit:
            spec["unit"] = unit
        out.append(spec)
    return out


PARAM_SPECS: list[dict] = _build_specs()
_BY_KEY = {s["key"]: s for s in PARAM_SPECS}
PARAM_KEYS = tuple(_BY_KEY)


def _fmt(v) -> str:
    return f"{v:g}".replace(".", ",") if isinstance(v, float) else str(v)


def _coerce(spec: dict, value):
    label = f"«{spec['label']}» ({spec['key']})"
    typ = spec["type"]
    if typ == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true"
        raise ValueError(f"{label}: ожидается да или нет (true / false)")
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label}: ожидается число")
    if isinstance(value, str):
        try:
            value = float(value.strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"{label}: ожидается число") from None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{label}: ожидается число")
    if not math.isfinite(float(value)):
        raise ValueError(f"{label}: ожидается конечное число")
    if typ == "int":
        if isinstance(value, float):
            if not value.is_integer():
                raise ValueError(f"{label}: ожидается целое число")
        value = int(value)
    else:
        value = float(value)
    if not spec["min"] <= value <= spec["max"]:
        unit = f" {spec['unit']}" if spec.get("unit") else ""
        raise ValueError(f"{label}: значение {_fmt(value)} вне диапазона "
                         f"{_fmt(spec['min'])}…{_fmt(spec['max'])}{unit}")
    return value


def validate_overrides(overrides: dict) -> dict:
    """Normalised overrides (known keys only, values of the spec's type, in the spec's order).
    Raises ValueError with a Russian message on an unknown key, a wrong type or a value out of
    range."""
    if overrides is None:
        return {}
    if not isinstance(overrides, dict):
        raise ValueError("Параметры должны быть объектом вида {\"раздел.параметр\": значение}")
    out = {}
    for key, value in overrides.items():
        spec = _BY_KEY.get(key) if isinstance(key, str) else None
        if spec is None:
            raise ValueError(f"Неизвестный параметр «{key}»")
        out[key] = _coerce(spec, value)
    return {k: out[k] for k in PARAM_KEYS if k in out}


def build_config(overrides: dict) -> DetectorConfig:
    """``configs/default.yaml`` (or the code defaults when it is absent) with the overrides."""
    d = copy.deepcopy(_base_dict())
    for key, value in validate_overrides(overrides).items():
        section, name = key.split(".", 1)
        d.setdefault(section, {})[name] = value
    return DetectorConfig.from_dict(d)


def config_snapshot(overrides: dict) -> dict:
    """The complete effective configuration as a JSON-safe dict (``DetectorConfig.to_dict()``,
    tuples as lists): ``DetectorConfig.from_dict(snapshot)`` rebuilds it."""
    return json.loads(json.dumps(build_config(overrides).to_dict()))


def defaults() -> dict:
    """{key: default} of every tunable parameter."""
    return {s["key"]: s["default"] for s in PARAM_SPECS}
