import math

class TvaCalculator:
    def get_ttc(self, ht, taux_tva):
        # Conversion en float et gestion des valeurs nulles/None
        ht = float(ht) if ht else 0.0
        taux_tva = float(taux_tva) if taux_tva else 0.0
        # Calcul et arrondi à 2 décimales
        return round(ht * ((taux_tva / 100) + 1), 2)
    
    def get_ht(self, ttc, taux_tva):
        ttc = float(ttc) if ttc else 0.0
        taux_tva = float(taux_tva) if taux_tva else 0.0
        if taux_tva == -100: return 0.0 # Éviter division par zéro
        return round(ttc / ((taux_tva / 100) + 1), 2)
    
    def get_tva_ht(self, ht, taux_tva):
        ht = float(ht) if ht else 0.0
        taux_tva = float(taux_tva) if taux_tva else 0.0
        return round((taux_tva / 100) * ht, 2)

    def get_tva_ttc(self, ttc, taux_tva):
        ttc = float(ttc) if ttc else 0.0
        taux_tva = float(taux_tva) if taux_tva else 0.0
        if (taux_tva + 100) == 0: return 0.0
        return round((ttc * taux_tva) / (taux_tva + 100), 2)

    def get_taux_tva_ht(self, ht, tva):
        ht = float(ht) if ht else 0.0
        tva = float(tva) if tva else 0.0
        try:
            # Vérification si HT est significativement supérieur à 0
            if round(ht, 2) > 0:
                # Reproduction de la logique de calcul du taux
                res = (tva / ht) * 100
                return round(res, 2)
            else:
                return 0.0
        except ZeroDivisionError:
            return 0.0
