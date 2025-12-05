from services.database_service import DatabaseService

from services.logger import Logger

logger = Logger.get_logger()

class TiersRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    
    def get_tiers_by_dossier_id(self, dossier_id):
        try:
            query = f"select * from tiers where dossier_id = {dossier_id} and (type = 1 or type = 0)"
            pool = self.databse.get_pool()
            connection = pool.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
                
        except:
            logger.error("Error fetching tiers by dossier_id")
