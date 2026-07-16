import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

active_connections: dict[int, WebSocket] = {}


def get_user_id_from_token(token: str) -> int | None:
    from core.security import decode_token

    payload = decode_token(token)
    if payload:
        sub = payload.get("sub")
        if sub:
            try:
                return int(sub)
            except (ValueError, TypeError):
                pass
    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = None

    try:
        auth_msg = await websocket.receive_text()
        data = json.loads(auth_msg)
        token = data.get("token", "")
        user_id = get_user_id_from_token(token)
        if not user_id:
            await websocket.send_json({"type": "error", "data": {"message": "Auth failed"}})
            await websocket.close()
            return

        active_connections[user_id] = websocket

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "typing_start":
                match_id = msg.get("data", {}).get("match_id")
                await websocket.send_json({"type": "typing_ack", "data": {"match_id": match_id}})

            elif msg_type == "typing_stop":
                match_id = msg.get("data", {}).get("match_id")
                await websocket.send_json({"type": "typing_stop_ack", "data": {"match_id": match_id}})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if user_id is not None and user_id in active_connections:
            del active_connections[user_id]


async def notify_user(user_id: int, event_type: str, data: dict):
    if user_id in active_connections:
        try:
            await active_connections[user_id].send_json({"type": event_type, "data": data})
        except Exception:
            active_connections.pop(user_id, None)
