"""
routers/widgets.py -- authenticated widget management. Every function call passes
current_user.tenant_id into the repository -- there is no code path here that can reach
another tenant's row, because the query itself won't match one.
"""
import os

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

import repository
from auth import get_current_user, CurrentUser
from routers.delivery import BUNDLE_VERSION
from schemas import WidgetCreate, WidgetUpdate

router = APIRouter(prefix="/widgets", tags=["widgets"])

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def with_embed_snippet(widget: dict) -> dict:
    widget = dict(widget)
    widget["embed_snippet"] = (
        f'<script src="{PUBLIC_BASE_URL}/widget.js?v={BUNDLE_VERSION}&id={widget["id"]}"></script>'
    )
    return widget


@router.post("", status_code=201)
def create_widget(payload: WidgetCreate, user: CurrentUser = Depends(get_current_user)):
    widget = repository.create_widget(
        tenant_id=user.tenant_id,
        type_=payload.type,
        title=payload.title,
        description=payload.description,
        fields=[f.model_dump() for f in payload.fields],
        button_text=payload.button_text,
        display_options=payload.display_options,
    )
    return JSONResponse(status_code=201, content=jsonable_encoder(with_embed_snippet(widget)))


@router.get("")
def list_widgets(user: CurrentUser = Depends(get_current_user)):
    widgets = repository.list_widgets(tenant_id=user.tenant_id)
    return [with_embed_snippet(w) for w in widgets]


@router.get("/{widget_id}")
def get_widget(widget_id: int, user: CurrentUser = Depends(get_current_user)):
    widget = repository.get_widget(tenant_id=user.tenant_id, widget_id=widget_id)
    if widget is None:
        return error(404, f"widget {widget_id} not found")
    return with_embed_snippet(widget)


@router.put("/{widget_id}")
def update_widget(widget_id: int, payload: WidgetUpdate, user: CurrentUser = Depends(get_current_user)):
    update_kwargs = {}
    if payload.type is not None:
        update_kwargs["type_"] = payload.type
    if payload.title is not None:
        update_kwargs["title"] = payload.title
    if payload.description is not None:
        update_kwargs["description"] = payload.description
    if payload.fields is not None:
        update_kwargs["fields"] = [f.model_dump() for f in payload.fields]
    if payload.button_text is not None:
        update_kwargs["button_text"] = payload.button_text
    if payload.display_options is not None:
        update_kwargs["display_options"] = payload.display_options

    if not update_kwargs:
        return error(400, "request body must include at least one field to update")

    widget = repository.update_widget(tenant_id=user.tenant_id, widget_id=widget_id, **update_kwargs)
    if widget is None:
        return error(404, f"widget {widget_id} not found")
    return with_embed_snippet(widget)


@router.delete("/{widget_id}", status_code=204)
def delete_widget(widget_id: int, user: CurrentUser = Depends(get_current_user)):
    from fastapi import Response
    deleted = repository.delete_widget(tenant_id=user.tenant_id, widget_id=widget_id)
    if not deleted:
        return error(404, f"widget {widget_id} not found")
    return Response(status_code=204)
