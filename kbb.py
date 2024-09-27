import requests
import time
class KBB:
    def __init__(self, plate, state):
        self.plate = plate
        self.state = state

    def lookup(self):
        url = 'https://www.kbb.com/owners-argo/api/'
        headers = {
            'authority': 'www.kbb.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'cookie': 'Your-Cookie-Values-Here',
            'mocks': 'undefined',
            'origin': 'https://www.kbb.com',
            'referer': 'https://www.kbb.com/whats-my-car-worth/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Your-User-Agent-Here'
        }

        data = {
            "operationName": "licenseSLPPageQuery",
            "variables": {
                "lp": f"{self.plate}",
                "state": f"{self.state}"
            },
            "query": "query licenseSLPPageQuery($lp: String, $state: String) {\n  vehicleUrlByLicense: vehicleUrlByLicense(lp: $lp, state: $state) {\n    url\n    error\n    make\n    makeId\n    model\n    modelId\n    year\n    vin\n    __typename\n  }\n}"
        }

        print(f"Looking up {self.plate} - {self.state}")
        retries = 0
        while retries < 5:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                time.sleep(2)
            retries += 1

        return None
