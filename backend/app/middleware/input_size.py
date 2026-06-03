"""Reject oversized request bodies before they reach application logic."""

from fastapi import HTTPException, Request, status

MAX_BODY_SIZE = 100 * 1024  # 100 KB


async def input_size_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request body too large. Maximum size is 100KB.",
        )
    return await call_next(request)
