from services.database_service import DatabaseService
from services import constant
import json
from services.logger import Logger

logger = Logger.get_logger()


class AiSeparationRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def add_ai_separation(self, data) -> int:
        try:
            logger.info(f"Adding ai_separation {data.get('image_id', None)}")
            query = "INSERT INTO ai_separation (image_id, categorie_id, sous_categorie_id, sous_sous_categorie_id, explication, created_at, ocr_content, ratio) VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)"
            self.cursor.execute(query, [data.get('image_id', None), data.get('categorie_id', None), data.get('sous_categorie_id', None), data.get('sous_sous_categorie_id', None), data.get('explication', ''), data.get('ocr_content', json.dumps(data.get('data', None))), data.get('ratio', 0)])
            self.connection.commit()
            logger.info(f"Ai_separation added {self.cursor.lastrowid}")
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding ai_separation: {e}")
            return None 

