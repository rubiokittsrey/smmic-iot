from paho.mqtt import client as mqtt, enums

from settings import Topics, Broker
    
client = mqtt.Client(client_id="irrigation_test")
client.connect(Broker.HOST, Broker.PORT)
client.loop_start()

payload = '1'
try:
    msg = client.publish(
        # 'smmic/sensor/triggers/interval'
        topic=f'smmic/sensor/triggers/irrigation/2d976174-d657-4f1d-9432-758996d36455',
        payload=payload,
        qos=1
        )
    msg.wait_for_publish()
    if msg.is_published():
        print('yea')

except Exception as e:
    print(str(e))

