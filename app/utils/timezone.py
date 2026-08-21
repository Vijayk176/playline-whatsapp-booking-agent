from datetime import datetime
import pytz
from app.config import settings

TZ = pytz.timezone(settings.timezone)


def now_local() -> datetime:
    return datetime.now(TZ)


def today_local():
    return now_local().date()
