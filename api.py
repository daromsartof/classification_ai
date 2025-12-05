from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from repositories.ai_separation_setting_repository import AiSeparationSettingRepository
from repositories.image_repository import ImageRepositorie
from main import process_single_image


class ImageIdPayload(BaseModel):
    id: int
    prompt: Optional[str] = None

class ImageTrainPayload(BaseModel):
    id: int
    explication: Optional[str] = None
    old_classification: Optional[str] = None
    new_classification: Optional[str] = None


app = FastAPI(title="AI Separation API", version="1.0.0")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/process-image")
async def process_image(payload: ImageIdPayload):
    try:
        settings_repo = AiSeparationSettingRepository()
        ai_settings = settings_repo.get_ai_separation_setting()
        if not ai_settings or ai_settings.get("power", 1) != 1:
            raise HTTPException(status_code=400, detail="AI Separation is not enabled or power is off")

        image_repo = ImageRepositorie()
        images: List[Dict[str, Any]] = image_repo.get_image_to_process(payload.id)
        if not images:
            raise HTTPException(status_code=404, detail=f"Image not found for id: {payload.id}")

        image_data = images[0]
        loop = asyncio.get_running_loop()
        #result = await loop.run_in_executor(None, lambda: process_single_image(image_data, ai_settings, payload.prompt))
        
        return {"success": bool(True), "image_id": payload.id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
