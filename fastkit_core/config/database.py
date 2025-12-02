import os

CONNECTIONS = {
    'default': {
        'driver':  os.getenv('DB_DRIVER', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME', 'fastkit'),
        'username': os.getenv('DB_USERNAME', 'root'),
        'password': os.getenv('DB_PASSWORD', 'secret'),
    }
}