from datetime import datetime

from croniter import croniter


def validate_cron(expression: str) -> str:
    expr = (expression or "").strip()
    if not expr:
        raise ValueError("Cron expression is empty")
    if not croniter.is_valid(expr):
        raise ValueError(f"Invalid cron expression: {expr}")
    return expr


def next_cron_run(expression: str, base: datetime | None = None) -> datetime:
    expr = validate_cron(expression)
    base = base or datetime.utcnow()
    itr = croniter(expr, base)
    return itr.get_next(datetime)
