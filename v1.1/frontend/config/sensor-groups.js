/**
 * EG-ICON Dashboard - 센서 그룹 설정
 * ==================================
 * 센서 그룹별 설정 정의
 */

export const sensorGroups = {
    "pressure-gas": {
        title: "기압/가스저항 센서",
        icon: "📏🔬", 
        metrics: ["pressure", "gas_resistance"],
        sensors: [],  // API 구조에 맞게 배열로 변경
        totalSensors: 0,  // 동적으로 업데이트됨
        containerId: "pressure-gas-widgets"
    },
    "temp-humidity": {
        title: "온습도 센서",
        icon: "🌡️💧", 
        metrics: ["temperature", "humidity"],
        sensors: {
            // SHT40 센서만 사용 (BME688 온습도 제거)
            sht40: []  // 동적으로 발견됨
        },
        totalSensors: 0,  // 동적으로 업데이트됨
        containerId: "temp-humidity-widgets"
    },
    "sht40": {
        title: "SHT40 온습도 센서",
        icon: "🌡️💧",
        metrics: ["temperature", "humidity"],
        sensors: {
            // SHT40 센서 (Bus 0 CH1, Bus 1 CH2)
            sht40: []  // 동적으로 발견됨
        },
        totalSensors: 2,
        containerId: "sht40-widgets"
    },
    "sdp810": {
        title: "SDP810 차압센서",
        icon: "🌬️",
        metrics: ["pressure"],
        sensors: {
            // SDP810 센서 (동적으로 발견됨)
            sdp810: []  // 동적으로 발견됨
        },
        totalSensors: 1,
        containerId: "sdp810-widgets"
    },
    "pressure": {
        title: "기압 센서",
        icon: "📏",
        metrics: ["pressure"],
        sensors: {
            // BME688 센서 기압 데이터 전용
            bme688: []  // 동적으로 발견됨
        },
        totalSensors: 0,  // 동적으로 업데이트됨
        containerId: "pressure-widgets",
        disabled: false  // 기압 센서 활성화
    },
    "differential-pressure": {
        title: "차압 센서",
        icon: "🌬️",
        metrics: ["differential_pressure"],
        sensors: {
            // SDP810 차압 센서 전용
            sdp810: []  // 동적으로 발견됨
        },
        totalSensors: 0,  // 동적으로 업데이트됨
        containerId: "differential-pressure-widgets",
        disabled: false  // 차압 센서 활성화
    },
    "light": {
        title: "조도 센서",
        icon: "☀️",
        metrics: ["light"],
        sensors: {
            // BH1750 센서 (동적으로 업데이트됨)
            bh1750: []
        },
        totalSensors: 0,
        containerId: "light-widgets"
    },
    "air-quality": {
        title: "공기질 센서",
        icon: "🍃",
        metrics: ["gas_resistance"],
        sensors: {
            // BME688 가스저항 + SPS30 미세먼지
            bme688: [],  // 동적으로 발견됨 (가스저항)
            sps30: []    // SPS30 미세먼지
        },
        totalSensors: 0,  // 동적으로 업데이트됨
        containerId: "air-quality-widgets"
    },
    "vibration": {
        title: "진동 센서",
        icon: "〜",
        metrics: ["vibration"],
        sensors: {
            // 진동센서 준비 중
        },
        totalSensors: 0,
        containerId: "vibration-widgets"
    }
};