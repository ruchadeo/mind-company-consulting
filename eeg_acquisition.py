# eeg_acquisition.py

import pickle
import websocket
import json
import threading
import time

class EmotivInsight:
    def __init__(self, client_id, client_secret):
        self.ws = None
        self.auth = None
        self.session_id = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.eeg_data = []
        self.is_running = False

    def connect(self):
        self.ws = websocket.create_connection("wss://localhost:6868")
        self.authenticate()
        self.create_session()

    def authenticate(self):
        # Request access
        request_access = {
            "jsonrpc": "2.0",
            "method": "requestAccess",
            "params": {
                "clientId": self.client_id,
                "clientSecret": self.client_secret
            },
            "id": 1
        }
        self.ws.send(json.dumps(request_access))
        result = self.ws.recv()
        print("Access Requested: ", result)

        # Authorize
        authorize = {
            "jsonrpc": "2.0",
            "method": "authorize",
            "params": {
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
                "debit": 1
            },
            "id": 2
        }
        self.ws.send(json.dumps(authorize))
        result = self.ws.recv()
        response = json.loads(result)
        self.auth = response['result']['cortexToken']
        print("Authorized")

    def create_session(self):
        create_session_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "createSession",
            "params": {
                "cortexToken": self.auth,
                "headset": "INSIGHT",
                "status": "active"
            }
        }
        self.ws.send(json.dumps(create_session_request))
        result = self.ws.recv()
        response = json.loads(result)
        self.session_id = response['result']['id']
        print("Session Created: ", self.session_id)

    def subscribe(self, streams):
        subscribe_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "subscribe",
            "params": {
                "cortexToken": self.auth,
                "session": self.session_id,
                "streams": streams
            }
        }
        self.ws.send(json.dumps(subscribe_request))
        result = self.ws.recv()
        print("Subscribed to Streams: ", result)

    def start_stream(self):
        self.is_running = True
        threading.Thread(target=self.receive_data).start()

    def receive_data(self):
        while self.is_running:
            try:
                result = self.ws.recv()
                data = json.loads(result)
                if 'eeg' in data:
                    self.eeg_data.append(data['eeg'])
            except Exception as e:
                print("Error receiving data: ", e)
                self.is_running = False

    def stop(self):
        self.is_running = False
        self.ws.close()

    def get_latest_data(self):
        if self.eeg_data:
            return self.eeg_data[-1]
        else:
            return None


    def record_data(self, duration, label):
        recorded_data = []
        start_time = time.time()
        while time.time() - start_time < duration:
            data = self.get_latest_data()
            if data:
                data.append(label)
                recorded_data.append(data)
            time.sleep(0.01)
        return recorded_data
    
    
if __name__ == "__main__":
    client_id = "th1QfJypPUpW7fVODWjFCEUZL61cC9o2nEdJZHs9"
    client_secret = "4RwyX1lkvmm8kMNVDP2ghUcxkqgwxMz4CqxKj9NAN7z5eL1lXdkniItd3oDJmzCv8a9U9c7HL52RgockfsVJwASr1YajL3hwHJx4V4ZKYpAfTBYJ14AiZq9ADXCNTgAa"

    emotiv = EmotivInsight(client_id, client_secret)
    emotiv.connect()
    emotiv.subscribe(['eeg'])
    emotiv.start_stream()

    try:
        while True:
            rest_data = emotiv.record_data(duration=120, label=0)
            jump_data = emotiv.record_data(duration=120, label=1)
            all_data = rest_data + jump_data

            with open('training_data.pkl', 'wb') as f:
                pickle.dump(all_data, f)

            if jump_data:
                print("EEG Data: ", jump_data)
            time.sleep(0.1)
    except KeyboardInterrupt:
        emotiv.stop()