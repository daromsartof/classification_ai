"""
Point d'entrée principal pour le traitement par lots des images.

Ce module orchestre le pipeline de classification automatique des documents:
1. Récupération des images à traiter depuis la base de données
2. Extraction du texte via OCR
3. Classification via OpenAI
4. Validation et affinement des résultats
5. Mise à jour de la base de données et copie des fichiers
"""

import asyncio
import multiprocessing
import os
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Optional

from numpy import imag
import pytesseract
from dotenv import load_dotenv
from PyPDF2 import PdfReader

from repositories import ai_ocr_content_repository
from repositories.ai_separation_repository import AiSeparationRepository
from repositories.ai_separation_setting_repository import AiSeparationSettingRepository
from repositories.categorie_repositorie import CategorieRepositorie
from repositories.decoupage_niveau1_controle_repository import DecoupageNiveau1ControleRepositorie
from repositories.decoupage_niveau2_controle_repository import DecoupageNiveau2ControleRepositorie
from repositories.decoupage_niveau2_repositorie import DecoupageNiveau2Repositorie
from repositories.image_repository import ImageRepositorie
from repositories.logs_repository import LogsRepository
from repositories.lot_repository import LotRepositorie
from repositories.panier_reception_resipository import PanierReceptionRepository
from services import constant
from services.constant import CategorieId, OcrLibrary, StatusNew
from services.easy_ocr_service import EasyOcrService
from services.image_service import ImageService
from services.logger import Logger
from services.ocr_service import OCRService
from services.openai_service import OpenAIService
from services.openai_service_vision import OpenAIServiceVision
from services.utils_service import UtilsService
from services.validation_service import ValidationService
from repositories.ai_ocr_prompts_repository import AiOcrPromptsRepository
from repositories.ai_ocr_content_repository import AiOcrContentRepository
from repositories.ai_ocr_content_docs_repository import AiOcrContentDocsRepository
import json

# Configuration
load_dotenv()
logger = Logger.get_logger()

IMAGE_BASE = os.getenv("IMAGE_BASE", r"//NAS/intranet images/IMAGES_V2/images")
IMAGE_COMPTABILISEE_BASE = os.getenv(
    "IMAGE_COMPTABILISEE_BASE",
    r"//NAS/images/Images comptabilisées"
)

# Service OCR global (pour éviter la réinitialisation)
easy_ocr_service = EasyOcrService()


class TerminatePoolException(Exception):
    """Exception levée pour arrêter le pool de workers."""
    pass


@dataclass
class ProcessingResult:
    """Résultat du traitement d'une image."""
    image_id: int
    categorie_id: Optional[int]
    lot_id: int
    status_new: int
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ProcessingPaths:
    """Chemins utilisés pour le traitement."""
    output_path: str
    comptabiliser_output_path: str
    local_output_path: str
    old_output_path: str


class ImageProcessor:
    """
    Processeur d'images pour la classification automatique.
    
    Gère le pipeline complet de traitement d'une image:
    - Extraction du texte
    - Classification IA
    - Validation
    - Persistance des résultats
    """
    
    # Limites de traitement
    MAX_PAGES: int = 10
    MAX_CHILD_IMAGES: int = 2
    
    # Paramètres de copie
    MAX_COPY_ATTEMPTS: int = 5
    COPY_RETRY_DELAY: float = 0.6

    def __init__(self, ai_settings: dict):
        """
        Initialise le processeur avec les paramètres IA.
        
        Args:
            ai_settings: Configuration de la séparation IA.
        """
        self.ai_settings = ai_settings
        self._init_services()
        self._init_repositories()

    def _init_services(self) -> None:
        """Initialise les services nécessaires."""
        self.image_service = ImageService()
        self.openai_service = OpenAIService()
        self.openai_vision_service = OpenAIServiceVision()
        self.ocr_service = OCRService()
       
        self.utils_service = UtilsService()
        self.validation_service = ValidationService()

    def _init_repositories(self) -> None:
        """Initialise les repositories nécessaires."""
        self.ai_separation_repo = AiSeparationRepository()
        self.image_repo = ImageRepositorie()
        self.ai_ocr_prompts_repo = AiOcrPromptsRepository() 
        self.ai_ocr_content_repository = AiOcrContentRepository()
        self.ai_ocr_content_docs_repository = AiOcrContentDocsRepository()
        self.decoupage_niveau2_repo = DecoupageNiveau2Repositorie()
        self.decoupage_niveau1_controle_repo = DecoupageNiveau1ControleRepositorie()
        self.decoupage_niveau2_controle_repo = DecoupageNiveau2ControleRepositorie()

    def process(
        self,
        image_data: dict,
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """
        Traite une image et retourne le résultat.
        
        Args:
            image_data: Métadonnées de l'image à traiter.
            prompt: Prompt personnalisé (optionnel).
            
        Returns:
            Résultat du traitement.
        """
        try:
            # Vérification du statut du service
            self._check_service_power()
            # Préparation des chemins
            paths = self._prepare_paths(image_data)
            
            # Localisation et copie du fichier
            local_path, is_local = self._prepare_image_file_with_conversion(image_data, paths)
            
            resultat = self._analyse_du_document(local_path, image_data)

            self._persist_results(resultat, image_data)
            
            # Nettoyage
            if is_local:
                self._cleanup_local_files(local_path)
            
            logger.info(f"Image traitée avec succès: {image_data['name']}")
            logger.info("=" * 80)
            
            return ProcessingResult(
                image_id=image_data['id'],
                categorie_id=image_data['categorie_id'],
                lot_id=image_data['lot_id'],
                status_new=image_data['status_new']
            )

        except TerminatePoolException:
            raise
        except Exception as e:
            logger.critical(f"Erreur critique pour {image_data['name']}: {e}")
            
            return ProcessingResult(
                image_id=image_data['id'],
                categorie_id=None,
                lot_id=image_data['lot_id'],
                status_new=StatusNew.ERROR,
                success=False,
                error_message=str(e)
            )

    def _check_service_power(self) -> None:
        """Vérifie si le service est actif."""
        settings_repo = AiSeparationSettingRepository()
        current_settings = settings_repo.get_ai_separation_setting(setting_id=2)
        
        if current_settings.get('power', 1) != 1:
            logger.warning("Service désactivé - arrêt du traitement")
            raise TerminatePoolException("Service désactivé")

    def _prepare_paths(self, image_data: dict) -> ProcessingPaths:
        """Prépare les chemins de sortie."""
        date_scan = self._parse_date(image_data['date_scan'])
        
        year = str(date_scan.year)
        month = str(date_scan.month).zfill(2)
        day = str(date_scan.day).zfill(2)
        
        output_path = f"{IMAGE_BASE}/images/{year}/{month}/{day}"
        old_output_path = f"{IMAGE_BASE}/IMAGES/{year}{month}{day}"
        comptabiliser_output_path = (
            f"{IMAGE_COMPTABILISEE_BASE}/"
            f"{image_data.get('client_nom', 'inconnu')}/"
            f"{image_data.get('dossier_nom', 'inconnu')}/"
            f"{image_data.get('exercice', 'inconnu')}"
        )
        
        local_output_path = "./outputs"
        
        # Création des répertoires
        os.makedirs(output_path, exist_ok=True)
        
        return ProcessingPaths(
            output_path=output_path,
            comptabiliser_output_path=comptabiliser_output_path,
            local_output_path=local_output_path,
            old_output_path=old_output_path
        )

    def _prepare_image_file_with_conversion(
        self,
        image_data: dict,
        paths: ProcessingPaths
    ) -> tuple[str, bool]:
        """Prépare le fichier image pour le traitement."""
        # Localisation du fichier source
        image_data['path'] = self.image_service.get_image_path(
            image_data, 
            image_data.get('ext_image', 'pdf'), 
            paths.output_path, 
            paths.old_output_path
        )
        
        logger.info(f"Traitement de l'image: {image_data['name']}")
        
        # Copie locale
        local_path, is_local = self.image_service.copy_the_image(
            image_data, paths.local_output_path
        )
        
        logger.info(f"Chemin local: {local_path}")
        image_data["path"] = local_path
        
        return str(local_path), is_local

    def _get_page_count(self, path: str, name: str) -> int:
        """Compte le nombre de pages du PDF."""
        reader = PdfReader(path)
        num_pages = len(reader.pages)
        
        logger.info(f"Nombre de pages: {num_pages}")
        return num_pages

    def _extract_text(self, image_path: str, name: str) -> str:
        """Extrait le texte du document via OCR."""
        ocr_library = self.ai_settings.get('ocr_library', 'tesseract')
        
        # Conversion PDF -> Image
        converted_path, _ = asyncio.run(
            self.utils_service.convert_pdf_to_images(
                image_path,
                os.path.dirname(image_path)
            )
        )
        
        logger.info(f"Image convertie: {converted_path}")
        
        # Extraction selon la bibliothèque configurée
        if ocr_library == OcrLibrary.EASYOCR.value:
            logger.info(f"Extraction EasyOCR pour {name}")
            text = easy_ocr_service.extract_text(converted_path)
            
        elif ocr_library == OcrLibrary.DOCUMENT_AI.value:
            logger.info(f"Extraction Document AI pour {name}")
            document = asyncio.run(
                self.image_service.process_image_file(converted_path)
            )
            if not document:
                raise ValueError(f"Échec Document AI pour {name}")
            text = document.text
            
        elif ocr_library == OcrLibrary.CUSTOM_PYTESSERACT.value:
            logger.info(f"Extraction Pytesseract personnalisé pour {name}")
            text = self.ocr_service.extract_from_image(converted_path)
            
        else:
            logger.info(f"Extraction Pytesseract standard pour {name}")
            text = pytesseract.image_to_string(converted_path, lang='fra')
        
        logger.info(f"Extraction terminée pour {name}")
        return text


    def _persist_results(
        self,
        resultat: dict,
        image_data: dict
    ) -> dict:
        """Persiste les résultats en base de données."""
        
        ai_ocr_content_docs = self.ai_ocr_content_docs_repository.createAiOcrContentDocs(
            {
                "image_id": image_data['id'] if image_data else None,
                "content": resultat.get("data", ""),
                "categorie_id": resultat.get("categorie", 49),
                "status": resultat.get("status", "green"),
                "json_data": json.dumps({
                    "num_facture": resultat.get("num_facture", 0)
                })
            }
        )

        if not ai_ocr_content_docs:
            raise ValueError(f"Échec d'insertion ai_ocr_content_docs pour {image_data['name']}")

        return ai_ocr_content_docs

    def _log_image_action(self, image_updated: dict) -> None:
        """Log l'action sur l'image."""
        try:
            log_repo = LogsRepository()
            log_repo.log_action(
                utilisateur_id=constant.GENZ_USER_ID,
                image_id=image_updated['id']
            )
        except Exception as e:
            logger.warning(f"Erreur de logging pour image {image_updated['id']}: {e}")

    def _copy_files(
        self,
        image_data: dict,
        paths: ProcessingPaths,
        data: dict
    ) -> None:
        """Copie les fichiers vers les destinations finales."""
        last_error: Optional[Exception] = None
        
        for attempt in range(self.MAX_COPY_ATTEMPTS):
            try:
                logger.info("copy image")
                shutil.copy2(image_data['path'], paths.output_path)
                
                # Copie vers comptabilisé si nécessaire
      
                os.makedirs(paths.comptabiliser_output_path, exist_ok=True)
                shutil.copy2(image_data['path'], paths.comptabiliser_output_path)
                
                return
                
            except PermissionError as e:
                last_error = e
            except OSError as e:
                if getattr(e, 'winerror', None) == 32 or "used by another process" in str(e):
                    last_error = e
                else:
                    raise
            
            time.sleep(self.COPY_RETRY_DELAY)
        
        if last_error:
            logger.warning(
                f"Échec de copie après {self.MAX_COPY_ATTEMPTS} tentatives: {last_error}"
            )

    def _cleanup_local_files(self, local_path: str) -> None:
        """Nettoie les fichiers locaux temporaires."""
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            
            # Suppression de l'image convertie
            base_path = Path(local_path)
            converted_path = base_path.parent / f"{base_path.stem}.ia.jpeg"
            if converted_path.exists():
                os.remove(converted_path)
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage: {e}")

    def _analyse_du_document(self, local_path: str, image_data: dict) -> dict:
        """Analyse le document."""
        logger.info(f"Analyse du document pour {image_data['name']}")
        logger.info(f"Modèle utilisé: {self.ai_settings.get('model')}")
        
        response = self.openai_vision_service.analyse_du_document(
            prompt_system=self.ai_settings.get('prompt_systeme'),
            image_path=image_data['path'],
            image=image_data,
            model=self.ai_settings.get('model', 'gpt-4o-mini'),
        )
        logger.info(f"Analyse du document terminée pour {image_data['name']}")
        return response

    @staticmethod
    def _parse_date(date_value) -> datetime:
        """Parse une date depuis différents formats."""
        if isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        return date_value


def process_single_image(
    image_data: dict,
    ai_separation_setting: dict,
    prompt: Optional[str] = None,
    is_training: bool = False
) -> dict:
    """
    Fonction de traitement d'une image unique (point d'entrée pour le multiprocessing).
    
    Args:
        image_data: Métadonnées de l'image.
        ai_separation_setting: Configuration IA.
        prompt: Prompt personnalisé (optionnel).
        is_training: Mode entraînement (non utilisé actuellement).
        
    Returns:
        Dictionnaire contenant le résultat du traitement.
    """
    processor = ImageProcessor(ai_separation_setting)
    result = processor.process(image_data, prompt)
    
    return {
        "image_id": result.image_id,
        "categorie_id": result.categorie_id,
        "lot_id": result.lot_id,
        "status_new": result.status_new
    }


def main() -> None:
    """
    Point d'entrée principal pour le traitement par lots.
    
    Orchestre le traitement parallèle des images en attente.
    """
    pool: Optional[Pool] = None
    
    try:
        # Initialisation des repositories
        image_repo = ImageRepositorie()
        settings_repo = AiSeparationSettingRepository()
        
        # Récupération des paramètres
        ai_settings = settings_repo.get_ai_separation_setting(setting_id=3)
        
        if not ai_settings or ai_settings.get('power', 1) != 1:
            logger.warning("Service IA désactivé ou non configuré")
            return
        
        # Récupération des images à traiter
        images = image_repo.get_image_to_process(for_analyse=True)
       
        num_processes = ai_settings.get('thread_number', 1)
        
        logger.info(f"Démarrage du traitement avec {num_processes} processus")
        logger.info(f"Images à traiter: {len(images)}")
        
        # Traitement parallèle
        with Pool(processes=num_processes) as pool:
            process_func = partial(
                process_single_image,
                ai_separation_setting=ai_settings,
                prompt=ai_settings.get('prompt_systeme')
            )
            results = pool.map(process_func, images)
        
        # Analyse des résultats
        successful = len(results)
        
        # Résumé
        logger.info("=" * 50)
        logger.info("TRAITEMENT TERMINÉ")
        logger.info(f"Succès: {successful}")
        logger.info("=" * 50)

    except Exception as e:
        logger.critical(f"Erreur fatale: {e}")
        if pool:
            pool.terminate()
            pool.join()
        sys.exit(1)
        
    finally:
        from colorama import Back, Fore, Style
        print(Fore.GREEN + Back.WHITE + 'Traitement terminé' + Style.RESET_ALL)


if __name__ == "__main__":
    # Configuration du multiprocessing pour Windows
    multiprocessing.set_start_method('spawn', force=True)
    
    while True:
        main()
        logger.info("Sleeping for 2 minutes...")

        for i in range(2, 0, -1):
            logger.info(f"{i} minutes remaining...")
            time.sleep(60)

        logger.info("Done!")
