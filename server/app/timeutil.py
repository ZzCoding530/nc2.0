"""时间口径（02 文档 §4 / §5）：
- 存储/比较：一律 naive UTC
- API 输出：UTC ISO8601（Z 结尾）
- 展示（邮件文案）：Asia/Shanghai
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
SH_TZ = ZoneInfo("Asia/Shanghai")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def now_utc() -> datetime:
    """当前 naive UTC（存储与比较基准）。"""
    return datetime.now(UTC).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    dt = to_naive_utc(dt)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return to_naive_utc(dt)


def in_shanghai(dt: datetime) -> datetime:
    return to_naive_utc(dt).replace(tzinfo=UTC).astimezone(SH_TZ)


def fmt_time_cn(dt: datetime) -> str:
    """2026-10-10 12:00Z →「10月10日 20:00」。"""
    local = in_shanghai(dt)
    return f"{local.month}月{local.day}日 {local:%H:%M}"


def weekday_cn(dt: datetime) -> str:
    return WEEKDAY_CN[in_shanghai(dt).weekday()]


def sh_date_bounds(dt_utc: datetime, day_offset: int = 0) -> tuple[datetime, datetime]:
    """以上海日历日为界的 [当日+day_offset 00:00, 次日 00:00) UTC naive 区间。"""
    local_today = in_shanghai(dt_utc).date()
    start_local = datetime.combine(local_today + timedelta(days=day_offset), time(0, 0), tzinfo=SH_TZ)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None),
        end_local.astimezone(UTC).replace(tzinfo=None),
    )


def preview_unlocked(scheduled_at: datetime, now: datetime) -> bool:
    """预习解锁：scheduled_at - 2 天 <= now（02 文档 §4）。"""
    return scheduled_at is not None and now >= scheduled_at - timedelta(days=2)
