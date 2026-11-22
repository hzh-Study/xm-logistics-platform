"""认证审核结论字面量换算：库内兼容旧值，对外统一 GLOSSARY 取值。

数据库 CHECK 无法用追加式迁移放宽，故 carrier_certifications.decision 仍存
'通过' / '驳回'；此模块是唯一换算点，API 入参与出参一律使用
'审核通过' / '审核不通过'。
"""

_API_TO_DB = {"审核通过": "通过", "审核不通过": "驳回"}
_DB_TO_API = {"通过": "审核通过", "驳回": "审核不通过", "": ""}


def to_db(decision: str) -> str:
    """把对外审核结论换算为库内兼容字面量。"""
    return _API_TO_DB[decision]


def to_api(decision: str) -> str:
    """把库内字面量换算为对外审核结论；未知值原样返回。"""
    return _DB_TO_API.get(decision, decision)
