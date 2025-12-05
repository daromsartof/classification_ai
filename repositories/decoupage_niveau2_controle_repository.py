from services.database_service import DatabaseService
from repositories.base_repo import BaseRepo

from services.logger import Logger

logger = Logger.get_logger()

class DecoupageNiveau2ControleRepositorie(BaseRepo):
    def __init__(self):
        super().__init__()
        
    def get_decoupage_niveau2_by_imageId(self, imageId: int) -> dict:
        try:
            query = "select * from decoupage_niveau2_controle where image_id = %s"
            self.cursor.execute(query, [imageId])
            res = self.cursor.fetchall() or []
            if len(res) > 0:
                return res[0]
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching decoupage_niveau2 by id: {e}")
            return None
    
    def insert_decoupage_niveau2(self, imageId: int, data: dict):
        try:
            decoupage_niveau2 = self.get_decoupage_niveau2_by_imageId(imageId)
            if decoupage_niveau2:
               logger.warning(f"l'image a déjà été classée")
               return decoupage_niveau2
            query = "INSERT INTO `decoupage_niveau2_controle` (`image_id`, `lot_id`, `date_creation`, `categorie_id`, `nbpage`) VALUES (%s, %s, NOW(), %s, %s);"
            self.cursor.execute(query, [imageId, data.get('lot_id'), data.get('categorie_id'), data.get('num_page')])
            self.connection.commit()
            logger.info("finish insertion decoupage_niveau2_controle")
            return data
        except Exception as e:
            logger.error(f"Error updating decoupage_niveau2_controle: {e}")
            return None
