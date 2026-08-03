"""
Политика видимости цен в каталоге.

Единственный источник истины по вопросу «какие ценовые поля видит роль».
Инвариант (`project-context.md` §3): оптовые цены и B2B-инфо-цены доступны
только верифицированным пользователям с B2B-ролью; все остальные, включая
гостей, розницу и контрагентов 1С без портального аккаунта, видят розничную
цену.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.users.models import User

# Сырые оптовые поля ответа каталога. Стори 39.3 добавляет сюда "opt4_price".
WHOLESALE_PRICE_FIELDS = ("opt1_price", "opt2_price", "opt3_price")

# Инфо-цены B2B. Не участвуют в расчётах, но так же закрыты от розницы.
INFO_PRICE_FIELDS = ("rrp", "msrp")

# Роли, которым видны РРЦ/МРЦ. federation_rep исключён намеренно —
# поведение перенесено как есть из литеральных списков сериализаторов.
# Стори 39.3 добавляет сюда "wholesale_level4".
INFO_PRICE_ROLES = frozenset({"wholesale_level1", "wholesale_level2", "wholesale_level3", "trainer", "admin"})


def resolve_pricing_role(user: "User | Any | None") -> str:
    """
    Роль, по которой считается цена для пользователя.

    B2B-роль без верификации понижается до "retail": менеджер ещё не
    подтвердил контрагента, поэтому оптовых условий у него нет.
    """
    from apps.users.models import User

    if user is None or not getattr(user, "is_authenticated", False):
        return "retail"

    role = getattr(user, "role", "retail")
    if role in User.B2B_ROLES and not getattr(user, "is_verified", False):
        return "retail"
    return role


def can_see_wholesale_prices(user: "User | Any | None") -> bool:
    """
    Видит ли пользователь сырые оптовые поля (`WHOLESALE_PRICE_FIELDS`).

    Роль без права получает `0.0` — это означает «нет права видеть оптовую
    цену», а НЕ «цена не заполнена» (пустая цена даёт тот же `0.0` в
    `get_optN_price`). Снятие этой проверки открывает всю оптовую сетку
    анонимным запросам — см. `tech-debt.md` п. 18.
    """
    from apps.users.models import User

    role = resolve_pricing_role(user)
    return role in User.B2B_ROLES or role == "admin"


def can_see_info_prices(user: "User | Any | None") -> bool:
    """Видит ли пользователь инфо-цены РРЦ/МРЦ (`INFO_PRICE_FIELDS`)."""
    return resolve_pricing_role(user) in INFO_PRICE_ROLES
