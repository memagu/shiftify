from datetime import datetime, timedelta
import json
import os
from time import sleep

from dotenv import load_dotenv

from pushover import Pushover
from planday import Planday, PlandayOAuth2


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

    recent_shift_ids = set()
    while True:
        sleep(1)

        shifts = planday.fetch_shifts(to_date=datetime.today() + timedelta(weeks=6))

        if shifts is None:
            pushover.notify("The current Planday API token has expired. Initiating automatic replacement.")
            planday.platform_access_token = planday_oath_2.fetch_new_platform_access_token()
            pushover.notify("The Planday API token has been updated successfully.")
            continue

        shift_ids = {shift["id"] for shift in shifts}
        if shift_ids.issubset(recent_shift_ids):
            continue

        available_shifts = [
            shift for shift in shifts
            if shift["shift_status"] == "Open" and shift["id"] not in recent_shift_ids
        ]

        recent_shift_ids = shift_ids

        available_shift_info = []
        for shift in available_shifts:
            location = shift["description"].split('\n')[0]
            date = datetime.strptime(shift["date"], "%Y-%m-%d")
            start_time = shift["start_time"]
            end_time = shift["end_time"]

            available_shift_info.append(f"{location} {date.strftime('%d/%m')} | {start_time} - {end_time}")

        print(*available_shift_info, datetime.today(), '-' * 32, sep='\n')
        pushover.notify('\n'.join(available_shift_info), title="Shifts available")


if __name__ == '__main__':
    main()
