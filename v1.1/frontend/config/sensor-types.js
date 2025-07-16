/**
 * EG-ICON Dashboard - 센서 타입 설정
 * =================================
 * 센서별 메트릭 설정 정의
 */

export const sensorTypes = {
    temperature: {
        label: '온도',
        icon: '🌡️',
        unit: '°C',
        color: '#ff6384',
        min: -10,
        max: 50
    },
    humidity: {
        label: '습도',
        icon: '💧',
        unit: '%',
        color: '#36a2eb',
        min: 0,
        max: 100
    },
    pressure: {
        label: '압력',
        icon: '📏',
        unit: 'hPa',
        color: '#4bc0c0',
        min: 950,
        max: 1050
    },
    light: {
        label: '조도',
        icon: '☀️',
        unit: 'lux',
        color: '#ffce56',
        min: 0,
        max: 3000
    },
    vibration: {
        label: '진동',
        icon: '〜',
        unit: 'Hz',
        color: '#9966ff',
        min: 0,
        max: 100
    },
    airquality: {
        label: '공기질',
        icon: '🍃',
        unit: '/100',
        color: '#00d084',
        min: 0,
        max: 100
    },
    gas_resistance: {
        label: '가스저항',
        icon: '🔬',
        unit: 'Ω',
        color: '#9966ff',
        min: 0,
        max: 200000
    }
};