"""Enum definitions for scenario configuration."""

from enum import Enum


class BizType(str, Enum):
    """사업자 유형"""
    INDIVIDUAL_BIZ = "individual_biz"  # 개인사업자
    NON_BIZ = "non_biz"  # 비사업자
    CORP = "corp"  # 법인


class CertType(str, Enum):
    """간편인증 유형"""
    KAKAO = "kakao"
    NAVER = "naver"
    PASS = "pass"
    PAYCO = "payco"
    SAMSUNG = "samsung"
    KB = "kb"
    SHINHAN = "shinhan"


class ErrorType(str, Enum):
    """에러 타입"""
    # Load 액션 에러
    NO_TAX_RETURN = "종소세신고내역없음"
    NO_BIZ = "사업자없음오류"
    CALC_ERROR = "계산오류"
    ALREADY_REFUNDED = "기환급자"
    NOT_COMPLETE = "미완료"
    NO_CONT_BIZ = "계속사업자없음"
    
    # 인증 관련 에러
    AUTH_EXPIRED = "간편인증토큰만료"
    AUTH_NOT_COMPLETE = "간편인증미완료"
    LOGIN_FAILED = "홈택스로그인실패"
    SESSION_EXPIRED = "세션만료"
    INVALID_SSN = "주민번호오류"


class ActionType(str, Enum):
    """액션 타입"""
    CERT_REQUEST = "cert_request"
    CERT_RESPONSE = "cert_response"
    CHECK = "check"
    LOAD = "load"
    CALC = "calc"


# 에러 타입별 기본 메시지
ERROR_MESSAGES: dict[ErrorType, str] = {
    ErrorType.NO_TAX_RETURN: "종합소득세 신고 내역이 없습니다.",
    ErrorType.NO_BIZ: "사업자 등록 정보가 없습니다.",
    ErrorType.CALC_ERROR: "환급액 계산 중 오류가 발생했습니다.",
    ErrorType.ALREADY_REFUNDED: "이미 환급 처리가 완료된 건입니다.",
    ErrorType.NOT_COMPLETE: "처리가 완료되지 않았습니다.",
    ErrorType.NO_CONT_BIZ: "계속사업자 정보가 없습니다.",
    ErrorType.AUTH_EXPIRED: "간편인증 토큰이 만료되었습니다.",
    ErrorType.AUTH_NOT_COMPLETE: "간편인증이 완료되지 않았습니다.",
    ErrorType.LOGIN_FAILED: "홈택스 로그인에 실패했습니다.",
    ErrorType.SESSION_EXPIRED: "세션이 만료되었습니다.",
    ErrorType.INVALID_SSN: "주민등록번호가 올바르지 않습니다.",
}

# 에러 타입별 기본 발생 액션
ERROR_DEFAULT_ACTION: dict[ErrorType, ActionType] = {
    ErrorType.NO_TAX_RETURN: ActionType.LOAD,
    ErrorType.NO_BIZ: ActionType.LOAD,
    ErrorType.CALC_ERROR: ActionType.LOAD,
    ErrorType.ALREADY_REFUNDED: ActionType.LOAD,
    ErrorType.NOT_COMPLETE: ActionType.LOAD,
    ErrorType.NO_CONT_BIZ: ActionType.LOAD,
    ErrorType.AUTH_EXPIRED: ActionType.CERT_RESPONSE,
    ErrorType.AUTH_NOT_COMPLETE: ActionType.CERT_RESPONSE,
    ErrorType.LOGIN_FAILED: ActionType.CHECK,
    ErrorType.SESSION_EXPIRED: ActionType.CHECK,
    ErrorType.INVALID_SSN: ActionType.CHECK,
}
