from fastapi import APIRouter, Depends, HTTPException, status

from .auth import get_current_user
from .models import QueryRequest, QueryResponse
from .query_service import QueryService
from .repository import UserRepository, get_db

# `tags` adds an Swagger tag for documentation. (Use http://127.0.0.1:8000/docs)
router = APIRouter(tags=["query"])
query_service = QueryService()


@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest, current_user=Depends(get_current_user), conn=Depends(get_db)):
    try:
        # Update last_activity for end users on each query.
        UserRepository(conn).update_last_activity(current_user["user_id"])
        # Loads config.toml, calls search_index(...) to retrieve chunks and maybe generate an LLM answer
        # and return a QueryResponse.
        result = query_service.run_query(
            payload.query,
            top_k=payload.k,
            include_answer=payload.include_answer,
            answer_model=payload.answer_model,
            user_id=current_user["user_id"],
        )
        return result
    except ValueError as e:
        # Bad user input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {e}",
        )
