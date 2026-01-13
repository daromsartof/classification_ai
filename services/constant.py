"""
Constants et énumérations pour le service de classification IA.

Ce module centralise toutes les constantes utilisées dans l'application,
notamment les identifiants de catégories, les bibliothèques OCR supportées,
et les configurations de statut.
"""

from enum import IntEnum, Enum
from typing import Final


class CategorieId(IntEnum):
    """
    Identifiants des catégories de documents.
    
    Attributes:
        FOURNISSEUR: Documents provenant de fournisseurs (factures d'achat, etc.)
        CLIENT: Documents destinés aux clients (factures de vente, etc.)
        GESTION: Documents de gestion interne
        BANQUE: Documents bancaires (relevés, etc.)
        ILLISIBLE: Documents non lisibles ou pages blanches
        JOCKER: Catégorie par défaut pour documents non classifiables
        COURRIER: Courriers divers
    """
    FOURNISSEUR = 10
    CLIENT = 9
    GESTION = 25
    BANQUE = 16
    ILLISIBLE = 18
    JURIDIQUES = 24
    FISCAL = 21
    SOCIAL = 20
    JOCKER = 49
    COURRIER = 23
    
class SousCategorieId(IntEnum):
    """
    Identifiants des sous-catégories de documents.
    
    Attributes:
        RELEVER_BANCAIRE: Relevés bancaires
    """
    RELEVER_BANCAIRE = 10


class OcrLibrary(str, Enum):
    """
    Bibliothèques OCR supportées pour l'extraction de texte.
    
    Attributes:
        TESSERACT: OCR Tesseract standard
        EASYOCR: Bibliothèque EasyOCR
        CUSTOM_PYTESSERACT: Version personnalisée de Pytesseract
        DOCUMENT_AI: Google Document AI
    """
    TESSERACT = "pytesseract"
    EASYOCR = "easy_ocr"
    CUSTOM_PYTESSERACT = "custom_pytesseract"
    DOCUMENT_AI = "document_ai"


class OpenAIModel(str, Enum):
    """
    Modèles OpenAI disponibles pour la classification.
    
    Attributes:
        GPT_4O_MINI: Modèle compact et rapide
        GPT_4O: Modèle complet avec meilleures performances
    """
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"


class StatusNew(IntEnum):
    """
    Statuts de traitement des images/lots.
    
    Attributes:
        FINISHED: Traitement terminé avec succès
        ERROR: Erreur lors du traitement
    """
    FINISHED = 6
    ERROR = 4


class Status(IntEnum):
    """
    Anciens statuts (rétrocompatibilité).
    
    Attributes:
        FINISHED: Traitement terminé
    """
    FINISHED = 4


# Utilisateurs du système pour le panier de réception
PANIER_RECEPTION_USERS: Final[dict[str, int]] = {
    "HARIVOLATIANA": 6641,
    "RAZAFINDRATSIMBA": 2517,
    "stephanie": 1307
}

# Identifiant de l'utilisateur système GenZ
GENZ_USER_ID: Final[int] = 6831

# Mots à ignorer lors de la validation par correspondance exacte
EXACT_WORDS_TO_IGNORE_IN_VALIDATION: Final[list[str]] = [
    "SARL", "EURL", "SAS", "SASU", "SA", 
    "Total", "ACTION", "INTERNET", "TOTAL"
]


# =============================================================================
# Rétrocompatibilité avec l'ancien format (dictionnaires)
# À terme, utiliser directement les Enums ci-dessus
# =============================================================================

categirie_id = {
    "fournisseur": CategorieId.FOURNISSEUR,
    "client": CategorieId.CLIENT,
    "gestion": CategorieId.GESTION,
    "banque": CategorieId.BANQUE,
    "illisible": CategorieId.ILLISIBLE,
    "jocker": CategorieId.JOCKER,
    "courrier": CategorieId.COURRIER,
}

ocr_library = {
    "tesseract": OcrLibrary.TESSERACT.value,
    "easyocr": OcrLibrary.EASYOCR.value,
    "custom_pytesseract": OcrLibrary.CUSTOM_PYTESSERACT.value,
    "document_ai": OcrLibrary.DOCUMENT_AI.value,
}

model = {
    "gpt-4o-mini": OpenAIModel.GPT_4O_MINI.value,
    "gpt-4o": OpenAIModel.GPT_4O.value,
}

status = {
    "finished": Status.FINISHED
}

status_new = {
    "finished": StatusNew.FINISHED
}

panier_reception_user = PANIER_RECEPTION_USERS
genz_user_id = GENZ_USER_ID
exact_word_to_ignore_in_validation = EXACT_WORDS_TO_IGNORE_IN_VALIDATION
