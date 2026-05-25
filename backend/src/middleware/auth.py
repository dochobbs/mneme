"""Authentication middleware for Mneme EMR.

Provides FastAPI dependencies for authenticating requests using Supabase Auth.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, Header
from pydantic import BaseModel
from src.db.supabase import get_supabase


class CurrentUser(BaseModel):
  """Authenticated user information."""
  id: str
  email: str
  display_name: str | None = None
  role: str = "student"


async def get_current_user(
  authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
  """
  Validate the authorization header and return the current user.

  Args:
      authorization: Bearer token from Authorization header

  Returns:
      CurrentUser with user details

  Raises:
      HTTPException: 401 if not authenticated or invalid token
  """
  if not authorization:
    raise HTTPException(
      status_code=401,
      detail="Not authenticated",
      headers={"WWW-Authenticate": "Bearer"},
    )

  if not authorization.startswith("Bearer "):
    raise HTTPException(
      status_code=401,
      detail="Invalid authentication scheme",
      headers={"WWW-Authenticate": "Bearer"},
    )

  token = authorization.split(" ")[1]

  try:
    # Use anon client to validate token
    supabase = get_supabase()
    user_response = supabase.auth.get_user(token)

    if not user_response or not user_response.user:
      raise HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
      )

    user = user_response.user

    # Get learner profile for additional info
    learner_result = supabase.table("learners").select("*").eq("id", user.id).single().execute()

    display_name = None
    role = "student"

    if learner_result.data:
      display_name = learner_result.data.get("display_name")
      role = learner_result.data.get("role", "student")

    return CurrentUser(
      id=user.id,
      email=user.email or "",
      display_name=display_name,
      role=role,
    )

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=401,
      detail=f"Authentication failed: {str(e)}",
      headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
  authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
  """
  Optionally validate the authorization header.

  Returns None if no token is provided, otherwise validates the token.
  Useful for endpoints that work both authenticated and unauthenticated.

  Args:
      authorization: Bearer token from Authorization header

  Returns:
      CurrentUser if authenticated, None otherwise
  """
  if not authorization:
    return None

  try:
    return await get_current_user(authorization)
  except HTTPException:
    return None
