#!/usr/bin/env python3
"""
Скрипт для экспорта логов бота
"""
import os
import shutil
from datetime import datetime

def export_logs():
    log_dir = 'logs'
    export_dir = 'logs_export'
    
    # Создаем директорию для экспорта, если её нет
    os.makedirs(export_dir, exist_ok=True)
    
    # Генерируем имя файла с текущей датой и временем
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_file = os.path.join(export_dir, f'bot_logs_{timestamp}.txt')
    
    # Проверяем, существует ли папка с логами
    if not os.path.exists(log_dir):
        print(f"❌ Папка {log_dir} не найдена!")
        return
    
    # Ищем все файлы логов
    log_files = []
    if os.path.exists(os.path.join(log_dir, 'bot.log')):
        log_files.append(os.path.join(log_dir, 'bot.log'))
    
    # Ищем ротированные логи (bot.log.1, bot.log.2, и т.д.)
    for i in range(1, 10):
        rotated_log = os.path.join(log_dir, f'bot.log.{i}')
        if os.path.exists(rotated_log):
            log_files.append(rotated_log)
    
    if not log_files:
        print(f"❌ Файлы логов не найдены в папке {log_dir}!")
        return
    
    # Сортируем файлы по дате модификации (новые первыми)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Объединяем все логи в один файл
    print(f"📝 Экспорт логов из {len(log_files)} файлов...")
    with open(export_file, 'w', encoding='utf-8') as outfile:
        for log_file in log_files:
            filename = os.path.basename(log_file)
            outfile.write(f"\n{'='*80}\n")
            outfile.write(f"Файл: {filename}\n")
            outfile.write(f"{'='*80}\n\n")
            try:
                with open(log_file, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                    outfile.write("\n\n")
            except Exception as e:
                outfile.write(f"Ошибка при чтении {filename}: {e}\n\n")
    
    print(f"✅ Логи экспортированы в: {export_file}")
    print(f"📊 Размер файла: {os.path.getsize(export_file) / 1024:.2f} КБ")
    
    # Также создаем краткую версию с последними 500 строками
    short_file = os.path.join(export_dir, f'bot_logs_last_{timestamp}.txt')
    with open(export_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
        last_lines = lines[-500:] if len(lines) > 500 else lines
    
    with open(short_file, 'w', encoding='utf-8') as outfile:
        outfile.write("Последние 500 строк логов:\n")
        outfile.write("="*80 + "\n\n")
        outfile.writelines(last_lines)
    
    print(f"✅ Краткая версия (последние 500 строк): {short_file}")

if __name__ == '__main__':
    export_logs()


