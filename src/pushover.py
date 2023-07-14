import requests


class Pushover:
    API_URL = "https://api.pushover.net/1/messages.json"

    def __init__(self, app_token: str, user_token: str):
        self.app_token = app_token
        self.user_token = user_token

    def notify(self, message: str, title: str = ""):
        data = {
            "token": self.app_token,
            "user": self.user_token,
            "title": title,
            "message": message
        }
        headers = {
            "Content-type": "application/x-www-form-urlencoded"
        }

        requests.post(self.API_URL, data=data, headers=headers)
