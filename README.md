# 🛰️ Aminos 3D Ground Scanner & Metal Detector - Multi-Agent AI Platform

An advanced Multi-Agent Autonomous Research & Development Platform powered by **Google Gemini Pro**, **LangGraph**, and **Streamlit** for designing, reverse-engineering, and manufacturing high-precision geophysical instruments.

---

## 🌟 Key Capabilities

1. **Pure 3D Geomagnetic Ground Scanner / Gradiometer:**
   * Differential fluxgate architecture (2x Stefan Mayer FLC-100 / FGM-3).
   * 16-bit Delta-Sigma ADC (ADS1115) with precision ultra-low noise LDO regulation (TPS7A20).
   * Dual-core 240MHz ESP32-WROOM-32 with Bluetooth BLE/Classic & MicroSD telemetry logging.
   * Golden 4-Layer KiCad PCB design with complete GND shield isolation and 0 DRC violations.

2. **Autonomous Multi-Agent Engineering Workflow:**
   * **Agent 1 (Research & Reverse-Engineering):** Live patent and forum crawler (Tavily & Google Gemini Vision).
   * **Agent 2 (Hardware Architecture & Physics):** Calculates magnetic anomalies, spatial resolution, and component BOM.
   * **Agent 3 (KiCad PCB Designer):** Verifies stackup, track impedance, analog-digital split plane, and decoupling.
   * **Agent 4 (DSP & Embedded Firmware):** Generates Kalman filter, moving average windowing, and C++ ESP32 firmware.
   * **Agent 5 (Lead System Reviewer):** Synthesizes comprehensive golden engineering reports with downloadable Markdown.

---

## 🚀 Live Cloud Deployment (Streamlit Cloud)

To run this platform on Streamlit Community Cloud:

1. Connect your repository on [share.streamlit.io](https://share.streamlit.io).
2. Set your **Secrets** in the Streamlit Cloud dashboard:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key"
   TAVILY_API_KEY = "your_tavily_api_key"
   ```
3. Set Main file path: `app.py`.
4. Deploy!

---

## 💻 Local Installation & Setup

```bash
# Clone the repository
git clone https://github.com/farouk1976omar/Aminos-3D-Scanner-Platform.git
cd Aminos-3D-Scanner-Platform

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run the platform
streamlit run app.py
```

---

## 📜 License
Developed for Open Engineering & Advanced Geophysical Instrumentation Research.
