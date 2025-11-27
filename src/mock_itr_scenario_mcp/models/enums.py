"""Enum definitions for scenario configuration."""

from enum import Enum


class BizType(str, Enum):
    """사업자 유형 (샘플 데이터: corp_type)"""
    INDIVIDUAL_BIZ = "individual_biz"  # 개인사업자
    NON_BIZ = "non_biz"  # 비사업자
    CORP = "corp"  # 법인


class CorpType(str, Enum):
    """법인 유형 (샘플 데이터 기반)"""
    INDIS = "INDIS"  # 개인사업자
    CORPS = "CORPS"  # 법인


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
    """에러 타입 (샘플 데이터 기반 - 빈도순)"""
    # Load 액션 에러 (샘플 데이터 기반 - 16,338건)
    NO_BIZ = "사업자없음오류"
    # 기환급자: 같은 귀속년도에 이미 환급을 받은 사람이 다시 조회(load) 액션을 할 때 발생 (208건)
    ALREADY_REFUNDED = "기환급자"
    # 세션만료 (106건)
    SESSION_EXPIRED = "세션만료"
    # 주민번호오류 (17건)
    INVALID_SSN = "주민번호오류"
    # 로그인오류 (2건)
    LOGIN_ERROR = "로그인오류"
    # 계속사업자없음오류 (1건)
    NO_CONT_BIZ = "계속사업자없음오류"
    # 계산오류 (1건)
    CALC_ERROR = "계산오류"
    
    # 기타 Load 에러 (샘플 데이터에서 미발견, 레거시 호환)
    NO_TAX_RETURN = "종소세신고내역없음"
    NOT_COMPLETE = "미완료"
    
    # 인증 관련 에러 (레거시 호환)
    AUTH_EXPIRED = "간편인증토큰만료"
    AUTH_NOT_COMPLETE = "간편인증미완료"
    LOGIN_FAILED = "홈택스로그인실패"


class ActionType(str, Enum):
    """액션 타입 (샘플 데이터 기반)"""
    CERT_REQUEST = "cert_request"
    CERT_RESPONSE = "cert_response"
    CHECK = "check"
    LOAD = "load"  # 개인사업자 조회 (99,090건)
    CALC = "calc"
    CORP_LOAD_CALC = "corp_load_calc"  # 법인 조회+계산 (908건)
    RELOAD_TO_S3 = "reload_to_s3"  # S3 재업로드 (2건)


class ProgressValue(str, Enum):
    """진행률 값 (샘플 데이터 기반)"""
    START = "1"      # 시작 (38,624건)
    LOADING = "80"   # 로딩 중 (227건) - 법인만 사용
    ALMOST = "95"    # 거의 완료 (22,238건)
    COMPLETE = "100" # 완료 (38,911건)


# 에러 타입별 기본 메시지 (샘플 데이터 기반 - 빈도순)
ERROR_MESSAGES: dict[ErrorType, str] = {
    # Load 액션 에러 (샘플 데이터 기반)
    ErrorType.NO_BIZ: "처리중 예외가 발생하였습니다. [ 사업자 변경대상이 아님 ]",  # 10,140건
    # ALREADY_REFUNDED는 get_error_message() 함수에서 동적으로 처리
    ErrorType.ALREADY_REFUNDED: "2024",  # 208건 - 같은 귀속년도에 이미 환급받은 경우 (기본값, 실제는 get_error_message에서 환경변수 사용)
    ErrorType.SESSION_EXPIRED: "중복접속으로 세션이 만료되었습니다.",  # 69건
    ErrorType.INVALID_SSN: "사업자등록번호/주민등록번호을(를) 확인하세요.",  # 17건
    ErrorType.LOGIN_ERROR: "[IDType]JUMIN_ID가 아닙니다.None",  # 2건
    ErrorType.CALC_ERROR: "브릭스모델_계산오류: division by zero",  # 1건
    ErrorType.NO_CONT_BIZ: "계속사업자 없음:주민번호 없음",  # 1건
    
    # 기타 에러 (레거시 호환)
    ErrorType.NO_TAX_RETURN: "종합소득세 신고 내역이 없습니다.",
    ErrorType.NOT_COMPLETE: "처리가 완료되지 않았습니다.",
    ErrorType.AUTH_EXPIRED: "간편인증 토큰이 만료되었습니다.",
    ErrorType.AUTH_NOT_COMPLETE: "간편인증이 완료되지 않았습니다.",
    ErrorType.LOGIN_FAILED: "홈택스 로그인에 실패했습니다.",
}

# 에러 타입별 대체 메시지 (샘플 데이터에서 발견된 변형 - 빈도순)
ERROR_MESSAGES_ALT: dict[ErrorType, list[str]] = {
    ErrorType.NO_BIZ: [
        "처리중 예외가 발생하였습니다. [ 사업자 변경대상이 아님 ]",  # 10,140건
        "경정청구 기간 내 사업자없음",  # 3,277건
        "환급대상사업자아님",  # 2,915건
    ],
    ErrorType.SESSION_EXPIRED: [
        "중복접속으로 세션이 만료되었습니다.",  # 69건
        "-9404(login):index_pp",  # 17건
        "-9404(login):UTESFAAF30",  # 7건
        "-9404(login):UTEABGAA21",  # 6건
        "-9404(login):UTXPPAAA24",  # 5건
        "-9404(login):UTERNAAZ99",  # 2건
    ],
}

# 에러 타입별 기본 발생 액션
ERROR_DEFAULT_ACTION: dict[ErrorType, ActionType] = {
    ErrorType.NO_BIZ: ActionType.LOAD,
    ErrorType.ALREADY_REFUNDED: ActionType.LOAD,
    ErrorType.SESSION_EXPIRED: ActionType.LOAD,
    ErrorType.INVALID_SSN: ActionType.LOAD,
    ErrorType.LOGIN_ERROR: ActionType.LOAD,
    ErrorType.CALC_ERROR: ActionType.LOAD,
    ErrorType.NO_CONT_BIZ: ActionType.LOAD,
    ErrorType.NO_TAX_RETURN: ActionType.LOAD,
    ErrorType.NOT_COMPLETE: ActionType.LOAD,
    ErrorType.AUTH_EXPIRED: ActionType.CERT_RESPONSE,
    ErrorType.AUTH_NOT_COMPLETE: ActionType.CERT_RESPONSE,
    ErrorType.LOGIN_FAILED: ActionType.CHECK,
}


def get_error_message(error_type: ErrorType) -> str:
    """에러 타입에 따른 메시지 반환 (환경변수 고려)"""
    import os
    
    # 기환급자 에러는 환경변수에서 귀속연도를 가져옴
    if error_type == ErrorType.ALREADY_REFUNDED:
        model_year = os.environ.get("MOCK_ITR_MODEL_YEAR", "2024")
        return model_year
    
    # 나머지는 기본 메시지 사용
    return ERROR_MESSAGES.get(error_type, "알 수 없는 오류가 발생했습니다.")


# 에러 빈도 통계 (샘플 데이터 기반)
ERROR_FREQUENCY: dict[ErrorType, int] = {
    ErrorType.NO_BIZ: 16338,
    ErrorType.ALREADY_REFUNDED: 208,
    ErrorType.SESSION_EXPIRED: 106,
    ErrorType.INVALID_SSN: 17,
    ErrorType.LOGIN_ERROR: 2,
    ErrorType.NO_CONT_BIZ: 1,
    ErrorType.CALC_ERROR: 1,
}
