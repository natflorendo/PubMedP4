from __future__ import annotations

import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from pipeline.utils.metadata_loader import ArticleMetadata, load_metadata_rows

from .auth import require_roles
from .models import DocumentSummary
from .pipeline_service import PipelineService
from .repository import DocumentRepository, get_db


# `prefix` adds the given prefix to every route inside this router.
# `tags` adds an Swagger tag for documentation. (Use http://127.0.0.1:8000/docs)
router = APIRouter(prefix="/curator", tags=["curator"])
pipeline_service = PipelineService()
_curator_guard = require_roles(["curator", "admin"])


def get_current_curator(user=Depends(_curator_guard)):
    """Returns the currently authenticated curator user."""
    return user


def get_document_repo(conn=Depends(get_db)):
    """Provides a DocumentRepository instance."""
    return DocumentRepository(conn)


def _persist_upload(upload: UploadFile, destination: Path) -> None:
    """Save an UploadFile to disk."""
    # Ensures the folder containing destination exists
    # parents=True ensures that all the parent directoies exist
    # exist_ok=True continues silently if the dirctory already exists instead of raising an error.
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Moves the file pointer back to the start. This is important after the first run because you might
    # write from the middle/end.
    upload.file.seek(0)
    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # Opens the destination path for writing in binary mode
    with destination.open("wb") as buffer:
        # Copies bytes from the uploaded file stream into the destination file stream.
        shutil.copyfileobj(upload.file, buffer)


# Return a tuple rather than a list because it is immutable
# Very similar to _parse_authors in pipeline/metadata_parser.py
def _normalize_authors(value: str | None) -> tuple[str, ...]:
    """Split and clean an authors string into a normalized tuple of author names."""
    if not value:
        return tuple()
    parts = re.split(r"[;,]", value)
    # First strip() gets rid of leading/trailing whitespace.
    # Second strip removes trailing periods (e.g., "McFarlane SI." -> "McFarlane SI")
    # Split on ',' or ';' and clean each segment.
    parts = [segment.strip().strip(".") for segment in parts]
    # None removes any empty strings ("") that may have been stored in parts
    return tuple(filter(None, parts))


def _strip(value: str | None) -> str | None:
    """
    Trim surrounding whitespace from a string safely. Unlike calling `.strip()` directly, this helper
    handles None without crashing and converts blank/whitespace-only strings to None (instead of "").
    """
    return value.strip() if value and value.strip() else None


def _parse_int(value: str | None) -> int | None:
    """Safely parse an optional string into an int."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _metadata_from_form(
    pmid: str | None,
    title: str | None,
    authors: str | None,
    doi: str | None,
    journal_name: str | None,
    publication_year: str | None,
    create_date: str | None,
    citation: str | None,
    first_author: str | None,
    pmcid: str | None,
    nihmsid: str | None,
) -> ArticleMetadata:
    """Takes a bunch of values that came from a form upload (all strings or None) and returns an ArticleMetadata object."""
    if not pmid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata form requires a PMID value.",
        )
    try:
        pmid_value = int(pmid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PMID must be an integer.",
        )

    # Use the internal strip function to normalize a lot of the fields (handles None without crashing)
    title_value = _strip(title) or f"PMID {pmid_value}"
    authors_list = _normalize_authors(authors)
    first_author_value = _strip(first_author) or (authors_list[0] if authors_list else None)

    return ArticleMetadata(
        pmid=pmid_value,
        title=title_value,
        authors=authors_list,
        citation=_strip(citation),
        first_author=first_author_value,
        journal_name=_strip(journal_name),
        publication_year=_parse_int(publication_year),
        create_date=_strip(create_date),
        pmcid=_strip(pmcid),
        nihmsid=_strip(nihmsid),
        doi=_strip(doi.lower() if doi else None),
    )


# `status_code=201` sets the default HTTP status
# File(...) means the field must be included
# Requires curator or admin role to upload documents
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    document: UploadFile = File(...),
    metadata_csv: UploadFile | None = File(None),
    pmid: str | None = Form(None),
    title: str | None = Form(None),
    authors: str | None = Form(None),
    doi: str | None = Form(None),
    journal_name: str | None = Form(None),
    publication_year: str | None = Form(None),
    create_date: str | None = Form(None),
    citation: str | None = Form(None),
    first_author: str | None = Form(None),
    pmcid: str | None = Form(None),
    nihmsid: str | None = Form(None),
    current_user=Depends(get_current_curator),
):
    """
    Handle curator uploads. 
    Supports either CSV metadata (Phase 3 schema) or manual metadata form fields (PMID, title, DOI, etc.).
    """
    filename = document.filename or "uploaded_document"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF or plain-text documents are supported.",
        )

    # Creates a temporary folder that automatically deletes itself afterward.
    with TemporaryDirectory() as tmpdir:
        tmp_dir_path = Path(tmpdir)
        doc_path = tmp_dir_path / Path(filename).name
        # Saves the uploaded document to disk at doc_path.
        _persist_upload(document, doc_path)

        # CSV or form metadata source
        metadata_rows: List[ArticleMetadata]
        metadata_source: str
        # If a CSV was uploaded, use that.
        if metadata_csv is not None:
            csv_path = tmp_dir_path / Path(metadata_csv.filename or "metadata.csv").name
            # Saves the csv to disk at csv_path.
            _persist_upload(metadata_csv, csv_path)
            try:
                # Try to parse the CSV into a list of structured ArticleMetadata objects.
                metadata_rows = load_metadata_rows(csv_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Metadata CSV could not be parsed: {e}",
                )
            # Record that metadata came from CSV for response.
            metadata_source = "csv"
        # Fall back to manual form metadata.
        else:
            if not pmid or not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Metadata form requires at least PMID and title when no CSV is provided.",
                )
            # Convert the form fields into a ArticleMetadata object.
            metadata_rows = [
                _metadata_from_form(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    doi=doi,
                    journal_name=journal_name,
                    publication_year=publication_year,
                    create_date=create_date,
                    citation=citation,
                    first_author=first_author,
                    pmcid=pmcid,
                    nihmsid=nihmsid,
                )
            ]
            # Record that metadata came from form for response.
            metadata_source = "form"

        # Try to run pipeline for a single uploaded document.
        try:
            result = pipeline_service.ingest_document(
                doc_path, 
                metadata_rows,
                added_by=current_user.get("user_id"),
            )
        except HTTPException:
            raise
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to match document to metadata: {e}",
            )
        except ValueError as e:
            # Bad user input
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to ingest document: {e}",
            )

    return {
        "message": "Document ingested successfully.",
        "pmid": result.pmid,
        "doc_id": result.doc_id,
        "title": result.title,
        "chunks": result.chunk_count,
        "embeddings": result.embedding_count,
        "metadata_source": metadata_source,
    }


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_curator)
):
    """Return a list of curator added documents with its metadata."""
    documents = []
    for record in repo.list_curator_documents():
        # `**`` is a dictionary unpacking operator. It means “take all the key–value pairs in 
        # this dict and pass them as keyword arguments.
        documents.append(DocumentSummary(**record))
    return documents


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_curator),
):
    """
    Delete a curator added document by its ID.
    Curators may only delete documents they originally uploaded, while admins can delete any document.
    """
    user_roles = {role.lower() for role in current_user.get("roles", [])}
    is_admin = "admin" in user_roles
    try:
        # Checks the document exists, enforces only owner curator unless admin, then deletes document.
        deleted = repo.delete_document(doc_id, current_user["user_id"], is_admin)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(e)
        )

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
