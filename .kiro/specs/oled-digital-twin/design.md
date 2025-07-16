# 설계 문서

## 개요

OLED 제조공장 디지털 트윈 시스템은 물리적 제조 환경을 디지털 세계에 복제하여 실시간 모니터링, 예지 보전, 공정 최적화를 제공하는 종합적인 IoT 플랫폼입니다. 이 시스템은 마이크로서비스 아키텍처를 기반으로 하며, 오감 신경망 개념을 통해 센서 데이터를 직관적으로 분류하고 관리합니다.

## 아키텍처

### 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           OLED 디지털 트윈 시스템 아키텍처                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        프레젠테이션 계층                                        │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │ 웹 브라우저 (React/HTML5)                                                     │    │
│  │ ├── 메인 대시보드 (공장 평면도 + KPI)                                          │    │
│  │ ├── 공정별 모니터링 페이지 (증착, 포토, 식각, 봉지, 검사)                        │    │
│  │ ├── 오감 신경망 시각화                                                        │    │
│  │ └── 예지 보전 대시보드                                                        │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                    ↕ HTTP/WebSocket                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         애플리케이션 계층                                       │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │ API 게이트웨이 (FastAPI)                                                      │    │
│  │ ├── REST API 엔드포인트                                                       │    │
│  │ ├── WebSocket 실시간 통신                                                     │    │
│  │ ├── 인증 및 권한 관리                                                         │    │
│  │ └── 요청 라우팅 및 로드 밸런싱                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                    ↕                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                          비즈니스 로직 계층                                     │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐                │    │
│  │ │ 센서 관리 서비스  │ │ 공정 모니터링    │ │ 예지 보전 서비스  │                │    │
│  │ │ - 센서 등록     │ │ 서비스          │ │ - AI 모델 관리   │                │    │
│  │ │ - 상태 모니터링  │ │ - 공정별 데이터  │ │ - 예측 분석     │                │    │
│  │ │ - 오감 분류     │ │ - 임계값 관리   │ │ - 알림 생성     │                │    │
│  │ └─────────────────┘ └─────────────────┘ └─────────────────┘                │    │
│  │                                                                             │    │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐                │    │
│  │ │ 데이터 처리     │ │ 알림 서비스      │ │ 리포트 서비스    │                │    │
│  │ │ 서비스          │ │ - 실시간 알림    │ │ - 데이터 분석   │                │    │
│  │ │ - 실시간 처리   │ │ - 이메일/SMS    │ │ - 보고서 생성   │                │    │
│  │ │ - 배치 처리     │ │ - 대시보드 알림  │ │ - 데이터 내보내기│                │    │
│  │ └─────────────────┘ └─────────────────┘ └─────────────────┘                │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                    ↕                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                           데이터 계층                                          │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐                │    │
│  │ │ 시계열 DB       │ │ 관계형 DB       │ │ 캐시 저장소     │                │    │
│  │ │ (InfluxDB)      │ │ (PostgreSQL)    │ │ (Redis)         │                │    │
│  │ │ - 센서 데이터   │ │ - 설정 정보     │ │ - 세션 데이터   │                │    │
│  │ │ - 시계열 분석   │ │ - 사용자 정보   │ │ - 실시간 캐시   │                │    │
│  │ └─────────────────┘ └─────────────────┘ └─────────────────┘                │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                    ↕                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         하드웨어 추상화 계층                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │ 센서 드라이버 및 통신 프로토콜                                                  │    │
│  │ ├── I2C 통신 (온도, 습도, 조도, 압력 센서)                                     │    │
│  │ ├── UART 통신 (미세먼지 센서)                                                 │    │
│  │ ├── SPI 통신 (진동 센서)                                                     │    │
│  │ └── TCA9548A 멀티플렉서 제어                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 오감 신경망 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            오감 신경망 센서 분류 시스템                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  👁️ 시각 (Vision) - 조도 센서                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ BH1750 센서 (I2C: 0x23, 0x5C)                                               │    │
│  │ ├── 포토공정: 2개 센서 (상부/하부 조도 균일성)                                  │    │
│  │ ├── 검사공정: 3개 센서 (검사 조명 균일성)                                      │    │
│  │ └── 기능: 조도 측정, 조명 수명 예측, 균일성 분석                                │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  🤚 촉각 (Touch) - 진동 센서                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ IIS3DWB 센서 (SPI 통신)                                                      │    │
│  │ ├── 증착공정: 1개 센서 (장비 진동 모니터링)                                     │    │
│  │ ├── 검사공정: 1개 센서 (진동 최소화 확인)                                      │    │
│  │ └── 기능: 진동 패턴 분석, 장비 고장 예측, 베어링 상태 진단                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  👃 후각 (Smell) - 미세먼지 센서                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ SPS30 센서 (UART 통신)                                                       │    │
│  │ ├── 포토공정: 1개 센서 (청정도 관리)                                           │    │
│  │ └── 기능: PM1.0/2.5/4.0/10 측정, 필터 교체 시기 예측, 공기질 등급 분류         │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  🌡️ 온감 (Temperature) - 온습도 센서                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ SHT40 센서 (I2C: 0x44, 0x45) + BME688 센서 (I2C: 0x76, 0x77)               │    │
│  │ ├── 증착공정: 3개 온도센서 (챔버별 온도 제어)                                   │    │
│  │ ├── 포토공정: 1개 온도센서 (환경 온도 관리)                                     │    │
│  │ ├── 식각공정: 4개 온도센서 (고온 공정 모니터링)                                 │    │
│  │ ├── 봉지공정: 1개 온도센서 (경화 온도 제어)                                     │    │
│  │ └── 검사공정: 1개 온도센서 (환경 안정성)                                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  📏 압감 (Pressure) - 차압 센서                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ SDP810 센서 (I2C: 0x25)                                                      │    │
│  │ ├── 봉지공정: 1개 센서 (공기 흐름 관리)                                        │    │
│  │ └── 기능: 차압 측정, 덕트 막힘 감지, 공기 흐름 최적화                           │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 컴포넌트 및 인터페이스

### 핵심 컴포넌트

#### 1. 센서 관리 컴포넌트
```python
class SensorManager:
    """오감 신경망 기반 센서 관리"""
    
    def __init__(self):
        self.sensor_registry = {}
        self.five_senses_mapping = {
            'vision': ['BH1750'],
            'touch': ['IIS3DWB'],
            'smell': ['SPS30'],
            'temperature': ['SHT40', 'BME688'],
            'pressure': ['SDP810']
        }
    
    def register_sensor(self, sensor_id: str, sensor_type: str, 
                       process: str, location: str) -> bool:
        """센서 등록 및 오감 분류"""
        
    def get_sensors_by_sense(self, sense: str) -> List[Sensor]:
        """감각별 센서 목록 조회"""
        
    def get_sensors_by_process(self, process: str) -> List[Sensor]:
        """공정별 센서 목록 조회"""
        
    def monitor_sensor_health(self) -> Dict[str, str]:
        """센서 건강 상태 모니터링"""
```

#### 2. 공정 모니터링 컴포넌트
```python
class ProcessMonitor:
    """5개 제조 공정 모니터링"""
    
    PROCESSES = {
        'deposition': {
            'name': '증착공정',
            'sensors': {
                'temperature': 3,
                'humidity': 2,
                'vibration': 1
            }
        },
        'photo': {
            'name': '포토공정',
            'sensors': {
                'illumination': 2,
                'temperature': 1,
                'particulate': 1
            }
        },
        'etch': {
            'name': '식각공정',
            'sensors': {
                'temperature': 4,
                'gas_concentration': 2,
                'safety': 1,
                'plasma': 1
            }
        },
        'encapsulation': {
            'name': '봉지공정',
            'sensors': {
                'humidity': 1,
                'curing_temperature': 1,
                'differential_pressure': 1
            }
        },
        'inspection': {
            'name': '검사공정',
            'sensors': {
                'illumination_uniformity': 3,
                'vibration_control': 1,
                'environmental_stability': 1
            }
        }
    }
    
    def get_process_status(self, process: str) -> ProcessStatus:
        """공정 상태 조회"""
        
    def calculate_process_kpi(self, process: str) -> Dict[str, float]:
        """공정별 KPI 계산"""
        
    def detect_process_anomalies(self, process: str) -> List[Anomaly]:
        """공정 이상 감지"""
```

#### 3. 예지 보전 컴포넌트
```python
class PredictiveMaintenanceEngine:
    """AI 기반 예지 보전 시스템"""
    
    def __init__(self):
        self.ml_models = {}
        self.prediction_accuracy = {}
        
    def load_models(self):
        """기계학습 모델 로드"""
        self.ml_models = {
            'equipment_failure': EquipmentFailureModel(),
            'quality_prediction': QualityPredictionModel(),
            'maintenance_scheduling': MaintenanceSchedulingModel()
        }
    
    def predict_equipment_failure(self, sensor_data: Dict) -> Prediction:
        """장비 고장 예측 (목표 정확도: 85% 이상)"""
        
    def generate_maintenance_alerts(self) -> List[MaintenanceAlert]:
        """유지보수 알림 생성 (긴급/주의/계획)"""
        
    def update_model_accuracy(self, model_name: str, accuracy: float):
        """모델 정확도 실시간 업데이트"""
```

#### 4. 실시간 데이터 처리 컴포넌트
```python
class RealTimeDataProcessor:
    """실시간 데이터 수집 및 처리"""
    
    def __init__(self):
        self.data_collection_interval = 1  # 1초 간격
        self.websocket_manager = WebSocketManager()
        
    def collect_sensor_data(self) -> Dict[str, Any]:
        """모든 센서로부터 데이터 수집"""
        
    def process_real_time_data(self, raw_data: Dict) -> ProcessedData:
        """실시간 데이터 처리 및 이상치 필터링"""
        
    def broadcast_to_clients(self, processed_data: ProcessedData):
        """WebSocket을 통한 클라이언트 브로드캐스트"""
        
    def store_historical_data(self, data: ProcessedData):
        """히스토리 데이터 저장 (1개월 상세, 1년 요약)"""
```

### API 인터페이스

#### REST API 엔드포인트
```python
# 공장 전체 현황
GET /api/factory/overview
GET /api/factory/kpi
GET /api/factory/floor-plan

# 공정별 모니터링
GET /api/processes/{process_name}/status
GET /api/processes/{process_name}/sensors
GET /api/processes/{process_name}/kpi
POST /api/processes/{process_name}/thresholds

# 오감 신경망
GET /api/senses/overview
GET /api/senses/{sense_type}/sensors
GET /api/senses/{sense_type}/status

# 예지 보전
GET /api/predictive/alerts
GET /api/predictive/predictions/{process_name}
GET /api/predictive/model-accuracy
POST /api/predictive/feedback

# 센서 관리
GET /api/sensors
GET /api/sensors/{sensor_id}
POST /api/sensors/{sensor_id}/calibrate
GET /api/sensors/health-check

# 데이터 분석
GET /api/data/historical
GET /api/data/trends
POST /api/data/export
GET /api/data/anomalies
```

#### WebSocket 이벤트
```javascript
// 실시간 데이터 스트림
ws://localhost:8000/ws/realtime

// 이벤트 타입
{
  "type": "sensor_data",
  "timestamp": "2025-07-16T10:30:00Z",
  "data": {
    "factory_overview": {...},
    "process_status": {...},
    "sensor_readings": {...},
    "alerts": [...]
  }
}

{
  "type": "process_alert",
  "severity": "warning|critical|info",
  "process": "etch",
  "message": "챔버 #2 온도 상승 감지",
  "recommended_action": "냉각 시스템 점검 권장"
}

{
  "type": "predictive_alert",
  "prediction_type": "equipment_failure",
  "confidence": 0.89,
  "time_to_failure": "2 hours",
  "affected_equipment": "증착 챔버 #1"
}
```

## 데이터 모델

### 센서 데이터 모델
```python
@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    process: str
    sense_category: str  # vision, touch, smell, temperature, pressure
    timestamp: datetime
    value: float
    unit: str
    status: str  # normal, warning, critical, offline
    location: str
    
@dataclass
class ProcessStatus:
    process_name: str
    overall_status: str  # normal, warning, critical
    efficiency: float
    quality_score: float
    sensor_count: int
    active_alerts: List[Alert]
    kpi_metrics: Dict[str, float]
    
@dataclass
class FactoryOverview:
    production_efficiency: float
    equipment_utilization: float  # OEE
    quality_metrics: float
    energy_consumption: float
    total_sensors: int
    active_processes: int
    critical_alerts: int
```

### 예지 보전 데이터 모델
```python
@dataclass
class Prediction:
    prediction_id: str
    model_name: str
    prediction_type: str  # equipment_failure, quality_issue, maintenance_need
    confidence: float
    time_horizon: timedelta
    affected_equipment: str
    recommended_actions: List[str]
    created_at: datetime
    
@dataclass
class MaintenanceAlert:
    alert_id: str
    severity: str  # emergency, warning, scheduled
    process: str
    equipment: str
    description: str
    predicted_failure_time: datetime
    recommended_actions: List[str]
    confidence_score: float
```

## 오류 처리

### 센서 통신 오류 처리
```python
class SensorErrorHandler:
    def __init__(self):
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
    async def handle_sensor_communication_error(self, sensor_id: str, error: Exception):
        """센서 통신 오류 처리"""
        # 1. 재시도 로직
        for attempt in range(self.retry_attempts):
            try:
                await self.reconnect_sensor(sensor_id)
                return True
            except Exception as e:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
        # 2. 센서 상태를 오프라인으로 변경
        await self.mark_sensor_offline(sensor_id)
        
        # 3. 알림 생성
        await self.create_sensor_offline_alert(sensor_id, error)
        
        # 4. Mock 데이터로 대체 (선택적)
        if self.use_mock_fallback:
            return await self.generate_mock_data(sensor_id)
```

### 시스템 복구 메커니즘
```python
class SystemRecoveryManager:
    async def handle_system_failure(self, failure_type: str):
        """시스템 장애 복구"""
        recovery_strategies = {
            'database_connection': self.recover_database_connection,
            'websocket_disconnection': self.recover_websocket_connections,
            'sensor_network_failure': self.recover_sensor_network,
            'ai_model_failure': self.recover_ai_models
        }
        
        if failure_type in recovery_strategies:
            await recovery_strategies[failure_type]()
            
    async def implement_graceful_degradation(self):
        """점진적 성능 저하 구현"""
        # 1. 비필수 기능 비활성화
        # 2. 데이터 수집 주기 조정
        # 3. 캐시 활용 증대
        # 4. 사용자에게 상태 알림
```

## 테스트 전략

### 단위 테스트
```python
class TestSensorManager:
    def test_sensor_registration(self):
        """센서 등록 테스트"""
        
    def test_five_senses_classification(self):
        """오감 분류 테스트"""
        
    def test_sensor_health_monitoring(self):
        """센서 건강 상태 모니터링 테스트"""

class TestPredictiveEngine:
    def test_prediction_accuracy(self):
        """예측 정확도 테스트 (목표: 85% 이상)"""
        
    def test_alert_generation(self):
        """알림 생성 테스트"""
        
    def test_model_update(self):
        """모델 업데이트 테스트"""
```

### 통합 테스트
```python
class TestSystemIntegration:
    def test_end_to_end_data_flow(self):
        """센서 → 처리 → 저장 → 표시 전체 플로우 테스트"""
        
    def test_real_time_performance(self):
        """실시간 성능 테스트 (1초 응답 시간)"""
        
    def test_concurrent_users(self):
        """동시 사용자 테스트 (10명 이상)"""
        
    def test_system_reliability(self):
        """시스템 신뢰성 테스트 (99.9% 가용성)"""
```

### 성능 테스트
```python
class TestPerformance:
    def test_data_collection_performance(self):
        """데이터 수집 성능 테스트 (1초 간격)"""
        
    def test_websocket_performance(self):
        """WebSocket 성능 테스트"""
        
    def test_database_performance(self):
        """데이터베이스 성능 테스트"""
        
    def test_ai_model_inference_time(self):
        """AI 모델 추론 시간 테스트"""
```

## 보안 고려사항

### 데이터 보안
- 센서 데이터 암호화 (AES-256)
- API 통신 HTTPS 강제
- 데이터베이스 접근 제어
- 로그 데이터 보안

### 접근 제어
- 역할 기반 접근 제어 (RBAC)
- JWT 토큰 기반 인증
- API 키 관리
- 세션 관리

### 네트워크 보안
- 방화벽 설정
- VPN 접근 제한
- 네트워크 세그멘테이션
- 침입 탐지 시스템

이 설계는 OLED 제조공장의 디지털 트윈을 구현하기 위한 포괄적인 아키텍처를 제공하며, 오감 신경망 개념을 통해 직관적인 센서 관리와 예지 보전 기능을 통합합니다.