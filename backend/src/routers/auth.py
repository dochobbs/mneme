"""Authentication router for Mneme EMR.

Provides endpoints for user signup, login, logout, and profile management
using Supabase Auth.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from src.db.supabase import get_supabase, get_supabase_admin
from src.middleware.auth import get_current_user, CurrentUser


router = APIRouter(prefix="/auth", tags=["auth"])


# --- Request/Response Models ---

class SignupRequest(BaseModel):
  """Request body for user signup."""
  email: EmailStr
  password: str
  display_name: str
  role: str = "student"
  institution: str | None = None


class LoginRequest(BaseModel):
  """Request body for user login."""
  email: EmailStr
  password: str


class AuthResponse(BaseModel):
  """Response for successful authentication."""
  access_token: str
  refresh_token: str
  user: CurrentUser


class UserProfileResponse(BaseModel):
  """Response for user profile."""
  id: str
  email: str
  display_name: str | None
  role: str
  institution: str | None


class UpdateProfileRequest(BaseModel):
  """Request body for updating user profile."""
  display_name: str | None = None
  institution: str | None = None


class RefreshRequest(BaseModel):
  """Request body for token refresh."""
  refresh_token: str


# --- Endpoints ---

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
  """
  Create a new user account.

  Creates a Supabase Auth user and associated learner profile.
  """
  try:
    supabase = get_supabase()

    # Sign up with Supabase Auth
    auth_response = supabase.auth.sign_up({
      "email": request.email,
      "password": request.password,
      "options": {
        "data": {
          "display_name": request.display_name,
        }
      }
    })

    if not auth_response.user:
      raise HTTPException(status_code=400, detail="Signup failed")

    if not auth_response.session:
      # User created but needs email confirmation
      raise HTTPException(
        status_code=202,
        detail="Account created. Please check your email to confirm your account."
      )

    user = auth_response.user
    session = auth_response.session

    # Update learner profile with additional fields
    # (The trigger should have created the basic record)
    admin_client = get_supabase_admin()
    admin_client.table("learners").update({
      "role": request.role,
      "institution": request.institution,
    }).eq("id", user.id).execute()

    return AuthResponse(
      access_token=session.access_token,
      refresh_token=session.refresh_token,
      user=CurrentUser(
        id=user.id,
        email=user.email or "",
        display_name=request.display_name,
        role=request.role,
      ),
    )

  except HTTPException:
    raise
  except Exception as e:
    error_msg = str(e)
    if "already registered" in error_msg.lower():
      raise HTTPException(status_code=409, detail="Email already registered")
    raise HTTPException(status_code=400, detail=f"Signup failed: {error_msg}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
  """
  Log in with email and password.

  Returns access and refresh tokens for authenticated requests.
  """
  try:
    supabase = get_supabase()

    auth_response = supabase.auth.sign_in_with_password({
      "email": request.email,
      "password": request.password,
    })

    if not auth_response.user or not auth_response.session:
      raise HTTPException(status_code=401, detail="Invalid credentials")

    user = auth_response.user
    session = auth_response.session

    # Get learner profile
    learner_result = supabase.table("learners").select("*").eq("id", user.id).single().execute()

    display_name = None
    role = "student"

    if learner_result.data:
      display_name = learner_result.data.get("display_name")
      role = learner_result.data.get("role", "student")

    return AuthResponse(
      access_token=session.access_token,
      refresh_token=session.refresh_token,
      user=CurrentUser(
        id=user.id,
        email=user.email or "",
        display_name=display_name,
        role=role,
      ),
    )

  except HTTPException:
    raise
  except Exception as e:
    error_msg = str(e)
    if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
      raise HTTPException(status_code=401, detail="Invalid email or password")
    raise HTTPException(status_code=400, detail=f"Login failed: {error_msg}")


@router.post("/logout")
async def logout(user: CurrentUser = Depends(get_current_user)):
  """
  Log out the current user.

  Invalidates the current session.
  """
  try:
    supabase = get_supabase()
    supabase.auth.sign_out()
    return {"message": "Logged out successfully"}
  except Exception as e:
    # Logout should always succeed from client perspective
    return {"message": "Logged out"}


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: CurrentUser = Depends(get_current_user)):
  """
  Get the current user's profile.
  """
  try:
    supabase = get_supabase()
    learner_result = supabase.table("learners").select("*").eq("id", user.id).single().execute()

    institution = None
    if learner_result.data:
      institution = learner_result.data.get("institution")

    return UserProfileResponse(
      id=user.id,
      email=user.email,
      display_name=user.display_name,
      role=user.role,
      institution=institution,
    )

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
  request: UpdateProfileRequest,
  user: CurrentUser = Depends(get_current_user),
):
  """
  Update the current user's profile.
  """
  try:
    update_data = {}
    if request.display_name is not None:
      update_data["display_name"] = request.display_name
    if request.institution is not None:
      update_data["institution"] = request.institution

    if not update_data:
      raise HTTPException(status_code=400, detail="No fields to update")

    admin_client = get_supabase_admin()
    result = admin_client.table("learners").update(update_data).eq("id", user.id).execute()

    if not result.data:
      raise HTTPException(status_code=404, detail="Profile not found")

    updated = result.data[0]

    return UserProfileResponse(
      id=user.id,
      email=user.email,
      display_name=updated.get("display_name"),
      role=updated.get("role", "student"),
      institution=updated.get("institution"),
    )

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
  """
  Refresh the access token using a refresh token.
  """
  try:
    supabase = get_supabase()

    auth_response = supabase.auth.refresh_session(request.refresh_token)

    if not auth_response.user or not auth_response.session:
      raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = auth_response.user
    session = auth_response.session

    # Get learner profile
    learner_result = supabase.table("learners").select("*").eq("id", user.id).single().execute()

    display_name = None
    role = "student"

    if learner_result.data:
      display_name = learner_result.data.get("display_name")
      role = learner_result.data.get("role", "student")

    return AuthResponse(
      access_token=session.access_token,
      refresh_token=session.refresh_token,
      user=CurrentUser(
        id=user.id,
        email=user.email or "",
        display_name=display_name,
        role=role,
      ),
    )

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=401, detail="Failed to refresh token")
