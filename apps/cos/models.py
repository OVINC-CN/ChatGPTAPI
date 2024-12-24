from pydantic import BaseModel as BaseDataModel


class TextAuditResponseJobsDetail(BaseDataModel):
    JobId: str
    Label: str
    Result: int
    Score: int


class TextAuditResponse(BaseDataModel):
    RequestId: str
    JobsDetail: TextAuditResponseJobsDetail


class ImageAuditResponse(BaseDataModel):
    JobId: str
    Label: str
    Result: int
    Score: int
