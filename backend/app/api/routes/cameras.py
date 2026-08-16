"""Camera routes. Lifecycle is delegated to CameraService."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CameraManagerDep
from app.cameras.types import CameraStatus
from app.schemas.camera import CameraListResponse
from app.services.camera import CameraService

router = APIRouter(prefix="/cameras", tags=["cameras"])


def get_camera_service(manager: CameraManagerDep) -> CameraService:
    return CameraService(manager)


CameraServiceDep = Annotated[CameraService, Depends(get_camera_service)]


@router.get("")
def list_cameras(service: CameraServiceDep) -> CameraListResponse:
    return CameraListResponse(cameras=service.list_cameras())


@router.get("/{camera_id}")
def get_camera(camera_id: str, service: CameraServiceDep) -> CameraStatus:
    return service.get_camera(camera_id)


@router.post("/{camera_id}/start")
def start_camera(camera_id: str, service: CameraServiceDep) -> CameraStatus:
    return service.start_camera(camera_id)


@router.post("/{camera_id}/stop")
def stop_camera(camera_id: str, service: CameraServiceDep) -> CameraStatus:
    return service.stop_camera(camera_id)
