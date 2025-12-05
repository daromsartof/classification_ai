"""
Module de logging centralisé pour l'application de classification IA.

Ce module fournit un logger singleton configuré avec:
- Sortie console colorée pour une meilleure lisibilité
- Rotation automatique des fichiers de log
- Formatage cohérent des messages

Exemple d'utilisation:
    >>> from services.logger import Logger
    >>> logger = Logger.get_logger()
    >>> logger.info("Traitement démarré")
    >>> logger.error("Une erreur est survenue")
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from colorama import Fore, Style, init

# Initialisation de colorama pour le support des couleurs sur Windows
init(autoreset=True)


class ColorFormatter(logging.Formatter):
    """
    Formateur de logs avec coloration selon le niveau de sévérité.
    
    Attributes:
        COLORS: Mapping des niveaux de log vers les couleurs correspondantes.
    """
    
    COLORS: dict[int, str] = {
        logging.DEBUG: Fore.WHITE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Formate un enregistrement de log avec la couleur appropriée.
        
        Args:
            record: L'enregistrement de log à formater.
            
        Returns:
            Le message formaté avec les codes de couleur ANSI.
        """
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


class Logger:
    """
    Classe singleton pour la gestion centralisée des logs.
    
    Cette classe implémente le pattern singleton pour garantir
    une seule instance de logger dans toute l'application.
    
    Attributes:
        _logger: Instance unique du logger (attribut de classe).
        
    Example:
        >>> logger = Logger.get_logger()
        >>> logger.info("Message d'information")
        >>> logger.warning("Message d'avertissement")
    """
    
    _logger: Optional[logging.Logger] = None
    
    # Configuration par défaut
    DEFAULT_LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    DEFAULT_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    DEFAULT_MAX_BYTES: int = 5_000_000  # 5 MB
    DEFAULT_BACKUP_COUNT: int = 3

    @classmethod
    def get_logger(
        cls,
        name: str = "AI Log",
        log_file: str = "app.log",
        level: int = logging.DEBUG
    ) -> logging.Logger:
        """
        Récupère ou crée l'instance unique du logger.
        
        Args:
            name: Nom du logger (utilisé dans les messages).
            log_file: Chemin du fichier de log.
            level: Niveau de log minimum (DEBUG par défaut).
            
        Returns:
            L'instance singleton du logger configuré.
            
        Note:
            Les paramètres ne sont pris en compte qu'à la première
            création du logger. Les appels suivants retournent
            l'instance existante.
        """
        if cls._logger is None:
            cls._logger = cls._create_logger(name, log_file, level)
        return cls._logger

    @classmethod
    def _create_logger(
        cls,
        name: str,
        log_file: str,
        level: int
    ) -> logging.Logger:
        """
        Crée et configure une nouvelle instance de logger.
        
        Args:
            name: Nom du logger.
            log_file: Chemin du fichier de log.
            level: Niveau de log minimum.
            
        Returns:
            Le logger nouvellement configuré.
        """
        # Création du répertoire de logs si nécessaire
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Handler console avec couleurs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            ColorFormatter(cls.DEFAULT_LOG_FORMAT, datefmt=cls.DEFAULT_DATE_FORMAT)
        )

        # Handler fichier avec rotation
        file_formatter = logging.Formatter(
            cls.DEFAULT_LOG_FORMAT,
            datefmt=cls.DEFAULT_DATE_FORMAT
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=cls.DEFAULT_MAX_BYTES,
            backupCount=cls.DEFAULT_BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)

        # Ajout des handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        # Évite la propagation vers le logger racine
        logger.propagate = False

        return logger

    @classmethod
    def reset(cls) -> None:
        """
        Réinitialise le logger singleton.
        
        Utile principalement pour les tests unitaires.
        """
        if cls._logger is not None:
            for handler in cls._logger.handlers[:]:
                handler.close()
                cls._logger.removeHandler(handler)
            cls._logger = None
