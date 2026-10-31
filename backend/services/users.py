from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from backend.models import Bot, BotUser, User, Preference, Usage, now
from backend.services import i18n, monetization
from backend.services.limits import policy
from backend.services.security import DomainError


def register(db, bot_id: str, user_id: int, username: str | None = None, first_name: str | None = None,
             language_code: str | None = None, referrer: int | None = None) -> tuple[User, bool]:
    """Create or refresh the shared user. Returns (user, created). New users get the Telegram language
    and remember who invited them (an invite link only counts for someone new to the whole platform)."""
    bot = db.get(Bot, bot_id)
    if not bot or not bot.enabled:
        raise DomainError("disabled")
    user = db.get(User, user_id)
    created = False
    if not user:
        try:
            with db.begin_nested():
                user = User(id=user_id, username=username, first_name=first_name, language_code=language_code)
                db.add(user)
                db.flush()
                db.add(Preference(user_id=user.id, language=i18n.resolve(language_code, policy(db).default_language)))
                monetization.link_referrer(db, user, referrer)
                db.flush()
            created = True
        except IntegrityError:
            user = db.get(User, user_id)
    if user.banned:
        raise DomainError("banned")
    user.last_seen = now()
    user.username = username
    if first_name:
        user.first_name = first_name[:128]
    if language_code:
        user.language_code = language_code[:16]
    if not db.get(BotUser, (user.id, bot_id)):
        try:
            with db.begin_nested():
                db.add(BotUser(user_id=user.id, bot_id=bot_id))
                db.flush()
        except IntegrityError:
            pass
    db.commit()
    return user, created


def daily_limit(db, user: User) -> int:
    """Downloads and uploads a day: the paid tier's limit (0 = unlimited) for paying users, else a personal limit set by
    an administrator, else the free limit."""
    return monetization.daily_limit(db, user, user.daily_limit or policy(db).daily_jobs)


def used_today(db, user_id: int) -> int:
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count()).select_from(Usage).where(Usage.user_id == user_id, Usage.created_at >= today))


def language(db, user_id: int) -> str:
    pref = db.get(Preference, user_id)
    return pref.language if pref and pref.language in i18n.catalogs() else policy(db).default_language


def set_language(db, user_id: int, lang: str) -> str:
    if lang not in i18n.catalogs():
        raise DomainError("unsupported")
    db.merge(Preference(user_id=user_id, language=lang))
    db.commit()
    return lang
