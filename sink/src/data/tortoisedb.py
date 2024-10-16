# TODO: documentation
#
#
#

# third-party
import uuid
from tortoise import fields, models, Tortoise
from datetime import datetime

# internal helpers, configurations
from settings import APPConfigurations

# internal models
class _SinkData(models.Model):
    timestamp = fields.DatetimeField(pk=True)
    battery_level = fields.DecimalField(max_digits=5, decimal_places=2)
    connected_clients = fields.IntField()
    total_clients = fields.IntField()
    sub_count = fields.IntField()
    bytes_sent = fields.IntField()
    bytes_received = fields.IntField()
    messages_sent = fields.IntField()
    messages_received = fields.IntField()
    payload = fields.TextField(null=False)

    def __str__(self):
        return f''

class _SensorDevice(models.Model):
    device_id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    latitude = fields.DecimalField(max_digits=9, decimal_places=6)
    longitude = fields.DecimalField(max_digits=9, decimal_places=6)
    lastsync = fields.DatetimeField()

    sensor_data: fields.ReverseRelation["_SensorData"]

    def __str__(self):
        return f''

class _SensorData(models.Model):
    device = fields.ForeignKeyField(
        "models.SensorDevice",
        related_name="sensor_data",
        on_delete=fields.CASCADE
    )
    battery_level = fields.DecimalField(max_digits=5, decimal_places=2)
    timestamp = fields.DatetimeField()
    soil_moisture = fields.DecimalField(max_digits=5, decimal_places=2)
    temperature = fields.DecimalField(max_digits=5, decimal_places=2)
    humidity = fields.DecimalField(max_digits=5, decimal_places=2)
    payload = fields.TextField(null=False)

    def __str__(self):
        return f''

# store the data as raw payloads
class _UnsyncedData(models.Model):
    topic = fields.CharField(max_length="100")
    origin = fields.TextField(null=False) # identifier of the origin of the unsynced data
    timestamp = fields.DatetimeField()
    payload = fields.TextField(null=False)

async def init():
    await Tortoise.init(
        db_url='sqlite://smmic.db',
        modules={'models': ['__main__']}
    )
    await Tortoise.generate_schemas()