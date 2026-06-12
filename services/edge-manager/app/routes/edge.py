from fastapi import APIRouter, status, Request
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid

router = APIRouter()

class DeviceRegister(BaseModel):
    mac_address: str
    name: str
    hardware_specs: Dict[str, Any]

@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
async def register_device(request: DeviceRegister, http_request: Request):
    """
    Registers a new edge device (e.g. Raspberry Pi, Jetson) calling home.
    """
    device_id = str(uuid.uuid4())
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    return {
        "data": {
            "id": device_id,
            "mac_address": request.mac_address,
            "name": request.name,
            "status": "online",
            "ip_address": client_ip,
            "message": "Device successfully registered."
        }
    }

@router.post("/devices/{device_id}/heartbeat", status_code=status.HTTP_200_OK)
async def heartbeat(device_id: str):
    """
    Receives periodic ping from the edge device to maintain online status.
    """
    return {"data": {"status": "ok", "device_id": device_id}}

@router.get("/devices/{device_id}/deployments", status_code=status.HTTP_200_OK)
async def poll_deployments(device_id: str):
    """
    Edge device polls this endpoint to discover assigned models or agents it should run locally.
    """
    # Mocking a deployment response
    return {
        "data": [
            {
                "deployment_id": str(uuid.uuid4()),
                "workload_type": "model",
                "workload_id": "gguf-llama-3-8b-instruct",
                "version": "v1.0",
                "status": "pending_download",
                "download_url": "s3://eaioc-edge-models/llama-3-8b.gguf"
            }
        ]
    }
