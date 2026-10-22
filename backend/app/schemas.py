"""请求体校验层。定义入参模型(camelCase→snake)，管入参"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# 1、枚举类型别名
Mode = Literal["review", "practice"]
Pool = Literal["fresh", "due", "weak", "all"]
RatingKey = Literal["fast", "back", "long", "gone"]


# 2、命名适配
def _camel(name: str) -> str:
    """family_id <--> familyId"""
    head, *rest = name.split("_")
    return head + "".join(w.title() for w in rest)

class Request(BaseModel):
    """前端 JSON 用 camelCase,Python 字段用 snake_case。"""
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True,
                               extra="forbid", str_strip_whitespace=True)


# 3、各路由的入参模型
class QueueRequest(Request):   #复习队列
    mode: Mode = "practice"
    family_id: Optional[int] = None
    pool: Pool = "all"

class RatingResult(Request):   #单个词评分
    word: str = Field(min_length=1, max_length=64)
    rating: RatingKey

class CommitRequest(Request):   #疲劳提交评分
    results: list[RatingResult] = Field(min_length=1, max_length=60)
    family_id: Optional[int] = None


class SettingsRequest(Request):   #设置页保存
    """None 表示这一项不改；空字符串表示清掉。密钥只写进 backend/.env，不回传前端。"""
    base_url: Optional[str] = Field(default=None, max_length=200)
    model: Optional[str] = Field(default=None, max_length=80)
    api_key: Optional[str] = Field(default=None, max_length=300)
    image_provider: Optional[Literal["none", "dashscope"]] = None
    image_model: Optional[str] = Field(default=None, max_length=80)
    verify: bool = False

    def as_env(self) -> dict[str, Optional[str]]:
        return {"DEEPSEEK_BASE_URL": self.base_url, "DEEPSEEK_MODEL": self.model,
                "DEEPSEEK_API_KEY": self.api_key,
                "WORDMEMO_IMAGE_PROVIDER": self.image_provider,
                "WORDMEMO_IMAGE_MODEL": self.image_model}

class GroupRequest(Request):   #文本归类词根
    text: str = Field(min_length=2, max_length=8000)
    max_families: int = Field(default=6, ge=1, le=12)

class BatchGroup(Request):   # 分组结果里的一族，回传给后端去生成
    """words 为空表示用户只给了一个词根，让模型自己挑常见词。"""
    root: str = Field(min_length=2, max_length=24)
    root_meaning: str = Field(default="", max_length=20)
    kind: Literal["root", "theme"] = "root"
    words: list[str] = Field(default_factory=list, max_length=12)

class BatchRequest(Request):   # 批量归类
    groups: list[BatchGroup] = Field(min_length=1, max_length=8)

class SaveRequest(Request):   # 预览完挑中的族，下标对着暂存结果的顺序
    picks: list[int] = Field(default_factory=list, max_length=8)
