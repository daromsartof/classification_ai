from services.database_service import DatabaseService
from repositories.base_repo import BaseRepo
from repositories.decoupage_niveau2_controle_repository import DecoupageNiveau2ControleRepositorie
from services.logger import Logger

logger = Logger.get_logger()

class DecoupageNiveau2Repositorie(BaseRepo):
    def __init__(self):
        super().__init__()
        
    def get_decoupage_niveau2_by_imageId(self, imageId: int) -> dict:
        try:
            query = "select * from decoupage_niveau2 where image_id = %s"
            self.cursor.execute(query, [imageId])
            res = self.cursor.fetchall() or []
            return res
        except Exception as e:
            logger.error(f"Error fetching decoupage_niveau2 by id: {e}")
            return None
    
    def insert_decoupage_niveau2(self, imageId: int, data: dict):
        try:
            decoupage_niveau2 = self.get_decoupage_niveau2_by_imageId(imageId)
            if len(decoupage_niveau2) > 0:
               data['explication'] = f"l'image a déjà été classée"

               for decoupage in decoupage_niveau2:
                decoupage_niveau2_controle_repo = DecoupageNiveau2ControleRepositorie()
                decoupage_niveau2_controle_repo.insert_decoupage_niveau2_controle_by_decoupage_niveau2({
                    "image_id": decoupage.get('image_id', None),
                    "nomdecoupee": decoupage.get('nomdecoupee', None),
                    "categorie_id": decoupage.get('categorie_id', None),
                    "nbpage": decoupage.get('nbpage', None),
                    "page_assembler": decoupage.get('page_assembler', None),
                    "operateur_id": decoupage.get('operateur_id', None),
                    "facturette": decoupage.get('facturette', None),
                    "mere": decoupage.get('mere', None),
                    "mere_assembler": decoupage.get('mere_assembler', None),
                    "lot_id": decoupage.get('lot_id', None),
                    "soussouscategorie_id": decoupage.get('soussouscategorie_id', None),
                    "utilisateur_id": decoupage.get('utilisateur_id', None),
                }, len(decoupage_niveau2))

            else:
                query = "INSERT INTO `decoupage_niveau2` (`image_id`, `nomdecoupee`, `lot_id`, `date_creation`, `categorie_id`, `nbpage`, `mere`) VALUES (%s, %s, %s, NOW(), %s, %s, %s);"
                self.cursor.execute(query, [imageId, data.get('nomdecoupee'), data.get('lot_id'), data.get('categorie_id'), data.get('num_page'), data.get('mere')])
                self.connection.commit()

                query = "INSERT INTO `decoupage_niveau2_controle` (`image_id`, `nomdecoupee`, `lot_id`, `date_creation`, `categorie_id`, `nbpage`, `mere`) VALUES (%s, %s, %s, NOW(), %s, %s, %s);"
                self.cursor.execute(query, [imageId, data.get('nomdecoupee'), data.get('lot_id'), data.get('categorie_id'), data.get('num_page'), data.get('mere')])
                self.connection.commit()
            return data
        except Exception as e:
            logger.error(f"Error inserting decoupage_niveau2: {e}")
            return None