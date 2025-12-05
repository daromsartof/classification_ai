"""
Service de traitement d'images avec OpenCV.

Ce module fournit des fonctionnalités de traitement d'images basées sur
OpenCV, notamment la détection et la correction de l'orientation des
documents scannés.
"""

from typing import Optional

import cv2
import imutils
import numpy as np
import pytesseract
from pytesseract import Output

from services.logger import Logger

logger = Logger.get_logger()


class OpenCvService:
    """
    Service de traitement d'images utilisant OpenCV et Tesseract.
    
    Fournit des méthodes pour:
    - Détecter l'orientation d'une image via OCR
    - Corriger automatiquement l'orientation des documents
    """

    def get_image_orientation_from_ocr(
        self,
        image_path: str
    ) -> tuple[Optional[dict], Optional[np.ndarray]]:
        """
        Détecte l'orientation d'une image en utilisant l'OCR Tesseract.
        
        Analyse le contenu textuel de l'image pour déterminer son
        orientation et calculer l'angle de rotation nécessaire.
        
        Args:
            image_path: Chemin vers le fichier image à analyser.
            
        Returns:
            Tuple contenant:
                - dict: Informations d'orientation (ou None si échec):
                    - orientation: Orientation détectée (0, 90, 180, 270)
                    - rotate: Angle de rotation pour corriger
                    - script: Type de script détecté
                    - script_conf: Confiance de détection du script
                - np.ndarray: Image chargée en mémoire (ou None si échec)
                
        Example:
            >>> service = OpenCvService()
            >>> orientation, image = service.get_image_orientation_from_ocr("doc.jpg")
            >>> if orientation:
            ...     print(f"Rotation nécessaire: {orientation['rotate']}°")
        """
        try:
            # Chargement de l'image
            image = cv2.imread(image_path)
            
            if image is None:
                raise ValueError(f"Image non trouvée ou impossible à charger: {image_path}")

            # Conversion en RGB pour Tesseract
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Analyse de l'orientation via OSD (Orientation and Script Detection)
            results = pytesseract.image_to_osd(rgb, output_type=Output.DICT)
            
            return results, image
            
        except pytesseract.TesseractError as e:
            logger.warning(f"Tesseract n'a pas pu déterminer l'orientation: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'orientation: {e}")
            return None, None

    def rotate_image(self, image_path: str) -> bool:
        """
        Corrige automatiquement l'orientation d'une image.
        
        Détecte l'orientation actuelle de l'image et applique une
        rotation si nécessaire pour la remettre à l'endroit.
        L'image est modifiée sur place (écrasée).
        
        Args:
            image_path: Chemin vers le fichier image à corriger.
            
        Returns:
            True si l'image a été corrigée avec succès ou si aucune
            correction n'était nécessaire, False en cas d'erreur.
            
        Note:
            Cette méthode modifie directement le fichier image.
            Aucune sauvegarde n'est créée automatiquement.
            
        Example:
            >>> service = OpenCvService()
            >>> success = service.rotate_image("document_scanne.jpg")
            >>> if success:
            ...     print("Orientation corrigée")
        """
        orientation_info, img = self.get_image_orientation_from_ocr(image_path)
        
        if orientation_info is None or img is None:
            logger.warning(
                f"Impossible de détecter l'orientation de l'image: {image_path}"
            )
            return False
            
        rotation_angle = orientation_info.get('rotate', 0)
        
        if rotation_angle == 0:
            logger.debug(f"Image déjà correctement orientée: {image_path}")
            return True
            
        logger.info(
            f"Orientation détectée: {orientation_info.get('orientation')}°, "
            f"rotation de {rotation_angle}° appliquée"
        )

        # Application de la rotation
        rotated = imutils.rotate_bound(img, angle=rotation_angle)
        
        # Sauvegarde de l'image corrigée
        cv2.imwrite(image_path, rotated)
        
        logger.info(f"Image corrigée et sauvegardée: {image_path}")
        return True
