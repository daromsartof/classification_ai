import asyncio
from dotenv import load_dotenv
from services.utils_service import UtilsService
from services.openai_service import OpenAIService
import pytesseract
from services.ocr_service import OCRService
from services.document_ai_service import DocumentAI
import os
import sys
from repositories.image_repository import ImageRepositorie
from services.image_service import ImageService
import json
from multiprocessing import Pool, cpu_count
import multiprocessing
from repositories.ai_separation_setting_repository import AiSeparationSettingRepository
from services import constant
from repositories.ai_separation_repository import AiSeparationRepository
import shutil
from datetime import datetime
from repositories.lot_repository import LotRepositorie
from repositories.categorie_repositorie import CategorieRepositorie
from repositories.decoupage_niveau2_repositorie import DecoupageNiveau2Repositorie
from functools import partial
from services.easy_ocr_service import EasyOcrService
import time
from services.validation_service import ValidationService
from repositories.logs_repository import LogsRepository
from collections import defaultdict
from PyPDF2 import PdfReader
from repositories.panier_reception_resipository import PanierReceptionRepository
from repositories.decoupage_niveau2_controle_repository import DecoupageNiveau2ControleRepositorie
from repositories.decoupage_niveau1_controle_repository import DecoupageNiveau1ControleRepositorie
from services.logger import Logger

logger = Logger.get_logger()
load_dotenv()
IMAGE_BASE = os.getenv("IMAGE_BASE", r"//NAS/intranet images/IMAGES_V2/images")
IMAGE_COMPTABILISEE_BASE = os.getenv("IMAGE_COMPTABILISEE_BASE", r"//NAS/images/Images comptabilisées")
easy_ocr_service = EasyOcrService()

class TerminatePoolException(Exception):
    def __init__(self, message):
        super().__init__(message)

def process_single_image(image_data, ai_separation_setting, prompt = None, is_training=False):
    ai_separation_repo = AiSeparationRepository()
    try:
        image_service = ImageService()
        # Re-fetch the latest ai_separation_setting at the start
        ai_separation_setting_repo = AiSeparationSettingRepository()
        ai_separation_setting = ai_separation_setting_repo.get_ai_separation_setting()
        decoupage_niveau1_controle_repos = DecoupageNiveau1ControleRepositorie()
        if ai_separation_setting.get('power', 1) != 1:
            logger.warning(f"Processing for image {image_data['name']} stopped")
            raise TerminatePoolException("Power Stopped")

        image_child = decoupage_niveau1_controle_repos.get_decoupage_niveau1_controle_by_imageId(image_data['id'])
        if len(image_child) >= 2:
            raise Exception(f"Image {image_data['name']} has more pages {len(image_child)}. Skipping.")
            """return
            for child_image in child_images:
                try:
                    source_path = self.get_image_path(child_image, ext="pdf", output_path=output_path)
                    dest_path, success = self.copy_the_image(child_image, output_path)
                    if success:
                        child_image['path'] = str(dest_path)
                        processed_images.append(child_image)
                    else:
                        logger.error(f"Failed to copy child image: {child_image['name']}")
                except Exception as e:
                    logger.error(f"Error processing child image {child_image['name']}: {str(e)}")
                
            raise Exception(f"Image {image_data['name']} has more pages {len(image_child)}. Skipping.")"""
        openai_service = OpenAIService()
        ocr_service = OCRService()
       
        utils_service = UtilsService()
        categorie_repo = CategorieRepositorie()
        
        image_repo = ImageRepositorie()
        decoupage_niveau2_repos = DecoupageNiveau2Repositorie()
        document_ai = DocumentAI()
        validation = ValidationService()
      
        lot_repo = LotRepositorie()
        
        date_scan = datetime.fromisoformat(image_data['date_scan'].replace('Z', '+00:00')) if isinstance(image_data['date_scan'], str) else image_data['date_scan']

        year = str(date_scan.year)
        month = str(date_scan.month).zfill(2)
        day = str(date_scan.day).zfill(2)
        output_path = f"{IMAGE_BASE}/{year}/{month}/{day}"
        image_comptabiliser_output_path = f"{IMAGE_COMPTABILISEE_BASE}/{image_data.get('client_nom', 'inconnu')}/{image_data.get('dossier_nom', 'inconnu')}/{image_data.get('exercice', 'inconnu')}"
        local_output_path = f"./outputs"
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        image_data['path'] = image_service.get_image_path(image_data, "pdf", output_path)
        logger.info(f"Processing image: {image_data['name']}")
        local_path, is_local_path = image_service.copy_the_image(image_data, local_output_path)
        logger.info(f"Local path: {local_path}")
        image_data["path"] = local_path
        reader = PdfReader(image_data["path"])
        num_page = len(reader.pages)
        if num_page > 10:
            raise Exception(f"Image {image_data['name']} has more than 10 pages ({num_page} pages). Skipping.")
        
        logger.info(f"Number of pages: {num_page}")
        
        path, page_number = asyncio.run(utils_service.convert_pdf_to_images(image_data["path"], local_output_path))
        logger.info(f"Converted PDF to image path: {path}, total pages: {page_number}")
        
        text = ""
        if ai_separation_setting.get('ocr_library', 'tesseract') == constant.ocr_library.get('easyocr', ''):
            logger.info(f'Debut extraction avec easyocr for {image_data["name"]}')
            text = easy_ocr_service.extract_text(path)
            logger.info(f"Fin extraction avec easyocr for {image_data['name']}")
            
        elif ai_separation_setting.get('ocr_library', 'tesseract') == constant.ocr_library.get('document_ai', ''):
            logger.info(f"Debut Extraction document ai for {image_data['name']}")
            document = asyncio.run(image_service.process_image_file(path))
            if not document:
                raise Exception(f"Error processing image {image_data['name']}")
            text = document.text
            
        elif ai_separation_setting.get('ocr_library', 'tesseract') == constant.ocr_library.get('custom_pytesseract', ''): 
            logger.info(f"Debut extraction text custom pytesseract for {image_data['name']}")
            text = ocr_service.extract_from_image(path)
            logger.info(f"Fin extraction text pytesseract for {image_data['name']}")
            
        else:
            logger.info(f"Debut extraction text pytesseract for {image_data['name']}")
            text = pytesseract.image_to_string(path, lang='fra')
            logger.info(f"Fin extraction text pytesseract for {image_data['name']}")
        
        logger.info(f"Debut extraction de categorie avec chat gpt for {image_data['name']}")
        logger.info(f"model used: {ai_separation_setting.get('model')}")
        
        response = openai_service.categorisation(text, image_data, model=ai_separation_setting.get('model', 'gpt-4o-mini'), prompt_system=prompt or ai_separation_setting.get('prompt_systeme', None))
        logger.info(f"Fin extraction de categorie avec chat gpt for {image_data['name']}")
        
        data = {}
        try:
            if isinstance(response, dict):
                data = {
                    #"categorie_id": 10 if (response.get('ID', '') == 14 or response.get('ID', '') == 18) else response.get('ID', ''),
                    "categorie_id": 10 if (response.get('ID', '') == 14) else response.get('ID', ''),
                    "sous_categorie": response.get('SousCategorie', None),
                    "sous_sous_categorie": response.get('SousSousCategorie', None),
                    "sous_categorie_id": response.get('SousCategorie_ID', None),
                    "sous_sous_categorie_id": response.get('SousSousCategorie_ID', None),
                    "explication":  f"{response.get('Explanation', '')}, Emetteur: {response.get('Emetteur', '')}, Recepteur: {response.get('Recepteur', '')}; {"Basculer vers la catégorie fournisseur." if (response.get('ID', '') == 14) else ""}",
                    "image_id": image_data['id'] or None, 
                    "ocr_content": "",
                    "SirenEmetteur": response.get('SirenEmetteur', None),
                    "ratio": int(response.get('ratio', 0)),
                    "Emetteur": response.get('Emetteur', None), 
                    "Recepteur": response.get('Recepteur', None)
                    #"ocr_content": "".join(text.splitlines())[:500]   Limit to 500 characters
                }
            else:
                raise Exception(f"Error extracting categorie for {image_data['name']}")
            
            
            # validation de la categorie
            if response.get('ID', None) == constant.categirie_id.get('client', None) or response.get('ID', None) == constant.categirie_id.get('fournisseur', None):
                data = validation.validation_manuel(data, image_data, ocr_content=text)
            
            if validation.is_blank_page(text):
                data['categorie_id'] = constant.categirie_id.get('illisible', None)
                data['ratio'] = 100
                data['explication'] += " (Page blanche détectée) "
            
            ### Validation avec contexte personnalisé
            categorie = validation.validation_with_custom_error(image_data, data.get('Emetteur', ''), data.get('Recepteur', ''))
            if categorie:
                data['categorie_id'] = categorie
                data['explication'] = f"le document est validé manuellement avec la correction du contexte personnalisé data['ratio']={data['ratio']} (Validation avec contexte personnalisé)"
                data['ratio'] = 95

            output_ocr_path = f"{output_path}/{image_data['name']}{ai_separation_setting.get('prefix', '')}.ocr"
            with open(output_ocr_path, 'w', encoding='utf-8') as file:
                file.write(text)

            #if (not categorie_repo.is_valid_categorie_relation(data.get('categorie_id', None), data.get('sous_categorie_id', None), data.get('sous_sous_categorie_id', None))):
            data['sous_categorie_id']=  None
            data['sous_sous_categorie_id'] = None
                
            decoupage_niveau2 = decoupage_niveau2_repos.insert_decoupage_niveau2(image_data['id'], {
                "num_page": num_page,
                "image_id": image_data['id'], 
                "lot_id": image_data['lot_id'],
                "categorie_id": data.get('categorie_id', None),
                "sous_categorie_id": data.get('sous_categorie_id', None),
                "sous_sous_categorie_id": data.get('sous_sous_categorie_id', None)
                #"status_new": constant.status_new.get('finished', 6)
            })

            """lot_update = lot_repo.update_lot(image_data['lot_id'], {
                "status_new": constant.status_new.get('finished', 6)
            })
            if not lot_update:
                raise Exception(f"Error updating lot for {image_data['name']}")"""

            data['explication'] += decoupage_niveau2.get('explication', "")
            
            ai_separation = ai_separation_repo.add_ai_separation(data)
            
            if not ai_separation:
                raise Exception(f"Error adding ai_separation for {image_data['name']}")
            
            # Update image with new categorie and status_new
            image_updated = {
                "id": image_data.get('id'),
                "categorie_id": image_data.get('categorie_id'),
                "lot_id": image_data.get('lot_id'),
                "status_new": image_data.get('status_new')
            }
            if(data.get("categorie_id") != constant.categirie_id.get('jocker', 49) and data.get("categorie_id") != constant.categirie_id.get('illisible', 18)):
                image_updated = image_repo.update_image(image_data['id'], data, status=constant.status_new.get('finished', 6))
                
                if not image_updated:
                    raise Exception(f"Error updating image for {image_data['name']}")
                try:
                    log_repo = LogsRepository()
                    decoupage_niveau2_controle_repos = DecoupageNiveau2ControleRepositorie()
                    decoupage_niveau2_controle_repos.insert_decoupage_niveau2(image_updated['id'], image_updated)
                    log_repo.log_action(utilisateur_id=constant.genz_user_id, image_id=image_updated['id'])
                    
                except Exception as e:
                    logger.warning(f"Error logging action for image {image_data['name']}: {str(e)}")
                    
            # Copy original file to output folder with retries to avoid Windows file lock issues
            copy_attempts = 0
            max_attempts = 5
            last_error = None
            
            while copy_attempts < max_attempts:
                try:
                    shutil.copy2(image_data['path'], output_path)
                    if(data.get("categorie_id") != constant.categirie_id.get('jocker', 49) 
                       and data.get("categorie_id") != constant.categirie_id.get('illisible', 18)):
                        if not os.path.exists(image_comptabiliser_output_path):
                            os.makedirs(image_comptabiliser_output_path)
                        shutil.copy2(image_data['path'], image_comptabiliser_output_path)
                    last_error = None
                    break
                except PermissionError as e:
                    last_error = e
                except OSError as e:
                    # Handle WinError 32 (file in use) and similar transient errors
                    if getattr(e, 'winerror', None) == 32 or "used by another process" in str(e):
                        last_error = e
                    else:
                        raise
                copy_attempts += 1
                time.sleep(0.6)
                
            if last_error is not None:
                logger.warning(f"Warning: could not copy file after {max_attempts} attempts: {last_error}")
            
            #if(data.get("categorie_id") != constant.categirie_id.get('jocker', 49) and data.get("categorie_id") != constant.categirie_id.get('illisible', 18)) and last_error is None:
            #    os.remove(image_data['path'])
            logger.info(f"Successfully processed {image_data['name']}")
            
            if(is_local_path):
                os.remove(image_data['path'])
                os.remove(path)
            logger.info("=============================================================================================================")
            
            return {
                "image_id": image_updated['id'],
                "categorie_id": image_updated['categorie_id'],
                "lot_id": image_updated['lot_id'],
                "status_new": image_updated['status_new']
            }
            
        except Exception as e:
            logger.error(f"Error processing {image_data['name']}: {str(e)}")
            raise e
            
    except Exception as e:
        logger.critical(f"Critical error processing {image_data['name']}: {str(e)}")
        if isinstance(e, TerminatePoolException):
            raise e        
        return {
            "image_id": image_data['id'],
            "categorie_id": None,
            "lot_id": image_data['lot_id'],
            "status_new": 4
        }

def main():
    try:
        image_repo = ImageRepositorie()
        image_service = ImageService()
        lot_repo = LotRepositorie()
        logs_repo = LogsRepository()
        panier_reception_repo = PanierReceptionRepository()
        ai_separation_setting_repo = AiSeparationSettingRepository()
        ai_separation_setting = ai_separation_setting_repo.get_ai_separation_setting()
        if not ai_separation_setting or ai_separation_setting.get('power', 1) != 1:
            logger.warning("AI Separation is not enabled or power is off")
            return
        images = image_repo.get_image_to_process()
        num_processes = ai_separation_setting.get('thread_number', 1)
        logger.info(f"Starting processing with {num_processes} processes")
        logger.info(f"Total images to process: {len(images)}")
        with Pool(processes=num_processes) as pool:
            # Map the work to the pool with partial to include ai_separation_setting
            process_with_settings = partial(process_single_image, ai_separation_setting=ai_separation_setting, prompt=ai_separation_setting.get('prompt_systeme', None))
            results = pool.map(process_with_settings, images)
        failed = 0
        successful = 0
        lot_success = defaultdict(int)
        for result in results:
            if result and result.get('status_new', 6) == constant.status_new.get("finished", 6):
                successful += 1
                lot_success[result['lot_id']] += 1
            else:
                failed += 1
                    
        for key in lot_success:
            numbre_image_ok = image_repo.count_status_finished_by_lot(int(key))
            if numbre_image_ok == lot_success[key]:
                try:
                    lot_repo.update_lot(int(key), {
                        "status_new": constant.status_new.get('finished', 6)
                    })
                    logs_repo.log_action(utilisateur_id=constant.genz_user_id, lot_id=int(key))
                    logger.debug(f"Updating or creating panier_reception for lot_id: {key}")
                    panier_reception_repo.update_or_create_panier_reception(int(key))
                except Exception as e:
                    logger.error(f"Error updating lot {key} to finished: {str(e)}")
            
        logger.info(f"Processing complete!")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        
    except Exception as e:
        logger.critical("Terminating all workers due to critical error!")
        logger.error(f"Error in main process: {str(e)}")
        pool.terminate()
        pool.join()
        sys.exit(1)
    finally:
        from colorama import Back, Fore, Style, deinit, init
        print(Fore.GREEN + Back.WHITE + 'Task is Done' + Style.RESET_ALL)

if __name__ == "__main__":
    # Set the start method for multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    main()
