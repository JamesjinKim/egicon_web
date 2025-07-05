#!/usr/bin/env python3
"""
EG-ICON WebSocket 관리자 모듈
===========================
main.py에서 분리된 WebSocket 실시간 통신 로직
"""

import asyncio
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
from hardware_scanner import get_scanner
from sensor_handlers import read_sensor_data

class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket):
        """새 WebSocket 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        print(f"📡 새 WebSocket 연결 (총 {len(self.active_connections)}개)")
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"📡 WebSocket 연결 해제 (총 {len(self.active_connections)}개)")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """개별 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"❌ 개별 메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        if not self.active_connections:
            return
            
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"❌ 브로드캐스트 전송 실패: {e}")
                disconnected_connections.append(connection)
        
        # 끊어진 연결 정리
        for connection in disconnected_connections:
            self.disconnect(connection)

# 전역 연결 관리자 인스턴스
manager = ConnectionManager()

class RealTimeDataCollector:
    """실시간 데이터 수집기"""
    
    def __init__(self):
        self.is_running = False
        self.collection_interval = 2.0  # 2초 간격
        self.sensors_cache = []
        self.last_scan_time = 0
        self.scan_interval = 60  # 60초마다 센서 목록 갱신
    
    async def start_collection(self):
        """실시간 데이터 수집 시작"""
        if self.is_running:
            return
            
        self.is_running = True
        print("🚀 실시간 데이터 수집 시작")
        
        try:
            while self.is_running:
                current_time = time.time()
                
                # 주기적으로 센서 목록 갱신
                if current_time - self.last_scan_time > self.scan_interval:
                    await self.refresh_sensor_list()
                    self.last_scan_time = current_time
                
                # 실시간 데이터 수집 및 브로드캐스트
                if manager.active_connections:
                    await self.collect_and_broadcast_data()
                
                await asyncio.sleep(self.collection_interval)
                
        except Exception as e:
            print(f"❌ 실시간 데이터 수집 오류: {e}")
        finally:
            self.is_running = False
            print("🛑 실시간 데이터 수집 중지")
    
    async def stop_collection(self):
        """실시간 데이터 수집 중지"""
        self.is_running = False
    
    async def refresh_sensor_list(self):
        """센서 목록 갱신"""
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            if scan_result.get("success", False):
                self.sensors_cache = scan_result.get("sensors", [])
                print(f"📋 센서 목록 갱신: {len(self.sensors_cache)}개 센서")
            else:
                print("⚠️ 센서 스캔 실패, 기존 목록 유지")
                
        except Exception as e:
            print(f"❌ 센서 목록 갱신 실패: {e}")
    
    async def collect_and_broadcast_data(self):
        """센서 데이터 수집 및 브로드캐스트"""
        try:
            sensor_data_list = []
            current_time = time.time()
            
            # I2C 센서 데이터 수집
            for sensor in self.sensors_cache:
                if sensor.get("interface") != "UART":  # I2C 센서만
                    try:
                        data = await read_sensor_data(sensor)
                        if data and "error" not in data:
                            sensor_data_list.append(data)
                    except Exception as sensor_error:
                        print(f"⚠️ 센서 데이터 읽기 실패 {sensor.get('sensor_name', 'Unknown')}: {sensor_error}")
            
            # SPS30 UART 센서 데이터 추가
            try:
                from main import get_sps30_thread
                sps30_thread = get_sps30_thread()
                
                if sps30_thread and sps30_thread.is_healthy():
                    sps30_data = sps30_thread.get_current_data()
                    
                    if sps30_data and sps30_data.get('connected', False):
                        # SPS30 데이터를 센서 데이터 형식으로 변환
                        sps30_sensor_data = {
                            "sensor_id": "sps30_uart",
                            "sensor_name": "SPS30",
                            "sensor_type": "SPS30",
                            "interface": "UART",
                            "timestamp": current_time,
                            "values": {
                                "pm1": sps30_data.get('pm1', 0.0),
                                "pm25": sps30_data.get('pm25', 0.0),
                                "pm4": sps30_data.get('pm4', 0.0),
                                "pm10": sps30_data.get('pm10', 0.0)
                            },
                            "units": {
                                "pm1": "μg/m³",
                                "pm25": "μg/m³", 
                                "pm4": "μg/m³",
                                "pm10": "μg/m³"
                            },
                            "status": "connected",
                            "data_age": sps30_data.get('data_age_seconds', 0)
                        }
                        sensor_data_list.append(sps30_sensor_data)
                        print(f"📊 SPS30 데이터 추가: PM2.5={sps30_data.get('pm25', 0):.1f} μg/m³")
                    
            except Exception as sps30_error:
                print(f"⚠️ SPS30 데이터 추가 실패: {sps30_error}")
            
            # 데이터가 있으면 브로드캐스트
            if sensor_data_list:
                realtime_message = {
                    "type": "sensor_data",
                    "timestamp": current_time,
                    "data": sensor_data_list,
                    "sensor_count": len(sensor_data_list)
                }
                
                await manager.broadcast(json.dumps(realtime_message))
                print(f"📡 실시간 데이터 브로드캐스트: {len(sensor_data_list)}개 센서")
            
        except Exception as e:
            print(f"❌ 데이터 수집/브로드캐스트 실패: {e}")

# 전역 데이터 수집기 인스턴스
data_collector = RealTimeDataCollector()

def setup_websocket_routes(app):
    """WebSocket 라우트 설정"""
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """실시간 센서 데이터 WebSocket 엔드포인트"""
        await manager.connect(websocket)
        
        # 첫 연결 시 데이터 수집 시작
        if len(manager.active_connections) == 1 and not data_collector.is_running:
            asyncio.create_task(data_collector.start_collection())
        
        try:
            # 연결 유지 및 클라이언트 메시지 처리
            while True:
                try:
                    # 클라이언트로부터 메시지 대기 (ping/pong 등)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    # 클라이언트 메시지 처리
                    try:
                        client_data = json.loads(message)
                        
                        if client_data.get("type") == "ping":
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "timestamp": time.time()
                            }))
                        elif client_data.get("type") == "request_status":
                            # 상태 정보 전송
                            status_data = {
                                "type": "status",
                                "connections": len(manager.active_connections),
                                "sensors": len(data_collector.sensors_cache),
                                "collector_running": data_collector.is_running,
                                "timestamp": time.time()
                            }
                            await websocket.send_text(json.dumps(status_data))
                            
                    except json.JSONDecodeError:
                        print(f"⚠️ 잘못된 JSON 메시지: {message}")
                        
                except asyncio.TimeoutError:
                    # 타임아웃 시 ping 전송
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": time.time()
                    }))
                    
        except WebSocketDisconnect:
            print("📡 WebSocket 클라이언트 연결 해제")
        except Exception as e:
            print(f"❌ WebSocket 오류: {e}")
        finally:
            manager.disconnect(websocket)
            
            # 마지막 연결이 해제되면 데이터 수집 중지
            if len(manager.active_connections) == 0 and data_collector.is_running:
                await data_collector.stop_collection()

    return app

# WebSocket 유틸리티 함수들
async def broadcast_system_message(message_type: str, data: Any):
    """시스템 메시지 브로드캐스트"""
    message = {
        "type": message_type,
        "timestamp": time.time(),
        "data": data
    }
    await manager.broadcast(json.dumps(message))

async def get_connection_stats():
    """연결 통계 반환"""
    return {
        "active_connections": len(manager.active_connections),
        "total_connections": manager.connection_count,
        "collector_running": data_collector.is_running,
        "cached_sensors": len(data_collector.sensors_cache)
    }