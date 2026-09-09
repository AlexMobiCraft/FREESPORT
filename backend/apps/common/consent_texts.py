"""Реестр текстов согласий (ФЗ-152 ст. 9).

Журнал `UserConsent` обязан быть доказуемым: по записи должно восстанавливаться,
на какую именно формулировку человек соглашался. Дата, IP и User-Agent этого
не дают — формулировка чекбокса живёт во фронтенде и меняется. Поэтому каждая
запись согласия хранит `consent_text_version`, а этот модуль связывает версию
с дословным текстом.

Версия считается как `<метка>-<первые 8 hex sha256 текста>`: метку читает человек
в админке, хеш делает пропуск бампа механически невозможным — правка текста
меняет версию сама, без дисциплины разработчика.

Историю ревизий страхует раздел `known_versions`: он перечисляет версии всех
когда-либо действовавших формулировок, и загрузчик требует точного совпадения
этого списка с тем, что даёт разбор ревизий. Правка текста старой ревизии,
её удаление «как устаревшей» и добавление ревизии без записи в список роняют
загрузку. Это процедурный страж, а не механическая неизменяемость: список лежит
в том же редактируемом JSON, поэтому согласованная замена ревизии **вместе** с её
строкой в `known_versions` пройдёт. Он ловит одностороннюю правку — самый вероятный
способ потерять доказательство по неосторожности.

Модуль намеренно не зависит от Django и ограничен стандартной библиотекой:
тот же JSON читает кросс-граничный страж на фронте
(`frontend/src/__tests__/consent-texts-registry.test.tsx`), который сверяет
доступное имя чекбокса с текстом текущей ревизии.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

# Реестр лежит рядом с модулем и попадает в образ (`COPY . .` в backend/Dockerfile).
REGISTRY_PATH = Path(__file__).with_name("consent_texts.json")

# Версия обязана помещаться в `UserConsent.consent_text_version` (`max_length=64`).
# Значение продублировано здесь намеренно: модуль не импортирует Django, потому
# что тот же JSON читает страж на фронте. Расхождение с моделью ловит тест
# `test_max_version_length_matches_model_field`.
MAX_VERSION_LENGTH = 64


class ConsentTextsError(RuntimeError):
    """Реестр текстов согласий отсутствует, повреждён или неполон.

    Исключение осознанно «громкое»: молчаливый фолбэк на `unknown` вернул бы
    ровно ту беду, которую чинит стори 41.9 — запись без доказуемого текста.
    """


def compute_consent_text_version(label: str, text: str) -> str:
    """Собрать версию ревизии: метка + первые 8 hex sha256 от текста."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{label}-{digest}"


def _normalized(text: str) -> str:
    """Одна строка, одиночные пробелы, без краёв — вид, в котором текст хранится."""
    return " ".join(text.split())


class ConsentTextRegistry:
    """Разобранный и провалидированный реестр текстов согласий.

    Валидация выполняется в конструкторе: ссылка на несуществующую поверхность,
    ненормализованный текст, слишком длинная версия и совпадение версий двух
    разных ревизий обнаруживаются при загрузке, а не на вставке в БД.
    """

    def __init__(self, data: Any, *, origin: str = "<in-memory>") -> None:
        self._origin = origin

        if not isinstance(data, dict):
            raise ConsentTextsError(f"Реестр согласий {origin}: ожидался объект, получен {type(data).__name__}")

        surfaces = data.get("surfaces")
        bindings = data.get("bindings")
        if not isinstance(surfaces, dict) or not surfaces:
            raise ConsentTextsError(f"Реестр согласий {origin}: раздел 'surfaces' отсутствует или пуст")
        if not isinstance(bindings, dict) or not bindings:
            raise ConsentTextsError(f"Реестр согласий {origin}: раздел 'bindings' отсутствует или пуст")

        # version -> text по всем ревизиям всех поверхностей. Поиск ведётся по
        # всему реестру, иначе версия, оставшаяся в старых строках после
        # переименования привязки, перестала бы разрешаться в текст.
        self._texts_by_version: dict[str, str] = {}
        # surface -> версия последней (действующей) ревизии
        self._current_by_surface: dict[str, str] = {}

        for surface_name, surface in surfaces.items():
            self._ingest_surface(surface_name, surface)

        self._check_known_versions(data.get("known_versions"))

        self._surface_by_pair: dict[tuple[str, str], str] = {}
        for binding_key, surface_name in bindings.items():
            self._ingest_binding(binding_key, surface_name)

    def _ingest_surface(self, surface_name: str, surface: Any) -> None:
        """Разобрать одну поверхность согласия и её историю ревизий."""
        if not isinstance(surface, dict):
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: поверхность '{surface_name}' не является объектом"
            )

        revisions = surface.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: у поверхности '{surface_name}' пустой список ревизий"
            )

        for index, revision in enumerate(revisions):
            if not isinstance(revision, dict):
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: ревизия #{index} поверхности "
                    f"'{surface_name}' не является объектом"
                )

            label = revision.get("label")
            text = revision.get("text")
            if not isinstance(label, str) or not label.strip():
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: ревизия #{index} поверхности '{surface_name}' без метки"
                )
            if not isinstance(text, str) or not text.strip():
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: ревизия '{label}' поверхности '{surface_name}' без текста"
                )
            if text != _normalized(text):
                # Страж на фронте сравнивает текст с доступным именем чекбокса
                # посимвольно — оно нормализовано, значит и в реестре текст
                # обязан храниться нормализованным.
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: текст ревизии '{label}' поверхности "
                    f"'{surface_name}' не нормализован (ожидались одна строка и одиночные пробелы)"
                )

            version = compute_consent_text_version(label, text)
            if len(version) > MAX_VERSION_LENGTH:
                # Версия длиннее поля молча обрезалась бы базой или роняла вставку
                # уже на живом согласии. Ограничение упирается в длину метки:
                # хеш всегда 8 символов.
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: версия '{version}' ревизии '{label}' поверхности "
                    f"'{surface_name}' длиннее {MAX_VERSION_LENGTH} символов "
                    f"(получено {len(version)}) — укоротите метку ревизии"
                )
            if version in self._texts_by_version:
                raise ConsentTextsError(
                    f"Реестр согласий {self._origin}: версия '{version}' встречается дважды — "
                    f"дубль ревизии (поверхность '{surface_name}')"
                )

            self._texts_by_version[version] = text
            # Действующая ревизия — последняя в списке: история дополняется, а не переписывается.
            self._current_by_surface[surface_name] = version

    def _check_known_versions(self, known_versions: Any) -> None:
        """Сверить набор ревизий со списком когда-либо действовавших версий.

        Одних ревизий мало: текст исторической ревизии можно поправить «по мелочи»,
        а саму ревизию — удалить как устаревшую. И то и другое тихо оборвёт связь
        уже записанных согласий со своим текстом — доказательство по ФЗ-152 ст. 9
        исчезнет. `known_versions` фиксирует версии отдельно от текстов, поэтому
        односторонняя правка истории видна как расхождение двух списков.

        Границы защиты: список лежит в том же редактируемом JSON, значит правка
        ревизии, согласованная с правкой её строки в `known_versions`, пройдёт.
        Это процедурный страж от неосторожности, а не механическая неизменяемость —
        последняя потребовала бы хранить историю вне репозитория.

        Сверка на точное равенство, а не на вхождение: новая ревизия тоже обязана
        быть внесена в список. Её версию не нужно считать руками — сообщение об
        ошибке называет готовую строку.
        """
        if not isinstance(known_versions, list) or not known_versions:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: раздел 'known_versions' отсутствует или пуст. "
                f"Он фиксирует версии всех ревизий и ловит одностороннюю правку истории; "
                f"ожидались: {sorted(self._texts_by_version)}"
            )
        if not all(isinstance(version, str) for version in known_versions):
            raise ConsentTextsError(f"Реестр согласий {self._origin}: 'known_versions' обязан быть списком строк")
        if len(set(known_versions)) != len(known_versions):
            raise ConsentTextsError(f"Реестр согласий {self._origin}: в 'known_versions' есть повторы")

        declared = set(known_versions)
        computed = set(self._texts_by_version)

        vanished = sorted(declared - computed)
        if vanished:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: версии {vanished} зафиксированы в 'known_versions', "
                f"но ни одна ревизия их больше не даёт — текст исторической ревизии изменён или "
                f"ревизия удалена. Уже записанные согласия перестанут разрешаться в свой текст; "
                f"история дополняется новой ревизией, а не переписывается"
            )

        unrecorded = sorted(computed - declared)
        if unrecorded:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: ревизии {unrecorded} не зафиксированы в 'known_versions'. "
                f"Внесите эти строки в раздел — по нему сверяется история ревизий"
            )

    def _ingest_binding(self, binding_key: str, surface_name: Any) -> None:
        """Разобрать одну привязку вида `<источник>.<тип согласия>` к поверхности."""
        if not isinstance(surface_name, str) or surface_name not in self._current_by_surface:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: привязка '{binding_key}' ссылается на "
                f"неизвестную поверхность '{surface_name}'"
            )

        source, separator, consent_type = binding_key.partition(".")
        if not separator or not source or not consent_type or "." in consent_type:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: ключ привязки '{binding_key}' должен иметь "
                f"вид '<источник>.<тип согласия>'"
            )

        self._surface_by_pair[(source, consent_type)] = surface_name

    def current_version(self, source: str, consent_type: str) -> str:
        """Версия действующей формулировки для пары (источник, тип согласия)."""
        surface_name = self._surface_by_pair.get((source, consent_type))
        if surface_name is None:
            raise ConsentTextsError(
                f"Реестр согласий {self._origin}: пара ('{source}', '{consent_type}') "
                f"не привязана ни к одной поверхности согласия"
            )
        return self._current_by_surface[surface_name]

    def current_text(self, source: str, consent_type: str) -> str:
        """Дословный текст действующей формулировки для пары (источник, тип согласия)."""
        return self._texts_by_version[self.current_version(source, consent_type)]

    def resolve_text(self, version: str) -> str | None:
        """Текст ревизии по ранее записанной версии; None — версии в реестре нет."""
        return self._texts_by_version.get(version)

    @property
    def bound_pairs(self) -> frozenset[tuple[str, str]]:
        """Все пары (источник, тип согласия), у которых есть привязка."""
        return frozenset(self._surface_by_pair)

    @property
    def versions(self) -> tuple[str, ...]:
        """Версии всех ревизий всех поверхностей — включая исторические."""
        return tuple(self._texts_by_version)

    @property
    def texts_by_version(self) -> Mapping[str, str]:
        """Только для чтения: соответствие «версия → текст»."""
        return dict(self._texts_by_version)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Собрать объект JSON, отбраковав повторяющиеся ключи.

    `json.loads` по умолчанию оставляет последнее значение повторяющегося ключа.
    В реестре это означало бы подмену: две привязки `registration.pdp_contract`
    или две поверхности с одним именем разошлись бы с тем, что видит человек в
    файле, — победила бы нижняя, а глазами читается верхняя.
    """
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ConsentTextsError(
                f"Реестр согласий: ключ '{key}' объявлен дважды — JSON молча оставил бы последнее значение"
            )
        seen[key] = value
    return seen


@lru_cache(maxsize=None)
def load_registry(path: Path = REGISTRY_PATH) -> ConsentTextRegistry:
    """Прочитать и провалидировать реестр; результат кэшируется по пути к файлу."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConsentTextsError(f"Реестр согласий не читается: {path}") from exc

    try:
        data = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ConsentTextsError(f"Реестр согласий {path} не разбирается как JSON: {exc}") from exc

    return ConsentTextRegistry(data, origin=str(path))


def current_consent_text_version(source: str, consent_type: str) -> str:
    """Версия формулировки, действующей для пары (источник, тип согласия).

    Значение кладётся в `UserConsent.consent_text_version` в момент записи.
    Хардкодить версию в местах записи нельзя: при правке текста бамп забудется,
    а расхождение обнаружится уже на живом журнале.
    """
    return load_registry().current_version(source, consent_type)


def resolve_consent_text(version: str) -> str | None:
    """Восстановить текст согласия по версии из журнала; None — версия неизвестна."""
    return load_registry().resolve_text(version)


def is_current_consent_text_version(source: str, consent_type: str, version: str) -> bool:
    """Совпадает ли присланная клиентом версия с действующей формулировкой.

    Форма отправляет версию текста, который она показала человеку. Вкладка,
    открытая до правки формулировки, пришлёт прежнюю версию — и такой запрос
    обязан быть отклонён: иначе в журнал легло бы согласие с текстом, которого
    человек не видел, и запись перестала бы быть доказательством по ФЗ-152 ст. 9.
    """
    return bool(version) and version == current_consent_text_version(source, consent_type)
