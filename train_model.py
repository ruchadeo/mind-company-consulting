# train_model.py

import pickle
import numpy as np
from signal_processing import SignalProcessor
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

# Load Training Data
with open('training_data.pkl', 'rb') as f:
    all_data = pickle.load(f)

processor = SignalProcessor()
X = []
y = []

for data in all_data:
    label = data[-1]  # The label is the last element
    features = processor.extract_features(data)
    X.append(features)
    y.append(label)

X = np.array(X)
y = np.array(y)

# Train the Model
model = LinearDiscriminantAnalysis()
model.fit(X, y)

# Save the Model
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model Trained and Saved")