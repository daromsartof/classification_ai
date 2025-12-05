from services.utils_service import UtilsService
import re
import ast
from services import constant
import Levenshtein
from repositories.ai_separation_context_repository import AiSeparationContextRepository
from services.logger import Logger

logger = Logger.get_logger()
class ValidationService:
    def __init__(self):
        pass

    import re

    def contains_exact_word_case_insensitive(self, text, word):
        found = re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE) is not None
        
        if found and word not in constant.exact_word_to_ignore_in_validation:
            logger.info(f"Found exact match for word: {word}")

        return found and word not in constant.exact_word_to_ignore_in_validation


    def convert_string_to_array(self, text):
        cleaned = text.strip('[]').strip()
        return [item.strip() for item in cleaned.split(',') if item.strip()]

    def validation_in_ocr_content(self, ocr_content: str, dossier_id: int) -> str:
        logger.debug("go manuel validation ")
        utils_service = UtilsService()
        fournisseurs, clients = utils_service.getFournisseurAndClientsList(dossier_id)
 
        is_fournisseur = any(self.contains_exact_word_case_insensitive(ocr_content, fournisseur) for fournisseur in self.convert_string_to_array(fournisseurs))
        is_client = any(self.contains_exact_word_case_insensitive(ocr_content, client) for client in self.convert_string_to_array(clients))
        logger.info(f"manuel validation response : is_fournisseur {is_fournisseur}, is_client: {is_client}")
        if is_fournisseur and not is_client:
            return constant.categirie_id.get('fournisseur', None)
        elif is_client and not is_fournisseur:
            return constant.categirie_id.get('client', None)
        return None

    def validation_manuel(self, data, image: dict, ocr_content: str) -> str:
        try:
            emmeteur = data.get('Emetteur', '').upper() if data.get('Emetteur', '') else ""
            recepteur = data.get('Recepteur', '').upper() if data.get('Recepteur', '') else ""
            siren_ste = str(image.get('siren_ste', ''))
            siren_emmeteur = str(data.get('SirenEmetteur', ''))
            if len(siren_ste) > 9:
                siren_ste = siren_ste[:9]
            if len(siren_emmeteur) > 9:
                siren_emmeteur = siren_emmeteur[:9]
                
            siren_ratio = int(Levenshtein.ratio(siren_ste, siren_emmeteur) * 100)
            logger.debug("==============================")
            logger.debug(f"siren_ste, siren_emmeteur, siren_ratio : {siren_ste}, {siren_emmeteur}, {siren_ratio}")
            dossier_rs = image.get('rs_ste', '').upper()
            dossier_nom = image.get('dossier_nom', '').upper()
            dossier_rs_ratio = int(Levenshtein.ratio(emmeteur, dossier_rs) * 100)
            logger.debug("==============================")
            logger.debug(f"dossier_rs_ratio, emmeteur  , dossier_rs : {emmeteur}, {dossier_rs}, {dossier_rs_ratio}")
            dossier_name_ratio = int(Levenshtein.ratio(emmeteur, dossier_nom) * 100)
            logger.debug("==============================")
            logger.debug(f"dossier_name_ratio, emmeteur, dossier_nom : {emmeteur}, {dossier_nom}, {dossier_name_ratio}")
            dossier_rs_recepteur_ratio = int(Levenshtein.ratio(recepteur, dossier_rs) * 100)
            logger.debug("==============================")
            logger.debug(f"dossier_rs_recepteur_ratio, recepteur, dossier_rs : {recepteur}, {dossier_rs}, {dossier_rs_recepteur_ratio}")
            dossier_name_recepteur_ratio = int(Levenshtein.ratio(recepteur, dossier_nom) * 100)
            logger.debug("==============================")
            logger.debug(f"dossier_name_recepteur_ratio, recepteur, dossier_nom : {recepteur}, {dossier_nom}, {dossier_name_recepteur_ratio}")
            ratio_fournisseur = max(dossier_rs_recepteur_ratio, dossier_name_recepteur_ratio) 
            ratio_client = max(dossier_rs_ratio, dossier_name_ratio)
            if ratio_client > 90:
                data['categorie_id'] = constant.categirie_id.get('client', None)
                data['explication'] += f" data['ratio']={data['ratio']}  (Validation manuelle) "
                data['ratio'] = ratio_client
                
            if ratio_fournisseur > 90 and ratio_fournisseur >= ratio_client:
                data['categorie_id'] = constant.categirie_id.get('fournisseur', None)
                data['explication'] += f" data['ratio']={data['ratio']} (Validation manuelle) "
                data['ratio'] = ratio_fournisseur
            
            if self.is_gestion(ocr_content=ocr_content):
                data['categorie_id'] = constant.categirie_id.get('gestion', None)
                data['explication'] = f" data['ratio']={data['ratio']} (Validation manuelle - Gestion) "
                data['ratio'] = 100
                
            #if not self.valider_phrase_complète(data['explication']):
            #    data['categorie_id'] = constant.categirie_id.get('jocker', None)
            #    data['explication'] += f" L'explication n'est pas coherant (Validation manuelle) "
            #    data['ratio'] = 80
                
            data['explication'] += f"\n ratio_client: {ratio_client}, ratio_fournisseur: {ratio_fournisseur}, siren_ratio: {siren_ratio}, \n siren_ste: {siren_ste}, siren_emmeteur: {siren_emmeteur}"
            return data
        except Exception as e:
            logger.error(f"Manuel validation error: {str(e)}")
            return data
    
    def is_blank_page(self, ocr_content: str) -> bool:
        if len(ocr_content.strip()) == 0:
            logger.info("Detected completely blank page.")
            return True
        return False
    
    def validation_with_custom_error(self, image: dict, emmeteur: str, recepteur: str):
        try:
            ai_separation_context_repository = AiSeparationContextRepository()
            custom_contexts = ai_separation_context_repository.get_ai_separation_context_by(
                dossier=image.get('dossier_id'),
                site=image.get('site_id'),
                client=image.get('client_id')
            )
            for context in custom_contexts:
                contexte_text = context.get("contexte", "")
                #logger.debug(f"Evaluating context: {contexte_text}")
                ratio_fournisseur = int(Levenshtein.ratio(contexte_text, emmeteur) * 100)
                #logger.debug(f"Ratio fournisseur: {ratio_fournisseur}")
                ratio_client = int(Levenshtein.ratio(contexte_text, recepteur) * 100)
                #logger.debug(f"Ratio client: {ratio_client}")
                if ratio_client >= 98 or ratio_fournisseur >= 98:
                    return context.get('categorie_id')

            # No match found
            return None

        except Exception as e:
            logger.error(f"[Custom validation error] {e}")
            return None
        
    def is_gestion(self, ocr_content: str) -> bool:
        gestion_keywords = [
            "BON DE LIVRAISON",
            "RELEVE COMPTE CLIENT",
            "RELEVE DE FACTURES"
        ]
        for word in gestion_keywords:
            pattern = rf'{word}'  # Use f-string with raw string (rf)
            match = re.search(pattern, ocr_content)  # Use ocr_content instead of text
            
            logger.info(f"Detected gestion keywords: pattern={pattern}, match={match}")
            if match and not re.search(r'FACTURE', ocr_content):
                return True
        return False
    
    def valider_phrase_complète(self, phrase: str) -> bool:
        """
            Vérifie :
            - Structure correcte
            - Si 'fournisseur' → les deux SIREN ET les deux raisons sociales sont différents
        """

        pattern = re.compile(
            r"^document\s+(?P<type>fournisseur|client)\s+car\s+le\s+siren\s+de\s+l['’]émetteur\s*\(\s*(?P<siren1>\d{9})\s*\)\s+est\s+différent\s+de\s+celui\s+du\s+dossier\s*\(\s*(?P<siren2>\d{9})\s*\)\s+et\s+la\s+raison\s+sociale\s+de\s+l['’]émetteur\s*\(\s*(?P<raison1>[^()]+?)\s*\)\s+est\s+différente\s+de\s+celle\s+du\s+dossier\s*\(\s*(?P<raison2>[^()]+?)\s*\)\s*$",
            re.IGNORECASE
        )

        match = pattern.match(phrase)
        if not match:
            return False  # Structure invalide

        type_entite = match.group("type").lower()
        siren1 = match.group("siren1").strip()
        siren2 = match.group("siren2").strip()
        raison1 = match.group("raison1").strip().upper()
        raison2 = match.group("raison2").strip().upper()

        # Vérification logique
        if type_entite == "fournisseur":
            # Les deux siren et les deux raisons doivent être différents
            return siren1 != siren2 and raison1 != raison2
        elif type_entite == "client":
            # (optionnel) tu peux inverser la logique si besoin
            return True

        return False