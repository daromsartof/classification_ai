from services.database_service import DatabaseService

from services.logger import Logger

logger = Logger.get_logger()


class AiSeparationSettingRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def get_ai_separation_setting(self):
        try:
            query = "SELECT * FROM ai_separation_setting where id = 1 order by id desc limit 1 ;"
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return rows[0]
        
        except Exception as e:
            logger.error(f"Error fetching ai_separation_context: {e}")
            return None 

    def set_power(self, power: int) -> bool:
        """Active/désactive le service IA (colonne power)."""
        try:
            query = "UPDATE ai_separation_setting SET power = %s WHERE id = 1"
            self.cursor.execute(query, [power])
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating power: {e}")
            self.connection.rollback()
            return False

