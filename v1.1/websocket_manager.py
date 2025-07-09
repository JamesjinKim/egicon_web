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
    """
    WebSocket 연결 관리 및 메시지 브로드캐스트 관리자
    
    운영 시 중요사항:
    - 다중 클라이언트 동시 접속 지원
    - 끊어진 연결 자동 감지 및 정리
    - 메시지 전송 실패 시 연결 목록에서 자동 제거
    - Thread-safe 연결 관리로 동시성 문제 방지
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket):
        """
        새로운 WebSocket 클라이언트 연결 수락
        
        운영 시 중요사항:
        - WebSocket 핸드셰이크 수행 후 연결 목록에 추가
        - 연결 개수 카운터 증가
        - 트래픽 모니터링을 위한 로그 출력
        
        Args:
            websocket (WebSocket): 연결할 WebSocket 인스턴스
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        print(f"📡 새 WebSocket 연결 (총 {len(self.active_connections)}개)")
    
    def disconnect(self, websocket: WebSocket):
        """
        WebSocket 클라이언트 연결 해제 및 정리
        
        운영 시 중요사항:
        - 연결 목록에서 해당 WebSocket 제거
        - 중복 제거 요청 시 예외 발생 방지
        - 연결 수 변화 로그 출력
        
        Args:
            websocket (WebSocket): 해제할 WebSocket 인스턴스
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"📡 WebSocket 연결 해제 (총 {len(self.active_connections)}개)")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        특정 클라이언트에게 개별 메시지 전송
        
        운영 시 중요사항:
        - 메시지 전송 실패 시 연결 자동 해제
        - 끊어진 연결에 대한 예외 처리
        - 개별 클라이언트 대상 메시지 (상태 응답 등)
        
        Args:
            message (str): 전송할 메시지 (JSON 문자열)
            websocket (WebSocket): 대상 WebSocket 연결
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"❌ 개별 메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """
        모든 연결된 클라이언트에게 동시 메시지 브로드캐스트
        
        운영 시 중요사항:
        - 실시간 센서 데이터 브로드캐스트용 메인 함수
        - 끊어진 연결 자동 감지 및 정리
        - 메시지 전송 실패 시 올바른 오류 처리
        - 빈 연결 목록에 대한 조기 종료 처리
        
        Args:
            message (str): 브로드캐스트할 메시지 (JSON 문자열)
        """
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
    """
    센서 데이터 실시간 수집 및 WebSocket 브로드캐스트 관리자
    
    운영 시 중요사항:
    - 비동기 백그라운드 루프로 주기적 데이터 수집
    - I2C 센서와 UART 센서(SPS30) 동시 처리
    - 센서 목록 주기적 갱신으로 하드웨어 변경 대응
    - WebSocket 클라이언트 있을 때만 데이터 수집
    - 데이터 수집 실패 시에도 시스템 계속 운영
    """
    
    def __init__(self):
        self.is_running = False
        self.collection_interval = 2.0  # 2초 간격
        self.sensors_cache = []
        self.last_scan_time = 0
        self.scan_interval = 60  # 60초마다 센서 목록 갱신
        
        # SHT40 전용 설정
        self.sht40_collection_interval = 3.0  # SHT40 센서는 3초 간격 (검증된 안정적 간격)
        self.last_sht40_scan_time = 0
        self.sht40_scan_interval = 60  # SHT40 센서 재스캔 간격
    
    async def start_collection(self):
        """
        비동기 데이터 수집 루프 시작
        
        운영 시 중요사항:
        - 이미 실행 중인 경우 중복 시작 방지
        - 센서 목록 주기적 갱신 (60초 간격)
        - WebSocket 클라이언트 있을 때만 데이터 수집 수행
        - 예외 발생 시에도 안전한 루프 종료 보장
        - 2초 간격 데이터 수집 및 브로드캐스트
        """
        if self.is_running:
            return
            
        self.is_running = True
        print("🚀 실시간 데이터 수집 시작")
        
        try:
            # 첫 실행 시 SHT40 센서 목록 로드
            await self.refresh_sht40_sensor_list()
            last_sht40_collection = 0
            
            while self.is_running:
                current_time = time.time()
                
                # 주기적으로 일반 센서 목록 갱신
                if current_time - self.last_scan_time > self.scan_interval:
                    await self.refresh_sensor_list()
                    self.last_scan_time = current_time
                
                # 주기적으로 SHT40 센서 목록 갱신
                if current_time - self.last_sht40_scan_time > self.sht40_scan_interval:
                    await self.refresh_sht40_sensor_list()
                    self.last_sht40_scan_time = current_time
                
                # WebSocket 클라이언트가 있을 때만 데이터 수집
                if manager.active_connections:
                    # 일반 센서 데이터 수집 (2초 간격)
                    await self.collect_and_broadcast_data()
                    
                    # SHT40 센서 데이터 수집 (3초 간격)
                    if current_time - last_sht40_collection >= self.sht40_collection_interval:
                        await self.collect_and_broadcast_sht40_data()
                        last_sht40_collection = current_time
                
                await asyncio.sleep(self.collection_interval)
                
        except Exception as e:
            print(f"❌ 실시간 데이터 수집 오류: {e}")
        finally:
            self.is_running = False
            print("🛑 실시간 데이터 수집 중지")
    
    async def stop_collection(self):
        """
        데이터 수집 루프 안전 중지
        
        운영 시 중요사항:
        - is_running 플래그를 통한 우아한 종료
        - 마지막 WebSocket 클라이언트 연결 해제 시 자동 호출
        - 리소스 절약을 위한 백그라운드 작업 중지
        """
        self.is_running = False
    
    async def refresh_sensor_list(self):
        """
        연결된 센서 목록 주기적 갱신
        
        운영 시 중요사항:
        - 전체 시스템 스캔을 수행하여 센서 목록 갱신
        - 센서 추가/제거 등 하드웨어 변경 사항 자동 반영
        - 스캔 실패 시 기존 센서 목록 유지로 안정성 보장
        - 60초 간격으로 주기적 실행
        """
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
        """
        전체 센서에서 데이터 수집 후 WebSocket 브로드캐스트
        
        운영 시 중요사항:
        - I2C 센서: 캐시된 센서 목록에서 순차적 데이터 수집
        - UART 센서(SPS30): 백그라운드 스레드에서 캐시된 데이터 가져오기
        - 센서별 데이터 수집 실패 시 다른 센서 영향 없이 계속 진행
        - 표준화된 데이터 형식으로 변환 후 브로드캐스트
        - 데이터 수집 성공 시에만 브로드캐스트 수행
        """
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
    
    async def collect_and_broadcast_sht40_data(self):
        """
        SHT40 센서 전용 데이터 수집 및 브로드캐스트
        
        운영 시 중요사항:
        - 3초 간격으로 호출 (검증된 안정적 간격)
        - CRC 에러 시 스킵 처리
        - 개별 센서 에러는 전체를 중단시키지 않음
        - 동적으로 발견된 센서들만 대상
        """
        try:
            from sensor_handlers import read_all_sht40_data, get_sht40_sensor_count
            
            # 발견된 SHT40 센서가 없으면 스킵
            if get_sht40_sensor_count() == 0:
                return
            
            # 모든 SHT40 센서에서 데이터 수집
            sht40_data = await read_all_sht40_data()
            
            if sht40_data:
                # SHT40 전용 메시지 브로드캐스트
                sht40_message = {
                    "type": "sht40_data",
                    "timestamp": time.time(),
                    "sensors": sht40_data,
                    "count": len(sht40_data),
                    "statistics": {
                        "success": sum(1 for d in sht40_data if d.get('status') == 'success'),
                        "crc_skip": sum(1 for d in sht40_data if d.get('status') == 'crc_skip'),
                        "error": sum(1 for d in sht40_data if d.get('status') == 'error')
                    }
                }
                
                await manager.broadcast(json.dumps(sht40_message))
                
                # 모든 상태 포함하여 로그 출력 (성공, CRC 스킵, 에러)
                success_count = sum(1 for d in sht40_data if d.get('status') == 'success')
                crc_skip_count = sum(1 for d in sht40_data if d.get('status') == 'crc_skip')
                error_count = sum(1 for d in sht40_data if d.get('status') == 'error')
                
                print(f"🌡️ SHT40 데이터 브로드캐스트: 성공 {success_count}, CRC 스킵 {crc_skip_count}, 에러 {error_count} (총 {len(sht40_data)}개)")
                
        except Exception as e:
            print(f"❌ SHT40 데이터 수집 실패: {e}")
    
    async def refresh_sht40_sensor_list(self):
        """SHT40 센서 목록 주기적 재스캔"""
        try:
            from sensor_handlers import update_sht40_sensor_list
            
            previous_count = get_sht40_sensor_count() if 'get_sht40_sensor_count' in globals() else 0
            new_sensors = update_sht40_sensor_list()
            
            if len(new_sensors) != previous_count:
                print(f"🔄 SHT40 센서 목록 업데이트: {len(new_sensors)}개 (이전: {previous_count}개)")
                
                # 센서 목록 변경 알림
                if manager.active_connections:
                    sensor_update_message = {
                        "type": "sht40_sensors_updated",
                        "timestamp": time.time(),
                        "sensors": new_sensors,
                        "count": len(new_sensors)
                    }
                    await manager.broadcast(json.dumps(sensor_update_message))
            
        except Exception as e:
            print(f"❌ SHT40 센서 목록 갱신 실패: {e}")

# 전역 데이터 수집기 인스턴스
data_collector = RealTimeDataCollector()

def setup_websocket_routes(app):
    """
    FastAPI 애플리케이션에 WebSocket 라우트 등록
    
    운영 시 중요사항:
    - /ws 엔드포인트로 실시간 센서 데이터 WebSocket 서비스
    - 첫 클라이언트 연결 시 데이터 수집 자동 시작
    - 마지막 클라이언트 연결 해제 시 데이터 수집 자동 중지
    - ping/pong 메시지로 연결 상태 관리
    - 클라이언트 요청에 따른 상태 정보 제공
    
    Args:
        app: WebSocket 라우트를 등록할 FastAPI 애플리케이션
    
    Returns:
        FastAPI: 라우트가 등록된 애플리케이션
    """
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        실시간 센서 데이터 WebSocket 엔드포인트
        
        운영 시 중요사항:
        - WebSocket 연결 수락 후 첫 클라이언트인 경우 데이터 수집 시작
        - 30초 타임아웃으로 끊어진 연결 감지
        - ping/pong 메시지로 연결 상태 유지
        - 클라이언트 요청 메시지 처리 (ping, request_status)
        - 연결 해제 시 자동 정리 및 마지막 클라이언트인 경우 데이터 수집 중지
        
        Args:
            websocket (WebSocket): 연결된 WebSocket 인스턴스
        """
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
    """
    시스템 전체 메시지 브로드캐스트
    
    운영 시 중요사항:
    - 시스템 상태 변경, 오류 알림 등 중요 이벤트 전송
    - 표준화된 메시지 형식 (type, timestamp, data)
    - 외부 시스템에서 호출 가능한 유틸리티 함수
    
    Args:
        message_type (str): 메시지 타입 식별자
        data (Any): 전송할 데이터
    """
    message = {
        "type": message_type,
        "timestamp": time.time(),
        "data": data
    }
    await manager.broadcast(json.dumps(message))

async def get_connection_stats():
    """
    WebSocket 연결 및 데이터 수집기 상태 통계 정보 반환
    
    운영 시 중요사항:
    - 현재 활성 WebSocket 연결 수 추적
    - 전체 연결 시도 횟수 카운터
    - 데이터 수집기 및 센서 캐시 상태 정보
    - 시스템 모니터링 및 디버깅용
    
    Returns:
        dict: WebSocket 및 데이터 수집기 상태 통계
    """
    return {
        "active_connections": len(manager.active_connections),
        "total_connections": manager.connection_count,
        "collector_running": data_collector.is_running,
        "cached_sensors": len(data_collector.sensors_cache)
    }