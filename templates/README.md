# Templates Directory

이 디렉토리는 시나리오 템플릿 파일들을 저장합니다.

## 파일 형식

- 파일명: `TPL_*.json` 형식 (예: `TPL_NORMAL_BIZ_HIGH.json`)
- 형식: JSON 파일로 시나리오 설정을 포함

## 템플릿 예시

템플릿 파일은 `ScenarioConfig` 모델 구조를 따릅니다:

```json
{
  "scenario_name": "템플릿 이름",
  "description": "템플릿 설명",
  "biz_type": "individual_biz",
  "refund_result": {
    "total_refund": 1000000
  },
  ...
}
```

## 사용 방법

템플릿은 `template_list` 및 `template_load` 도구를 통해 조회하고, `scenario_assign`에서 `template_id`로 사용할 수 있습니다.
