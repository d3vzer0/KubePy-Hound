import requests
import hmac
import hashlib
import base64
import datetime
from datetime import timedelta


class BloodHound:
    def __init__(
        self, token_key: str, token_id: str, bhe_uri: str = "http://localhost:8000"
    ):
        self.token_key = token_key
        self.token_id = token_id
        self.base_uri = bhe_uri

    def request(self, method: str, path: str, body: bytes | None = None):
        # HMAC Part 1
        digester = hmac.new(self.token_key.encode(), None, hashlib.sha256)
        digester.update(f"{method}{path}".encode())

        # HMAC Part 2
        digester = hmac.new(digester.digest(), None, hashlib.sha256)
        datetime_formatted = (
            datetime.datetime.now(datetime.UTC).astimezone() - timedelta(hours=0)
        ).isoformat("T")
        datetime_short = datetime_formatted[0:13]
        digester.update(datetime_short.encode())

        # HMAC Part 3
        digester = hmac.new(digester.digest(), None, hashlib.sha256)
        if body is not None:
            digester.update(body)

        sig = base64.b64encode(digester.digest())
        return requests.request(
            method=method,
            url=f"{self.base_uri}{path}",
            headers={
                "User-Agent": "bhe-python",
                "Authorization": f"bhesignature {self.token_id}",
                "RequestDate": datetime_formatted,
                "Signature": sig,
                "Content-Type": "application/json",
            },
            data=body,
        )

    def start_upload_job(self) -> int:
        path = "/api/v2/file-upload/start"
        response = self.request(method="POST", path=path)
        return response.json()["data"]["id"]

    def upload_graph(self, id: int, body: str):
        path = f"/api/v2/file-upload/{id}"
        response = self.request(method="POST", path=path, body=body.encode())
        return response

    def stop_upload_job(self, id: int):
        path = f"/api/v2/file-upload/{id}/end"
        response = self.request(method="POST", path=path)
        return response

    # def upload(self, body: str):
    #     job_id = self._start_upload()
    #     response = self._start_upload_job(job_id, body.encode())
    #     if response.status_code == 202:
    #         self._stop_upload_job(job_id)
    #     else:
    #         print("Issue with uploading job")
    #         print(response.json())

    def saved_query(self, body: str):
        path = "/api/v2/saved-queries"
        response = self.request(method="POST", path=path, body=body.encode())
        return response

    def custom_node(self, body: str):
        path = "/api/v2/custom-nodes"
        response = self.request(method="POST", path=path, body=body.encode())
        return response
