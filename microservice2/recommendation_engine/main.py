import json
from fastapi import Depends, FastAPI
from openai import OpenAI
from recommendation_engine import settings
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import recommendation_engine.todo_pb2 as todos
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator, List
import asyncio

consumed_messages: List[str] = []

async def consumer_task(name: str, server: str):
    consumer = AIOKafkaConsumer(
        name,
        bootstrap_servers=server,
        group_id=settings.KAFKA_GROUP_ID,
        auto_offset_reset='earliest'  
    )
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            new_todo = todos.Todo()
            new_todo.ParseFromString(msg.value)
            message = str(new_todo.content)
            print(f"message: {message}")
            consumed_messages.append(message)
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()

async def produce_message():
    producer = AIOKafkaProducer(bootstrap_servers="broker:19092")
    await producer.start()
    try:
        # Produce message
        yield producer
    finally:
        # Wait for all pending messages to be delivered or expire.
        await producer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("consuming messages")
    asyncio.create_task(consumer_task(settings.KAFKA_CONSUMER_TOPIC, settings.KAFKA_SERVER))
    yield

app = FastAPI(lifespan=lifespan)

client = OpenAI(api_key=settings.OPENAI_KEY)

@app.get("/", tags=["Root"])
def read_root():
    return {"Hello": "Pakistan"}

@app.post("/recommendation", tags=["Assistant"])
async def get_recommendation(text: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
        {"role": "system", "content": "You are a helpful assistant. You would give suggestions to the user related to the items the user enters. you would suggest items that are similar. just provise the list of products. just provide the list of products in json format."},
        {"role": "user", "content": text}
        ]
    )
    json.dumps(response.choices[0].message.content)
    return response.choices[0].message.content

@app.get("/consume_and_recommend", tags=["Assistant"])
async def consume_and_recommend(producer: Annotated[AIOKafkaProducer, Depends(produce_message)]):
    if consumed_messages:
        # Use the latest consumed message for recommendation
        latest_message = consumed_messages.pop(0)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. You would give suggestions to the user related to the items the user enters. you would suggest items that are similar. just provide the list of product names in json format."},
                {"role": "user", "content": latest_message}
            ]
        )
        ai_response = todos.Recommended(response = response.choices[0].message.content)
        serialized_data = ai_response.SerializeToString()
        print(f"serialize data: {serialized_data}")
        await producer.send_and_wait(settings.KAFKA_PRODUCER_TOPIC, serialized_data)
        return response.choices[0].message.content
    return {"message": "No messages to process"}