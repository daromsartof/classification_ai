"""
Service utilitaire pour les opérations communes.

Ce module fournit des fonctionnalités transversales utilisées par
plusieurs autres services, notamment:
- Conversion de PDF en images
- Scan de répertoires pour trouver des images
- Récupération des listes de tiers (fournisseurs/clients)
"""

import os
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
from PIL import Image

from repositories.tiers_repository import TiersRepository
from services.logger import Logger
from services.opencv_service import OpenCvService

logger = Logger.get_logger()


class UtilsService:
    """
    Service utilitaire regroupant des fonctions communes.
    
    Cette classe centralise les opérations fréquemment utilisées
    par d'autres services de l'application.
    """
    
    # Dimensions A4 en pouces
    A4_WIDTH_INCH: float = 8.27
    A4_HEIGHT_INCH: float = 11.69
    
    # Extensions d'images supportées par défaut
    DEFAULT_IMAGE_EXTENSIONS: list[str] = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf'
    ]

    async def convert_pdf_to_images(
        self,
        pdf_path: str,
        output_dir: str,
        options: Optional[dict] = None
    ) -> tuple[str, int]:
        """
        Convertit un fichier PDF en image(s).
        
        Extrait la première page du PDF et la convertit en image JPEG,
        avec correction automatique de l'orientation via OCR.
        
        Args:
            pdf_path: Chemin vers le fichier PDF source.
            output_dir: Répertoire de destination pour l'image générée.
            options: Options de conversion optionnelles:
                - format (str): Format de sortie ('jpeg' par défaut)
                - quality (int): Qualité de compression (90 par défaut)
                - density (int): Résolution en DPI (300 par défaut)
                
        Returns:
            Tuple contenant:
                - str: Chemin de l'image générée (ou chaîne vide si échec)
                - int: Nombre total de pages dans le PDF (ou 0 si échec)
                
        Example:
            >>> utils = UtilsService()
            >>> path, pages = await utils.convert_pdf_to_images(
            ...     "document.pdf", 
            ...     "./output"
            ... )
            >>> print(f"Image: {path}, Pages: {pages}")
        """
        try:
            options = options or {}
            
            # Options avec valeurs par défaut
            image_format = options.get('format', 'jpeg')
            quality = options.get('quality', 90)
            density = options.get('density', 300)

            # Calcul des dimensions en pixels
            width = round(self.A4_WIDTH_INCH * density)
            height = round(self.A4_HEIGHT_INCH * density)

            # Création du répertoire de sortie
            os.makedirs(output_dir, exist_ok=True)

            base_name = Path(pdf_path).stem

            # Conversion PDF vers images en mémoire
            images = convert_from_path(pdf_path, dpi=density, size=(width, height))

            if not images:
                logger.warning(f"Aucune image extraite du PDF: {pdf_path}")
                return "", 0

            # Sauvegarde de la première page
            new_filename = f"{base_name}.ia.{image_format}"
            new_path = os.path.join(output_dir, new_filename)

            images[0].save(new_path, format=image_format.upper(), quality=quality)
            images[0].close()

            # Correction de l'orientation
            opencv_service = OpenCvService()
            opencv_service.rotate_image(new_path)

            logger.info(f"PDF converti avec succès: {new_path} ({len(images)} pages)")
            return new_path, len(images)

        except Exception as e:
            logger.error(f"Erreur lors de la conversion PDF en images: {e}")
            return "", 0

    def get_images_from_directory(
        self,
        directory: str,
        allowed_extensions: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Scanne un répertoire pour trouver des fichiers images.
        
        Parcourt récursivement le répertoire et ses sous-répertoires
        pour collecter les fichiers avec des extensions autorisées.
        
        Args:
            directory: Chemin du répertoire à scanner.
            allowed_extensions: Liste des extensions autorisées.
                Si None, utilise DEFAULT_IMAGE_EXTENSIONS.
                
        Returns:
            Liste de dictionnaires contenant les métadonnées de chaque image:
                - path (str): Chemin absolu du fichier
                - name (str): Nom du fichier sans extension
                - size (int): Taille en octets
                - created (float): Timestamp de création
                - modified (float): Timestamp de modification
                - relative_path (str): Chemin relatif au répertoire scanné
                - extension (str): Extension du fichier
                
        Example:
            >>> utils = UtilsService()
            >>> images = utils.get_images_from_directory("./documents")
            >>> for img in images:
            ...     print(f"{img['name']}: {img['size']} bytes")
        """
        if allowed_extensions is None:
            allowed_extensions = self.DEFAULT_IMAGE_EXTENSIONS
            
        logger.info(f"Scan du répertoire: {directory}")
        images: list[dict] = []

        # Vérification de l'existence du répertoire
        if not os.path.exists(directory):
            logger.warning(f"Répertoire inexistant: {directory}")
            return images

        # Lecture du contenu du répertoire
        try:
            items = os.listdir(directory)
        except OSError as e:
            logger.error(f"Erreur de lecture du répertoire {directory}: {e}")
            return images

        logger.info(f"{len(items)} éléments trouvés dans le répertoire")

        # Traitement de chaque élément
        for item in items:
            file_path = os.path.join(directory, item)
            
            try:
                stat = os.stat(file_path)
            except OSError as e:
                logger.error(f"Erreur d'accès à {file_path}: {e}")
                continue

            # Traitement récursif des sous-répertoires
            if os.path.isdir(file_path):
                logger.debug(f"Sous-répertoire trouvé: {item}")
                sub_dir_images = self.get_images_from_directory(
                    file_path, 
                    allowed_extensions
                )
                images.extend(sub_dir_images)
                
            # Traitement des fichiers avec extension autorisée
            elif os.path.isfile(file_path):
                ext = os.path.splitext(item)[1].lower()
                
                if ext in allowed_extensions:
                    logger.debug(f"Image trouvée: {item}")
                    images.append({
                        'path': file_path,
                        'name': os.path.splitext(item)[0],
                        'size': stat.st_size,
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime,
                        'relative_path': os.path.relpath(file_path, directory),
                        'extension': ext
                    })
                else:
                    logger.debug(f"Fichier ignoré (extension {ext}): {item}")

        logger.info(f"{len(images)} images trouvées dans {directory}")
        return images

    def getFournisseurAndClientsList(
        self,
        dossier_id: Optional[int]
    ) -> tuple[str, str]:
        """
        Récupère les listes formatées des fournisseurs et clients d'un dossier.
        
        Interroge la base de données pour obtenir les tiers associés
        au dossier et les formate en chaînes de caractères.
        
        Args:
            dossier_id: Identifiant du dossier.
            
        Returns:
            Tuple contenant:
                - str: Liste des fournisseurs au format "[ nom1, nom2, ... ]"
                - str: Liste des clients au format "[ nom1, nom2, ... ]"
                
        Example:
            >>> utils = UtilsService()
            >>> fournisseurs, clients = utils.getFournisseurAndClientsList(123)
            >>> print(f"Fournisseurs: {fournisseurs}")
            >>> print(f"Clients: {clients}")
        """
        tiers_repo = TiersRepository()
        tiers = tiers_repo.get_tiers_by_dossier_id(dossier_id)
        
        clients_list: list[str] = []
        fournisseurs_list: list[str] = []
        
        for tier in tiers:
            intitule = tier.get('intitule', '')
            tier_type = tier.get('type')
            
            if tier_type == 1:  # Client
                clients_list.append(intitule)
            elif tier_type == 0:  # Fournisseur
                fournisseurs_list.append(intitule)
        
        # Formatage des listes
        fournisseurs = f"[ {', '.join(fournisseurs_list)} ]"
        clients = f"[ {', '.join(clients_list)} ]"
        
        return fournisseurs, clients
