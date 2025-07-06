# CLAUDE 개발 지원 문서

이 파일은 AI 어시스턴트 Claude가 프로젝트에 대해 기억해야 할 중요한 정보들을 담고 있습니다.

## 🏗️ 개발 환경 구조

### 개발 워크플로우
```
Mac PC (개발환경)
    ↓ 코드 작성 및 기본적인 구문 테스트만 가능 (실제 센서 관련 각종 테스트는 Raspberry Pi 4에서 만 가능함.)
GitHub Repository
    ↓ 배포
Raspberry Pi 4 (실행환경)
    ↓ 실제 센서 연결
하드웨어 센서들 (SHT40, BME688, BH1750, SDP810, SPS30, IIS3DWB 진동센서 등)
```

### 중요한 환경 차이점

#### Mac PC (개발환경)
- **센서 연동**: 불가능 (하드웨어 센서가 연결되어 있지 않음)
- **테스트 방식**: Mock 데이터 기반 테스트만 가능
- **I2C/UART**: 사용 불가 (라즈베리파이 하드웨어 없음)
- **개발 모드**: `config.py`에서 자동으로 개발 모드로 인식
- **라이브러리**: smbus2, shdlc_sps30 등이 설치되지 않거나 작동하지 않음

#### Raspberry Pi 4 (실행환경)
- **센서 연동**: 실제 하드웨어 센서와 연결
- **I2C 버스**: Bus 0, Bus 1 모두 활성화
- **TCA9548A 멀티플렉서**: 2개 연결 (16채널)
- **실제 센서들**: 
  - SHT40 온습도센서
  - BME688 환경센서 (기압/가스저항)
  - BH1750 조도센서
  - SDP810 차압센서
  - SPS30 UART 미세먼지센서

## 🔧 개발 시 고려사항

### 코드 작성 원칙
1. **환경 자동 감지**: `config.py`의 `is_raspberry_pi()` 함수 활용
2. **Mock 데이터 지원**: Mac에서도 UI 테스트 가능하도록 Mock 데이터 제공
3. **하드웨어 의존성 분리**: 센서 관련 코드는 try/except로 처리
4. **라이브러리 조건부 import**: 하드웨어 라이브러리는 ImportError 처리

### 테스트 전략
```python
# 좋은 예시 - 환경 대응 코드
if not scanner.is_raspberry_pi:
    # Mac에서는 Mock 데이터 반환
    return mock_sensor_data
else:
    # 라즈베리파이에서는 실제 센서 데이터
    return real_sensor_data
```

### 배포 프로세스
1. Mac에서 코드 작성 및 프론트엔드 테스트
2. GitHub에 커밋 및 푸시
3. 라즈베리파이에서 git pull
4. 라즈베리파이에서 실제 센서 연동 테스트

## 📝 개발 명령어

### Mac PC에서 개발 시
```bash
# 개발 환경 설정
python -m venv mvenv
source mvenv/bin/activate
pip install -r requirements-dev.txt

# 개발 서버 실행 (Mock 모드)
python main.py

# 프론트엔드만 테스트 가능
# - 대시보드 UI/UX
# - 설정 페이지 레이아웃
# - JavaScript 기능
# - CSS 스타일링
```

### Raspberry Pi에서 실행 시
```bash
# 프로덕션 환경
pip install -r requirements.txt

# I2C 확인
sudo i2cdetect -y 0
sudo i2cdetect -y 1

# 실제 센서 연동 서버 실행
python main.py

# 실제 센서 테스트 가능
# - 모든 I2C 센서 스캔
# - UART SPS30 센서
# - 실시간 데이터 수집
```

## 🚨 주의사항

### 절대 하지 말아야 할 것
- Mac에서 실제 센서 연동 코드를 테스트하려고 시도하지 말 것
- 하드웨어 라이브러리 없이 실제 센서 함수를 호출하지 말 것
- 라즈베리파이 전용 코드를 Mac에서 강제로 실행하지 말 것

### 개발 시 확인사항
- 새로운 센서 코드 작성 시 Mock 모드 지원 여부 확인
- 하드웨어 의존성이 있는 라이브러리는 조건부 import 처리
- 환경별로 다른 동작을 하는 코드는 명확히 문서화

## 🔍 디버깅 가이드

### Mac에서 확인 가능한 것
- 웹 UI가 정상적으로 로드되는지
- JavaScript 오류가 없는지
- API 엔드포인트가 응답하는지 (Mock 데이터)
- CSS 스타일이 올바르게 적용되는지

### 라즈베리파이에서만 확인 가능한 것
- 실제 센서 연결 상태
- I2C 통신 정상 여부
- 센서 데이터 정확성
- 하드웨어 스캔 결과
- 실시간 데이터 수집

## 📋 자주 사용하는 체크리스트

### 새 기능 개발 시
- [ ] Mac에서 Mock 데이터로 UI 테스트 완료
- [ ] 환경 감지 코드 추가 (`is_raspberry_pi()` 활용)
- [ ] 하드웨어 라이브러리 조건부 import 처리
- [ ] GitHub에 커밋 및 푸시
- [ ] 라즈베리파이에서 실제 센서 테스트
- [ ] 실제 환경에서 정상 동작 확인

---

**작성일**: 2025-07-06  
**업데이트**: 개발 환경 및 배포 구조 정리  
**목적**: Claude AI가 프로젝트 환경을 정확히 이해하고 적절한 지원 제공