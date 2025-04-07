# 🌱 SMMIC IoT Sink

This is the **sink** component of the **SMMIC (Soil Moisture Monitoring and Irrigation Control)** project. It runs on a Raspberry Pi and acts as the central node responsible for managing sensor data, hardware control, MQTT messaging, and integration with remote services.

---

## 📦 Requirements

- **Python 3.10 or later**
- Raspberry Pi OS (or any Linux-based system with GPIO support)

---

## ⚙️ Installation & Setup

1. **Create and activate a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate

2. **Install Dependencies:**
   ```bash
   cd smmic-iot/sink
   pip install -r requirements.txt

3. **Configure Settings:**
   ```bash
   cp settings.example.yaml settings.yaml
   ```

   Make sure to replace the example values to your environment variables.

4. **Set your $PYTHONPATH:**
   Add the following to your ~/.bashrc (or ~/.zshrc):

   ```bash
   export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/common"
   export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/data"
   export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/hardware"
   export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/mqtt"
   ```

   Then apply changes
   ```bash
   source ~/.bashrc

5. **Run the application:**  
   `debug`: Verbose logging, log file enabled  
   `dev`: Verbose logging, no log file  
   `normal`: Warnings only, log file enabled  
   `info`: Info-level logging, log file enabled  

   ```bash
   python3 smmic.py start [mode]
