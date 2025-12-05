"""
Service d'intégration avec l'API OpenAI.

Ce module fournit des fonctionnalités pour:
- Interagir avec les modèles de langage OpenAI (GPT-4, etc.)
- Catégoriser automatiquement les documents comptables
- Valider les classifications via l'IA
"""

import json
import os
from typing import Any, Optional

from openai import OpenAI

from repositories.ai_separation_context_repository import AiSeparationContextRepository
from services import constant
from services.constant import CategorieId, OpenAIModel
from services.logger import Logger
from services.utils_service import UtilsService

logger = Logger.get_logger()


class OpenAIService:
    """
    Service d'interaction avec l'API OpenAI.
    
    Fournit des méthodes pour utiliser les modèles GPT afin de:
    - Catégoriser des documents comptables
    - Valider des classifications existantes
    
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
        Initialise le service OpenAI.
        
        Args:
            model: Modèle par défaut à utiliser pour les requêtes.
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

    def call_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None
    ) -> str:
        """
        Appelle l'API OpenAI avec les prompts spécifiés.
        
        Args:
            system_prompt: Instructions système pour le modèle.
            user_prompt: Message utilisateur à traiter.
            model: Modèle à utiliser (utilise le modèle par défaut si None).
            
        Returns:
            Contenu de la réponse du modèle.
            
        Example:
            >>> service = OpenAIService()
            >>> response = service.call_agent(
            ...     "Tu es un assistant comptable.",
            ...     "Classe ce document: [texte du document]"
            ... )
        """
        effective_model = model or self.model
        logger.info(f"Appel API OpenAI avec le modèle: {effective_model}")
        
        completion = self.client.chat.completions.create(
            model=effective_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return completion.choices[0].message.content

    def categorisation(
        self,
        user_prompt: str,
        image: dict,
        model: str,
        prompt_system: Optional[str]
    ) -> dict[str, Any]:
        """
        Catégorise un document comptable via l'IA.
        
        Utilise le contenu OCR du document et les informations du dossier
        pour déterminer la catégorie appropriée.
        
        Args:
            user_prompt: Texte extrait du document par OCR.
            image: Métadonnées de l'image contenant les infos du dossier.
            model: Modèle OpenAI à utiliser.
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
            replacements = self._build_replacements(image, user_prompt, fournisseurs, clients)
            
            # Récupération des contextes personnalisés
            self._add_custom_contexts(replacements, image)

            # Application des remplacements au prompt
            if prompt_system:
                prompt_system = self._apply_replacements(prompt_system, replacements)

            # Appel à l'API
            response = self.call_agent(
                system_prompt=prompt_system,
                user_prompt=f"voici le contenu de la première page du document : {user_prompt}",
                model=model
            )
            
            logger.info(f"Réponse brute OpenAI: {response}")
            return self.response_parse(response)

        except Exception as e:
            logger.error(f"Erreur de catégorisation: {e}")
            return self._create_error_response(str(e))

    def validation(
        self,
        user_prompt: str,
        image: dict,
        model: str = OpenAIModel.GPT_4O_MINI.value
    ) -> dict[str, Any]:
        """
        Valide une classification via l'IA.
        
        Utilise un prompt spécialisé pour vérifier si la classification
        d'un document est correcte.
        
        Args:
            user_prompt: Texte extrait du document par OCR.
            image: Métadonnées de l'image avec les infos du dossier.
            model: Modèle OpenAI à utiliser.
            
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
            
            # Application des remplacements
            replacements = {
                '{{dossier_nom}}': image.get('dossier_nom', ''),
                '{{dossier_ape}}': image.get('ape', ''),
                '{{activite_com_cat}}': image.get('activite_0', ''),
                '{{activite_com_cat_1}}': image.get('activite_1', ''),
                '{{activite_com_cat_2}}': image.get('activite_2', ''),
                '{{activite_com_cat_3}}': image.get('activite_3', ''),
                '{{document_text}}': user_prompt,
                '{{dossier_tiers_list}}': clients,
                '{{dossier_tiers_list_fournisseur}}': fournisseurs,
                '{{recepteur}}': image.get('Recepeutteur', ''),
            }
            
            system_prompt = self._apply_replacements(system_prompt, replacements)

            response = self.call_agent(
                system_prompt=system_prompt,
                user_prompt=f"voici le contenu de la première page du document : {user_prompt}",
                model=model
            )

            return self.response_parse(response)

        except Exception as e:
            logger.error(f"Erreur de validation: {e}")
            return self._create_error_response(str(e))

    def _build_replacements(
        self,
        image: dict,
        document_text: str,
        fournisseurs: str,
        clients: str
    ) -> dict[str, str]:
        """
        Construit le dictionnaire de remplacement pour les prompts.
        
        Args:
            image: Métadonnées de l'image.
            document_text: Texte du document.
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
            '{{document_text}}': document_text,
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
            "Explication": f"Erreur GPT: {error_message}"
        }


# Alias pour rétrocompatibilité
callAgent = OpenAIService.call_agent
