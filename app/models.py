from pydantic import BaseModel,Field,ConfigDict
class ScanRequest(BaseModel):
 relative_path:str=Field(default=".",max_length=500)
class AnalyzeRequest(BaseModel):
 relative_path:str=Field(min_length=1,max_length=500)
class FileRecord(BaseModel):
 relative_path:str
 name:str
 extension:str
 size_bytes:int
 modified_at:str
 detected_type:str
 readable:bool
 note:str|None=None
class AIRecommendation(BaseModel):
 model_config=ConfigDict(extra="ignore")
 document_type:str=Field(default="Unknown",max_length=80)
 suggested_category:str=Field(default="Review",max_length=80)
 suggested_filename:str=Field(default="",max_length=180)
 summary:str=Field(default="",max_length=700)
 evidence:list[str]=Field(default_factory=list,max_length=5)
 needs_review:bool=True
 limitations:list[str]=Field(default_factory=list,max_length=5)
