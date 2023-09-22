import base64
from dataclasses import dataclass
from datetime import datetime, time
import hashlib
import json
import os
from typing import Optional
import urllib.parse

from bs4 import BeautifulSoup
import requests


@dataclass(frozen=True)
class Shift:
    location: str
    date: datetime
    start_time: time
    end_time: time
    status: str


class PlandayOAuth2:
    URL_ROOT = "https://id.planday.com"
    CODE_VERIFIER_SIZE = 64

    def __init__(self, client_id: str, portal_alias: str, username: str, password: str):
        self.client_id = client_id
        self.portal_alias = portal_alias
        self.username = username
        self.password = password
        self.code_verifier = base64.urlsafe_b64encode(os.urandom(self.CODE_VERIFIER_SIZE)).rstrip(b'=').decode("utf-8")
        self.code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
        self.redirect_uri = f"https://{portal_alias}/auth-callback"
        self.return_url_path = f"/connect/authorize/callback?client_id={client_id}&redirect_uri={self.redirect_uri}&response_type=code&scope=openid impersonate plandayid&code_challenge={self.code_challenge}&code_challenge_method=S256&acr_values=tenant:{portal_alias}&response_mode=query"
        self.login_url_path = f"/Login?ReturnUrl={urllib.parse.quote(self.return_url_path)}"

    def fetch_request_verification_key(self, session: requests.Session) -> str:
        response = session.get(self.URL_ROOT + self.login_url_path)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.find("input", {"name": "__RequestVerificationToken"})["value"]

    def fetch_authorization_code(self, session: requests.Session, username: str, password: str,
                                 request_verification_token: str) -> str:
        data = {
            "Username": username,
            "Password": password,
            "LoginStep": "PasswordValidation",
            "__RequestVerificationToken": request_verification_token
        }

        response = session.post(self.URL_ROOT + self.login_url_path, data=data)

        return urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query)["code"][0]

    def fetch_platform_access_token(self, session: requests.Session, authorization_code: str) -> str:
        data = {
            "client_id": self.client_id,
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": self.code_verifier,
            "grant_type": "authorization_code"
        }

        response = session.post(f"{self.URL_ROOT}/connect/token", data=data)

        return json.loads(response.content)["platform_access_token"]

    def fetch_new_platform_access_token(self) -> str:
        session = requests.Session()

        request_verification_token = self.fetch_request_verification_key(session)
        authorization_code = self.fetch_authorization_code(session, self.username, self.password,
                                                           request_verification_token)

        return self.fetch_platform_access_token(session, authorization_code)


class Planday:
    def __init__(self, platform_access_token: str, api_url_base: str, api_url_path_shifts: str):
        self.platform_access_token = platform_access_token
        self.api_url_base = api_url_base
        self.api_url_path_shifts = api_url_path_shifts

    def fetch_shifts(self, from_date: datetime = None, to_date: datetime = None) -> Optional[list[Shift]]:
        from_date = from_date or datetime.today()
        to_date = to_date or (datetime.today() if datetime.today() >= from_date else from_date)

        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        }
        headers = {
            "Authorization": f"Bearer {self.platform_access_token}"
        }

        response = requests.get(f"{self.api_url_base}{self.api_url_path_shifts}", params=params, headers=headers)

        if response.status_code != 200:
            return

        shifts = []
        for shift in json.loads(response.content.decode("utf-8"))["shifts"]:
            location = shift["description"].split('\n')[0].strip()
            date = datetime.strptime(shift["date"], "%Y-%m-%d")
            start_time = datetime.strptime(shift["start_time"], "%H:%M")
            end_time = datetime.strptime(shift["end_time"], "%H:%M")
            status = shift["shift_status"]

            shifts.append(Shift(location, date, start_time, end_time, status))

        return shifts
