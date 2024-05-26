import asyncio
from fastapi import FastAPI, Depends
from sqlmodel import Session
from typing import Annotated, AsyncGenerator
from todo.utils import curd, settings
from todo.utils.models import Todo
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import todo.todo_pb2 as proto_todo
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine

messages: list[str] = []

connection_string = str(settings.DATABASE_URL)

# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)

async def consumer_task(name, broker):
    consumer = AIOKafkaConsumer(
        name,
        bootstrap_servers=broker,
        group_id= settings.KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            new_todo = proto_todo.Recommended()
            new_todo.ParseFromString(msg.value)
            response_message = new_todo.response
            messages.append(response_message)
            print(f"Consumed message: {response_message}")
    finally:
        await consumer.stop()

# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    asyncio.create_task(consumer_task(settings.KAFKA_CONSUMER_TOPIC, settings.KAFKA_SERVER))
    create_db_and_tables()
    yield

def db_session():
    with Session(engine) as session:
        yield session

app = FastAPI(lifespan=lifespan, title="Todo App", description="A simple todo app with docker")

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@app.get("/", tags=["Root"])
async def read_root():
    return {"Hello": "Pakistan"}

@app.get("/todos", response_model=list[Todo], tags=["Todos"])
def read_todos(session: Annotated[Session, Depends(db_session)]):
        todos = curd.read_todos(session)
        return todos

@app.post("/todos", tags=["Todos"])
async def create_todos(todo: Todo, session: Annotated[Session, Depends(db_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    todo_protobuf = proto_todo.Todo(id=todo.id, content=todo.task)
    serialize_todo = todo_protobuf.SerializeToString()
    await producer.send_and_wait(settings.KAFKA_PRODUCER_TOPIC, serialize_todo)
    return curd.create_todos(todo.task, session)

@app.get("/consume_and_recommend", tags=["Recommendations"])
async def consume_and_recommend():
    if messages:
        latest_message = messages.pop(0)  # Get the latest consumed message
        # Here you can process the message as needed, e.g., pass it to OpenAI or other services
        # For demonstration, just return the latest message
        return {"recommendation": latest_message}
    return {"message": "No messages to process"}

@app.delete("/todos", response_model=dict, tags=["Todos"])
def delete_todos(id: int, session: Annotated[Session, Depends(db_session)]):
    return curd.delete_todos(id, session)

@app.patch("/todos", response_model=Todo, tags=["Todos"])
def update_todos(id: int, update_todo: str, session: Annotated[Session, Depends(db_session)]):
    return curd.update_todos(id, update_todo, session)