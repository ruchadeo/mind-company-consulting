# signal_processing.py

import numpy as np
from scipy.signal import butter, lfilter
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import pickle

class SignalProcessor:
    def __init__(self):
        self.fs = 128  # Sampling frequency of Emotiv Insight
        self.lowcut = 1.0
        self.highcut = 50.0
        self.order = 5
        self.model = self.load_model()

    def butter_bandpass(self):
        nyq = 0.5 * self.fs
        low = self.lowcut / nyq
        high = self.highcut / nyq
        b, a = butter(self.order, [low, high], btype='band')
        return b, a

    def bandpass_filter(self, data):
        b, a = self.butter_bandpass()
        y = lfilter(b, a, data)
        return y

    def extract_features(self, data):
        # Convert data to NumPy array and select channels
        eeg_channels = np.array(data[2:])  # Skip first two elements (timestamp and marker)
        filtered = self.bandpass_filter(eeg_channels)
        features = np.log(np.var(filtered))
        return features

    def load_model(self):
        try:
            with open('model.pkl', 'rb') as f:
                model = pickle.load(f)
            print("Model Loaded")
            return model
        except FileNotFoundError:
            print("Model not found. Please train the model first.")
            return None

    def predict_command(self, data):
        features = self.extract_features(data)
        if self.model:
            command = self.model.predict([features])[0]
            return command
        else:
            return None

# Usage Example
if __name__ == "__main__":
    from eeg_acquisition import EmotivInsight
    import time

    client_id = "th1QfJypPUpW7fVODWjFCEUZL61cC9o2nEdJZHs9"
    client_secret = "4RwyX1lkvmm8kMNVDP2ghUcxkqgwxMz4CqxKj9NAN7z5eL1lXdkniItd3oDJmzCv8a9U9c7HL52RgockfsVJwASr1YajL3hwHJx4V4ZKYpAfTBYJ14AiZq9ADXCNTgAa"

    emotiv = EmotivInsight(client_id, client_secret)
    emotiv.connect()
    emotiv.subscribe(['eeg'])
    emotiv.start_stream()

    processor = SignalProcessor()

    try:
        while True:
            data = emotiv.get_latest_data()
            if data:
                command = processor.predict_command(data)
                print("Predicted Command: ", command)
            time.sleep(0.1)
    except KeyboardInterrupt:
        emotiv.stop()