"""Presigned URL upload flow for avatars and attachments."""

import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/media", tags=["media"])
settings = get_settings()

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


def _get_s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


class UploadUrlOut(BaseModel):
    upload_url: str
    public_url: str
    key: str


@router.post("/avatar-upload-url", response_model=UploadUrlOut)
async def get_avatar_upload_url(
    content_type: str = "image/jpeg",
    current_user: User = Depends(get_current_user),
) -> UploadUrlOut:
    if content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type. Allowed: {', '.join(ALLOWED_AVATAR_TYPES)}",
        )

    ext = content_type.split("/")[1].replace("jpeg", "jpg")
    key = f"avatars/{current_user.id}/{uuid.uuid4()}.{ext}"

    try:
        s3 = _get_s3()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.storage_bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": MAX_AVATAR_SIZE,
            },
            ExpiresIn=300,  # 5 minutes
        )
    except ClientError as exc:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL") from exc

    public_url = f"{settings.storage_public_url}/{key}"
    return UploadUrlOut(upload_url=upload_url, public_url=public_url, key=key)
