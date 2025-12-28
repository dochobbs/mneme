"""Import API routes for Mneme EMR."""

import json
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from src.db.supabase import SupabaseDB
from src.importers.oread_json import OreadImporter

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportResult(BaseModel):
  """Result of an import operation."""
  success: bool
  import_id: str | None = None
  patient_count: int = 0
  details: dict = {}
  errors: list[str] = []


@router.post("/oread")
async def import_oread_json(file: UploadFile = File(...)) -> ImportResult:
  """
  Import an oread JSON patient file.

  Accepts a single patient JSON file from oread and imports it
  into the Mneme database.
  """
  if not file.filename.endswith(".json"):
    raise HTTPException(status_code=400, detail="File must be a JSON file")

  db = SupabaseDB()

  # Create import record
  import_record = db.create_import_record(file.filename, "oread-json")
  import_id = import_record.data[0]["id"]

  try:
    # Read and parse the file
    content = await file.read()
    data = json.loads(content.decode("utf-8"))

    # Import the patient
    importer = OreadImporter(db)
    result = importer.import_patient(data, source_file=file.filename)

    if result["success"]:
      db.update_import_record(import_id, "completed", patient_count=1)
      return ImportResult(
        success=True,
        import_id=import_id,
        patient_count=1,
        details={
          "patient_id": result["patient_id"],
          "counts": result["counts"],
        },
      )
    else:
      db.update_import_record(import_id, "failed", error="; ".join(result["errors"]))
      return ImportResult(
        success=False,
        import_id=import_id,
        errors=result["errors"],
      )

  except json.JSONDecodeError as e:
    db.update_import_record(import_id, "failed", error=f"Invalid JSON: {str(e)}")
    raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
  except Exception as e:
    db.update_import_record(import_id, "failed", error=str(e))
    raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/oread/batch")
async def import_oread_batch(files: list[UploadFile] = File(...)) -> ImportResult:
  """
  Import multiple oread JSON patient files.

  Accepts multiple patient JSON files and imports them all.
  """
  db = SupabaseDB()

  # Create import record for batch
  import_record = db.create_import_record(
    f"batch_{len(files)}_files",
    "oread-json-batch"
  )
  import_id = import_record.data[0]["id"]

  results = {
    "successful": 0,
    "failed": 0,
    "patients": [],
    "errors": [],
  }

  importer = OreadImporter(db)

  for file in files:
    if not file.filename.endswith(".json"):
      results["failed"] += 1
      results["errors"].append(f"{file.filename}: Not a JSON file")
      continue

    try:
      content = await file.read()
      data = json.loads(content.decode("utf-8"))

      result = importer.import_patient(data, source_file=file.filename)

      if result["success"]:
        results["successful"] += 1
        results["patients"].append({
          "file": file.filename,
          "patient_id": result["patient_id"],
          "counts": result["counts"],
        })
      else:
        results["failed"] += 1
        results["errors"].extend(result["errors"])

    except Exception as e:
      results["failed"] += 1
      results["errors"].append(f"{file.filename}: {str(e)}")

  # Update import record
  status = "completed" if results["failed"] == 0 else "partial"
  if results["successful"] == 0:
    status = "failed"

  db.update_import_record(
    import_id,
    status,
    patient_count=results["successful"],
    error="; ".join(results["errors"][:5]) if results["errors"] else None,
  )

  return ImportResult(
    success=results["failed"] == 0,
    import_id=import_id,
    patient_count=results["successful"],
    details={
      "patients": results["patients"],
      "failed_count": results["failed"],
    },
    errors=results["errors"],
  )


@router.get("/history")
async def get_import_history(limit: int = 20):
  """Get recent import operations."""
  db = SupabaseDB()

  result = (
    db.client.table("imports")
    .select("*")
    .order("created_at", desc=True)
    .limit(limit)
    .execute()
  )

  return result.data


@router.get("/{import_id}")
async def get_import_status(import_id: str):
  """Get status of a specific import."""
  db = SupabaseDB()

  result = (
    db.client.table("imports")
    .select("*")
    .eq("id", import_id)
    .single()
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Import not found")

  return result.data
