
import os

print("Информация о REPL:")
print(f"REPL ID: {os.environ.get('REPL_ID', 'Не найден')}")
print(f"REPL Slug: {os.environ.get('REPL_SLUG', 'Не найден')}")
print(f"REPL Owner: {os.environ.get('REPL_OWNER', 'Не найден')}")
print(f"REPL Language: {os.environ.get('REPL_LANGUAGE', 'Не найден')}")
