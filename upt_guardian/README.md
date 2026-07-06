# 🌍 UPT Guardian

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)

**UPT Guardian** is an advanced, proprietary AI Engine designed for Global Disaster Monitoring and Quantum Reactor Stability prediction. Built with 4D LSTM networks and DBSCAN clustering, it provides real-time, geofenced threat intelligence.

## 🚀 Key Features

- **Decoupled Architecture:** Completely database-agnostic. Feed it any valid dataset (dictionaries/JSON) and it will train.
- **Deep Learning Core:** Uses TensorFlow/Keras LSTM to predict disaster probabilities (Earthquakes, Volcanos, Tsunamis, Nuclear anomalies).
- **Dynamic Hotspotting:** Implements DBSCAN to automatically cluster and identify active hazard zones worldwide.
- **Quantum Reactor Math:** Includes mathematical formulas for neutron flux, core temperature estimation, and K-effective stability.

## 📦 Installation

You can install the library directly via pip:

```bash
pip install upt-guardian
```

## 💻 Quick Start

Here is a simple example of how to initialize the AI, train it with your own data, and make global predictions.

```python
from upt_guardian import DeepGuardian

# 1. Initialize the AI Engine
ai_core = DeepGuardian()

# 2. Prepare your raw data (List of Dictionaries)
# Data must contain: mag, depth, mmi, alert_level
historical_logs = [
    {"mag": 5.4, "depth": 10.0, "mmi": 5, "alert_level": "WARNING", "lat": 35.0, "lng": 139.0},
    {"mag": 7.1, "depth": 15.2, "mmi": 8, "alert_level": "CRITICAL", "lat": 36.2, "lng": 140.1},
    # ... Add hundreds of logs for better accuracy
]

# 3. Train the Engine (In-Memory)
ai_core.train(historical_logs)

# 4. Predict disaster risks for current hotspots
predictions = ai_core.predict_global_risk()

for p in predictions:
    print(f"Location: {p['name']} | Risk: {p['risk_score']*100:.1f}% | Level: {p['alert_level']}")
```

## ☢️ Quantum Reactor Module

UPT Guardian also ships with a simulation core for Quantum Reactors.

```python
from upt_guardian import UPTReactorCore

reactor = UPTReactorCore()

# Start the background simulation thread
reactor.start_reactor()

# Fetch real-time telemetry
status = reactor.get_status()
print(f"Core Temp: {status['core_temp']}K | Flux: {status['neutron_flux']}")

# Safely shut down
reactor.stop_reactor()
```

## 🛠️ Configuration & Customization
You can tweak the AI parameters directly:
```python
ai_core.look_back = 20         # Adjust LSTM temporal window
ai_core.spatial_look_back = 10 # Adjust spatial sequence length
```

## 📄 License
**Proprietary & Confidential**
Copyright (c) 2026 Võ Trần Hoàng Uy. All Rights Reserved.
This source code is completely closed and proprietary. You are not allowed to copy, distribute, modify, or reverse-engineer this technology under any circumstances.
