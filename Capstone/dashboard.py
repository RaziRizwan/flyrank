"""
routers/dashboard.py -- the owner's view of their own data. Every query goes through
repository functions that take tenant_id, same isolation guarantee as widgets.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends

import repository
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(user: CurrentUser = Depends(get_current_user)):
    return repository.submission_stats(tenant_id=user.tenant_id)


@router.get("/submissions")
def get_submissions(widget_id: Optional[int] = None, limit: int = 50,
                     user: CurrentUser = Depends(get_current_user)):
    submissions = repository.list_submissions(tenant_id=user.tenant_id, widget_id=widget_id, limit=limit)
    return [
        {**s, "created_at": s["created_at"].isoformat()}
        for s in submissions
    ]
