from fastapi import HTTPException
from sqlmodel import Session, select
from todo import main

def read_todos(session: Session):
        todos = session.exec(select(main.Todo)).all()
        # if todos is None:
        #     raise HTTPException(status_code=404, detail="No todos found")
        return todos

def create_todos(title: str, session: Session):
        todo = main.Todo(task=title)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo

def delete_todos(id: int, session: Session):
        todo = session.exec(select(main.Todo).where(main.Todo.id == id)).first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        session.delete(todo)
        session.commit()
        return {"message": "Todo deleted successfully"}

def update_todos(id: int, title: str, session: Session):
        todo = session.exec(select(main.Todo).where(main.Todo.id == id)).first()
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        todo.task = title
        session.commit()
        session.refresh(todo)
        return todo