from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger
from typing import Dict, Any

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.voice import Voice
from core.models.service_provider import ServiceProvider

class VoiceService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None):
        super().__init__(db, user_id)


    def get_voices(self):
        return self.db.query(Voice).all()


    def get_voices_by_provider_id(self, provider_id: int):
        try:
            data = self.db.query(Voice, ServiceProvider).join(ServiceProvider, Voice.service_provider_id == ServiceProvider.id).filter(Voice.service_provider_id == provider_id).all()

            provider = data[0][1]

            result = {
            "id": provider.id,
            "uuid": str(provider.uuid),
            "name": provider.name,
            "display_name": provider.display_name,
            "description": provider.description,
            "provider_type": provider.provider_type,
            "logo_url": provider.logo_url,
                "voices": []
            }


            languages = set()
            genders = set()

            for voice, _ in data:
                result["voices"].append({
                    "id": voice.id,
                    "uuid": str(voice.uuid),
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "language": voice.language,
                    "gender": voice.gender,
                    "accent": voice.accent,
                    "description": voice.description,
                    "sample_url": voice.sample_url,
                    "created_at": voice.created_at,
                    "updated_at": voice.updated_at,
                    })
                if voice.language:
                    languages.add(voice.language)
                if voice.gender:
                    genders.add(voice.gender)

            result["languages"] = sorted(languages)
            result["genders"] = sorted(genders)

            return result

        except Exception as e:
            logger.error(f"Error getting voices by provider id: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


    def upsert_voice(self, data: Dict[str, Any]):
        try:
            voice = Voice(
                service_provider_id=data.get("service_provider_id"),
                voice_id=data.get("voice_id"),
                name=data.get("name"),
                language=data.get("language"),
                gender=data.get("gender"),
                accent=data.get("accent"),
                description=data.get("description"),
            )
        except Exception as e:
            logger.error(f"Error upserting voice: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        self.db.add(voice)
        self.db.commit()
        self.db.refresh(voice)
        return voice


    def delete_voice(self, voice_id: int):
        try:
            voice = self.db.query(Voice).filter(Voice.id == voice_id).first()
            if not voice:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")
            self.db.delete(voice)
            self.db.commit()
            return {"message": "Voice deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting voice: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))