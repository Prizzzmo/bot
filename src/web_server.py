import os

def get_base_url():
    """Возвращает базовый URL для формирования ссылок"""
    return "https://" + os.environ.get("REPL_SLUG", "history-map") + "." + os.environ.get("REPL_OWNER", "repl") + ".repl.co"