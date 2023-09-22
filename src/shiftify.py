from datetime import datetime, timedelta
import os
from time import sleep

from dotenv import load_dotenv

from pushover import Pushover
from planday import Planday, PlandayOAuth2

POLL_INTERVAL_SECONDS = 1
SHIFT_ADDED = '+'
SHIFT_UNCHANGED = '⟳'
SHIFT_REMOVED = '–'


def main():
    load_dotenv()

    pushover = Pushover(
        os.getenv("PUSHOVER_TOKEN_APP"),
        os.getenv("PUSHOVER_TOKEN_USER")
    )
    planday_oath_2 = PlandayOAuth2(
        "b116846e-8ff0-42dc-83b6-5392543ca73c",
        "loviseberg.planday.com",

        os.getenv("PLANDAY_USERNAME"),
        os.getenv("PLANDAY_PASSWORD")
    )
    planday = Planday(
        planday_oath_2.fetch_new_platform_access_token(),
        "https://scheduling-shift-api.prod-westeurope.planday.cloud",
        "/schedules/128422/shifts"
    )

    recent_shifts = set()
    while True:
        sleep(POLL_INTERVAL_SECONDS)

        shifts = planday.fetch_shifts(to_date=datetime.today() + timedelta(weeks=6))
        if shifts is None:
            planday.platform_access_token = planday_oath_2.fetch_new_platform_access_token()
            continue

        available_shifts = set(filter(lambda shift: shift.status == "Open", shifts))
        if available_shifts == recent_shifts:
            continue

        shift_groups = (
            (SHIFT_ADDED, available_shifts.difference(recent_shifts)),
            (SHIFT_UNCHANGED, available_shifts.intersection(recent_shifts)),
            (SHIFT_REMOVED, recent_shifts.difference(available_shifts))
        )

        recent_shifts = available_shifts

        shift_information = []
        for symbol, shift_group in shift_groups:
            for shift in shift_group:
                shift_information.append(
                    f"[{symbol}] {shift.location} {shift.date:%d/%m} | {shift.start_time:%H:%M} - {shift.end_time:%H:%M}"
                )

        print(*shift_information, datetime.today(), '-' * 32, sep='\n', flush=True)
        pushover.notify('\n'.join(shift_information), title="Shifts available")


if __name__ == '__main__':
    main()
