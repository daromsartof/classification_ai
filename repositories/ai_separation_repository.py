from services.database_service import DatabaseService
from services import constant

from services.logger import Logger

logger = Logger.get_logger()


class AiSeparationRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def add_ai_separation(self, data):
        try:
            query = "INSERT INTO ai_separation (image_id, categorie_id, sous_categorie_id, sous_sous_categorie_id, explication, created_at, ocr_content, ratio) VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)"
            self.cursor.execute(query, (data['image_id'], data['categorie_id'], data['sous_categorie_id'], data['sous_sous_categorie_id'], data['explication'], data.get('ocr_content', None), data.get('ratio', 0)))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding ai_separation: {e}")
            return False 

