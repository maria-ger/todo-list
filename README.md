# todo-list
RESTful CRUD-сервис для управления задачами (Todo)

## Запуск
Добавить файл .env с ссылкой на базу данных (PostgreSQL)
```
DATABASE_URL = "your_link_here"
```
Выполнить в терминале команды:
```
python init_db.py
uvicorn main:app --reload
```
Перейти по ссылке [http://127.0.0.1:8000](http://127.0.0.1:8000)
