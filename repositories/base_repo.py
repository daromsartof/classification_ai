from services.database_service import DatabaseService

class BaseRepo:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor = self.connection.cursor(dictionary=True)
