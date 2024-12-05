from paho.mqtt import client as mqtt, enums

from settings import Topics, Broker
    
client = mqtt.Client(client_id="irrigation_test")
client.connect(Broker.HOST, Broker.PORT)
client.loop_start()

payload = '300'
try:
    msg = client.publish(
        # 'smmic/sensor/triggers/interval'
        topic=f'smmic/sensor/triggers/interval/58c6dd67-3200-4bf0-8044-a851465edd02',
        payload=payload,
        qos=1
        )
    msg.wait_for_publish()
    if msg.is_published():
        print('yea')

except Exception as e:
    print(str(e))

