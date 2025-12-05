"""
Service de validation des classifications de documents.

Ce module fournit des méthodes de validation pour affiner et corriger
les classifications effectuées par l'IA, en utilisant:
- La comparaison avec les listes de tiers connus
- Le calcul de similarité (distance de Levenshtein)
- Les règles métier personnalisées
"""

import re
from typing import Optional

import Levenshtein

from repositories.ai_separation_context_repository import AiSeparationContextRepository
from services import constant
from services.constant import CategorieId
from services.logger import Logger
from services.utils_service import UtilsService

logger = Logger.get_logger()


class ValidationService:
    """
    Service de validation et d'affinage des classifications.
    
    Fournit des méthodes pour:
    - Valider les classifications fournisseur/client
    - Détecter les pages blanches
    - Appliquer des règles de contexte personnalisées
    - Détecter les documents de gestion
    """

    # Seuil de similarité pour la validation manuelle (%)
    SIMILARITY_THRESHOLD: int = 90
    
    # Seuil de similarité pour le contexte personnalisé (%)
    CUSTOM_CONTEXT_THRESHOLD: int = 98
    
    # Mots-clés identifiant les documents de gestion
    GESTION_KEYWORDS: list[str] = [
        "BON DE LIVRAISON",
        "RELEVE COMPTE CLIENT",
        "RELEVE DE FACTURES"
    ]

    def contains_exact_word_case_insensitive(
        self,
        text: str,
        word: str
    ) -> bool:
        """
        Vérifie si un mot exact est présent dans le texte (insensible à la casse).
        
        Args:
            text: Texte dans lequel rechercher.
            word: Mot à rechercher.
            
        Returns:
            True si le mot est trouvé comme mot entier et n'est pas
            dans la liste des mots à ignorer.
        """
        # Utilisation de word boundaries pour la correspondance exacte
        found = re.search(
            r'\b' + re.escape(word) + r'\b',
            text,
            re.IGNORECASE
        ) is not None
        
        if found and word not in constant.EXACT_WORDS_TO_IGNORE_IN_VALIDATION:
            logger.debug(f"Correspondance exacte trouvée: '{word}'")
            return True
            
        return False

    def convert_string_to_array(self, text: str) -> list[str]:
        """
        Convertit une chaîne au format liste en tableau Python.
        
        Args:
            text: Chaîne au format "[ item1, item2, ... ]"
            
        Returns:
            Liste des éléments extraits.
            
        Example:
            >>> service = ValidationService()
            >>> service.convert_string_to_array("[ A, B, C ]")
            ['A', 'B', 'C']
        """
        cleaned = text.strip('[]').strip()
        return [item.strip() for item in cleaned.split(',') if item.strip()]

    def validation_in_ocr_content(
        self,
        ocr_content: str,
        dossier_id: int
    ) -> Optional[int]:
        """
        Valide la catégorie en cherchant des noms de tiers dans le contenu OCR.
        
        Args:
            ocr_content: Texte extrait par OCR du document.
            dossier_id: Identifiant du dossier pour récupérer les tiers.
            
        Returns:
            ID de la catégorie détectée (fournisseur ou client),
            ou None si aucune correspondance claire.
        """
        logger.debug("Début de la validation par contenu OCR")
        
        utils_service = UtilsService()
        fournisseurs, clients = utils_service.getFournisseurAndClientsList(dossier_id)

        fournisseurs_list = self.convert_string_to_array(fournisseurs)
        clients_list = self.convert_string_to_array(clients)
        
        is_fournisseur = any(
            self.contains_exact_word_case_insensitive(ocr_content, f)
            for f in fournisseurs_list
        )
        is_client = any(
            self.contains_exact_word_case_insensitive(ocr_content, c)
            for c in clients_list
        )
        
        logger.info(
            f"Validation OCR: fournisseur={is_fournisseur}, client={is_client}"
        )
        
        if is_fournisseur and not is_client:
            return CategorieId.FOURNISSEUR
        elif is_client and not is_fournisseur:
            return CategorieId.CLIENT
            
        return None

    def validation_manuel(
        self,
        data: dict,
        image: dict,
        ocr_content: str
    ) -> dict:
        """
        Affine la classification en utilisant la similarité de chaînes.
        
        Compare l'émetteur et le récepteur extraits avec les informations
        du dossier pour déterminer si le document est de type client
        ou fournisseur.
        
        Args:
            data: Données de classification à affiner (modifié sur place).
            image: Métadonnées de l'image avec les infos du dossier.
            ocr_content: Contenu textuel extrait par OCR.
            
        Returns:
            Le dictionnaire data mis à jour avec la catégorie affinée.
        """
        try:
            # Normalisation des données
            emetteur = (data.get('Emetteur') or '').upper()
            recepteur = (data.get('Recepteur') or '').upper()
            
            siren_ste = str(image.get('siren_ste', ''))[:9]
            siren_emetteur = str(data.get('SirenEmetteur', ''))[:9]
            
            dossier_rs = image.get('rs_ste', '').upper()
            dossier_nom = image.get('dossier_nom', '').upper()

            # Calcul des ratios de similarité
            siren_ratio = self._calculate_similarity(siren_ste, siren_emetteur)
            
            dossier_rs_ratio = self._calculate_similarity(emetteur, dossier_rs)
            dossier_name_ratio = self._calculate_similarity(emetteur, dossier_nom)
            
            dossier_rs_recepteur_ratio = self._calculate_similarity(recepteur, dossier_rs)
            dossier_name_recepteur_ratio = self._calculate_similarity(recepteur, dossier_nom)

            # Logs de debug pour le diagnostic
            self._log_similarity_details(
                emetteur, recepteur, dossier_rs, dossier_nom,
                siren_ste, siren_emetteur,
                dossier_rs_ratio, dossier_name_ratio,
                dossier_rs_recepteur_ratio, dossier_name_recepteur_ratio,
                siren_ratio
            )

            # Calcul des scores finaux
            ratio_fournisseur = max(dossier_rs_recepteur_ratio, dossier_name_recepteur_ratio)
            ratio_client = max(dossier_rs_ratio, dossier_name_ratio)
            original_ratio = data.get('ratio', 0)

            # Application des règles de validation
            if ratio_client > self.SIMILARITY_THRESHOLD:
                data['categorie_id'] = CategorieId.CLIENT
                data['explication'] += f" ratio_original={original_ratio} (Validation manuelle) "
                data['ratio'] = ratio_client

            if ratio_fournisseur > self.SIMILARITY_THRESHOLD and ratio_fournisseur >= ratio_client:
                data['categorie_id'] = CategorieId.FOURNISSEUR
                data['explication'] += f" ratio_original={original_ratio} (Validation manuelle) "
                data['ratio'] = ratio_fournisseur

            # Vérification des documents de gestion
            if self.is_gestion(ocr_content):
                data['categorie_id'] = CategorieId.GESTION
                data['explication'] = f" ratio_original={original_ratio} (Validation manuelle - Gestion) "
                data['ratio'] = 100

            # Ajout des détails de validation
            data['explication'] += (
                f"\n ratio_client: {ratio_client}, "
                f"ratio_fournisseur: {ratio_fournisseur}, "
                f"siren_ratio: {siren_ratio}, "
                f"\n siren_ste: {siren_ste}, siren_emetteur: {siren_emetteur}"
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation manuelle: {e}")
            return data

    def is_blank_page(self, ocr_content: str) -> bool:
        """
        Détecte si une page est vide ou presque vide.
        
        Args:
            ocr_content: Contenu textuel extrait par OCR.
            
        Returns:
            True si la page est considérée comme vide.
        """
        if len(ocr_content.strip()) == 0:
            logger.info("Page blanche détectée")
            return True
        return False

    def validation_with_custom_error(
        self,
        image: dict,
        emetteur: str,
        recepteur: str
    ) -> Optional[int]:
        """
        Valide en utilisant les contextes personnalisés du dossier.
        
        Recherche des correspondances dans les contextes de correction
        définis pour le dossier, le site ou le client.
        
        Args:
            image: Métadonnées de l'image.
            emetteur: Nom de l'émetteur extrait.
            recepteur: Nom du récepteur extrait.
            
        Returns:
            ID de la catégorie si une correspondance est trouvée,
            None sinon.
        """
        try:
            ai_separation_context_repo = AiSeparationContextRepository()
            
            custom_contexts = ai_separation_context_repo.get_ai_separation_context_by(
                dossier=image.get('dossier_id'),
                site=image.get('site_id'),
                client=image.get('client_id')
            )
            
            for context in custom_contexts:
                contexte_text = context.get("contexte", "")
                
                ratio_emetteur = self._calculate_similarity(contexte_text, emetteur)
                ratio_recepteur = self._calculate_similarity(contexte_text, recepteur)
                
                if ratio_emetteur >= self.CUSTOM_CONTEXT_THRESHOLD or \
                   ratio_recepteur >= self.CUSTOM_CONTEXT_THRESHOLD:
                    logger.info(
                        f"Contexte personnalisé appliqué: {contexte_text} "
                        f"(ratio: {max(ratio_emetteur, ratio_recepteur)}%)"
                    )
                    return context.get('categorie_id')

            return None

        except Exception as e:
            logger.error(f"Erreur lors de la validation par contexte personnalisé: {e}")
            return None

    def is_gestion(self, ocr_content: str) -> bool:
        """
        Détecte si un document est de type gestion.
        
        Recherche des mots-clés caractéristiques des documents de gestion,
        tout en excluant les factures.
        
        Args:
            ocr_content: Contenu textuel extrait par OCR.
            
        Returns:
            True si le document est identifié comme document de gestion.
        """
        for keyword in self.GESTION_KEYWORDS:
            if re.search(keyword, ocr_content, re.IGNORECASE):
                # Exclure si c'est une facture
                if not re.search(r'FACTURE', ocr_content, re.IGNORECASE):
                    logger.info(f"Document de gestion détecté (mot-clé: {keyword})")
                    return True
        return False

    def valider_phrase_complete(self, phrase: str) -> bool:
        """
        Vérifie la cohérence structurelle d'une explication de classification.
        
        Analyse si la phrase d'explication respecte le format attendu
        et si les informations sont cohérentes.
        
        Args:
            phrase: Phrase d'explication à valider.
            
        Returns:
            True si la phrase est valide et cohérente.
        """
        pattern = re.compile(
            r"^document\s+(?P<type>fournisseur|client)\s+car\s+le\s+siren\s+de\s+"
            r"l['']émetteur\s*\(\s*(?P<siren1>\d{9})\s*\)\s+est\s+différent\s+de\s+"
            r"celui\s+du\s+dossier\s*\(\s*(?P<siren2>\d{9})\s*\)\s+et\s+la\s+raison\s+"
            r"sociale\s+de\s+l['']émetteur\s*\(\s*(?P<raison1>[^()]+?)\s*\)\s+est\s+"
            r"différente\s+de\s+celle\s+du\s+dossier\s*\(\s*(?P<raison2>[^()]+?)\s*\)\s*$",
            re.IGNORECASE
        )

        match = pattern.match(phrase)
        if not match:
            return False

        type_entite = match.group("type").lower()
        siren1 = match.group("siren1").strip()
        siren2 = match.group("siren2").strip()
        raison1 = match.group("raison1").strip().upper()
        raison2 = match.group("raison2").strip().upper()

        if type_entite == "fournisseur":
            return siren1 != siren2 and raison1 != raison2
        elif type_entite == "client":
            return True

        return False

    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> int:
        """
        Calcule le pourcentage de similarité entre deux chaînes.
        
        Args:
            str1: Première chaîne.
            str2: Deuxième chaîne.
            
        Returns:
            Pourcentage de similarité (0-100).
        """
        return int(Levenshtein.ratio(str1, str2) * 100)

    @staticmethod
    def _log_similarity_details(
        emetteur: str,
        recepteur: str,
        dossier_rs: str,
        dossier_nom: str,
        siren_ste: str,
        siren_emetteur: str,
        dossier_rs_ratio: int,
        dossier_name_ratio: int,
        dossier_rs_recepteur_ratio: int,
        dossier_name_recepteur_ratio: int,
        siren_ratio: int
    ) -> None:
        """Log les détails de calcul de similarité pour le debug."""
        logger.debug("=" * 50)
        logger.debug(f"SIREN: ste={siren_ste}, emetteur={siren_emetteur}, ratio={siren_ratio}%")
        logger.debug(f"RS vs Emetteur: {emetteur} <-> {dossier_rs} = {dossier_rs_ratio}%")
        logger.debug(f"Nom vs Emetteur: {emetteur} <-> {dossier_nom} = {dossier_name_ratio}%")
        logger.debug(f"RS vs Recepteur: {recepteur} <-> {dossier_rs} = {dossier_rs_recepteur_ratio}%")
        logger.debug(f"Nom vs Recepteur: {recepteur} <-> {dossier_nom} = {dossier_name_recepteur_ratio}%")
        logger.debug("=" * 50)
