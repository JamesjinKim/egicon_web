# EG-ICON Dashboard

**TCA9548A 이중 멀티플렉서 기반 16채널 센서 실시간 모니터링 대시보드**

## 📋 프로젝트 개요

EG-ICON Dashboard는 라즈베리파이에서 TCA9548A 멀티플렉서 2개를 사용하여 총 16개 채널의 I2C 센서를 실시간으로 모니터링하는 웹 기반 대시보드입니다.

### 🏗️ 시스템 아키텍처

```
Raspberry Pi I2C Master
├── Channel 1 (I2C Bus 0) → TCA9548A #1 (8채널)
│   ├── MUX Channel 0-7: SHT40, BME688, BH1750 등
└── Channel 2 (I2C Bus 1) → TCA9548A #2 (8채널)
    └── MUX Channel 0-7: 추가 센서들

주의: 하드웨어 라벨(Channel 1/2)과 소프트웨어 버스(Bus 0/1)는 다릅니다.
```

### 🎯 주요 기능

- **실시간 센서 모니터링**: WebSocket 기반 실시간 데이터 업데이트
- **이중 멀티플렉서 관리**: Channel 1/Bus 0, Channel 2/Bus 1 독립적 관리
- **16채널 시각화**: 2×8 그리드 채널 카드 표시
- **센서 자동 스캔**: I2C 주소 스캔 및 센서 타입 자동 인식
- **센서 테스트**: 개별 센서 진단 및 상태 확인
- **반응형 웹 UI**: 모바일, 태블릿, 데스크톱 지원

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.8+
- 라즈베리파이 (I2C 활성화)
- TCA9548A 멀티플렉서 2개
- 지원 센서: SHT40, BME688, BH1750, SDP810 등

### 🔄 Git 브랜치 버전 관리

#### 브랜치 구조
```
egicon_web (저장소)
├── master - 메인 브랜치 (기존)
├── v1.1 - 안정 버전 (현재 기능 고정)
└── v2 - 새로운 개발 브랜치 (OLED 제조공장 디지털 트윈)
```

#### 브랜치별 폴더 구조
```
egicon_web/
├── v1.1/                     # V1.1 안정 버전
│   ├── main.py               # V1.1 메인 서버
│   ├── frontend/             # V1.1 프론트엔드
│   └── requirements.txt      # V1.1 의존성
├── v2/                       # V2 디지털 트윈 프로토타입
│   ├── main_prototype.py     # V2 프로토타입 서버
│   ├── frontend/             # V2 프론트엔드
│   └── requirements_prototype.txt  # V2 의존성
└── docs/                     # 문서 모음
    ├── README.md
    ├── CLAUDE.md
    └── PRD_V2.md
```

#### V1.1 (안정 버전) 설치 및 실행
```bash
# 저장소 클론
git clone <repository-url>
cd egicon_web

# v2 브랜치로 전환
git checkout v2

# V1.1 실행
cd v1.1
pip install -r requirements.txt
python main.py
# → http://localhost:8001
```

#### V2 (디지털 트윈 프로토타입) 설치 및 실행
```bash
# 저장소 클론
git clone <repository-url>
cd egicon_web

# v2 브랜치로 전환
git checkout v2

# V2 실행
cd v2
pip install -r requirements_prototype.txt
python main_prototype.py
# → http://localhost:8002
```

#### 다른 컴퓨터에서 V2만 사용하기
```bash
# 방법 1: 전체 클론 후 V2 사용
git clone <repository-url>
cd egicon_web
git checkout v2
cd v2
pip install -r requirements_prototype.txt
python main_prototype.py

# 방법 2: V2 폴더만 Sparse Checkout
git clone --no-checkout <repository-url>
cd egicon_web
git checkout v2
git config core.sparseCheckout true
echo "v2/*" > .git/info/sparse-checkout
git checkout
cd v2
pip install -r requirements_prototype.txt
python main_prototype.py
```

### 설치 방법

#### 라즈베리파이 (프로덕션)
```bash
# 의존성 설치
pip install -r requirements.txt

# I2C 활성화 확인
sudo raspi-config
# Interface Options > I2C > Enable

# 서버 실행
python main.py
```

#### Mac/Windows (개발환경)
```bash
# 가상환경 생성 (권장)
python -m venv mvenv
source mvenv/bin/activate  # Mac/Linux
# mvenv\Scripts\activate   # Windows

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 서버 실행
python main.py
```

### 실행 방법

```bash
python main.py
```

서버가 시작되면 다음 URL로 접속:
- **메인 대시보드**: http://localhost:8001
- **센서 설정**: http://localhost:8001/settings
- **API 문서**: http://localhost:8001/docs

## 🎨 사용자 인터페이스

### 메인 대시보드
- **실시간 센서 데이터**: 온도, 습도, 압력, 조도 등
- **센서 그룹별 표시**: SHT40, BME688, 기타 센서
- **Chart.js 기반 차트**: 실시간 데이터 시각화
- **사이드바 네비게이션**: 센서별 필터링

### 센서 설정 페이지
- **이중 멀티플렉서 시각화**: Channel 1/Bus 0, Channel 2/Bus 1 독립 표시
- **16채널 그리드**: 채널별 센서 상태 확인
- **센서 스캔 기능**: 자동/수동 센서 검색
- **센서 테스트**: 개별 센서 진단
- **실시간 상태 모니터링**: 연결/해제 상태 추적

## 🔧 API 엔드포인트

### 센서 관리
```
GET  /api/sensors           # 전체 센서 목록
GET  /api/sensors/status    # 센서 상태 조회
POST /api/sensors/scan-all  # 통합 센서 스캔
POST /api/sensors/scan-dual-mux  # 이중 멀티플렉서 스캔
POST /api/sensors/scan-bus/{bus_number}  # 단일 채널 스캔
POST /api/sensors/test      # 센서 테스트
```

### 실시간 데이터
```
WebSocket: /ws/realtime     # 실시간 센서 데이터 스트리밍
```

## 📁 프로젝트 구조

```
egicon_web/
├── main.py                    # FastAPI 메인 서버 (라이프사이클 관리)
├── config.py                  # 환경 설정 (라즈베리파이/개발환경 자동감지)
├── api_endpoints.py           # REST API 엔드포인트 (센서 관리, 테스트)
├── websocket_manager.py       # WebSocket 실시간 통신 관리
├── hardware_scanner.py        # 하드웨어 스캔 및 센서 감지
├── sensor_handlers.py         # 센서별 데이터 읽기 함수
├── sps30_background.py        # SPS30 백그라운드 스레드 처리
├── sdp810_sensor.py          # SDP810 차압센서 전용 모듈
├── sht40_sensor.py           # SHT40 온습도센서 모듈
├── iis3dwb.py               # IIS3DWB 진동센서 모듈
├── frontend/                # 프론트엔드 파일
│   ├── index.html           # 메인 대시보드 (센서 그룹별 표시)
│   ├── settings.html        # 센서 설정 페이지 (16채널 시각화)
│   ├── dustsensor.html      # SPS30 미세먼지 센서 전용 페이지
│   ├── style.css            # 통합 스타일시트 (반응형 디자인)
│   ├── dashboard.js         # 대시보드 JavaScript (Chart.js 통합)
│   ├── settings.js          # 설정 페이지 JavaScript (하드웨어 제어)
│   └── dustsensor.js        # 미세먼지 페이지 JavaScript
├── ref/                     # 참고용 코드 및 테스트 파일
├── mvenv/                   # Python 가상환경 (개발용)
├── requirements.txt         # 프로덕션 의존성
├── requirements-dev.txt     # 개발 의존성
├── PRD.md                  # 제품 요구사항 문서
├── DEVELOPMENT_SUMMARY.md  # 개발 요약 문서
└── README.md               # 프로젝트 문서
```

## 🏗️ 백엔드 아키텍처

### 모듈별 역할 및 운영 가이드

#### 1. 핵심 서버 모듈
- **`main.py`**: FastAPI 애플리케이션 진입점
  - 라이프사이클 관리 (서버 시작/종료)
  - SPS30 백그라운드 스레드 초기화
  - 정적 파일 서빙 (HTML, CSS, JS)
  - 기본 라우트 설정

- **`config.py`**: 환경 설정 관리
  - 라즈베리파이 환경 자동 감지
  - 프로덕션/개발 모드 구분
  - 네트워크 및 포트 설정

#### 2. API 및 통신 모듈
- **`api_endpoints.py`**: REST API 엔드포인트
  - 센서 스캔 API (`/api/sensors/scan-dual-mux`)
  - 센서 테스트 API (`/api/sensors/test`)
  - 센서별 전용 API (SHT40, SDP810, BME688)
  - 동적 센서 그룹 관리

- **`websocket_manager.py`**: WebSocket 실시간 통신
  - 클라이언트 연결 관리
  - 실시간 데이터 브로드캐스트
  - 센서 데이터 수집 및 전송

#### 3. 하드웨어 제어 모듈
- **`hardware_scanner.py`**: 하드웨어 스캔 시스템
  - TCA9548A 이중 멀티플렉서 감지
  - I2C 센서 자동 검색
  - UART 센서 스캔 (SPS30)
  - 센서 타입별 전용 스캔

- **`sensor_handlers.py`**: 센서 데이터 읽기
  - BH1750 조도 센서 데이터 읽기
  - BME688 환경 센서 (기압/가스저항)
  - SPS30 UART 센서 테스트
  - 센서별 통합 데이터 함수

#### 4. 센서 전용 모듈
- **`sps30_background.py`**: SPS30 백그라운드 처리
  - 독립적인 스레드에서 데이터 수집
  - Thread-safe 캐시 시스템
  - 센서 상태 모니터링

- **`sdp810_sensor.py`**: SDP810 차압센서 전용
  - CRC 검증 기반 데이터 읽기
  - 재시도 로직 구현
  - 연속 측정 기능

### 데이터 흐름

```
클라이언트 (브라우저)
       ↓
FastAPI 서버 (main.py)
       ↓
┌─────────────────────┬─────────────────────┐
│   REST API          │   WebSocket         │
│ (api_endpoints.py)  │ (websocket_manager) │
├─────────────────────┼─────────────────────┤
│ - 센서 스캔         │ - 실시간 데이터     │
│ - 센서 테스트       │ - 클라이언트 연결   │
│ - 설정 관리         │ - 브로드캐스트      │
└─────────────────────┴─────────────────────┘
       ↓                       ↓
하드웨어 스캐너 (hardware_scanner.py)
       ↓
┌─────────────────────┬─────────────────────┐
│   I2C 센서          │   UART 센서         │
│ (sensor_handlers)   │ (sps30_background)  │
├─────────────────────┼─────────────────────┤
│ - SHT40 온습도      │ - SPS30 미세먼지    │
│ - BME688 환경       │ - 백그라운드 스레드 │
│ - BH1750 조도       │ - Thread-safe 캐시  │
│ - SDP810 차압       │                     │
└─────────────────────┴─────────────────────┘
       ↓
라즈베리파이 하드웨어
       ↓
TCA9548A 이중 멀티플렉서 (16채널)
```

## 🎨 프론트엔드 아키텍처

### 페이지 구조 및 역할

#### 1. 메인 대시보드 (`index.html` + `dashboard.js`)
```
대시보드 레이아웃
├── 사이드바 네비게이션
│   ├── 대시보드 (홈)
│   ├── 센서별 메뉴 (온도, 습도, 조도, 미세먼지, 진동)
│   ├── 설정 페이지
│   └── 데이터 갱신
├── 헤더
│   ├── 페이지 제목
│   └── 사용자 정보
├── 상태바
│   ├── 마지막 업데이트 시간
│   └── 데이터베이스 상태
└── 센서 그룹별 표시
    ├── 기압/가스저항 센서 그룹 (BME688)
    ├── SPS30 미세먼지 센서 그룹
    ├── 조도 센서 그룹 (BH1750)
    ├── SHT40 온습도 센서 그룹
    ├── SDP810 차압 센서 그룹
    └── 진동 센서 그룹 (준비 중)
```

**주요 기능:**
- 실시간 WebSocket 연결을 통한 데이터 업데이트
- Chart.js 기반 실시간 차트 시각화
- 센서 그룹별 요약 위젯 표시
- 반응형 레이아웃 (모바일/태블릿/데스크톱)

#### 2. 설정 페이지 (`settings.html` + `settings.js`)
```
설정 페이지 레이아웃
├── 시스템 개요
│   ├── 이중 멀티플렉서 상태
│   ├── 총 연결 센서 수
│   └── 전체 스캔 버튼
├── 통합 센서 검색 섹션
│   ├── I2C Bus 0 + Bus 1 통합 스캔
│   └── 스캔 결과 테이블
└── 이중 멀티플렉서 시각화
    ├── CH1 (I2C Bus 0) - 8채널 그리드
    │   ├── Channel 0-7 카드
    │   └── 센서 정보 표시
    └── CH2 (I2C Bus 1) - 8채널 그리드
        ├── Channel 8-15 카드
        └── 센서 정보 표시
```

**주요 기능:**
- 16채널 시각화 (2×8 그리드)
- 실시간 센서 스캔 및 결과 표시
- 개별 센서 테스트 기능
- 센서 상태 모니터링

#### 3. 미세먼지 페이지 (`dustsensor.html` + `dustsensor.js`)
```
미세먼지 페이지 레이아웃
├── 헤더 (SPS30 전용)
├── 상태바
│   ├── 센서 연결 상태
│   ├── 마지막 업데이트
│   └── WebSocket 연결 상태
├── 센서 정보 카드
│   ├── 센서 모델
│   ├── 시리얼 번호
│   ├── 연결 포트
│   └── 측정 성공률
├── 실시간 측정값 위젯
│   ├── PM1.0
│   ├── PM2.5 (강조 표시)
│   ├── PM4.0
│   └── PM10
├── 공기질 등급 표시
│   ├── 종합 등급 (좋음/보통/나쁨/매우나쁨)
│   └── 등급별 기준 표시
├── 실시간 차트
│   ├── 미세먼지 농도 추이 차트
│   └── PM 농도 비교 차트
└── 통계 정보
    ├── 오늘 평균
    ├── 최고 농도
    └── 최저 농도
```

### JavaScript 아키텍처

#### 1. `dashboard.js` - 메인 대시보드 제어
```javascript
class EGIconDashboard {
    constructor() {
        // 성능 최적화 설정
        this.config = {
            maxDataPoints: 100,     // 차트 데이터 포인트 제한
            updateInterval: 2000,   // 2초 간격 업데이트
            batchSize: 4,          // 배치 처리 크기
            enableAnimations: true  // 차트 애니메이션
        };
        
        // 센서 그룹 정의
        this.sensorGroups = {
            "pressure-gas": { ... },    // 기압/가스저항
            "sht40": { ... },          // SHT40 온습도
            "light": { ... },          // 조도
            "sdp810": { ... }          // 차압
        };
    }
}
```

**주요 기능:**
- WebSocket 연결 관리
- Chart.js 차트 관리
- 센서 그룹별 데이터 처리
- 실시간 UI 업데이트

#### 2. `settings.js` - 설정 페이지 제어
```javascript
class SettingsManager {
    constructor() {
        // 스캔 상태 관리
        this.scanStatus = {
            isScanning: false,
            lastScanTime: null,
            connectedDevices: 0
        };
        
        // UI 요소 관리
        this.initializeEventListeners();
        this.setupChannelCards();
    }
}
```

**주요 기능:**
- 하드웨어 스캔 제어
- 16채널 시각화 업데이트
- 센서 테스트 실행
- 실시간 상태 업데이트

#### 3. `dustsensor.js` - 미세먼지 페이지 제어
```javascript
class DustSensorMonitor {
    constructor() {
        // SPS30 전용 설정
        this.sps30Config = {
            updateInterval: 5000,   // 5초 간격
            maxDataPoints: 144,     // 12시간 데이터
            airQualityStandards: {
                good: 15,           // 좋음
                moderate: 35,       // 보통
                unhealthy: 75       // 나쁨
            }
        };
    }
}
```

### CSS 아키텍처 (`style.css`)

#### 반응형 디자인
```css
/* 모바일 우선 설계 */
@media (max-width: 768px) { ... }
@media (min-width: 769px) and (max-width: 1024px) { ... }
@media (min-width: 1025px) { ... }
```

#### 컴포넌트 기반 스타일링
```css
/* 센서 그룹 스타일 */
.sensor-group { ... }
.sensor-group-header { ... }
.summary-widgets-container { ... }

/* 채널 카드 스타일 */
.channel-card { ... }
.channel-card.connected { ... }
.channel-card.disconnected { ... }

/* 차트 컨테이너 */
.charts-grid { ... }
.chart-card { ... }
.chart-container { ... }
```

### 상태 관리

#### WebSocket 통신
```javascript
// 실시간 데이터 수신
websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'sensor_data') {
        this.updateSensorGroups(data.data);
        this.updateCharts(data.data);
    }
};
```

#### 데이터 플로우
```
서버 (Python) → WebSocket → JavaScript → Chart.js → DOM 업데이트
                              ↓
                         로컬 데이터 캐시
                              ↓
                         UI 상태 관리
```

## 🔌 지원 센서

| 센서 | 타입 | I2C 주소 | 측정값 |
|------|------|----------|--------|
| SHT40 | 온습도 | 0x44, 0x45 | 온도, 습도 |
| BME688 | 환경 | 0x76, 0x77 | 온도, 습도, 압력, 공기질 |
| BH1750 | 조도 | 0x23, 0x5C | 조도 |
| SDP810 | 차압 | 0x25 | 차압 |
| VL53L0X | 거리 | 0x29 | 거리 |

## ⚙️ 설정

### 성능 최적화 우선순위
1. **메모리 사용량 최적화**
2. **실시간성 보장**
3. **응답 속도 향상**

### 환경 설정
- **WebSocket 업데이트 주기**: 2초
- **차트 데이터 포인트**: 최대 30개
- **센서 스캔 타임아웃**: 10초
- **재연결 시도**: 최대 5회

## 🐛 문제 해결

### 일반적인 문제

1. **I2C 인식 안됨**
   ```bash
   sudo i2cdetect -y 1  # I2C 버스 1 스캔
   sudo i2cdetect -y 0  # I2C 버스 0 스캔
   ```

2. **포트 충돌**
   ```bash
   lsof -i :8001  # 포트 사용 확인
   kill -9 <PID>  # 프로세스 종료
   ```

3. **권한 문제**
   ```bash
   sudo usermod -a -G i2c $USER  # I2C 그룹 추가
   ```

### 로그 확인
```bash
# 서버 로그
tail -f /var/log/egicon-dashboard.log

# 시스템 로그
sudo journalctl -u egicon-dashboard
```

## 🚦 개발 가이드

### 개발 서버 실행
```bash
# 개발 모드 (auto-reload)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 디버그 모드
python main.py --debug
```

### 코드 스타일
- **Python**: PEP 8 준수
- **JavaScript**: ES6+ 표준
- **CSS**: BEM 방법론

### 테스트
```bash
# 단위 테스트
pytest tests/

# API 테스트
pytest tests/test_api.py

# 통합 테스트
pytest tests/test_integration.py
```

## 📈 성능 모니터링

### 시스템 메트릭
- CPU 사용률 모니터링
- 메모리 사용량 추적
- WebSocket 연결 수 관리
- 센서 응답 시간 측정

### 모니터링 도구
- **Prometheus**: 메트릭 수집
- **Grafana**: 시각화 대시보드
- **systemd**: 서비스 관리

## 🔒 보안

### 접근 제어
- 네트워크 기반 접근 제한
- HTTPS 지원 (프로덕션)
- API 키 인증 (선택사항)

### 데이터 보호
- 센서 데이터 암호화
- 로그 데이터 보안
- 백업 및 복구

## 📝 라이선스

MIT License - 자세한 내용은 LICENSE 파일 참조

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/issues)
- **기술 지원**: tech-support@example.com
- **문서**: [Wiki](https://github.com/your-repo/wiki)

---

## 🚀 최근 개발 현황 (2025.07.05)

### 완료된 기능
- ✅ TCA9548A 이중 멀티플렉서 시스템 (16채널)
- ✅ BME688 온습도 센서 7개 연동
- ✅ SPS30 UART 미세먼지 센서 연동
- ✅ BH1750 조도 센서 동적 스캔
- ✅ FastAPI 백엔드 + WebSocket 실시간 스트리밍
- ✅ 반응형 웹 대시보드
- ✅ Chart.js 기반 실시간 차트 (오류 복구 시스템 포함)
- ✅ Font Awesome 아이콘 오프라인 지원
- ✅ 동적 센서 그룹 관리 및 API 통합
- ✅ UI/UX 개선 (아이콘, 레이아웃, 네비게이션)

### 진행 중인 기능
- 🔄 IIS3DWB 진동센서 SPI 통합 (하드웨어 연결 검증 중)
- 🔄 압력 센서 차트 개선
- 🔄 알림 시스템 구현

### 최근 업데이트
- ✅ 센서 상태 표시 위치 최적화 (SPS30 센서)
- ✅ 사이드바 메뉴 아이콘 업데이트 (진동: 🌬️, 진동센서: 📳)
- ✅ 미세먼지센서 페이지 네비게이션 활성화
- ✅ 위젯 레이아웃 최적화 (아이콘 겹침 문제 해결)
- ✅ 조도센서 동적 카운트 표시 개선
- 🔄 IIS3DWB 진동센서 SPI 통신 기반 구축 (ref/iis3dwb.py 기반)

---

---

## 🆕 V2 디지털 트윈 대시보드 (2025-07-08)

### 🏭 OLED 제조공장 디지털 트윈 시스템

V2는 기존 V1.1의 센서 모니터링에서 발전하여 **OLED 제조공장 디지털 트윈**을 구현합니다.

#### 핵심 기능
- **🏠 메인 대시보드**: 공장 전체 KPI 및 평면도 시각화
- **🏭 공정별 모니터링**: 5개 공정 (증착, 포토, 식각, 봉지, 검사)
- **🧠 오감 신경망**: 센서를 5감으로 분류한 직관적 시스템
- **🔮 예지 보전**: AI 기반 장애 예측 및 권장 조치

#### 접속 URL (V2 실행 시)
- **메인 대시보드**: http://localhost:8002/
- **증착 공정**: http://localhost:8002/process/deposition
- **포토 공정**: http://localhost:8002/process/photo
- **식각 공정**: http://localhost:8002/process/etch (주의 상태 시뮬레이션)
- **봉지 공정**: http://localhost:8002/process/encapsulation
- **검사 공정**: http://localhost:8002/process/inspection

#### V2 특징
- **Mock 데이터 기반**: Mac PC에서 실행 가능
- **실시간 시뮬레이션**: 2초마다 데이터 업데이트
- **반응형 UI**: 모바일/태블릿/데스크톱 지원
- **WebSocket 연결**: 실시간 데이터 스트리밍

#### V1.1 vs V2 비교
| 항목 | V1.1 | V2 |
|------|------|-----|
| **관점** | 센서 중심 모니터링 | 공정 중심 디지털 트윈 |
| **메뉴** | 센서 타입별 | 공정별 |
| **메인 화면** | 센서 그룹 나열 | 공장 평면도 + KPI |
| **데이터** | 실시간 센서 데이터 | Mock 데이터 + 예측 |
| **포트** | 8001 | 8002 |
| **환경** | 라즈베리파이 필요 | Mac PC 실행 가능 |

---


다른 컴퓨터에서 V2 디지털 트윈 대시보드를 사용하려면:

  # 방법 1: 전체 클론
  git clone https://github.com/JamesjinKim/egicon_web.git
  cd egicon_web
  git checkout v2
  cd v2
  pip install -r requirements_prototype.txt
  python main_prototype.py

  # 방법 2: V2만 클론 (용량 절약)
  git clone --no-checkout https://github.com/JamesjinKim/egicon_web.git
  cd egicon_web
  git checkout v2
  git config core.sparseCheckout true
  echo "v2/*" > .git/info/sparse-checkout
  git checkout
  cd v2
  pip install -r requirements_prototype.txt
  python main_prototype.py

  📍 접속 주소

  - V2 디지털 트윈: http://localhost:8002
  - V1.1 안정 버전: http://localhost:8001

**개발자**: ShinHoTechnology  
**업데이트**: 2025년 7월 8일  
**버전**: V2 디지털 트윈 프로토타입 완성 (V1.1 안정 버전 병행 관리)