from datetime import datetime

from services.utils_service import UtilsService

class Humain:
    def __init__(self):
        self.utils = UtilsService()

    def date_facture_validation(self, date_facture):
        """
        Valide la date de facture : présence, format et cohérence (±2 ans).
        """
        result = date_facture.copy()
        value = date_facture.get('value')

        if not value:
            result.update({
                "ratio": 0,
                "explication": "Date manquante"
            })
            return result

        # Appel à la méthode de Utility
        format_info = self.utils.test_date_format(value)
        
        if not format_info["isValid"]:
            result.update({
                "ratio": 0,
                "explication": "Format de date invalide"
            })
            return result

        # Extraction de l'année
        current_year = datetime.now().year
        date_obj = format_info["date"]
        # En Python, date_obj est déjà un objet datetime.date issu de notre conversion précédente
        date_year = date_obj.year

        if abs(current_year - date_year) > 2:
            result.update({
                "ratio": 0,
                "explication": "Année hors plage acceptable (±2 ans)"
            })
            return result

        result.update({
            "ratio": 90,
            "explication": "Date au format valide et dans la plage acceptable (±2 ans)"
        })
        return result

    def date_livraison_validation(self, date_liv, date_facture):
        """
        Valide la date de livraison par rapport à la date de facture (±30 jours).
        """
        result = date_liv.copy()
        value_liv = date_liv.get('value')

        if not value_liv:
            return {
                "value": date_facture.get('value'),
                "ratio": 90,
                "explication": "Date manquante"
            }

        format_info_liv = self.utils.test_date_format(value_liv)
        if not format_info_liv["isValid"]:
            result.update({
                "ratio": 0,
                "explication": "Format de date invalide"
            })
            return result

        # Conversion de la date de facture pour calcul
        # On utilise Utility pour parser la date de facture qui est une string
        format_info_fact = self.utils.test_date_format(date_facture.get('value'))
        
        if not format_info_fact["isValid"]:
            # Si la date facture est elle-même invalide, on ne peut pas comparer
            result.update({
                "ratio": 0,
                "explication": "Comparaison impossible : date facture invalide"
            })
            return result

        date_liv_obj = format_info_liv["date"]
        date_fact_obj = format_info_fact["date"]

        # Calcul de la différence en jours
        diff_days = abs((date_liv_obj - date_fact_obj).days)

        if diff_days > 30:
            result.update({
                "ratio": 0,
                "explication": "Date de livraison hors plage acceptable (±30 jours de la date de facture)"
            })
            return result

        result.update({
            "ratio": 90,
            "explication": "Date de livraison dans la plage acceptable (±30 jours de la date de facture)"
        })
        return result