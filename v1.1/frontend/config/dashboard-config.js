/**
 * EG-ICON Dashboard - 대시보드 설정
 * ================================
 * 대시보드 기본 설정 정의
 */

export const dashboardConfig = {
    maxDataPoints: 100,       // 메모리 최적화: 차트 데이터 포인트 제한 확대 (450Pa 급변 감지용)
    updateInterval: 2000,     // 안정성 우선: 2초 간격 업데이트 (CRC 오류 최소화, 75% 성공률)
    batchSize: 4,            // 응답속도: 배치 처리 크기
    enableAnimations: true,   // 모던 차트 애니메이션
    
    // WebSocket 설정
    websocket: {
        maxReconnectAttempts: 5,
        reconnectInterval: 1000
    }
};