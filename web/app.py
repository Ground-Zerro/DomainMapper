from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()

# Указываем директории для статических файлов и шаблонов
templates = Jinja2Templates(directory=os.path.dirname(os.path.realpath(__file__)))
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_form(request: Request):
    # Загружаем HTML шаблон (index.html) и передаем в него данные
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/run")
async def run_dns_resolver(
    services: list[str] = Form(...),
    dns_servers: list[str] = Form(...),
    cloudflare: str = Form(...),
    aggregation: str = Form(...),
    format: str = Form(...),
    gateway: str = Form(None),
    commentary: str = Form(None)
):
    # Генерация config.ini
    config_path = "config.ini"
    with open(config_path, "w") as config:
        config.write("[DomainMapper]\n")
        config.write(f"service={','.join(services)}\n")
        config.write(f"dnsserver={','.join(dns_servers)}\n")
        config.write(f"cloudflare={cloudflare}\n")
        config.write(f"subnet={aggregation}\n")
        config.write(f"filetype={format}\n")
        if gateway:
            config.write(f"gateway={gateway}\n")
        if commentary:
            config.write(f"commentary={commentary}\n")

    # Запуск скрипта
    result_file = "output.txt"
    os.system(f"python3 main.py -c {config_path}")

    # Возвращаем файл результата
    return FileResponse(path=result_file, filename="output.txt", media_type="text/plain")
