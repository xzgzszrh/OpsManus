from fastapi import APIRouter, Depends, Query

from app.application.services.node_service import NodeService
from app.interfaces.dependencies import get_current_user, get_node_service
from app.interfaces.schemas.base import APIResponse
from app.interfaces.schemas.node import (
    CreateServerNodeRequest,
    DecideApprovalRequest,
    DecideApprovalResponse,
    ListServerNodesResponse,
    NodeOverviewMetric,
    NodeOverviewResponse,
    PendingApprovalListResponse,
    PendingApprovalItem,
    SSHExecRequest,
    SSHExecResponse,
    SSHLogsResponse,
    SSHLogItem,
    SSHMonitorResponse,
    ServerNodeResponse,
    UpdateServerNodeRequest,
)
from app.domain.models.user import User


router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=APIResponse[ListServerNodesResponse])
async def list_nodes(
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[ListServerNodesResponse]:
    nodes = await node_service.list_nodes(current_user.id)
    return APIResponse.success(ListServerNodesResponse(nodes=[ServerNodeResponse.from_model(node) for node in nodes]))


@router.post("", response_model=APIResponse[ServerNodeResponse])
async def create_node(
    request: CreateServerNodeRequest,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[ServerNodeResponse]:
    node = await node_service.create_node(current_user.id, request.model_dump())
    return APIResponse.success(ServerNodeResponse.from_model(node))


@router.put("/{node_id}", response_model=APIResponse[ServerNodeResponse])
async def update_node(
    node_id: str,
    request: UpdateServerNodeRequest,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[ServerNodeResponse]:
    node = await node_service.update_node(current_user.id, node_id, request.model_dump())
    return APIResponse.success(ServerNodeResponse.from_model(node))


@router.delete("/{node_id}", response_model=APIResponse[None])
async def delete_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[None]:
    await node_service.delete_node(current_user.id, node_id)
    return APIResponse.success()


@router.post("/{node_id}/ssh/exec", response_model=APIResponse[SSHExecResponse])
async def exec_node_ssh(
    node_id: str,
    request: SSHExecRequest,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[SSHExecResponse]:
    result = await node_service.run_command(
        user_id=current_user.id,
        node_id=node_id,
        command=request.command,
        exec_dir=request.exec_dir,
        actor_type="user",
        actor_id=current_user.id,
        source="takeover" if request.sync_to_ai else "manual",
        session_id=request.session_id,
    )
    if request.sync_to_ai and request.session_id:
        await node_service.append_takeover_message(
            session_id=request.session_id,
            node_id=node_id,
            command=result.data.get("command", request.command) if result.data else request.command,
            output=result.data.get("output", "") if result.data else "",
        )
    data = result.data or {}
    return APIResponse.success(
        SSHExecResponse(
            success=result.success,
            output=data.get("output", ""),
            command=data.get("command", request.command),
            node_id=data.get("node_id", node_id),
            node_name=data.get("node_name", ""),
        )
    )


@router.get("/{node_id}/monitor", response_model=APIResponse[SSHMonitorResponse])
async def monitor_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[SSHMonitorResponse]:
    node = await node_service.get_node(current_user.id, node_id)
    info = await node_service.get_monitor_info(current_user.id, node_id)
    return APIResponse.success(
        SSHMonitorResponse(
            node_id=node.id,
            node_name=node.name,
            system_info=info,
        )
    )


@router.get("/{node_id}/overview", response_model=APIResponse[NodeOverviewResponse])
async def node_overview(
    node_id: str,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[NodeOverviewResponse]:
    overview = await node_service.get_node_overview(current_user.id, node_id)
    return APIResponse.success(
        NodeOverviewResponse(
            node_id=overview["node_id"],
            node_name=overview["node_name"],
            checked_at=overview["checked_at"],
            status=overview["status"],
            summary=overview["summary"],
            hostname=overview.get("hostname"),
            os_name=overview.get("os_name"),
            kernel=overview.get("kernel"),
            uptime=overview.get("uptime"),
            load_average=overview.get("load_average"),
            memory_total=overview.get("memory_total"),
            memory_used=overview.get("memory_used"),
            memory_free=overview.get("memory_free"),
            disk_total=overview.get("disk_total"),
            disk_used=overview.get("disk_used"),
            disk_use_percent=overview.get("disk_use_percent"),
            metrics=[NodeOverviewMetric(**metric) for metric in overview.get("metrics", [])],
            raw_output=overview.get("raw_output", ""),
        )
    )


@router.get("/{node_id}/logs", response_model=APIResponse[SSHLogsResponse])
async def list_node_logs(
    node_id: str,
    limit: int = Query(default=100, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[SSHLogsResponse]:
    logs = await node_service.list_logs(current_user.id, node_id, limit)
    return APIResponse.success(SSHLogsResponse(logs=[SSHLogItem.from_model(log) for log in logs]))


@router.get("/sessions/{session_id}/approvals", response_model=APIResponse[PendingApprovalListResponse])
async def list_session_pending_approvals(
    session_id: str,
    _current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[PendingApprovalListResponse]:
    approvals = await node_service.list_pending_approvals(session_id)
    return APIResponse.success(PendingApprovalListResponse(approvals=[PendingApprovalItem.from_model(a) for a in approvals]))


@router.post("/approvals/{approval_id}/decision", response_model=APIResponse[DecideApprovalResponse])
async def decide_approval(
    approval_id: str,
    request: DecideApprovalRequest,
    current_user: User = Depends(get_current_user),
    node_service: NodeService = Depends(get_node_service),
) -> APIResponse[DecideApprovalResponse]:
    result = await node_service.decide_approval(
        user_id=current_user.id,
        approval_id=approval_id,
        approve=request.approve,
        reject_reason=request.reject_reason,
    )
    data = result.data or {}
    return APIResponse.success(
        DecideApprovalResponse(
            approval_id=approval_id,
            status=data.get("status"),
            output=data.get("output"),
        )
    )
