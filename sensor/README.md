# sensor

## esp32 sensor node
- **sink_main.py** -> main script, should handle all the other modules within the applications
- /common contains helper, provider modules (utils, constants, etc.)
- /src contains application modules (api, mqtt, tests)
- /tests/test_pub.py and test_sub.py scripts are not exported and should not be imported on other modules (strictly for testing)
