"""
Service de gestion des images et documents.

Ce module fournit des fonctionnalités pour:
- Localiser les fichiers images dans le système de fichiers
- Traiter les documents PDF et images avec Document AI
- Copier les fichiers vers les destinations appropriées
"""

import base64
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from services.logger import Logger

load_dotenv()
logger = Logger.get_logger()


class ImageService:
    """
    Service de gestion des images et documents.
    
    Gère la localisation, le traitement et la copie des fichiers
    images dans le système de fichiers de l'application.
    
    Attributes:
        IMAGE_A_TRAITER: Chemin de base pour les images à traiter.
        OLD_IMAGE_A_TRAITER: Chemin de l'ancien répertoire d'images.
        allowed_extensions: Liste des extensions de fichiers supportées.
    """
    
    # Configuration par défaut
    DEFAULT_ALLOWED_EXTENSIONS: list[str] = [
        '.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif'
    ]
    
    # Paramètres de retry pour les opérations fichiers
    MAX_COPY_ATTEMPTS: int = 5
    COPY_RETRY_DELAY: float = 0.6

    def __init__(self):
        """Initialise le service avec les chemins de configuration."""
        self.IMAGE_A_TRAITER = os.getenv(
            'IMAGE_A_TRAITER',
            r'//NAS/intranet images/IMAGES_A_TRAITER'
        )
        self.OLD_IMAGE_A_TRAITER = os.getenv(
            'OLD_IMAGE_A_TRAITER',
            r'//NAS/intranet images/NS_SU/IMAGES_A_TRAITER'
        )
        self.allowed_extensions = self.DEFAULT_ALLOWED_EXTENSIONS

    def get_image_path(
        self,
        img: dict,
        ext: str = "pdf",
        output_path: str = "",
        old_output_path: str = ""
    ) -> Path:
        """
        Localise le chemin d'un fichier image dans le système.
        
        Recherche le fichier dans plusieurs emplacements possibles:
        1. Répertoire principal (IMAGE_A_TRAITER)
        2. Ancien répertoire (OLD_IMAGE_A_TRAITER)
        3. Chemin de sortie spécifié
        
        Args:
            img: Dictionnaire contenant les métadonnées de l'image:
                - date_scan: Date de scan du document
                - client_nom: Nom du client
                - dossier_nom: Nom du dossier
                - exercice: Année d'exercice
                - lot_num: Numéro du lot
                - name: Nom du fichier (sans extension)
            ext: Extension du fichier (par défaut "pdf").
            output_path: Chemin de sortie alternatif.

        Returns:
            Chemin Path vers le fichier trouvé.
            
        Raises:
            FileNotFoundError: Si le fichier n'est trouvé dans aucun emplacement.
            
        Example:
            >>> service = ImageService()
            >>> path = service.get_image_path(
            ...     {"date_scan": "2024-01-15", "name": "DOC001", ...},
            ...     ext="pdf"
            ... )
        """
        # Parse de la date de scan
        date_scan = self._parse_date_scan(img['date_scan'])
        
        year = str(date_scan.year)
        month = str(date_scan.month).zfill(2)
        day = str(date_scan.day).zfill(2)
        
        # Construction du sous-chemin
        date_folder = f'{year}-{month}-{day}'
        relative_path = Path(
            img['client_nom'],
            img['dossier_nom'],
            str(img['exercice']),
            date_folder,
            str(img['lot_num'])
        )

        filename = f"{img['name']}.{ext}"
        original_filename = f"{img['originale']}.{ext}"

        # Tentative dans le répertoire principal
        if img.get('parent_name', ''):
            relative_path = Path(relative_path, img.get('parent_name', ''))

        source_path = Path(self.IMAGE_A_TRAITER) / relative_path / filename
        if self._file_exists(source_path):
            logger.debug(f"fichier trouver dans : {source_path}")
            return source_path
        
        logger.debug(f"fichier non trouver dans : {source_path}")
        # Tentative dans l'ancien répertoire
        source_path = Path(self.OLD_IMAGE_A_TRAITER) / relative_path / filename
        if self._file_exists(source_path):
            logger.debug(f"fichier trouver dans : {source_path}")
            return source_path

        logger.debug(f"fichier non trouver dans : {source_path}")
        # Tentative dans le répertoire de sortie
        if output_path:
            source_path = Path(output_path) / filename
            if self._file_exists(source_path):
                return source_path
                
        logger.debug(f"fichier non trouver dans : {source_path}")

        if old_output_path:
            source_path = Path(old_output_path) / filename
            if self._file_exists(source_path):
                return source_path

        logger.debug(f"fichier non trouver dans : {source_path}")
        source_path = Path(self.OLD_IMAGE_A_TRAITER) / relative_path / original_filename
        if self._file_exists(source_path):
            logger.debug(f"fichier trouver dans : {source_path}")
            return source_path

        raise FileNotFoundError(f"Fichier non trouvé: {filename}")

    def copy_the_image(
        self,
        image: dict,
        destination_path: str
    ) -> tuple[Path, bool]:
        """
        Copie un fichier image vers une destination avec gestion des erreurs.
        
        Implémente un mécanisme de retry pour gérer les erreurs de
        verrouillage de fichiers Windows.
        
        Args:
            image: Dictionnaire contenant les métadonnées de l'image:
                - path: Chemin source du fichier
                - name: Nom du fichier (sans extension)
            destination_path: Répertoire de destination.
            
        Returns:
            Tuple contenant:
                - Path: Chemin du fichier copié
                - bool: True si la copie a réussi
                
        Note:
            En cas d'échec après plusieurs tentatives, retourne le
            chemin source original avec False.
        """
        source_path = Path(image["path"])
        print("destination_path ", destination_path)
        dest_dir = Path(destination_path)
        
        # Création du répertoire de destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        if image.get('is_child', False):
            dest_file = dest_dir / f"{image.get('nom', '')}.{image.get('ext_image', 'pdf')}"
        else:
            dest_file = dest_dir / f"{image.get('name', '')}.{image.get('ext_image', 'pdf')}"
        
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_COPY_ATTEMPTS):
            try:
                shutil.copy2(source_path, dest_file)
                logger.debug(f"Fichier copié avec succès: {dest_file}")
                return dest_file, True
                
            except PermissionError as e:
                last_error = e
                logger.warning(
                    f"Tentative {attempt + 1}/{self.MAX_COPY_ATTEMPTS}: "
                    f"Permission refusée pour {source_path}"
                )
                
            except OSError as e:
                # Gestion des erreurs Windows (fichier en cours d'utilisation)
                if getattr(e, 'winerror', None) == 32 or "used by another process" in str(e):
                    last_error = e
                    logger.warning(
                        f"Tentative {attempt + 1}/{self.MAX_COPY_ATTEMPTS}: "
                        f"Fichier verrouillé {source_path}"
                    )
                else:
                    raise

            time.sleep(self.COPY_RETRY_DELAY)

        logger.error(
            f"Échec de copie après {self.MAX_COPY_ATTEMPTS} tentatives: {last_error}"
        )
        return source_path, False

    def process_child_images(
        self,
        child_images: list[dict],
        output_path: str
    ) -> list[dict]:
        """
        Traite une liste d'images enfants en les copiant vers le répertoire de sortie.
        
        Args:
            child_images: Liste de dictionnaires contenant les métadonnées des images.
            output_path: Répertoire de destination.
            
        Returns:
            Liste des images traitées avec succès (chemins mis à jour).
        """
        processed_images: list[dict] = []
        
        for child_image in child_images:
            try:
                # Localisation du fichier source
                self.get_image_path(child_image, ext="pdf", output_path=output_path)
                
                # Copie vers la destination
                dest_path, success = self.copy_the_image(child_image, output_path)
                
                if success:
                    child_image['path'] = str(dest_path)
                    processed_images.append(child_image)
                else:
                    logger.error(f"Échec de copie de l'image enfant: {child_image['name']}")
                    
            except Exception as e:
                logger.error(
                    f"Erreur lors du traitement de l'image enfant "
                    f"{child_image.get('name', 'unknown')}: {e}"
                )

        return processed_images

    @staticmethod
    def _parse_date_scan(date_scan) -> datetime:
        """
        Parse une date de scan en objet datetime.
        
        Args:
            date_scan: Date au format string ISO ou objet datetime.
            
        Returns:
            Objet datetime.
        """
        if isinstance(date_scan, str):
            return datetime.fromisoformat(date_scan.replace('Z', '+00:00'))
        return date_scan

    @staticmethod
    def _file_exists(path: Path) -> bool:
        """
        Vérifie si un fichier existe.
        
        Args:
            path: Chemin du fichier à vérifier.
            
        Returns:
            True si le fichier existe et est accessible.
        """
        try:
            path.stat()
            return True
        except (FileNotFoundError, OSError):
            return False
