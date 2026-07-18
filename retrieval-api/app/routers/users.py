import psycopg
from fastapi import APIRouter, Depends

from app.deps import get_db
from app.models import UserResponse, UserUpsertRequest
from app.services.users import upsert_user

router = APIRouter()


@router.post("/users/upsert", response_model=UserResponse)
def post_user_upsert(
    body: UserUpsertRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> UserResponse:
    """Upsert a GitHub user (called by the BFF after OAuth) and return the internal id."""
    row = upsert_user(conn, body.github_id, body.username, body.name, body.avatar_url)
    return UserResponse(**row)
