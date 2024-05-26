from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

OPENAI_KEY = config("OPENAI_KEY", cast=Secret)
KAFKA_SERVER = config("KAFKA_SERVER", cast=str)
KAFKA_GROUP_ID = config("KAFKA_GROUP_ID", cast=str)
KAFKA_CONSUMER_TOPIC = config("KAFKA_CONSUMER_TOPIC", cast=str)
KAFKA_PRODUCER_TOPIC = config("KAFKA_PRODUCER_TOPIC", cast=str)