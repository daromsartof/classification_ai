"""
API REST pour le service de classification IA de documents.

Ce module expose des endpoints HTTP pour:
- Vérifier l'état de santé du service
- Déclencher le traitement d'images individuelles
- Gérer les paramètres de classification

Utilisation:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from main import process_single_image
from repositories.ai_separation_setting_repository import AiSeparationSettingRepository
from repositories.image_repository import ImageRepositorie


# =============================================================================
# Modèles Pydantic
# =============================================================================

class ImageIdPayload(BaseModel):
    """
    Payload pour le traitement d'une image.
    
    Attributes:
        id: Identifiant unique de l'image à traiter.
        prompt: Prompt personnalisé pour la classification (optionnel).
    """
    id: int = Field(..., description="Identifiant unique de l'image", gt=0)
    prompt: Optional[str] = Field(
        None,
        description="Prompt système personnalisé pour la classification"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"id": 123, "prompt": None},
                {"id": 456, "prompt": "Instructions spécifiques de classification..."}
            ]
        }
    }


class ImageTrainPayload(BaseModel):
    """
    Payload pour l'entraînement/correction d'une classification.
    
    Attributes:
        id: Identifiant de l'image.
        explication: Explication de la correction.
        old_classification: Ancienne catégorie assignée.
        new_classification: Nouvelle catégorie corrigée.
    """
    id: int = Field(..., description="Identifiant unique de l'image", gt=0)
    explication: Optional[str] = Field(
        None,
        description="Explication de la correction apportée"
    )
    old_classification: Optional[str] = Field(
        None,
        description="Ancienne classification"
    )
    new_classification: Optional[str] = Field(
        None,
        description="Nouvelle classification corrigée"
    )


class HealthResponse(BaseModel):
    """Réponse du endpoint de santé."""
    status: str = Field(..., description="État du service")


class ProcessResponse(BaseModel):
    """Réponse du traitement d'une image."""
    success: bool = Field(..., description="Indique si le traitement a réussi")
    image_id: int = Field(..., description="Identifiant de l'image traitée")
    message: Optional[str] = Field(None, description="Message informatif")


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""
    detail: str = Field(..., description="Description de l'erreur")


# =============================================================================
# Application FastAPI
# =============================================================================

app = FastAPI(
    title="AI Classification API",
    description=(
        "API de classification automatique de documents comptables "
        "utilisant l'intelligence artificielle (OpenAI GPT) et l'OCR."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}
    }
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Vérification de l'état du service",
    description="Vérifie que le service API est opérationnel.",
    tags=["Monitoring"]
)
def health_check() -> HealthResponse:
    """
    Endpoint de vérification de santé.
    
    Returns:
        HealthResponse avec le statut "ok".
    """
    return HealthResponse(status="ok")


@app.post(
    "/process-image",
    response_model=ProcessResponse,
    summary="Traiter une image",
    description=(
        "Déclenche le traitement d'une image spécifique. "
        "L'image sera analysée par OCR puis classifiée via l'IA."
    ),
    tags=["Classification"],
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Service désactivé ou paramètres invalides"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Image non trouvée"
        }
    }
)
async def process_image(payload: ImageIdPayload) -> ProcessResponse:
    """
    Traite une image individuelle.
    
    Args:
        payload: Contient l'ID de l'image et un prompt optionnel.
        
    Returns:
        ProcessResponse avec le résultat du traitement.
        
    Raises:
        HTTPException: Si le service est désactivé, l'image non trouvée,
                      ou en cas d'erreur de traitement.
    """
    try:
        # Vérification de l'état du service
        settings_repo = AiSeparationSettingRepository()
        ai_settings = settings_repo.get_ai_separation_setting()
        
        if not ai_settings or ai_settings.get("power", 1) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le service de classification IA est désactivé"
            )

        # Récupération de l'image
        image_repo = ImageRepositorie()
        images = image_repo.get_image_to_process(payload.id)
        
        if not images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image non trouvée pour l'ID: {payload.id}"
            )

        
        
        # Traitement asynchrone
        loop = asyncio.get_running_loop()
        for image_data in images:   
            await loop.run_in_executor(
                None,
                lambda: process_single_image(
                    image_data,
                    ai_settings
                )
            )

        return ProcessResponse(
            success=True,
            image_id=payload.id,
            message=f"Image traitée avec succès "
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement: {str(exc)}"
        )


@app.get(
    "/settings",
    summary="Récupérer les paramètres",
    description="Retourne les paramètres actuels du service de classification.",
    tags=["Configuration"]
)
async def get_settings() -> dict[str, Any]:
    """
    Récupère les paramètres de configuration du service.
    
    Returns:
        Dictionnaire contenant les paramètres actuels.
    """
    settings_repo = AiSeparationSettingRepository()
    settings = settings_repo.get_ai_separation_setting()
    
    return {
        "power": settings.get("power", 0),
        "model": settings.get("model", "gpt-4o-mini"),
        "ocr_library": settings.get("ocr_library", "pytesseract"),
        "thread_number": settings.get("thread_number", 1)
    }


# =============================================================================
# Point d'entrée
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
