# Mock ITR Scenario MCP Server

Mock ItrLoader 프로젝트의 시나리오를 생성하고 관리하는 MCP(Model Context Protocol) 서버입니다.

## 기능

### MCP Tools

| 도구 | 설명 |
|------|------|
| `template_list` | 사용 가능한 시나리오 템플릿 목록 조회 |
| `template_load` | 특정 템플릿 로드 |
| `scenario_build_normal` | 정상 환급 시나리오 생성 |
| `scenario_build_error` | 에러 시나리오 생성 |
| `scenario_build_progress` | 진행률 전송 시나리오 생성 |
| `scenario_validate` | 시나리오 유효성 검사 |
| `scenario_assign` | 시나리오를 user_ern에 할당 |
| `scenario_unassign` | 시나리오 할당 해제 |

### MCP Resources

| 리소스 | 설명 |
|--------|------|
| `scenario://templates` | 템플릿 목록 |
| `scenario://error-types` | 지원하는 에러 타입 목록 |
| `scenario://schema` | 시나리오 JSON Schema |

## 설치

```bash
# uv 사용
uv pip install -e .

# pip 사용
pip install -e .
```

## 사용법

### Cursor 설정

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mock-itr-scenario": {
      "command": "python",
      "args": ["-m", "mock_itr_scenario_mcp.server"],
      "cwd": "/path/to/mock-itr-scenario-mcp",
      "env": {
        "MOCK_ITR_LOADER_PATH": "/path/to/mock-itrLoader",
        "DYNAMODB_ENDPOINT_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Claude Desktop 설정

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mock-itr-scenario": {
      "command": "python",
      "args": ["-m", "mock_itr_scenario_mcp.server"],
      "cwd": "/path/to/mock-itr-scenario-mcp",
      "env": {
        "MOCK_ITR_LOADER_PATH": "/path/to/mock-itrLoader"
      }
    }
  }
}
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `MOCK_ITR_LOADER_PATH` | mock-itrLoader 프로젝트 경로 | (필수) |
| `DYNAMODB_ENDPOINT_URL` | DynamoDB 엔드포인트 URL | (AWS 기본) |
| `SCENARIO_TABLE_NAME` | DynamoDB 테이블 이름 | `mock-itr-scenarios` |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |

## 사용 예시

### 템플릿 목록 조회

```
사용자: "사용 가능한 템플릿 목록 보여줘"

AI: template_list 도구를 사용합니다.

사용 가능한 템플릿:
- TPL_NORMAL_BIZ_HIGH: 개인사업자 고액환급 (5,500,000원)
- TPL_NORMAL_BIZ_LOW: 개인사업자 저액환급 (150,000원)
- TPL_ERR_NO_TAX_RETURN: 종소세신고내역없음 에러
...
```

### 시나리오 생성

```
사용자: "300만원 환급 시나리오 만들어줘"

AI: scenario_build_normal 도구를 사용합니다.

생성된 시나리오:
- 사용자: 테스트사용자
- 환급액: 3,000,000원
- 사업자 유형: 개인사업자
```

### 에러 시나리오 생성

```
사용자: "종소세 신고내역 없음 에러 시나리오 만들어줘"

AI: scenario_build_error 도구를 사용합니다.

생성된 시나리오:
- 에러 타입: 종소세신고내역없음
- 에러 메시지: "종합소득세 신고 내역이 없습니다."
```

## 개발

```bash
# 개발 의존성 설치
uv pip install -e ".[dev]"

# 테스트 실행
pytest

# 린트
ruff check .

# 타입 체크
mypy src
```

## 참고 자료

- [Mock ItrLoader](https://github.com/danny-zent/mock-itrLoader)
- [MCP Specification](https://modelcontextprotocol.io/specification)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
