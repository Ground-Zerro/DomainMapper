import os
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Определение модели для данных запроса
class RunScriptRequest(BaseModel):
    config: str
    userId: str

# Инициализация FastAPI приложения
app = FastAPI()

@app.post("/run")
async def run_script(request: RunScriptRequest):
    config_content = request.config
    user_id = request.userId

    # Создание имени файла конфигурации
    config_filename = f"config-id_{user_id}.ini"
    try:
        # Запись конфигурации в файл
        with open(config_filename, 'w') as f:
            f.write(config_content)

        # Выполнение команды через subprocess
        result = subprocess.run(
            ['python3', 'main.py', '-c', config_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Возвращение результатов выполнения скрипта
        return {"stdout": result.stdout, "stderr": result.stderr}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

# Запуск приложения (для использования с Uvicorn)
if __name__ == "__main__":
    # Запуск FastAPI с использованием Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
