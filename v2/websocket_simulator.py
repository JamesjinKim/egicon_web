#!/usr/bin/env python3
"""
WebSocket Simulator for V2 Digital Twin Dashboard
실시간 데이터 시뮬레이션을 위한 WebSocket 관리자

Author: ShinHoTechnology
Version: V2.0 Prototype
Date: 2025-07-08
"""

import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketSimulator:
    """V2 프로토타입용 WebSocket 시뮬레이터"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.is_running = False
        self.update_interval = 2.0  # 2초 간격
        self.simulation_task = None
        
    async def connect(self, websocket: WebSocket):
        """WebSocket 연결 처리"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket 연결됨. 활성 연결: {len(self.active_connections)}")
        
        try:
            # 연결 유지 및 메시지 수신
            while True:
                try:
                    # 클라이언트로부터 메시지 수신 (ping/pong)
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket 메시지 처리 오류: {e}")
                    break
                    
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"🔌 WebSocket 연결 해제됨. 활성 연결: {len(self.active_connections)}")
    
    async def start(self):
        """시뮬레이션 시작"""
        if not self.is_running:
            self.is_running = True
            self.simulation_task = asyncio.create_task(self._simulation_loop())
            logger.info("🚀 WebSocket 시뮬레이션 시작")
    
    async def stop(self):
        """시뮬레이션 중지"""
        self.is_running = False
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ WebSocket 시뮬레이션 중지")
    
    async def _simulation_loop(self):
        """시뮬레이션 루프"""
        from mock_data_generator import MockDataGenerator
        mock_generator = MockDataGenerator()
        await mock_generator.initialize()
        
        while self.is_running:
            try:
                if self.active_connections:
                    # 시간 업데이트
                    mock_generator.update_time()
                    
                    # 실시간 데이터 생성
                    realtime_data = {
                        "type": "realtime_update",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "factory_kpi": mock_generator.get_factory_kpi(),
                            "factory_layout": mock_generator.get_factory_layout(),
                            "neural_network": mock_generator.get_neural_network_status()
                        }
                    }
                    
                    # 모든 연결된 클라이언트에게 전송
                    await self._broadcast(realtime_data)
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"시뮬레이션 루프 오류: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast(self, data: Dict[str, Any]):
        """모든 연결된 클라이언트에게 데이터 전송"""
        if not self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = []
        
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket 전송 오류: {e}")
                disconnected.append(websocket)
        
        # 연결이 끊어진 WebSocket 제거
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_alert(self, process_name: str, alert_type: str, message: str):
        """특정 알림 전송"""
        alert_data = {
            "type": "alert",
            "timestamp": datetime.now().isoformat(),
            "process": process_name,
            "alert_type": alert_type,
            "message": message
        }
        
        await self._broadcast(alert_data)
    
    async def send_process_update(self, process_name: str, data: Dict[str, Any]):
        """공정별 업데이트 전송"""
        update_data = {
            "type": "process_update",
            "timestamp": datetime.now().isoformat(),
            "process": process_name,
            "data": data
        }
        
        await self._broadcast(update_data)
    
    def get_connection_count(self) -> int:
        """현재 연결 수 반환"""
        return len(self.active_connections)
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return len(self.active_connections) > 0