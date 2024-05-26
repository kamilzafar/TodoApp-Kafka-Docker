from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)

TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)

KAFKA_SERVER = config("KAFKA_SERVER", cast=str)
KAFKA_GROUP_ID = config("KAFKA_GROUP_ID", cast=str)
KAFKA_CONSUMER_TOPIC = config("KAFKA_CONSUMER_TOPIC", cast=str)
KAFKA_PRODUCER_TOPIC = config("KAFKA_PRODUCER_TOPIC", cast=str)