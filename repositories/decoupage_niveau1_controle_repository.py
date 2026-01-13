from services.database_service import DatabaseService
from repositories.base_repo import BaseRepo

from services.logger import Logger

logger = Logger.get_logger()

class DecoupageNiveau1ControleRepositorie(BaseRepo):
    def __init__(self):
        super().__init__()
        
    def get_decoupage_niveau1_controle_by_imageId(self, imageId: int) -> list:
        try:
            query = "select * from decoupage_niveau1_controle where image_id = %s"
            self.cursor.execute(query, [imageId])
            res = self.cursor.fetchall() or []
            return res
        except Exception as e:
            logger.error(f"Error fetching decoupage_niveau1_controle by id: {e}")
            return None
