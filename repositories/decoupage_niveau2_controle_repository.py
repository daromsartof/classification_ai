from services.database_service import DatabaseService
from repositories.base_repo import BaseRepo

from services.logger import Logger

logger = Logger.get_logger()

class DecoupageNiveau2ControleRepositorie(BaseRepo):
    def __init__(self):
        super().__init__()
        
    def get_decoupage_niveau2_controle_by_imageId(self, imageId: int) -> dict:
        try:
            query = "select * from decoupage_niveau2_controle where image_id = %s"
            self.cursor.execute(query, [imageId])
            res = self.cursor.fetchall() or []
            return res
        except Exception as e:
            logger.error(f"Error fetching decoupage_niveau2 by id: {e}")
            return None
    
    def insert_decoupage_niveau2_controle(self, imageId: int, data: dict):
        try:
            decoupage_niveau2_controle = self.get_decoupage_niveau2_controle_by_imageId(imageId)
            if len(decoupage_niveau2_controle) > 0:
               data['explication'] = f"l'image a déjà été classée"
               return decoupage_niveau2_controle
            query = "INSERT INTO `decoupage_niveau2_controle` (`image_id`, `lot_id`, `date_creation`, `categorie_id`) VALUES (%s, %s, NOW(), %s);"
            self.cursor.execute(query, [imageId, data.get('lot_id'), data.get('categorie_id')])
            self.connection.commit()
            return data
        except Exception as e:
            logger.error(f"Error inserting decoupage_niveau2_controle: {e}")
            return None
    
    def insert_decoupage_niveau2_controle_by_decoupage_niveau2(self, decoupage_niveau2: dict, len_decoupage_niveau2: int):
        try:
            decoupage_niveau2_controle = self.get_decoupage_niveau2_controle_by_imageId(decoupage_niveau2['image_id'])
            if len(decoupage_niveau2_controle) > 0 and len_decoupage_niveau2 == len(decoupage_niveau2_controle):
                return True
            else:
                query = """INSERT INTO `decoupage_niveau2_controle` (
                `image_id`, `nomdecoupee`, `categorie_id`, `nbpage`, 
                `page_assembler`, `operateur_id`, `facturette`, 
                `mere`, `mere_assembler`, `lot_id`, `soussouscategorie_id`, `utilisateur_id`,
                `date_creation`
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());"""
                self.cursor.execute(query, [
                    decoupage_niveau2['image_id'], 
                    decoupage_niveau2['nomdecoupee'], 
                    decoupage_niveau2['categorie_id'], 
                    decoupage_niveau2['nbpage'], 
                    decoupage_niveau2['page_assembler'], 
                    decoupage_niveau2['operateur_id'], 
                    decoupage_niveau2['facturette'], 
                    decoupage_niveau2['mere'], 
                    decoupage_niveau2['mere_assembler'], 
                    decoupage_niveau2['lot_id'], 
                    decoupage_niveau2['soussouscategorie_id'], 
                    decoupage_niveau2['utilisateur_id']]
                )
                self.connection.commit()

            return True
        except Exception as e:
            logger.error(f"Error inserting decoupage_niveau2_controle_by_decoupage_niveau2: {e}")
            return False
