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

### 설치 방법

#### 라즈베리파이 (프로덕션)
```bash
# 프로젝트 클론
git clone <repository-url>
cd egicon_web

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
# 프로젝트 클론
git clone <repository-url>
cd egicon_web

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
├── main.py                 # FastAPI 메인 서버
├── frontend/              # 프론트엔드 파일
│   ├── index.html         # 메인 대시보드
│   ├── settings.html      # 센서 설정 페이지
│   ├── style.css          # 통합 스타일시트
│   ├── dashboard.js       # 대시보드 JavaScript
│   └── settings.js        # 설정 페이지 JavaScript
├── requirements.txt       # 프로덕션 의존성
├── requirements-dev.txt   # 개발 의존성
├── PRD.md                # 제품 요구사항 문서
└── README.md             # 프로젝트 문서
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

**개발자**: ShinHoTechnology  
**업데이트**: 2025년 7월 5일  
**버전**: 1.1.0