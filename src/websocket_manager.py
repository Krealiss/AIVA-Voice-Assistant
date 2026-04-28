"""
WebSocket manager для real-time оновлень dashboard
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    """Менеджер WebSocket з'єднань"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Підключити нового клієнта"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or f"client-{len(self.active_connections)}",
            "connected_at": datetime.now().isoformat()
        }
        logger.info(f"Client connected: {self.connection_info[websocket]['client_id']}")

        # Відправляємо привітання
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "client_id": self.connection_info[websocket]["client_id"],
            "timestamp": datetime.now().isoformat()
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """Відключити клієнта"""
        if websocket in self.active_connections:
            client_id = self.connection_info.get(websocket, {}).get("client_id", "unknown")
            self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            logger.info(f"Client disconnected: {client_id}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Відправити повідомлення конкретному клієнту"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any], exclude: WebSocket = None):
        """Відправити повідомлення всім клієнтам"""
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Видаляємо відключені з'єднання
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_command(self, command: str, response: str, source: str, success: bool):
        """Broadcast виконаної команди"""
        await self.broadcast({
            "type": "command",
            "data": {
                "command": command,
                "response": response,
                "source": source,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        })

    async def broadcast_status(self, status: Dict[str, Any]):
        """Broadcast статусу системи"""
        await self.broadcast({
            "type": "status",
            "data": status
        })

    async def broadcast_log(self, level: str, message: str):
        """Broadcast лог повідомлення"""
        await self.broadcast({
            "type": "log",
            "data": {
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        })

    def get_active_count(self) -> int:
        """Отримати кількість активних з'єднань"""
        return len(self.active_connections)


# Глобальний екземпляр менеджера
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для dashboard"""
    client_id = None
    try:
        await manager.connect(websocket)

        while True:
            # Отримуємо повідомлення від клієнта
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    # Відповідаємо на ping
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

                elif msg_type == "subscribe":
                    # Клієнт підписується на оновлення
                    channels = message.get("channels", [])
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "channels": channels
                    }, websocket)

                elif msg_type == "command":
                    # Клієнт відправляє команду
                    command = message.get("command")
                    # TODO: Виконати команду через handle_intent
                    await manager.broadcast_command(
                        command=command,
                        response="Command received",
                        source="web",
                        success=True
                    )

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
