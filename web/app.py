from fastapi import FastAPI, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
import asyncio
import os

app = FastAPI()

@app.get("/")
async def get_form():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DNS Resolver Settings</title>
    </head>
    <body>
        <h2>Настройки</h2>
        <form action="/run" method="post" enctype="multipart/form-data">
            <label><strong>Список сервисов:</strong></label><br>
            <input type="checkbox" name="services" value="service1"> Service 1<br>
            <input type="checkbox" name="services" value="service2"> Service 2<br>
            <input type="checkbox" name="services" value="service3"> Service 3<br><br>

            <label><strong>Список используемых DNS серверов:</strong></label><br>
            <input type="checkbox" name="dns_servers" value="dns1"> DNS Server 1<br>
            <input type="checkbox" name="dns_servers" value="dns2"> DNS Server 2<br>
            <input type="checkbox" name="dns_servers" value="dns3"> DNS Server 3<br><br>

            <label><strong>Фильтрация Cloudflare:</strong></label><br>
            <input type="checkbox" name="cloudflare" value="yes"> Исключить Cloudflare<br><br>

            <label><strong>Агрегация подсетей:</strong></label><br>
            <input type="radio" name="aggregation" value="16"> До /16 (255.255.0.0)<br>
            <input type="radio" name="aggregation" value="24"> До /24 (255.255.255.0)<br>
            <input type="radio" name="aggregation" value="mix"> Микс /24 и /32<br>
            <input type="radio" name="aggregation" value="none" checked> Не агрегировать<br><br>

            <label><strong>Формат сохранения:</strong></label><br>
            <input type="radio" name="format" value="win"> Windows Route<br>
            <input type="radio" name="format" value="unix"> Unix Route<br>
            <input type="radio" name="format" value="cidr" checked> CIDR<br><br>

            <button type="submit">Запустить</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/run")
async def run_dns_resolver(
    services: list[str] = Form(...),
    dns_servers: list[str] = Form(...),
    cloudflare: str = Form(...),
    aggregation: str = Form(...),
    format: str = Form(...)
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

    # Запуск скрипта
    result_file = "output.txt"
    os.system(f"python3 main.py -c {config_path}")

    # Возвращаем файл результата
    return FileResponse(path=result_file, filename="output.txt", media_type="text/plain")
