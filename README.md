# smmic-iot

## dev instructions (unloading on raspberry pi)
- open configs.yaml, verify configurations, constants etc.
- if configs.yaml is not present / not provided, ask for configurations
- unload contents of sink into .smmic folder on /home/rpi
- run 'pip install mosquitto', 'sudo apt install mosquitto' is fine too
- inside ~/ run 'python -m venv .smmic-env'
- the run 'source .smmic-env/bin/activate'
- run 'pip install -r requirements.txt'
- add this line > 'export PYTHONPATH="$HOME/.smmic/common:$HOME/.smmic/src/api:$HOME/.smmic/src/mqtt:$PYTHONPATH" to ~/.bashrc
- run 'python /.smmic/src/tests/test_pub.py' and 'python /.smmic/src/tests/test_sub.py' to test if everything's good
