"""Tests for MCP server."""

import json
import pytest
from unittest.mock import patch, MagicMock

# Set mock path before importing server
import os
os.environ["MOCK_ITR_LOADER_PATH"] = "/tmp/mock-itrLoader"

from mock_itr_scenario_mcp.models.enums import BizType, ErrorType, ERROR_MESSAGES
from mock_itr_scenario_mcp.models.scenario import (
    ScenarioConfig,
    UserInfo,
    RefundResult,
    ActionConfig,
)


class TestModels:
    """Test Pydantic models."""
    
    def test_scenario_config_default(self):
        """Test default ScenarioConfig creation."""
        scenario = ScenarioConfig()
        
        assert scenario.user_info.name == "테스트사용자"
        assert scenario.biz_type == BizType.INDIVIDUAL_BIZ
        assert scenario.refund_result.total_refund == 0
    
    def test_scenario_config_custom(self):
        """Test custom ScenarioConfig creation."""
        scenario = ScenarioConfig(
            scenario_name="테스트 시나리오",
            user_info=UserInfo(name="홍길동"),
            biz_type=BizType.NON_BIZ,
            refund_result=RefundResult(total_refund=1000000),
        )
        
        assert scenario.scenario_name == "테스트 시나리오"
        assert scenario.user_info.name == "홍길동"
        assert scenario.biz_type == BizType.NON_BIZ
        assert scenario.refund_result.total_refund == 1000000
    
    def test_scenario_to_dict(self):
        """Test ScenarioConfig.to_dict()."""
        scenario = ScenarioConfig(
            scenario_name="딕셔너리 테스트",
            refund_result=RefundResult(total_refund=500000),
        )
        
        data = scenario.to_dict()
        
        assert data["scenario_name"] == "딕셔너리 테스트"
        assert data["refund_result"]["total_refund"] == 500000
    
    def test_scenario_from_dict(self):
        """Test ScenarioConfig.from_dict()."""
        data = {
            "scenario_name": "From Dict 테스트",
            "user_info": {"name": "김철수"},
            "refund_result": {"total_refund": 750000},
        }
        
        scenario = ScenarioConfig.from_dict(data)
        
        assert scenario.scenario_name == "From Dict 테스트"
        assert scenario.user_info.name == "김철수"
        assert scenario.refund_result.total_refund == 750000


class TestEnums:
    """Test enum definitions."""
    
    def test_biz_type_values(self):
        """Test BizType enum values."""
        assert BizType.INDIVIDUAL_BIZ.value == "individual_biz"
        assert BizType.NON_BIZ.value == "non_biz"
        assert BizType.CORP.value == "corp"
    
    def test_error_type_values(self):
        """Test ErrorType enum values."""
        assert ErrorType.NO_TAX_RETURN.value == "종소세신고내역없음"
        assert ErrorType.NO_BIZ.value == "사업자없음오류"
    
    def test_error_messages(self):
        """Test error messages mapping."""
        assert ERROR_MESSAGES[ErrorType.NO_TAX_RETURN] == "종합소득세 신고 내역이 없습니다."
        assert ERROR_MESSAGES[ErrorType.NO_BIZ] == "사업자 등록 정보가 없습니다."


class TestScenarioBuilder:
    """Test scenario building functions."""
    
    def test_build_normal_scenario(self):
        """Test building a normal refund scenario."""
        scenario = ScenarioConfig(
            scenario_name="정상환급_테스트",
            user_info=UserInfo(name="테스트"),
            biz_type=BizType.INDIVIDUAL_BIZ,
            refund_result=RefundResult(
                total_refund=3000000,
                창중감_환급액=1000000,
                고용증대_환급액=1500000,
                사회보험료_환급액=500000,
            ),
        )
        
        assert scenario.refund_result.total_refund == 3000000
        assert scenario.load_config.success == True
    
    def test_build_error_scenario(self):
        """Test building an error scenario."""
        scenario = ScenarioConfig(
            scenario_name="에러_종소세신고내역없음",
            user_info=UserInfo(name="테스트"),
            load_config=ActionConfig(
                success=False,
                error_type=ErrorType.NO_TAX_RETURN.value,
                error_msg=ERROR_MESSAGES[ErrorType.NO_TAX_RETURN],
            ),
        )
        
        assert scenario.load_config.success == False
        assert scenario.load_config.error_type == "종소세신고내역없음"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
