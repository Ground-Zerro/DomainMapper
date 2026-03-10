import os
import shutil

def copy_and_rename_py_files():
    # Получаем текущую директорию
    current_dir = os.getcwd()
    
    # Имя самого скрипта, чтобы не копировать себя бесконечно
    script_name = os.path.basename(__file__)
    
    print(f"Обработка папки: {current_dir}")
    
    count = 0
    for filename in os.listdir(current_dir):
        # Проверяем расширение .py и исключаем сам скрипт
        if filename.endswith(".py") and filename != script_name:
            source_path = os.path.join(current_dir, filename)
            
            # Если это файл (а не папка с таким именем)
            if os.path.isfile(source_path):
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_copy.txt"
                dest_path = os.path.join(current_dir, new_filename)
                
                # Если файл с новым именем уже есть, добавляем цифру
                counter = 1
                while os.path.exists(dest_path):
                    new_filename = f"{name}_copy{counter}{ext}"
                    dest_path = os.path.join(current_dir, new_filename)
                    counter += 1
                
                # Копируем файл (copy2 сохраняет метаданные)
                shutil.copy2(source_path, dest_path)
                print(f"[OK] Скопировано: {filename} -> {new_filename}")
                count += 1

    print(f"\nГотово. Всего скопировано файлов: {count}")

if __name__ == "__main__":
    copy_and_rename_py_files()