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

from .models.enums import BizType, CertType, ErrorType, ERROR_MESSAGES, ERROR_DEFAULT_ACTION, ActionType
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
    
    # 환급 항목
    창중감 = arguments.get("창중감_환급액", 0)
    고용증대 = arguments.get("고용증대_환급액", 0)
    사회보험료 = arguments.get("사회보험료_환급액", 0)
    
    # 시나리오 생성
    scenario = ScenarioConfig(
        scenario_name=f"정상환급_{user_name}_{total_refund}원",
        description=f"{user_name}의 정상 환급 시나리오 (총 {total_refund:,}원)",
        user_info=UserInfo(name=user_name),
        biz_type=BizType(biz_type_str),
        refund_result=RefundResult(
            total_refund=total_refund,
            창중감_환급액=창중감,
            고용증대_환급액=고용증대,
            사회보험료_환급액=사회보험료,
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
    
    # 기본 메시지 사용
    if not error_msg:
        error_msg = ERROR_MESSAGES.get(error_type, "알 수 없는 오류가 발생했습니다.")
    
    # 기본 액션 사용
    if not action_str:
        action_type = ERROR_DEFAULT_ACTION.get(error_type, ActionType.LOAD)
        action_str = action_type.value
    
    # 시나리오 생성
    scenario = ScenarioConfig(
        scenario_name=f"에러_{error_type.value}_{user_name}",
        description=f"{user_name}의 {error_type.value} 에러 시나리오",
        user_info=UserInfo(name=user_name),
    )
    
    # 해당 액션에 에러 설정
    error_config = ActionConfig(
        success=False,
        error_type=error_type.value,
        error_msg=error_msg,
    )
    
    if action_str == "cert_request":
        scenario.cert_request_config = error_config
    elif action_str == "cert_response":
        scenario.cert_response_config = error_config
    elif action_str == "check":
        scenario.check_config = error_config
    else:  # load
        scenario.load_config = error_config
    
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
    
    scenario = ScenarioConfig(
        scenario_name=f"진행률테스트_{user_name}",
        description=f"{user_name}의 진행률 전송 테스트 시나리오",
        user_info=UserInfo(name=user_name),
        refund_result=RefundResult(total_refund=total_refund),
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
        error_types.append({
            "type": error_type.value,
            "message": ERROR_MESSAGES.get(error_type, ""),
            "default_action": default_action.value,
        })
    
    return [TextContent(
        type="text",
        text=json.dumps({"error_types": error_types}, ensure_ascii=False, indent=2)
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
                "message": ERROR_MESSAGES.get(error_type, ""),
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
