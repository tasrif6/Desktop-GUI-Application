import calendar
from datetime import date

def last_day(year:int, month:int) -> int:
    return calendar.monthrange(year, month)[1]

def month_label(year:int, month:int) -> str:
    return f"{calendar.month_abbr[month].upper()}{str(year)[-2:]}"

def oracle_date(d: date) -> str:
    return d.strftime("%d-%b-%Y").upper()

def previous_month_end(year:int, month:int) -> date:
    if month == 1:
        return date(year-1,12,31)
    return date(year,month-1,last_day(year,month-1))
