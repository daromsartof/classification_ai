"""
Service d'intégration avec l'API OpenAI Vision.

Ce module fournit des fonctionnalités pour:
- Interagir avec les modèles de vision OpenAI (GPT-4o, GPT-4o-mini avec vision)
- Catégoriser automatiquement les documents comptables en envoyant directement les images
- Valider les classifications via l'IA avec vision
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from repositories.ai_separation_context_repository import AiSeparationContextRepository
from services import constant
from services.constant import CategorieId, OpenAIModel
from services.logger import Logger
from services.utils_service import UtilsService

logger = Logger.get_logger()


class OpenAIServiceVision:
    """
    Service d'interaction avec l'API OpenAI Vision.
    
    Fournit des méthodes pour utiliser les modèles GPT avec vision afin de:
    - Catégoriser des documents comptables en envoyant directement les images
    - Valider des classifications existantes avec vision
    
    Attributes:
        client: Client OpenAI configuré avec la clé API.
        model: Modèle par défaut à utiliser.
    """
    
    # Placeholders supportés dans les prompts
    PROMPT_PLACEHOLDERS: dict[str, str] = {
        '{{dossier_nom}}': 'rs_ste',
        '{{dossier_siren}}': 'siren_ste',
        '{{dossier_rs}}': 'rs_ste',
        '{{dossier_ape}}': 'ape',
        '{{activite_com_cat}}': 'activite_0',
        '{{activite_com_cat_1}}': 'activite_1',
        '{{activite_com_cat_2}}': 'activite_2',
        '{{activite_com_cat_3}}': 'activite_3',
    }

    def __init__(self, model: str = OpenAIModel.GPT_4O_MINI.value):
        """
        Initialise le service OpenAI Vision.
        
        Args:
            model: Modèle par défaut à utiliser pour les requêtes (doit supporter la vision).
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def response_parse(self, response: str) -> dict[str, Any]:
        """
        Parse une réponse JSON de l'API OpenAI.
        
        Gère les cas où la réponse est encapsulée dans des balises
        de code markdown (```json ... ```).
        
        Args:
            response: Chaîne JSON à parser.
            
        Returns:
            Dictionnaire contenant les données parsées.
            
        Raises:
            ValueError: Si le parsing échoue après nettoyage.
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Tentative de nettoyage des balises markdown
            cleaned_response = (
                response
                .replace('```json\n', '')
                .replace('```', '')
                .strip()
            )
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError as err:
                raise ValueError(
                    f"Échec du parsing JSON après nettoyage: {cleaned_response[:100]}..."
                ) from err

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Encode une image en base64 pour l'API Vision.
        
        Args:
            image_path: Chemin vers le fichier image.
            
        Returns:
            Chaîne base64 encodée de l'image.
        """
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _get_image_mime_type(self, image_path: str) -> str:
        """
        Détermine le type MIME d'une image à partir de son extension.
        
        Args:
            image_path: Chemin vers le fichier image.
            
        Returns:
            Type MIME de l'image (par défaut 'image/jpeg').
        """
        extension = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        return mime_types.get(extension, 'image/jpeg')

    def _prepare_image_for_vision(
        self,
        file_path: str
    ) -> tuple[str, str, bool]:
        """
        Prépare un fichier (PDF ou image) pour l'API Vision.
        
        Si c'est un PDF, convertit la première page en image.
        Si c'est une image, l'encode directement.
        
        Args:
            file_path: Chemin vers le fichier (PDF ou image).
            
        Returns:
            Tuple contenant:
                - image_path: Chemin vers l'image à envoyer
                - mime_type: Type MIME de l'image
                - is_temporary: True si l'image est temporaire (créée depuis PDF)
        """
        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()
        
        # Si c'est un PDF, convertir en image
        if extension == '.pdf':
            logger.info(f"Conversion PDF en image pour Vision: {file_path}")
            utils_service = UtilsService()
            import asyncio
            image_path, _ = asyncio.run(
                utils_service.convert_pdf_to_images(
                    file_path,
                    str(file_path_obj.parent)
                )
            )
            if not image_path:
                raise ValueError(f"Échec de conversion PDF en image: {file_path}")
            # L'image convertie sera nettoyée par le cleanup dans main.py
            # car elle utilise le pattern .ia.jpeg
            return image_path, 'image/jpeg', True
        
        # Sinon, c'est déjà une image
        return file_path, self._get_image_mime_type(file_path), False

    def call_agent_vision(
        self,
        system_prompt: str,
        image_path: str,
        user_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Appelle l'API OpenAI Vision avec une image.
        
        Args:
            system_prompt: Instructions système pour le modèle.
            image_path: Chemin vers l'image à analyser.
            user_prompt: Message utilisateur optionnel à ajouter.
            model: Modèle à utiliser (utilise le modèle par défaut si None).
            
        Returns:
            Contenu de la réponse du modèle.
        """
        effective_model = model or self.model
        logger.info(f"Appel API OpenAI Vision avec le modèle: {effective_model}")
        
        # Préparation de l'image
        prepared_image_path, mime_type, _ = self._prepare_image_for_vision(image_path)
        
        # Encodage en base64
        base64_image = self._encode_image_to_base64(prepared_image_path)
        
        # Construction du message avec l'image
        content = [
            {
                "type": "text",
                "text": user_prompt or "Analyse ce document comptable et classe-le selon les catégories disponibles."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            }
        ]
        
        completion = self.client.chat.completions.create(
            model=effective_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
        )
        
        return completion.choices[0].message.content

    def categorisation(
        self,
        image_path: str,
        image: dict,
        model: str,
        prompt_system: Optional[str]
    ) -> dict[str, Any]:
        """
        Catégorise un document comptable via l'IA Vision.
        
        Envoie directement l'image au modèle Vision au lieu d'utiliser l'OCR.
        
        Args:
            image_path: Chemin vers le fichier image/PDF à analyser.
            image: Métadonnées de l'image contenant les infos du dossier.
            model: Modèle OpenAI à utiliser (doit supporter la vision).
            prompt_system: Template du prompt système avec placeholders.
            
        Returns:
            Dictionnaire contenant:
                - Categorie: Nom de la catégorie
                - ID: Identifiant de la catégorie
                - SousCategorie: Sous-catégorie (optionnel)
                - SousSousCategorie: Sous-sous-catégorie (optionnel)
                - Explanation: Explication de la classification
                - Emetteur: Émetteur détecté
                - Recepteur: Récepteur détecté
                - SirenEmetteur: SIREN de l'émetteur
                - ratio: Score de confiance (0-100)
                
        Note:
            En cas d'erreur, retourne une classification "ILLISIBLES".
        """
        try:
            # Récupération des listes de tiers
            utils_service = UtilsService()
            fournisseurs, clients = utils_service.getFournisseurAndClientsList(
                image.get('dossier_id')
            )

            # Construction du dictionnaire de remplacement
            # Note: pas de document_text car on utilise la vision
            replacements = self._build_replacements(image, fournisseurs, clients)
            
            # Récupération des contextes personnalisés
            self._add_custom_contexts(replacements, image)

            # Application des remplacements au prompt
            if prompt_system:
                prompt_system = self._apply_replacements(prompt_system, replacements)

            # Message utilisateur pour la vision
            user_prompt = "Analyse ce document comptable et classe-le selon les catégories disponibles. Extrais toutes les informations pertinentes du document."

            # Appel à l'API Vision
            response = self.call_agent_vision(
                system_prompt=prompt_system or "",
                image_path=image_path,
                user_prompt=user_prompt,
                model=model
            )
            
            logger.info(f"Réponse brute OpenAI Vision: {response}")
            return self.response_parse(response)

        except Exception as e:
            logger.error(f"Erreur de catégorisation Vision: {e}")
            return self._create_error_response(str(e))

    def validation(
        self,
        image_path: str,
        image: dict,
        model: str = OpenAIModel.GPT_4O_MINI.value
    ) -> dict[str, Any]:
        """
        Valide une classification via l'IA Vision.
        
        Utilise un prompt spécialisé pour vérifier si la classification
        d'un document est correcte en analysant directement l'image.
        
        Args:
            image_path: Chemin vers le fichier image/PDF à analyser.
            image: Métadonnées de l'image avec les infos du dossier.
            model: Modèle OpenAI à utiliser (doit supporter la vision).
            
        Returns:
            Dictionnaire contenant le résultat de la validation.
            
        Note:
            En cas d'erreur, retourne une classification "ILLISIBLES".
        """
        try:
            utils_service = UtilsService()
            fournisseurs, clients = utils_service.getFournisseurAndClientsList(
                image.get('dossier_id')
            )

            # Chargement du template de prompt
            system_prompt = self._load_prompt_template('services/prompts/validation.md')
            
            # Application des remplacements (sans document_text car vision)
            replacements = {
                '{{dossier_nom}}': image.get('dossier_nom', ''),
                '{{dossier_ape}}': image.get('ape', ''),
                '{{activite_com_cat}}': image.get('activite_0', ''),
                '{{activite_com_cat_1}}': image.get('activite_1', ''),
                '{{activite_com_cat_2}}': image.get('activite_2', ''),
                '{{activite_com_cat_3}}': image.get('activite_3', ''),
                '{{document_text}}': '',  # Vide car on utilise la vision
                '{{dossier_tiers_list}}': clients,
                '{{dossier_tiers_list_fournisseur}}': fournisseurs,
                '{{recepteur}}': image.get('Recepeutteur', ''),
            }
            
            system_prompt = self._apply_replacements(system_prompt, replacements)

            user_prompt = "Valide la classification de ce document comptable en analysant directement l'image."

            response = self.call_agent_vision(
                system_prompt=system_prompt,
                image_path=image_path,
                user_prompt=user_prompt,
                model=model
            )

            return self.response_parse(response)

        except Exception as e:
            logger.error(f"Erreur de validation Vision: {e}")
            return self._create_error_response(str(e))

    def _build_replacements(
        self,
        image: dict,
        fournisseurs: str,
        clients: str
    ) -> dict[str, str]:
        """
        Construit le dictionnaire de remplacement pour les prompts.
        
        Args:
            image: Métadonnées de l'image.
            fournisseurs: Liste formatée des fournisseurs.
            clients: Liste formatée des clients.
            
        Returns:
            Dictionnaire placeholder -> valeur.
        """
        return {
            '{{dossier_nom}}': image.get('rs_ste', ''),
            '{{dossier_siren}}': image.get('siren_ste', ''),
            '{{dossier_rs}}': image.get('rs_ste', ''),
            '{{dossier_ape}}': image.get('ape', ''),
            '{{autre_remarque}}': "",
            '{{list_des_erreurs_fournisseurs}}': "",
            '{{list_des_erreurs_client}}': "",
            '{{custom_critaire_banque}}': "",
            '{{custom_critaire_gestion}}': "",
            '{{document_text}}': "",  # Vide car on utilise la vision
            '{{activite_com_cat}}': image.get('activite_0', ''),
            '{{activite_com_cat_1}}': image.get('activite_1', ''),
            '{{activite_com_cat_2}}': image.get('activite_2', ''),
            '{{activite_com_cat_3}}': image.get('activite_3', ''),
            '{{dossier_tiers_list}}': clients,
            '{{dossier_tiers_list_fournisseur}}': fournisseurs,
            '{{custom_critaire_courrier}}': "",
            '{{custom_critaire_fiscal}}': "",
            '{{custom_critaire_social}}': "",
            '{{custom_critaire_caisse}}': "",
            '{{custom_critaire_frais}}': "",
        }

    def _add_custom_contexts(self, replacements: dict[str, str], image: dict) -> None:
        """
        Ajoute les contextes personnalisés au dictionnaire de remplacement.
        
        Args:
            replacements: Dictionnaire à enrichir (modifié sur place).
            image: Métadonnées de l'image pour récupérer les contextes.
        """
        ai_separation_context_repo = AiSeparationContextRepository()
        
        custom_contexts = ai_separation_context_repo.get_ai_separation_context_by(
            dossier=image.get('dossier_id'),
            site=image.get('site_id'),
            client=image.get('client_id')
        )

        # Mapping catégorie -> placeholder
        category_placeholder_map = {
            CategorieId.FOURNISSEUR: '{{list_des_erreurs_fournisseurs}}',
            CategorieId.CLIENT: '{{list_des_erreurs_client}}',
            CategorieId.BANQUE: '{{custom_critaire_banque}}',
            CategorieId.GESTION: '{{custom_critaire_gestion}}',
            CategorieId.COURRIER: '{{custom_critaire_courrier}}',
        }

        for context in custom_contexts:
            categorie_id = context.get('categorie_id')
            contexte_text = context.get('contexte', '')
            
            placeholder = category_placeholder_map.get(categorie_id, '{{autre_remarque}}')
            replacements[placeholder] += f"{contexte_text}, "

    @staticmethod
    def _apply_replacements(template: str, replacements: dict[str, str]) -> str:
        """
        Applique les remplacements de placeholders dans un template.
        
        Args:
            template: Template avec placeholders.
            replacements: Dictionnaire placeholder -> valeur.
            
        Returns:
            Template avec les placeholders remplacés.
        """
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, str(value))
        return result

    @staticmethod
    def _load_prompt_template(path: str) -> str:
        """
        Charge un template de prompt depuis un fichier.
        
        Args:
            path: Chemin vers le fichier template.
            
        Returns:
            Contenu du fichier template.
        """
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _create_error_response(error_message: str) -> dict[str, Any]:
        """
        Crée une réponse d'erreur standardisée.
        
        Args:
            error_message: Message d'erreur à inclure.
            
        Returns:
            Dictionnaire de réponse pour une erreur.
        """
        return {
            "Categorie": "ILLISIBLES",
            "ID": CategorieId.ILLISIBLE,
            "Explication": f"Erreur GPT Vision: {error_message}"
        }

