"""Scenario configuration models."""

from typing import Any
from pydantic import BaseModel, Field

from .enums import BizType, CertType


class UserInfo(BaseModel):
    """사용자 정보"""
    name: str = Field(default="테스트사용자", description="사용자 이름")
    phone: str = Field(default="01012345678", description="전화번호")
    birthday: str = Field(default="19900101", description="생년월일 (YYYYMMDD)")


class TaxpayerInfo(BaseModel):
    """납세자 정보"""
    tin: str = Field(default="123456789012345678", description="납세자관리번호 (18자리)")
    tax_office_code: str = Field(default="123", description="관할세무서코드")
    tax_office_name: str = Field(default="강남세무서", description="관할세무서명")


class CertInfo(BaseModel):
    """인증 정보"""
    cert_type: CertType = Field(default=CertType.KAKAO, description="간편인증 유형")
    tx_id: str = Field(default="", description="간편인증 트랜잭션 ID")


class ActionConfig(BaseModel):
    """액션별 설정"""
    success: bool = Field(default=True, description="성공 여부")
    delay_seconds: float = Field(default=0.0, description="응답 지연 시간 (초)")
    error_type: str | None = Field(default=None, description="에러 타입")
    error_msg: str | None = Field(default=None, description="에러 메시지")
    extra_data: dict[str, Any] | None = Field(default=None, description="추가 데이터")


class ProgressStep(BaseModel):
    """진행률 단계"""
    step_name: str = Field(description="단계 이름")
    progress: str = Field(description="진행률 (예: '20%')")
    delay_seconds: float = Field(default=0.5, description="지연 시간")


class ProgressConfig(BaseModel):
    """진행률 설정"""
    enabled: bool = Field(default=False, description="진행률 전송 활성화")
    queue_name: str = Field(default="refund-search.fifo", description="SQS 큐 이름")
    steps: list[ProgressStep] = Field(default_factory=list, description="진행률 단계")


class RefundItem(BaseModel):
    """환급 항목"""
    name: str = Field(description="항목명")
    amount: int = Field(default=0, description="금액")


class BizLocation(BaseModel):
    """사업장 정보"""
    biz_no: str = Field(default="", description="사업자번호")
    biz_name: str = Field(default="", description="상호")
    address: str = Field(default="", description="주소")


class RefundResult(BaseModel):
    """환급 결과"""
    total_refund: int = Field(default=0, description="총 환급세액")
    refund_items: list[RefundItem] = Field(default_factory=list, description="환급 항목 목록")
    biz_locations: list[BizLocation] = Field(default_factory=list, description="사업장 목록")
    
    # 세부 환급 항목 (레거시 호환)
    창중감_환급액: int = Field(default=0, alias="창중감_환급액")
    고용증대_환급액: int = Field(default=0, alias="고용증대_환급액")
    사회보험료_환급액: int = Field(default=0, alias="사회보험료_환급액")
    중소기업특별세액_환급액: int = Field(default=0, alias="중소기업특별세액_환급액")
    
    class Config:
        populate_by_name = True


class VersionInfo(BaseModel):
    """버전 정보"""
    gcexcel_version: str = Field(default="1.0.0", description="GCExcel 버전")
    itrloader_version: str = Field(default="1.0.0", description="ItrLoader 버전")


class ScenarioConfig(BaseModel):
    """시나리오 설정"""
    # 메타데이터
    scenario_id: str = Field(default="", description="시나리오 ID")
    scenario_name: str = Field(default="", description="시나리오 이름")
    description: str = Field(default="", description="시나리오 설명")
    
    # 사용자/납세자 정보
    user_info: UserInfo = Field(default_factory=UserInfo, description="사용자 정보")
    taxpayer_info: TaxpayerInfo = Field(default_factory=TaxpayerInfo, description="납세자 정보")
    cert_info: CertInfo = Field(default_factory=CertInfo, description="인증 정보")
    
    # 사업자 유형 및 환급 결과
    biz_type: BizType = Field(default=BizType.INDIVIDUAL_BIZ, description="사업자 유형")
    refund_result: RefundResult = Field(default_factory=RefundResult, description="환급 결과")
    
    # 버전 정보
    version_info: VersionInfo = Field(default_factory=VersionInfo, description="버전 정보")
    
    # 액션별 설정
    cert_request_config: ActionConfig = Field(default_factory=ActionConfig, description="cert_request 설정")
    cert_response_config: ActionConfig = Field(default_factory=ActionConfig, description="cert_response 설정")
    check_config: ActionConfig = Field(default_factory=ActionConfig, description="check 설정")
    load_config: ActionConfig = Field(default_factory=ActionConfig, description="load 설정")
    calc_config: ActionConfig = Field(default_factory=ActionConfig, description="calc 설정")
    
    # 진행률 설정
    progress_config: ProgressConfig = Field(default_factory=ProgressConfig, description="진행률 설정")
    
    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return self.model_dump(by_alias=True, exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioConfig":
        """딕셔너리에서 생성"""
        return cls.model_validate(data)
