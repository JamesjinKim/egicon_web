#!/usr/bin/env python3
"""
Mock Data Generator for V2 Digital Twin Dashboard
OLED 제조공장 디지털 트윈 Mock 데이터 생성기

Author: ShinHoTechnology
Version: V2.0 Prototype
Date: 2025-07-08
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class MockDataGenerator:
    """V2 프로토타입용 Mock 데이터 생성기"""
    
    def __init__(self):
        self.is_initialized = False
        self.current_time = datetime.now()
        
        # 공정별 센서 개수
        self.process_sensors = {
            "deposition": 6,
            "photo": 4,
            "etch": 8,
            "encapsulation": 3,
            "inspection": 5,
            "packaging": 20,
            "shipping": 10
        }
        
        # 상태 시뮬레이션 (정상, 주의, 위험)
        self.process_status = {
            "deposition": "normal",
            "photo": "normal",
            "etch": "warning",  # 식각 공정은 주의 상태로 설정
            "encapsulation": "normal",
            "inspection": "normal",
            "packaging": "normal",
            "shipping": "normal"
        }
        
        # 트렌드 시뮬레이션
        self.trends = ["up", "down", "stable"]
        
    async def initialize(self):
        """초기화"""
        if not self.is_initialized:
            logger.info("📊 Mock 데이터 생성기 초기화 중...")
            await self._load_base_data()
            self.is_initialized = True
            logger.info("✅ Mock 데이터 생성기 초기화 완료")
    
    async def _load_base_data(self):
        """기본 데이터 로드"""
        # 실제 환경에서는 파일에서 로드하지만, 프로토타입에서는 코드에서 생성
        pass
    
    def get_factory_kpi(self) -> Dict[str, Any]:
        """공장 전체 KPI 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "factory_kpi": {
                "production_efficiency": {
                    "value": round(random.uniform(85, 95), 1),
                    "status": "normal" if random.random() > 0.2 else "warning",
                    "trend": random.choice(self.trends),
                    "change": round(random.uniform(-5, 5), 1)
                },
                "equipment_utilization": {
                    "value": round(random.uniform(80, 90), 1),
                    "status": "warning" if random.random() > 0.7 else "normal",
                    "trend": random.choice(self.trends),
                    "change": round(random.uniform(-3, 3), 1)
                },
                "quality_index": {
                    "value": round(random.uniform(95, 99), 1),
                    "status": "normal",
                    "trend": random.choice(self.trends),
                    "change": round(random.uniform(-1, 1), 1)
                },
                "energy_consumption": {
                    "value": random.randint(2000, 3000),
                    "unit": "kW",
                    "status": "normal",
                    "trend": random.choice(self.trends),
                    "change": round(random.uniform(-10, 10), 1)
                },
                "ai_prediction_accuracy": {
                    "value": round(random.uniform(85, 95), 1),
                    "status": "normal",
                    "trend": "stable",
                    "change": round(random.uniform(-2, 2), 1)
                }
            }
        }
    
    def get_factory_layout(self) -> Dict[str, Any]:
        """공장 평면도 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "factory_layout": {
                "processes": {
                    "deposition": {
                        "name": "증착실",
                        "status": self.process_status["deposition"],
                        "sensor_count": self.process_sensors["deposition"],
                        "sensors": ["🌡️", "💧", "📳", "💨"],
                        "alert_message": None
                    },
                    "photo": {
                        "name": "포토실",
                        "status": self.process_status["photo"],
                        "sensor_count": self.process_sensors["photo"],
                        "sensors": ["☀️", "🌡️", "💨"],
                        "alert_message": None
                    },
                    "etch": {
                        "name": "식각실",
                        "status": self.process_status["etch"],
                        "sensor_count": self.process_sensors["etch"],
                        "sensors": ["🌡️", "💨", "🛡️", "🔥"],
                        "alert_message": "온도상승"
                    },
                    "encapsulation": {
                        "name": "봉지실",
                        "status": self.process_status["encapsulation"],
                        "sensor_count": self.process_sensors["encapsulation"],
                        "sensors": ["💧", "🌡️", "📏"],
                        "alert_message": None
                    },
                    "inspection": {
                        "name": "검사실",
                        "status": self.process_status["inspection"],
                        "sensor_count": self.process_sensors["inspection"],
                        "sensors": ["☀️", "📳", "🌡️"],
                        "alert_message": None
                    },
                    "packaging": {
                        "name": "패키징실",
                        "status": self.process_status["packaging"],
                        "sensor_count": self.process_sensors["packaging"],
                        "sensors": ["📦", "🏷️", "⚖️"],
                        "alert_message": None
                    },
                    "shipping": {
                        "name": "출하실",
                        "status": self.process_status["shipping"],
                        "sensor_count": self.process_sensors["shipping"],
                        "sensors": ["📊", "🌡️", "💨"],
                        "alert_message": None
                    }
                }
            }
        }
    
    def get_process_sensors(self, process_name: str) -> Dict[str, Any]:
        """공정별 센서 데이터 생성"""
        sensor_count = self.process_sensors.get(process_name, 1)
        status = self.process_status.get(process_name, "normal")
        
        # 공정별 특화 센서 데이터
        if process_name == "photo":
            return self._generate_photo_sensors(status)
        elif process_name == "etch":
            return self._generate_etch_sensors(status)
        elif process_name == "packaging":
            return self._generate_packaging_sensors(status)
        elif process_name == "shipping":
            return self._generate_shipping_sensors(status)
        else:
            return self._generate_generic_sensors(process_name, sensor_count, status)
    
    def _generate_photo_sensors(self, status: str) -> Dict[str, Any]:
        """포토 공정 센서 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "process": "photo",
            "process_status": status,
            "sensor_count": 4,
            "sensors": {
                "light": [
                    {
                        "id": "light_photo_01",
                        "channel": "Ch5",
                        "value": round(random.uniform(800, 900), 1),
                        "unit": "lux",
                        "status": "normal",
                        "location": "포토부스 상부",
                        "trend": "stable",
                        "target": 850
                    },
                    {
                        "id": "light_photo_02",
                        "channel": "Ch2",
                        "value": round(random.uniform(800, 900), 1),
                        "unit": "lux",
                        "status": "normal",
                        "location": "포토부스 하부",
                        "trend": "stable",
                        "target": 850
                    }
                ],
                "temperature": [
                    {
                        "id": "temp_photo_01",
                        "channel": "Ch3",
                        "value": round(random.uniform(22, 25), 1),
                        "unit": "°C",
                        "status": "normal",
                        "location": "포토부스 중앙",
                        "trend": "stable",
                        "target": 23
                    }
                ],
                "dust": [
                    {
                        "id": "dust_photo_01",
                        "channel": "Ch7",
                        "value": round(random.uniform(5, 15), 1),
                        "unit": "µg/m³",
                        "status": "normal",
                        "location": "포토부스 입구",
                        "trend": "stable",
                        "target": 10
                    }
                ]
            }
        }
    
    def _generate_etch_sensors(self, status: str) -> Dict[str, Any]:
        """식각 공정 센서 데이터 생성 (주의 상태)"""
        return {
            "timestamp": self.current_time.isoformat(),
            "process": "etch",
            "process_status": status,
            "sensor_count": 8,
            "alert_count": 2,
            "alerts": [
                {
                    "type": "temperature_high",
                    "sensor": "temp_etch_02",
                    "message": "챔버 #2 온도 상승 감지",
                    "severity": "warning",
                    "value": 185.1,
                    "target": 180
                },
                {
                    "type": "plasma_unstable",
                    "sensor": "plasma_etch_01",
                    "message": "플라즈마 안정성 변동 감지",
                    "severity": "warning",
                    "value": 91.8,
                    "target": 95
                }
            ],
            "sensors": {
                "temperature": [
                    {
                        "id": "temp_etch_01",
                        "channel": "Ch7",
                        "value": round(random.uniform(175, 180), 1),
                        "unit": "°C",
                        "status": "normal",
                        "location": "챔버 #1",
                        "trend": "stable",
                        "target": 180
                    },
                    {
                        "id": "temp_etch_02",
                        "channel": "Ch8",
                        "value": round(random.uniform(180, 190), 1),
                        "unit": "°C",
                        "status": "warning",
                        "location": "챔버 #2",
                        "trend": "up",
                        "target": 180
                    }
                ],
                "plasma": [
                    {
                        "id": "plasma_etch_01",
                        "channel": "Ch11",
                        "value": round(random.uniform(85, 95), 1),
                        "unit": "%",
                        "status": "warning",
                        "location": "플라즈마 제어기",
                        "trend": "down",
                        "target": 95
                    }
                ]
            }
        }
    
    def _generate_generic_sensors(self, process_name: str, sensor_count: int, status: str) -> Dict[str, Any]:
        """일반 공정 센서 데이터 생성"""
        sensors = []
        for i in range(sensor_count):
            sensors.append({
                "id": f"sensor_{process_name}_{i+1:02d}",
                "channel": f"Ch{i+1}",
                "value": round(random.uniform(20, 30), 1),
                "unit": "°C",
                "status": status,
                "location": f"위치 {i+1}",
                "trend": random.choice(self.trends),
                "target": 25
            })
        
        return {
            "timestamp": self.current_time.isoformat(),
            "process": process_name,
            "process_status": status,
            "sensor_count": sensor_count,
            "sensors": {"generic": sensors}
        }
    
    def get_process_prediction(self, process_name: str) -> Dict[str, Any]:
        """공정별 예지 보전 데이터 생성"""
        if process_name == "etch":
            return {
                "timestamp": self.current_time.isoformat(),
                "process": process_name,
                "overall_health": round(random.uniform(75, 85), 1),
                "predictions": {
                    "next_24h": {
                        "normal_probability": round(random.uniform(60, 70), 1),
                        "warning_probability": round(random.uniform(25, 35), 1),
                        "critical_probability": round(random.uniform(5, 10), 1)
                    },
                    "urgent_actions": [
                        {
                            "priority": 1,
                            "action": "챔버 #2 냉각 시스템 점검",
                            "estimated_time": "즉시",
                            "confidence": 89.3
                        }
                    ],
                    "recommendations": [
                        {
                            "type": "maintenance",
                            "action": "가스 유량 조절",
                            "schedule": "30분 이내",
                            "confidence": 85.7
                        }
                    ]
                }
            }
        else:
            return {
                "timestamp": self.current_time.isoformat(),
                "process": process_name,
                "overall_health": round(random.uniform(90, 98), 1),
                "predictions": {
                    "next_24h": {
                        "normal_probability": round(random.uniform(90, 95), 1),
                        "warning_probability": round(random.uniform(4, 8), 1),
                        "critical_probability": round(random.uniform(0, 2), 1)
                    },
                    "recommendations": [
                        {
                            "type": "maintenance",
                            "action": "정기 점검 유지",
                            "schedule": "5일 후",
                            "confidence": 94.2
                        }
                    ]
                }
            }
    
    def get_neural_network_status(self) -> Dict[str, Any]:
        """오감 신경망 상태 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "neural_network": {
                "sight": {
                    "name": "시각(조도)",
                    "sensor_count": 6,
                    "status": "normal",
                    "coverage": 95.2
                },
                "hearing": {
                    "name": "청각(진동)",
                    "sensor_count": 4,
                    "status": "normal",
                    "coverage": 88.7
                },
                "smell": {
                    "name": "후각(공기)",
                    "sensor_count": 3,
                    "status": "normal",
                    "coverage": 92.1
                },
                "touch": {
                    "name": "촉각(온도)",
                    "sensor_count": 12,
                    "status": "warning",
                    "coverage": 96.8
                },
                "pressure": {
                    "name": "압감(압력)",
                    "sensor_count": 2,
                    "status": "normal",
                    "coverage": 89.3
                }
            }
        }
    
    def update_time(self):
        """시간 업데이트"""
        self.current_time = datetime.now()
    
    def simulate_alert(self, process_name: str, alert_type: str):
        """알림 시뮬레이션"""
        if process_name in self.process_status:
            if alert_type == "warning":
                self.process_status[process_name] = "warning"
            elif alert_type == "critical":
                self.process_status[process_name] = "critical"
            elif alert_type == "normal":
                self.process_status[process_name] = "normal"
    
    def _generate_packaging_sensors(self, status: str) -> Dict[str, Any]:
        """패키징 공정 센서 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "process": "packaging",
            "process_status": status,
            "sensor_count": 20,
            "sensors": {
                "sealing_pressure": [
                    {
                        "id": "sealing_pressure_01",
                        "channel": "Ch1",
                        "value": round(random.uniform(45, 55), 1),
                        "unit": "kPa",
                        "status": "normal",
                        "location": "포장 유닛 1",
                        "trend": "stable",
                        "target": 50
                    }
                ],
                "labeling_position": [
                    {
                        "id": "labeling_position_01",
                        "channel": "Ch2",
                        "value": round(random.uniform(0.1, 0.6), 2),
                        "unit": "mm",
                        "status": "normal",
                        "location": "라벨링 스테이션",
                        "trend": "stable",
                        "target": 0.2
                    }
                ],
                "weight": [
                    {
                        "id": "weight_01",
                        "channel": "Ch3",
                        "value": round(random.uniform(155, 160), 1),
                        "unit": "g",
                        "status": "normal",
                        "location": "무게 측정대",
                        "trend": "stable",
                        "target": 157
                    }
                ],
                "temperature": [
                    {
                        "id": "temp_packaging_01",
                        "channel": "Ch4",
                        "value": round(random.uniform(23, 26), 1),
                        "unit": "°C",
                        "status": "normal",
                        "location": "포장 챔버",
                        "trend": "stable",
                        "target": 24
                    }
                ],
                "ventilation": [
                    {
                        "id": "ventilation_01",
                        "channel": "Ch5",
                        "value": round(random.uniform(180, 200), 0),
                        "unit": "CFM",
                        "status": "normal",
                        "location": "환기 시스템",
                        "trend": "stable",
                        "target": 190
                    }
                ]
            }
        }
    
    def _generate_shipping_sensors(self, status: str) -> Dict[str, Any]:
        """출하 공정 센서 데이터 생성"""
        return {
            "timestamp": self.current_time.isoformat(),
            "process": "shipping",
            "process_status": status,
            "sensor_count": 10,
            "sensors": {
                "loading_capacity": [
                    {
                        "id": "loading_capacity_01",
                        "channel": "Ch1",
                        "value": round(random.uniform(70, 90), 0),
                        "unit": "%",
                        "status": "normal",
                        "location": "출하 적재대",
                        "trend": "stable",
                        "target": 85
                    }
                ],
                "storage_temperature": [
                    {
                        "id": "storage_temp_01",
                        "channel": "Ch2",
                        "value": round(random.uniform(18, 22), 1),
                        "unit": "°C",
                        "status": "normal",
                        "location": "출하 대기실",
                        "trend": "stable",
                        "target": 20
                    }
                ],
                "ventilation_flow": [
                    {
                        "id": "ventilation_flow_01",
                        "channel": "Ch3",
                        "value": round(random.uniform(150, 180), 0),
                        "unit": "CFM",
                        "status": "normal",
                        "location": "출하 대기실",
                        "trend": "stable",
                        "target": 165
                    }
                ],
                "security_status": [
                    {
                        "id": "security_01",
                        "channel": "Ch4",
                        "value": "정상",
                        "unit": "",
                        "status": "normal",
                        "location": "출하 게이트",
                        "trend": "stable",
                        "target": "정상"
                    }
                ]
            }
        }