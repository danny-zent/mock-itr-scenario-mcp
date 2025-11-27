"""MCP Server for Mock ITR Scenario management."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .models.enums import BizType, CertType, ErrorType, ERROR_MESSAGES, ERROR_MESSAGES_ALT, ERROR_DEFAULT_ACTION, ActionType, CorpType, ProgressValue, ERROR_FREQUENCY, get_error_message
from .models.scenario import (
    ScenarioConfig,
    UserInfo,
    TaxpayerInfo,
    RefundResult,
    RefundItem,
    BizLocation,
    ActionConfig,
    ProgressConfig,
    ProgressStep,
    CertInfo,
    CommonCert,
    CertRequestRequest,
    CertRequestResponse,
    CertResponseRequest,
    CertResponseResponse,
    CheckRequest,
    CheckResponse,
    LoadRequest,
    LoadResponse,
    CalcRequest,
    CalcResponse,
    CorpCheckRequest,
    CorpCheckResponse,
    CorpLoadCalcRequest,
    CorpLoadCalcResponse,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("mock-itr-scenario")

# Template storage (loaded from mock-itrLoader project)
TEMPLATES: dict[str, dict[str, Any]] = {}
MOCK_ITR_LOADER_PATH: Path | None = None


def get_mock_itr_loader_path() -> Path:
    """Get mock-itrLoader project path from environment."""
    global MOCK_ITR_LOADER_PATH
    if MOCK_ITR_LOADER_PATH is None:
        path = os.environ.get("MOCK_ITR_LOADER_PATH", "")
        if not path:
            # Try to find it relative to this project
            current_dir = Path(__file__).parent.parent.parent.parent
            possible_path = current_dir / "mock-itrLoader"
            if possible_path.exists():
                MOCK_ITR_LOADER_PATH = possible_path
            else:
                raise ValueError(
                    "MOCK_ITR_LOADER_PATH environment variable not set. "
                    "Please set it to the mock-itrLoader project path."
                )
        else:
            MOCK_ITR_LOADER_PATH = Path(path)
    return MOCK_ITR_LOADER_PATH


def load_templates() -> dict[str, dict[str, Any]]:
    """Load templates from mock-itrLoader project."""
    global TEMPLATES
    if TEMPLATES:
        return TEMPLATES
    
    try:
        mock_path = get_mock_itr_loader_path()
        templates_dir = mock_path / "mock_lambda" / "templates"
        
        if not templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            return TEMPLATES
        
        for template_file in templates_dir.glob("TPL_*.json"):
            template_id = template_file.stem
            with open(template_file, "r", encoding="utf-8") as f:
                TEMPLATES[template_id] = json.load(f)
                logger.info(f"Loaded template: {template_id}")
        
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")
    
    return TEMPLATES


# ============================================================================
# Helper Functions for Request/Response Data
# ============================================================================

def build_cert_request_data(user_info: UserInfo, user_ern: str = "") -> dict[str, Any]:
    """cert_request 요청 데이터 생성"""
    # cert_type이 없으면 기본값 설정
    if not user_info.cert_type:
        user_info_with_cert = UserInfo(
            name=user_info.name,
            phone=user_info.phone,
            birthday=user_info.birthday,
            cert_type="kakao",  # 기본값
        )
    else:
        user_info_with_cert = user_info
    
    request = CertRequestRequest(
        action="cert_request",
        user_info=user_info_with_cert,
        user_ern=user_ern,
    )
    return request.model_dump(exclude_none=True)


def build_cert_request_response(success: bool, cert_info: CertInfo | None = None, error_type: str | None = None, error_msg: str | None = None) -> dict[str, Any]:
    """cert_request 응답 데이터 생성"""
    if success and cert_info:
        response = CertRequestResponse(
            error={"status": False, "type": "", "msg": ""},
            result={
                "reqTxId": cert_info.req_tx_id or "7cd3...",
                "token": cert_info.token or "eyJh...",
                "cxId": cert_info.cx_id or "10db...",
            }
        )
    else:
        response = CertRequestResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_cert_response_data(user_info: UserInfo, cert_info: CertInfo, user_ern: str = "") -> dict[str, Any]:
    """cert_response 요청 데이터 생성"""
    request = CertResponseRequest(
        action="cert_response",
        user_info=user_info,
        cert_info=cert_info,
        user_ern=user_ern,
    )
    return request.model_dump(exclude_none=True)


def build_cert_response_response(success: bool, token: str = "", error_type: str | None = None, error_msg: str | None = None) -> dict[str, Any]:
    """cert_response 응답 데이터 생성"""
    if success:
        response = CertResponseResponse(
            error={"status": False, "type": "", "msg": ""},
            result={"token": token or "eyJh..."}
        )
    else:
        response = CertResponseResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_check_request_data(id: str = "", pw: str = "", token: str = "", common_cert: CommonCert | None = None, cookies: dict[str, Any] | None = None, user_ern: str = "") -> dict[str, Any]:
    """check 요청 데이터 생성"""
    request = CheckRequest(
        action="check",
        id=id,
        pw=pw,
        token=token,  # cert_response에서 받은 token (간편인증 flow)
        common_cert=common_cert,  # 공동인증서 정보 (공동인증서 flow)
        cookies=cookies,
        user_ern=user_ern,
    )
    return request.model_dump(exclude_none=True)


def build_check_response(success: bool, tin: str = "", cookies: dict[str, Any] | None = None, error_type: str | None = None, error_msg: str | None = None) -> dict[str, Any]:
    """check 응답 데이터 생성"""
    if success:
        response = CheckResponse(
            error={"status": False, "type": "", "msg": ""},
            result={
                "tin": tin or "000000000000000000",
                "cookies": cookies or {
                    ".hometax.go.kr": {
                        "NTS_LOGIN_SYSTEM_CODE_P": "TXPP",
                        "TXPPsessionID": "Fe8izH1OP6CLH0x5pRJps7hZm28ySco3x3NPWDxcgYyfmsXGbNyF6NpJZK9r3OQ1.tupiwsp26_servlet_TXPP01"
                    }
                }
            }
        )
    else:
        response = CheckResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_load_request_data(
    id: str = "",
    pw: str = "",
    token: str = "",
    cookies: dict[str, Any] | None = None,
    reg_no: str = "",
    export_file_prefix: str = "",
    user_ern: str = "",
    use_sqs: bool = False,
    corp_type: str = "",
    tin: str = "",
    send_next_step: bool = True,
) -> dict[str, Any]:
    """load 요청 데이터 생성"""
    request = LoadRequest(
        action="load",
        id=id,
        pw=pw,
        token=token,
        cookies=cookies,
        reg_no=reg_no,
        export_file_prefix=export_file_prefix,
        user_ern=user_ern,
        use_sqs=use_sqs,
        corp_type=corp_type,
        tin=tin,
        send_next_step=send_next_step,
    )
    return request.model_dump(exclude_none=True)


def build_load_response(
    success: bool,
    refund_result: RefundResult | None = None,
    taxpayer_info: TaxpayerInfo | None = None,
    version_info: dict[str, Any] | None = None,
    error_type: str | None = None,
    error_msg: str | None = None,
) -> dict[str, Any]:
    """load 응답 데이터 생성"""
    if success and refund_result:
        tin = taxpayer_info.tin if taxpayer_info else "000000154401000000"
        # 환경변수에서 귀속연도 가져오기
        model_year = os.environ.get("MOCK_ITR_MODEL_YEAR", "2024")
        response = LoadResponse(
            error={"status": False, "type": "", "msg": ""},
            result={
                "수집데이터_key": f"{tin}_data.json",
                "계산데이터_key": f"{tin}_calc_data.json",
                "결과데이터_key": f"{tin}_result_data.json",
                "납세자명": taxpayer_info.tax_office_name if taxpayer_info else "테스트납세자",
                "총환급세액": float(refund_result.total_refund),
                "버전정보": version_info or {"연도": model_year, "버전": "1.0"},
                "신고자": taxpayer_info.tax_office_name if taxpayer_info else "테스트납세자",
                "주민등록번호": "",
                "관할세무서": taxpayer_info.tax_office_name if taxpayer_info else "강남세무서",
                "담당조사관": "",
                "담당조사관전화번호": "",
                "감면Only추가구제": False,
                "감면Only환급가능금액": 0.0,
                "고용보험조회필요": False,
                "전자신고": True,
                "최근계산연도": int(model_year),
                "사업장": {
                    "2019": {},
                    "2020": {},
                    "2021": {},
                    "2022": {},
                    "2023": {},
                },
                "터칭콜반영": False,
                "터칭콜검토필요": {
                    "2019": True,
                    "2020": True,
                    "2021": True,
                    "2022": True,
                    "2023": True,
                },
                "refundAmt_SVI": float(refund_result.total_refund),
            }
        )
    else:
        response = LoadResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_calc_request_data(
    export_file_prefix: str,
    model_year: str = "",
    survey_contents: dict[str, Any] | None = None,
    user_ern: str = "",
    calc_version: str = "latest",
) -> dict[str, Any]:
    """calc 요청 데이터 생성"""
    request = CalcRequest(
        action="calc",
        export_file_prefix=export_file_prefix,
        model_year=model_year,
        survey_contents=survey_contents,
        user_ern=user_ern,
        calc_version=calc_version,
    )
    return request.model_dump(exclude_none=True)


def build_calc_response(success: bool, result_data: dict[str, Any] | None = None, error_type: str | None = None, error_msg: str | None = None) -> dict[str, Any]:
    """calc 응답 데이터 생성"""
    if success:
        response = CalcResponse(
            error={"status": False, "type": "", "msg": ""},
            result=result_data or {}
        )
    else:
        response = CalcResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_corp_check_request_data(
    id: str = "",
    pw: str = "",
    resno: str = "",
    common_cert: CommonCert | None = None,
    cookies: dict[str, Any] | None = None,
    user_ern: str = "",
) -> dict[str, Any]:
    """corp_check 요청 데이터 생성"""
    request = CorpCheckRequest(
        action="corp_check",
        id=id,
        pw=pw,
        resno=resno,
        common_cert=common_cert,
        cookies=cookies,
        user_ern=user_ern,
    )
    return request.model_dump(exclude_none=True)


def build_corp_check_response(
    success: bool,
    biz_name: str = "",
    biz_no: str = "",
    ceo_name: str = "",
    tin: str = "",
    cookies: dict[str, Any] | None = None,
    error_type: str | None = None,
    error_msg: str | None = None,
) -> dict[str, Any]:
    """corp_check 응답 데이터 생성"""
    if success:
        response = CorpCheckResponse(
            error={"status": False, "type": "", "msg": ""},
            result={
                "구분": "법인사업자",
                "사업체명": biz_name or "주식회사 테스트사업자",
                "사업자번호": biz_no or "1234104321",
                "대표자명": ceo_name or "테스트대표자",
                "tin": tin or "000000000000000000",
                "cookies": cookies or {
                    ".hometax.go.kr": {
                        "NTS_LOGIN_SYSTEM_CODE_P": "TXPP",
                        "TXPPsessionID": "Fe8izH1OP6CLH0x5pRJps7hZm28ySco3x3NPWDxcgYyfmsXGbNyF6NpJZK9r3OQ1.tupiwsp26_servlet_TXPP01"
                    }
                }
            }
        )
    else:
        response = CorpCheckResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


def build_corp_load_calc_request_data(
    cookies: dict[str, Any] | None = None,
    export_file_prefix: str = "",
    user_ern: str = "",
    use_sqs: bool = False,
    tin: str = "",
) -> dict[str, Any]:
    """corp_load_calc 요청 데이터 생성"""
    request = CorpLoadCalcRequest(
        action="corp_load_calc",
        cookies=cookies,  # check에서 받은 cookies
        export_file_prefix=export_file_prefix,
        user_ern=user_ern,
        use_sqs=use_sqs,
        tin=tin,
    )
    return request.model_dump(exclude_none=True)


def build_corp_load_calc_response(
    success: bool,
    result_data: dict[str, Any] | None = None,
    error_type: str | None = None,
    error_msg: str | None = None,
) -> dict[str, Any]:
    """corp_load_calc 응답 데이터 생성"""
    if success:
        response = CorpLoadCalcResponse(
            error={"status": False, "type": "", "msg": ""},
            result=result_data or {
                "계산결과": {
                    "총납부세액": 0.0,
                    "미래절세효과": 0.0,
                }
            }
        )
    else:
        response = CorpLoadCalcResponse(
            error={
                "status": True,
                "type": error_type or "",
                "msg": error_msg or "",
            },
            result={}
        )
    return response.model_dump(exclude_none=True)


# ============================================================================
# MCP Tools
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="template_list",
            description="사용 가능한 시나리오 템플릿 목록을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "템플릿 카테고리 (normal, error, corp, all)",
                        "enum": ["normal", "error", "corp", "all"],
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="template_load",
            description="특정 템플릿을 로드하여 상세 내용을 확인합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "템플릿 ID (예: TPL_NORMAL_BIZ_HIGH)"
                    }
                },
                "required": ["template_id"]
            }
        ),
        Tool(
            name="scenario_build_normal",
            description="정상 환급 시나리오를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "total_refund": {
                        "type": "integer",
                        "description": "총 환급액 (원)"
                    },
                    "biz_type": {
                        "type": "string",
                        "description": "사업자 유형",
                        "enum": ["individual_biz", "non_biz", "corp"],
                        "default": "individual_biz"
                    },
                    "창중감_환급액": {
                        "type": "integer",
                        "description": "창업중소기업감면 환급액",
                        "default": 0
                    },
                    "고용증대_환급액": {
                        "type": "integer",
                        "description": "고용증대 환급액",
                        "default": 0
                    },
                    "사회보험료_환급액": {
                        "type": "integer",
                        "description": "사회보험료 환급액",
                        "default": 0
                    },
                    "양도세_환급액": {
                        "type": "integer",
                        "description": "양도세 환급액",
                        "default": 0
                    }
                },
                "required": ["total_refund"]
            }
        ),
        Tool(
            name="scenario_build_error",
            description="에러 시나리오를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "에러 타입",
                        "enum": [e.value for e in ErrorType]
                    },
                    "error_msg": {
                        "type": "string",
                        "description": "에러 메시지 (미입력시 기본 메시지 사용)"
                    },
                    "action": {
                        "type": "string",
                        "description": "에러 발생 액션",
                        "enum": ["cert_request", "cert_response", "check", "load"],
                        "default": "load"
                    }
                },
                "required": ["error_type"]
            }
        ),
        Tool(
            name="scenario_build_progress",
            description="진행률 전송을 포함한 시나리오를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "total_refund": {
                        "type": "integer",
                        "description": "총 환급액 (원)"
                    },
                    "queue_name": {
                        "type": "string",
                        "description": "SQS 큐 이름",
                        "default": "refund-search.fifo"
                    },
                    "steps": {
                        "type": "array",
                        "description": "진행률 단계 목록",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_name": {"type": "string"},
                                "progress": {"type": "string"},
                                "delay_seconds": {"type": "number", "default": 0.5}
                            },
                            "required": ["step_name", "progress"]
                        }
                    }
                },
                "required": ["total_refund"]
            }
        ),
        Tool(
            name="scenario_validate",
            description="시나리오 유효성을 검사합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "object",
                        "description": "검사할 시나리오 객체"
                    }
                },
                "required": ["scenario"]
            }
        ),
        Tool(
            name="scenario_assign",
            description="시나리오를 특정 user_ern에 할당합니다 (DynamoDB에 저장).",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_ern": {
                        "type": "string",
                        "description": "사용자 ERN"
                    },
                    "scenario": {
                        "type": "object",
                        "description": "할당할 시나리오 객체"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "사용할 템플릿 ID (scenario 미입력시)"
                    }
                },
                "required": ["user_ern"]
            }
        ),
        Tool(
            name="scenario_unassign",
            description="user_ern에서 시나리오 할당을 해제합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_ern": {
                        "type": "string",
                        "description": "사용자 ERN"
                    }
                },
                "required": ["user_ern"]
            }
        ),
        Tool(
            name="error_types_list",
            description="지원하는 에러 타입 목록을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="scenario_build_simple_auth",
            description="[개인] 간편인증 flow 시나리오를 생성합니다. (cert_request -> cert_response -> check -> load)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "phone": {
                        "type": "string",
                        "description": "전화번호",
                        "default": "01012345678"
                    },
                    "birthday": {
                        "type": "string",
                        "description": "생년월일 (YYYYMMDD)",
                        "default": "19900101"
                    },
                    "cert_type": {
                        "type": "string",
                        "description": "간편인증 유형",
                        "enum": ["kakao", "naver"],
                        "default": "kakao"
                    },
                    "total_refund": {
                        "type": "integer",
                        "description": "총 환급액 (원)"
                    }
                },
                "required": ["total_refund"]
            }
        ),
        Tool(
            name="scenario_build_common_cert",
            description="[개인] 공동인증서 flow 시나리오를 생성합니다. (check -> load)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "total_refund": {
                        "type": "integer",
                        "description": "총 환급액 (원)"
                    }
                },
                "required": ["total_refund"]
            }
        ),
        Tool(
            name="scenario_build_corp_common_cert",
            description="[법인] 공동인증서 flow 시나리오를 생성합니다. (check -> corp_load_calc)",
            inputSchema={
                "type": "object",
                "properties": {
                    "biz_name": {
                        "type": "string",
                        "description": "사업체명",
                        "default": "주식회사 테스트사업자"
                    },
                    "biz_no": {
                        "type": "string",
                        "description": "사업자번호",
                        "default": "1234104321"
                    },
                    "ceo_name": {
                        "type": "string",
                        "description": "대표자명",
                        "default": "테스트대표자"
                    }
                }
            }
        ),
        Tool(
            name="scenario_build_simple_auth_fail",
            description="카카오톡 간편인증 요청 실패 시나리오를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "phone": {
                        "type": "string",
                        "description": "전화번호",
                        "default": "01012345678"
                    },
                    "birthday": {
                        "type": "string",
                        "description": "생년월일 (YYYYMMDD)",
                        "default": "19900101"
                    },
                    "cert_type": {
                        "type": "string",
                        "description": "간편인증 유형",
                        "enum": ["kakao", "naver"],
                        "default": "kakao"
                    },
                    "error_msg": {
                        "type": "string",
                        "description": "에러 메시지 (미입력시 기본 메시지 사용)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="scenario_build_cert_response_fail",
            description="간편인증 완료 확인(cert_response) 실패 시나리오를 생성합니다. (cert_request 성공 후 cert_response 실패)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "사용자 이름",
                        "default": "테스트사용자"
                    },
                    "phone": {
                        "type": "string",
                        "description": "전화번호",
                        "default": "01012345678"
                    },
                    "birthday": {
                        "type": "string",
                        "description": "생년월일 (YYYYMMDD)",
                        "default": "19900101"
                    },
                    "cert_type": {
                        "type": "string",
                        "description": "간편인증 유형",
                        "enum": ["kakao", "naver"],
                        "default": "kakao"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "에러 타입",
                        "enum": ["간편인증토큰만료", "간편인증미완료", "간편인증오류"],
                        "default": "간편인증미완료"
                    },
                    "error_msg": {
                        "type": "string",
                        "description": "에러 메시지 (미입력시 기본 메시지 사용)",
                        "default": ""
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "template_list":
        return await handle_template_list(arguments)
    elif name == "template_load":
        return await handle_template_load(arguments)
    elif name == "scenario_build_normal":
        return await handle_scenario_build_normal(arguments)
    elif name == "scenario_build_error":
        return await handle_scenario_build_error(arguments)
    elif name == "scenario_build_progress":
        return await handle_scenario_build_progress(arguments)
    elif name == "scenario_validate":
        return await handle_scenario_validate(arguments)
    elif name == "scenario_assign":
        return await handle_scenario_assign(arguments)
    elif name == "scenario_unassign":
        return await handle_scenario_unassign(arguments)
    elif name == "error_types_list":
        return await handle_error_types_list(arguments)
    elif name == "scenario_build_simple_auth":
        return await handle_scenario_build_simple_auth(arguments)
    elif name == "scenario_build_common_cert":
        return await handle_scenario_build_common_cert(arguments)
    elif name == "scenario_build_corp_common_cert":
        return await handle_scenario_build_corp_common_cert(arguments)
    elif name == "scenario_build_simple_auth_fail":
        return await handle_scenario_build_simple_auth_fail(arguments)
    elif name == "scenario_build_cert_response_fail":
        return await handle_scenario_build_cert_response_fail(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_template_list(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle template_list tool."""
    category = arguments.get("category", "all")
    templates = load_templates()
    
    result = []
    for template_id, template_data in templates.items():
        # 카테고리 필터링
        if category != "all":
            if category == "normal" and "ERR" in template_id:
                continue
            if category == "error" and "ERR" not in template_id:
                continue
            if category == "corp" and "CORP" not in template_id:
                continue
        
        # 템플릿 요약 정보
        refund_result = template_data.get("refund_result", {})
        total_refund = refund_result.get("total_refund", 0)
        biz_type = template_data.get("biz_type", "unknown")
        description = template_data.get("description", "")
        
        result.append({
            "template_id": template_id,
            "description": description,
            "total_refund": total_refund,
            "biz_type": biz_type,
        })
    
    return [TextContent(
        type="text",
        text=json.dumps({"templates": result, "count": len(result)}, ensure_ascii=False, indent=2)
    )]


async def handle_template_load(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle template_load tool."""
    template_id = arguments.get("template_id", "")
    templates = load_templates()
    
    if template_id not in templates:
        available = list(templates.keys())
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Template not found: {template_id}",
                "available_templates": available
            }, ensure_ascii=False, indent=2)
        )]
    
    return [TextContent(
        type="text",
        text=json.dumps(templates[template_id], ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_normal(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_build_normal tool."""
    user_name = arguments.get("user_name", "테스트사용자")
    total_refund = arguments.get("total_refund", 0)
    biz_type_str = arguments.get("biz_type", "individual_biz")
    
    biz_type = BizType(biz_type_str)
    
    # 환급 항목
    창중감 = arguments.get("창중감_환급액", 0)
    고용증대 = arguments.get("고용증대_환급액", 0)
    사회보험료 = arguments.get("사회보험료_환급액", 0)
    양도세 = arguments.get("양도세_환급액", 0)
    
    # 사용자 정보 생성
    user_info = UserInfo(name=user_name)
    taxpayer_info = TaxpayerInfo()
    
    # 비사업자인 경우: 항상 사업자없음오류 발생 (양도세 환급액이 있어도 에러)
    if biz_type == BizType.NON_BIZ:
        refund_result = RefundResult(
            total_refund=total_refund,
            양도세_환급액=양도세,
        )
        
        # load 액션 요청/응답 데이터 생성
        load_request = build_load_request_data(
            token="",
            export_file_prefix=taxpayer_info.tin,
        )
        load_response = build_load_response(
            success=False,
            error_type=ErrorType.NO_BIZ.value,
            error_msg=ERROR_MESSAGES[ErrorType.NO_BIZ],
        )
        
        scenario = ScenarioConfig(
            scenario_name=f"비사업자_{user_name}",
            description=f"{user_name}의 비사업자 시나리오 (사업자없음오류 발생, 양도세 환급액: {양도세:,}원)",
            user_info=user_info,
            taxpayer_info=taxpayer_info,
            biz_type=biz_type,
            refund_result=refund_result,
            load_config=ActionConfig(
                success=False,
                error_type=ErrorType.NO_BIZ.value,
                error_msg=ERROR_MESSAGES[ErrorType.NO_BIZ],
                request_data=load_request,
                response_data=load_response,
            ),
        )
        
        return [TextContent(
            type="text",
            text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
        )]
    
    # 정상 환급 시나리오 생성
    refund_result = RefundResult(
        total_refund=total_refund,
        창중감_환급액=창중감,
        고용증대_환급액=고용증대,
        사회보험료_환급액=사회보험료,
        양도세_환급액=양도세,
    )
    
    # check 액션 요청/응답 데이터 생성
    check_request = build_check_request_data(user_ern="")
    check_response = build_check_response(
        success=True,
        tin=taxpayer_info.tin,
    )
    
    # load 액션 요청/응답 데이터 생성
    load_request = build_load_request_data(
        cookies=check_response.get("result", {}).get("cookies"),
        export_file_prefix=taxpayer_info.tin,
    )
    load_response = build_load_response(
        success=True,
        refund_result=refund_result,
        taxpayer_info=taxpayer_info,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"정상환급_{user_name}_{total_refund}원",
        description=f"{user_name}의 정상 환급 시나리오 (총 {total_refund:,}원)",
        user_info=user_info,
        taxpayer_info=taxpayer_info,
        biz_type=biz_type,
        refund_result=refund_result,
        check_config=ActionConfig(
            success=True,
            request_data=check_request,
            response_data=check_response,
        ),
        load_config=ActionConfig(
            success=True,
            request_data=load_request,
            response_data=load_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_error(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_build_error tool."""
    user_name = arguments.get("user_name", "테스트사용자")
    error_type_str = arguments.get("error_type", "")
    error_msg = arguments.get("error_msg", "")
    action_str = arguments.get("action", "")
    
    try:
        error_type = ErrorType(error_type_str)
    except ValueError:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Unknown error type: {error_type_str}",
                "available_types": [e.value for e in ErrorType]
            }, ensure_ascii=False, indent=2)
        )]
    
    # 기본 메시지 사용 (환경변수 고려)
    if not error_msg:
        error_msg = get_error_message(error_type)
    
    # 기본 액션 사용
    if not action_str:
        action_type = ERROR_DEFAULT_ACTION.get(error_type, ActionType.LOAD)
        action_str = action_type.value
    
    # 사용자 정보 생성
    user_info = UserInfo(name=user_name)
    
    # 시나리오 생성
    scenario = ScenarioConfig(
        scenario_name=f"에러_{error_type.value}_{user_name}",
        description=f"{user_name}의 {error_type.value} 에러 시나리오",
        user_info=user_info,
    )
    
    # 해당 액션에 에러 설정 및 요청/응답 데이터 생성
    if action_str == "cert_request":
        request_data = build_cert_request_data(user_info=user_info)
        response_data = build_cert_request_response(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
        )
        scenario.cert_request_config = ActionConfig(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
            request_data=request_data,
            response_data=response_data,
        )
    elif action_str == "cert_response":
        cert_info = CertInfo()
        request_data = build_cert_response_data(user_info=user_info, cert_info=cert_info)
        response_data = build_cert_response_response(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
        )
        scenario.cert_response_config = ActionConfig(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
            request_data=request_data,
            response_data=response_data,
        )
    elif action_str == "check":
        request_data = build_check_request_data()
        response_data = build_check_response(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
        )
        scenario.check_config = ActionConfig(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
            request_data=request_data,
            response_data=response_data,
        )
    else:  # load
        taxpayer_info = TaxpayerInfo()
        request_data = build_load_request_data(export_file_prefix=taxpayer_info.tin)
        response_data = build_load_response(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
        )
        scenario.load_config = ActionConfig(
            success=False,
            error_type=error_type.value,
            error_msg=error_msg,
            request_data=request_data,
            response_data=response_data,
        )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_progress(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_build_progress tool."""
    user_name = arguments.get("user_name", "테스트사용자")
    total_refund = arguments.get("total_refund", 0)
    queue_name = arguments.get("queue_name", "refund-search.fifo")
    steps_data = arguments.get("steps", [])
    
    # 기본 진행률 단계
    if not steps_data:
        steps_data = [
            {"step_name": "홈택스 로그인", "progress": "10%", "delay_seconds": 0.5},
            {"step_name": "신고내역 조회", "progress": "30%", "delay_seconds": 1.0},
            {"step_name": "환급액 계산", "progress": "60%", "delay_seconds": 1.5},
            {"step_name": "결과 생성", "progress": "90%", "delay_seconds": 0.5},
        ]
    
    steps = [
        ProgressStep(
            step_name=s.get("step_name", ""),
            progress=s.get("progress", "0%"),
            delay_seconds=s.get("delay_seconds", 0.5),
        )
        for s in steps_data
    ]
    
    user_info = UserInfo(name=user_name)
    taxpayer_info = TaxpayerInfo()
    refund_result = RefundResult(total_refund=total_refund)
    
    # check 액션 요청/응답 데이터 생성
    check_request = build_check_request_data(user_ern="")
    check_response = build_check_response(
        success=True,
        tin=taxpayer_info.tin,
    )
    
    # load 액션 요청/응답 데이터 생성
    load_request = build_load_request_data(
        cookies=check_response.get("result", {}).get("cookies"),
        export_file_prefix=taxpayer_info.tin,
        use_sqs=True,
    )
    load_response = build_load_response(
        success=True,
        refund_result=refund_result,
        taxpayer_info=taxpayer_info,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"진행률테스트_{user_name}",
        description=f"{user_name}의 진행률 전송 테스트 시나리오",
        user_info=user_info,
        taxpayer_info=taxpayer_info,
        refund_result=refund_result,
        check_config=ActionConfig(
            success=True,
            request_data=check_request,
            response_data=check_response,
        ),
        load_config=ActionConfig(
            success=True,
            request_data=load_request,
            response_data=load_response,
        ),
        progress_config=ProgressConfig(
            enabled=True,
            queue_name=queue_name,
            steps=steps,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_validate(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_validate tool."""
    scenario_data = arguments.get("scenario", {})
    
    errors = []
    warnings = []
    
    try:
        scenario = ScenarioConfig.from_dict(scenario_data)
        
        # 추가 검증
        if scenario.biz_type == BizType.INDIVIDUAL_BIZ:
            if scenario.refund_result.total_refund == 0:
                warnings.append("개인사업자 시나리오인데 환급액이 0원입니다.")
        
        if scenario.user_info.phone and len(scenario.user_info.phone) != 11:
            warnings.append("전화번호가 11자리가 아닙니다.")
        
        if scenario.user_info.birthday and len(scenario.user_info.birthday) != 8:
            errors.append("생년월일은 YYYYMMDD 형식이어야 합니다.")
        
        if scenario.taxpayer_info.tin and len(scenario.taxpayer_info.tin) != 18:
            errors.append("납세자관리번호는 18자리여야 합니다.")
        
    except Exception as e:
        errors.append(f"시나리오 파싱 오류: {str(e)}")
    
    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, ensure_ascii=False, indent=2)
    )]


async def handle_scenario_assign(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_assign tool."""
    user_ern = arguments.get("user_ern", "")
    scenario_data = arguments.get("scenario")
    template_id = arguments.get("template_id")
    
    if not user_ern:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "user_ern is required"}, ensure_ascii=False)
        )]
    
    # 시나리오 결정
    if scenario_data:
        scenario = scenario_data
    elif template_id:
        templates = load_templates()
        if template_id not in templates:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Template not found: {template_id}",
                    "available_templates": list(templates.keys())
                }, ensure_ascii=False, indent=2)
            )]
        scenario = templates[template_id]
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "Either scenario or template_id is required"}, ensure_ascii=False)
        )]
    
    # DynamoDB 저장 시도
    try:
        import boto3
        
        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")
        table_name = os.environ.get("SCENARIO_TABLE_NAME", "mock-itr-scenarios")
        region = os.environ.get("AWS_REGION", "ap-northeast-2")
        
        if endpoint_url:
            dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        else:
            dynamodb = boto3.resource("dynamodb", region_name=region)
        
        table = dynamodb.Table(table_name)
        
        item = {
            "user_ern": user_ern,
            "scenario_config": scenario,
        }
        
        table.put_item(Item=item)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "user_ern": user_ern,
                "message": f"시나리오가 {user_ern}에 할당되었습니다."
            }, ensure_ascii=False, indent=2)
        )]
        
    except Exception as e:
        # DynamoDB 연결 실패시 JSON 출력
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"DynamoDB 저장 실패: {str(e)}",
                "user_ern": user_ern,
                "scenario": scenario,
                "note": "DynamoDB에 저장하지 못했습니다. 위 시나리오를 수동으로 저장해주세요."
            }, ensure_ascii=False, indent=2)
        )]


async def handle_scenario_unassign(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scenario_unassign tool."""
    user_ern = arguments.get("user_ern", "")
    
    if not user_ern:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "user_ern is required"}, ensure_ascii=False)
        )]
    
    try:
        import boto3
        
        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")
        table_name = os.environ.get("SCENARIO_TABLE_NAME", "mock-itr-scenarios")
        region = os.environ.get("AWS_REGION", "ap-northeast-2")
        
        if endpoint_url:
            dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        else:
            dynamodb = boto3.resource("dynamodb", region_name=region)
        
        table = dynamodb.Table(table_name)
        table.delete_item(Key={"user_ern": user_ern})
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "user_ern": user_ern,
                "message": f"{user_ern}의 시나리오 할당이 해제되었습니다."
            }, ensure_ascii=False, indent=2)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"DynamoDB 삭제 실패: {str(e)}",
                "user_ern": user_ern,
            }, ensure_ascii=False, indent=2)
        )]


async def handle_error_types_list(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle error_types_list tool."""
    error_types = []
    
    for error_type in ErrorType:
        default_action = ERROR_DEFAULT_ACTION.get(error_type, ActionType.LOAD)
        alt_messages = ERROR_MESSAGES_ALT.get(error_type, [])
        frequency = ERROR_FREQUENCY.get(error_type, 0)
        error_types.append({
            "type": error_type.value,
            "message": get_error_message(error_type),
            "alt_messages": alt_messages,
            "default_action": default_action.value,
            "frequency": frequency,  # 샘플 데이터 기반 빈도
        })
    
    # 빈도순 정렬
    error_types.sort(key=lambda x: x["frequency"], reverse=True)
    
    return [TextContent(
        type="text",
        text=json.dumps({"error_types": error_types}, ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_simple_auth(arguments: dict[str, Any]) -> list[TextContent]:
    """[개인] 간편인증 flow 시나리오 생성: cert_request -> cert_response -> check -> load"""
    user_name = arguments.get("user_name", "테스트사용자")
    phone = arguments.get("phone", "01012345678")
    birthday = arguments.get("birthday", "19900101")
    cert_type = arguments.get("cert_type", "kakao")
    total_refund = arguments.get("total_refund", 0)
    
    # 사용자 정보 생성
    user_info = UserInfo(
        name=user_name,
        phone=phone,
        birthday=birthday,
        cert_type=cert_type,
    )
    taxpayer_info = TaxpayerInfo()
    refund_result = RefundResult(total_refund=total_refund)
    
    # 1. cert_request: 간편인증 요청
    cert_request_data = build_cert_request_data(user_info=user_info)
    cert_info = CertInfo(
        cert_type=CertType(cert_type),
        req_tx_id="7cd3...",
        token="eyJh...",
        cx_id="10db...",
    )
    cert_request_response = build_cert_request_response(success=True, cert_info=cert_info)
    
    # 2. cert_response: 간편인증 완료 (token 반환)
    cert_response_data = build_cert_response_data(user_info=user_info, cert_info=cert_info)
    auth_token = "eyJh..."  # cert_response에서 반환되는 token
    cert_response_response = build_cert_response_response(success=True, token=auth_token)
    
    # 3. check: token으로 tin, cookies 반환
    check_request = build_check_request_data(token=auth_token)
    check_response = build_check_response(
        success=True,
        tin=taxpayer_info.tin,
    )
    
    # 4. load: cookies로 수집 및 계산
    load_request = build_load_request_data(
        cookies=check_response.get("result", {}).get("cookies"),
        export_file_prefix=taxpayer_info.tin,
    )
    load_response = build_load_response(
        success=True,
        refund_result=refund_result,
        taxpayer_info=taxpayer_info,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"간편인증_{user_name}_{total_refund}원",
        description=f"[개인] 간편인증 flow: {user_name}의 환급 시나리오 (총 {total_refund:,}원)",
        user_info=user_info,
        taxpayer_info=taxpayer_info,
        cert_info=cert_info,
        biz_type=BizType.INDIVIDUAL_BIZ,
        refund_result=refund_result,
        cert_request_config=ActionConfig(
            success=True,
            request_data=cert_request_data,
            response_data=cert_request_response,
        ),
        cert_response_config=ActionConfig(
            success=True,
            request_data=cert_response_data,
            response_data=cert_response_response,
        ),
        check_config=ActionConfig(
            success=True,
            request_data=check_request,
            response_data=check_response,
        ),
        load_config=ActionConfig(
            success=True,
            request_data=load_request,
            response_data=load_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_common_cert(arguments: dict[str, Any]) -> list[TextContent]:
    """[개인] 공동인증서 flow 시나리오 생성: check -> load"""
    user_name = arguments.get("user_name", "테스트사용자")
    total_refund = arguments.get("total_refund", 0)
    
    user_info = UserInfo(name=user_name)
    taxpayer_info = TaxpayerInfo()
    refund_result = RefundResult(total_refund=total_refund)
    
    # 공동인증서 정보
    common_cert = CommonCert(
        sign_cert="base64_encoded_cert...",
        sign_pri="base64_encoded_pri...",
        sign_pw="cert_password",
    )
    
    # 1. check: 공동인증서로 tin, cookies 반환
    check_request = build_check_request_data(common_cert=common_cert)
    check_response = build_check_response(
        success=True,
        tin=taxpayer_info.tin,
    )
    
    # 2. load: cookies로 수집 및 계산
    load_request = build_load_request_data(
        cookies=check_response.get("result", {}).get("cookies"),
        export_file_prefix=taxpayer_info.tin,
    )
    load_response = build_load_response(
        success=True,
        refund_result=refund_result,
        taxpayer_info=taxpayer_info,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"공동인증서_{user_name}_{total_refund}원",
        description=f"[개인] 공동인증서 flow: {user_name}의 환급 시나리오 (총 {total_refund:,}원)",
        user_info=user_info,
        taxpayer_info=taxpayer_info,
        biz_type=BizType.INDIVIDUAL_BIZ,
        refund_result=refund_result,
        check_config=ActionConfig(
            success=True,
            request_data=check_request,
            response_data=check_response,
        ),
        load_config=ActionConfig(
            success=True,
            request_data=load_request,
            response_data=load_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_corp_common_cert(arguments: dict[str, Any]) -> list[TextContent]:
    """[법인] 공동인증서 flow 시나리오 생성: check -> corp_load_calc"""
    biz_name = arguments.get("biz_name", "주식회사 테스트사업자")
    biz_no = arguments.get("biz_no", "1234104321")
    ceo_name = arguments.get("ceo_name", "테스트대표자")
    
    taxpayer_info = TaxpayerInfo()
    
    # 공동인증서 정보
    common_cert = CommonCert(
        sign_cert="base64_encoded_cert...",
        sign_pri="base64_encoded_pri...",
        sign_pw="cert_password",
    )
    
    # 1. check: 공동인증서로 tin, cookies 반환
    check_request = build_check_request_data(common_cert=common_cert)
    check_response = build_check_response(
        success=True,
        tin=taxpayer_info.tin,
    )
    
    # 2. corp_load_calc: cookies로 법인 수집 및 계산
    corp_load_calc_request = build_corp_load_calc_request_data(
        cookies=check_response.get("result", {}).get("cookies"),
        export_file_prefix=taxpayer_info.tin,
        tin=taxpayer_info.tin,
    )
    corp_load_calc_response = build_corp_load_calc_response(
        success=True,
        result_data={
            "계산결과": {
                "총납부세액": 0.0,
                "미래절세효과": 0.0,
            }
        }
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"법인공동인증서_{biz_name}",
        description=f"[법인] 공동인증서 flow: {biz_name}의 법인 조회 시나리오",
        taxpayer_info=taxpayer_info,
        biz_type=BizType.CORP,
        check_config=ActionConfig(
            success=True,
            request_data=check_request,
            response_data=check_response,
        ),
        corp_load_calc_config=ActionConfig(
            success=True,
            request_data=corp_load_calc_request,
            response_data=corp_load_calc_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_simple_auth_fail(arguments: dict[str, Any]) -> list[TextContent]:
    """카카오톡 간편인증 요청 실패 시나리오 생성"""
    user_name = arguments.get("user_name", "테스트사용자")
    phone = arguments.get("phone", "01012345678")
    birthday = arguments.get("birthday", "19900101")
    cert_type = arguments.get("cert_type", "kakao")
    error_msg = arguments.get("error_msg", "")
    
    # 사용자 정보 생성
    user_info = UserInfo(
        name=user_name,
        phone=phone,
        birthday=birthday,
        cert_type=cert_type,
    )
    
    # 기본 에러 메시지 설정
    if not error_msg:
        if cert_type == "kakao":
            error_msg = "카카오톡 간편인증 요청에 실패했습니다. 사용자 정보를 확인해주세요."
        else:
            error_msg = "네이버 간편인증 요청에 실패했습니다. 사용자 정보를 확인해주세요."
    
    # cert_request 요청 데이터 생성
    cert_request_data = build_cert_request_data(user_info=user_info)
    
    # cert_request 실패 응답 데이터 생성
    cert_request_response = build_cert_request_response(
        success=False,
        error_type="간편인증오류",
        error_msg=error_msg,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"간편인증실패_{cert_type}_{user_name}",
        description=f"카카오톡 간편인증 요청 실패 시나리오: {user_name}",
        user_info=user_info,
        cert_request_config=ActionConfig(
            success=False,
            error_type="간편인증오류",
            error_msg=error_msg,
            request_data=cert_request_data,
            response_data=cert_request_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


async def handle_scenario_build_cert_response_fail(arguments: dict[str, Any]) -> list[TextContent]:
    """간편인증 완료 확인(cert_response) 실패 시나리오 생성"""
    user_name = arguments.get("user_name", "테스트사용자")
    phone = arguments.get("phone", "01012345678")
    birthday = arguments.get("birthday", "19900101")
    cert_type = arguments.get("cert_type", "kakao")
    error_type_str = arguments.get("error_type", "간편인증미완료")
    error_msg = arguments.get("error_msg", "")
    
    # 사용자 정보 생성
    user_info = UserInfo(
        name=user_name,
        phone=phone,
        birthday=birthday,
        cert_type=cert_type,
    )
    
    # cert_request는 성공 (간편인증 요청은 성공했지만 완료 확인에서 실패)
    cert_info = CertInfo(
        cert_type=CertType(cert_type),
        req_tx_id="7cd3...",
        token="eyJh...",
        cx_id="10db...",
    )
    
    # 1. cert_request: 성공
    cert_request_data = build_cert_request_data(user_info=user_info)
    cert_request_response = build_cert_request_response(success=True, cert_info=cert_info)
    
    # 기본 에러 메시지 설정
    if not error_msg:
        if error_type_str == "간편인증토큰만료":
            error_msg = ERROR_MESSAGES.get(ErrorType.AUTH_EXPIRED, "간편인증 토큰이 만료되었습니다.")
        elif error_type_str == "간편인증미완료":
            error_msg = ERROR_MESSAGES.get(ErrorType.AUTH_NOT_COMPLETE, "간편인증이 완료되지 않았습니다.")
        else:
            if cert_type == "kakao":
                error_msg = "카카오톡 간편인증 완료 확인에 실패했습니다."
            else:
                error_msg = "네이버 간편인증 완료 확인에 실패했습니다."
    
    # 2. cert_response: 실패
    cert_response_data = build_cert_response_data(user_info=user_info, cert_info=cert_info)
    cert_response_response = build_cert_response_response(
        success=False,
        error_type=error_type_str,
        error_msg=error_msg,
    )
    
    scenario = ScenarioConfig(
        scenario_name=f"간편인증완료실패_{cert_type}_{user_name}",
        description=f"간편인증 완료 확인 실패 시나리오: {user_name} ({error_type_str})",
        user_info=user_info,
        cert_info=cert_info,
        cert_request_config=ActionConfig(
            success=True,
            request_data=cert_request_data,
            response_data=cert_request_response,
        ),
        cert_response_config=ActionConfig(
            success=False,
            error_type=error_type_str,
            error_msg=error_msg,
            request_data=cert_response_data,
            response_data=cert_response_response,
        ),
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2)
    )]


# ============================================================================
# MCP Resources
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="scenario://templates",
            name="Templates",
            description="사용 가능한 시나리오 템플릿 목록",
            mimeType="application/json",
        ),
        Resource(
            uri="scenario://error-types",
            name="Error Types",
            description="지원하는 에러 타입 목록",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri == "scenario://templates":
        templates = load_templates()
        result = []
        for template_id, template_data in templates.items():
            refund_result = template_data.get("refund_result", {})
            result.append({
                "template_id": template_id,
                "description": template_data.get("description", ""),
                "total_refund": refund_result.get("total_refund", 0),
                "biz_type": template_data.get("biz_type", "unknown"),
            })
        return json.dumps({"templates": result}, ensure_ascii=False, indent=2)
    
    elif uri == "scenario://error-types":
        error_types = []
        for error_type in ErrorType:
            default_action = ERROR_DEFAULT_ACTION.get(error_type, ActionType.LOAD)
            error_types.append({
                "type": error_type.value,
                "message": get_error_message(error_type),
                "default_action": default_action.value,
            })
        return json.dumps({"error_types": error_types}, ensure_ascii=False, indent=2)
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


# ============================================================================
# Main
# ============================================================================

async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
