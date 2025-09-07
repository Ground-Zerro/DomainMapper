def split_file_exact(input_file, max_lines=1000):
    """
    Разбивает файл согласно точному описанию: 
    - В исходном файле оставляет первые 1000 строк
    - Остальные строки переносит в domain-ip-resolve2.txt, domain-ip-resolve3.txt и т.д.
    """
    
    try:
        # Читаем все строки из исходного файла
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        if total_lines <= max_lines:
            print(f"Файл содержит {total_lines} строк, разбиение не требуется.")
            return
        
        # Оставляем первые 1000 строк в исходном файле
        with open(input_file, 'w', encoding='utf-8') as f:
            f.writelines(lines[:max_lines])
        
        # Остальные строки распределяем по новым файлам
        remaining_lines = lines[max_lines:]
        num_additional_files = (len(remaining_lines) + max_lines - 1) // max_lines
        
        for i in range(num_additional_files):
            start_index = i * max_lines
            end_index = min((i + 1) * max_lines, len(remaining_lines))
            
            output_file = f"domain-ip-resolve{i+2}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.writelines(remaining_lines[start_index:end_index])
            
            print(f"Создан файл {output_file} со строками {max_lines + start_index + 1}-{max_lines + end_index}")
        
        print(f"Разбиение завершено. Создано {num_additional_files} дополнительных файлов.")
    
    except FileNotFoundError:
        print(f"Ошибка: Файл {input_file} не найден.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Использование
if __name__ == "__main__":
    input_filename = "domain-ip-resolve.txt"
    split_file_exact(input_filename)