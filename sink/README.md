# smmic-iot/sink

The central IoT hub for the **SMMIC (Soil Moisture Monitoring and Irrigation Control)** system. Runs on a Raspberry Pi to collect sensor data, control irrigation hardware, and communicate via MQTT.

## Features

- Multi-process async architecture with asyncio and multiprocessing
- MQTT-based sensor data collection and command routing
- GPIO irrigation control (water pump on/off via configurable channel)
- Local SQLite storage with offline-first sync to remote API
- Real-time device commands via Pusher WebSocket integration
- System health monitoring (CPU, memory, broker stats)
- Mosquitto broker telemetry collection

## Getting Started

### Prerequisites

- Python 3.10+
- Raspberry Pi OS (or any Linux-based system with GPIO support)
- Mosquitto MQTT broker

### Installation

```bash
git clone https://github.com/rubiokittsrey/smmic-iot.git
cd smmic-iot/sink
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp settings.example.yaml settings.yaml
```

Edit `settings.yaml` and `.env` with your environment values.

Add the following to your `~/.bashrc` (or `~/.zshrc`):

```bash
export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/common"
export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/data"
export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/hardware"
export PYTHONPATH="$PYTHONPATH:$HOME/path_to_smmic_iot/smmic-iot/sink/src/mqtt"
```

Then apply changes:

```bash
source ~/.bashrc
```

### Running

```bash
python3 smmic.py start [mode]
```

| Mode | Logging | Log File |
|------|---------|----------|
| `dev` | Verbose | No |
| `normal` | Warnings only | Yes |
| `info` | Info-level | Yes |
| `debug` | Verbose | Yes |

## Architecture

```
MQTT Broker <-> MQTT Client (Main Process)
                      |
                Task Manager --> Router
                      |
            +---------+---------+
            |                   |
    Hardware Process     HTTP Client Process
     (GPIO control)      (API sync + retry)
            |                   |
            +----> SQLite <-----+
                (local storage)
```

The application spawns 3 child processes from the main process:

- **Task Manager** - routes messages from MQTT to appropriate handlers
- **HTTP Client** - handles API communication and retries
- **Hardware** - manages GPIO irrigation control

The main process runs the MQTT client and system monitor. Processes communicate via multiprocessing queues. Data is stored locally in SQLite and synced to the remote API when available.

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `{ROOT}/sensor/data` | Subscribe | Incoming sensor readings |
| `{ROOT}/sensor/alert` | Subscribe | Sensor alerts |
| `{ROOT}/sink/data` | Publish | Sink telemetry data |
| `{ROOT}/sink/alert` | Publish | Sink alerts |
| `{ROOT}/irrigation` | Pub/Sub | Irrigation control commands |
| `{ROOT}/commands/feedback` | Publish | Command feedback responses |
| `{ROOT}/admin/settings` | Subscribe | Admin settings |
| `{ROOT}/admin/commands` | Subscribe | Admin commands |

`{ROOT}` is the configurable root topic prefix set via the `ROOT_TOPIC` environment variable.

### Broker Statistics

The sink also subscribes to Mosquitto `$SYS` topics for telemetry:

- `$SYS/broker/clients/connected`
- `$SYS/broker/clients/total`
- `$SYS/broker/subscriptions/count`
- `$SYS/broker/load/bytes/sent` / `received`
- `$SYS/broker/load/messages/sent` / `received`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API health check |
| `/sensor/data` | POST | Submit sensor readings |
| `/sensor/alert` | POST | Submit sensor alerts |
| `/sink/data` | POST | Submit sink system telemetry |

Base URL is configured via the `API_URL` environment variable.

## Configuration

### settings.yaml

```yaml
app_configurations:
  client_id: 'your-client-uuid'
  global_semaphore_count: 5
  api_disconnect_await: 1800
  local_storage:
    directory: '/home/smmic/.smmic/sink/storage/'
  network:
    primary_interface: 'wlan0'
    gateway: '192.168.100.1'
    timeout: 10
  pusher:
    app_id: 'your-pusher-app-id'
    cluster: 'ap3'
    channels: ['private-user_commands']

hardware_configurations:
  irrigation_channel: 23

registered_sensors:
  - 'sensor-uuid-1'
  - 'sensor-uuid-2'
```

### .env

```
BROKER_HOST_ADDRESS=192.168.x.x
BROKER_PORT=1883
ROOT_TOPIC=smmic
API_URL=http://your-api-url
HEALTH_CHECK_URL=/health
SENSOR_DATA=/sensor/data
SINK_DATA=/sink/data
SECRET_KEY=your-secret-key
```

## Project Structure

```
sink/
├── smmic.py                     # Main entry point and process orchestrator
├── taskmanager.py               # Message router/dispatcher
├── requirements.txt
├── settings.yaml
├── common/
│   ├── settings.py              # Config loader (YAML + env)
│   └── utils.py                 # Logging, status codes, helpers
├── src/
│   ├── hardware/
│   │   ├── hardware.py          # Hardware task orchestrator
│   │   ├── irrigation.py        # GPIO pump control
│   │   └── network.py           # Network management
│   ├── mqtt/
│   │   ├── mqttclient.py        # MQTT client with callbacks
│   │   ├── service.py           # Broker status checks
│   │   └── telemetrymanager.py  # Broker telemetry collection
│   └── data/
│       ├── httpclient.py        # Async HTTP API client
│       ├── locstorage.py        # SQLite local storage
│       ├── sysmonitor.py        # System metrics monitoring
│       ├── pusherclient.py      # Pusher WebSocket client
│       ├── reqs.py              # HTTP request utilities
│       └── tortoisedb.py        # ORM model definitions
└── tests/
    ├── mqtt_pub_scripts/        # MQTT test publishers
    ├── mqtt_sub_scripts/        # MQTT test subscribers
    ├── data/                    # Data module tests
    └── lab/                     # Experimental code
```

---

**Author**: [@rubiokittsrey](https://github.com/rubiokittsrey)
