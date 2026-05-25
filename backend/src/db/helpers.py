"""Shared helpers for Supabase response handling.

The Supabase client returns objects with a `.data` attribute that may be
an empty list. Accessing `.data[0]` directly raises IndexError, which
bubbles up as a generic 500 with no useful detail. Use these helpers
to extract the first row safely.
"""
from fastapi import HTTPException


def first_or_500(result, what: str = "record"):
  """Return the first row from a Supabase result, raising HTTPException(500) if empty.

  Args:
    result: The Supabase response object (must have a `.data` attribute).
    what: Singular noun describing what's being fetched. Used in error message.

  Raises:
    HTTPException(500): If `result.data` is empty or None.

  Returns:
    The first element of `result.data`.
  """
  if not result.data:
    raise HTTPException(
      status_code=500,
      detail=f"Database operation succeeded but returned no {what}",
    )
  return result.data[0]
