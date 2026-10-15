"""Bounded declarative form language. Never evaluate user expressions or HTML."""
import math
import re
from datetime import date
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Option(Input):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    label: str = Field(min_length=1, max_length=200)


class Condition(Input):
    question_id: str = Field(max_length=64)
    op: Literal['equals', 'not_equals', 'contains', 'answered']
    value: JsonValue = None


class Visibility(Input):
    all: list[Condition] = Field(default_factory=list, max_length=100)
    any: list[Condition] = Field(default_factory=list, max_length=100)


class Question(Input):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    kind: Literal['short_text', 'long_text', 'number', 'date', 'boolean', 'single_choice',
                  'multiple_choice', 'scale', 'rating', 'acknowledgement']
    label: str = Field(min_length=1, max_length=500)
    required: bool = False
    options: list[Option] = Field(default_factory=list, max_length=100)
    minimum: float = Field(default=1, allow_inf_nan=False)
    maximum: float = Field(default=5, allow_inf_nan=False)
    max_length: int = Field(default=10000, ge=1, le=10000)
    visibility: Visibility | None = None

    @model_validator(mode='after')
    def valid(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError('Invalid range')
        if len({o.id for o in self.options}) != len(self.options):
            raise ValueError('Duplicate options')
        if ('choice' in self.kind) != bool(self.options):
            raise ValueError('Options apply only to choices and cannot be empty')
        return self


class FormSchema(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=10000)
    kind: Literal['questionnaire', 'survey'] = 'questionnaire'
    questions: list[Question] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def references(self) -> Self:
        previous: set[str] = set()
        for q in self.questions:
            if q.id in previous:
                raise ValueError('Duplicate question')
            if q.visibility:
                for c in q.visibility.all + q.visibility.any:
                    if c.question_id not in previous:
                        raise ValueError('Conditions require previous questions')
            previous.add(q.id)
        return self


def visible(q: Question, answers: dict[str, JsonValue]) -> bool:
    def matches(c: Condition) -> bool:
        value = answers.get(c.question_id)
        if c.op == 'answered':
            return value is not None and value != '' and value != []
        if c.op == 'equals':
            return type(value) is type(c.value) and value == c.value
        if c.op == 'not_equals':
            return type(value) is not type(c.value) or value != c.value
        return isinstance(value, (list, str)) and c.value in value if isinstance(
            c.value, str
        ) else isinstance(value, list) and c.value in value
    v = q.visibility
    return v is None or (all(matches(c) for c in v.all) and
                         (not v.any or any(matches(c) for c in v.any)))


def validate_answers(
    schema: FormSchema, answers: dict[str, JsonValue], *, final: bool
) -> dict[str, JsonValue]:
    if set(answers) - {q.id for q in schema.questions}:
        raise ValueError('Unknown question')
    clean: dict[str, JsonValue] = {}
    for q in schema.questions:
        if not visible(q, clean):
            continue
        v = answers.get(q.id)
        if v is None or v == '' or v == []:
            if final and q.required:
                raise ValueError('Required question')
            continue
        valid = False
        if q.kind in ('short_text', 'long_text'):
            valid = isinstance(v, str) and len(v) <= min(
                q.max_length, 1000 if q.kind == 'short_text' else 10000
            )
        elif q.kind == 'date':
            try:
                valid = isinstance(v, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v))
                if valid:
                    date.fromisoformat(str(v))
            except ValueError:
                valid = False
        elif q.kind in ('boolean', 'acknowledgement'):
            valid = type(v) is bool and (q.kind != 'acknowledgement' or not final or
                                        not q.required or v is True)
        elif q.kind in ('number', 'scale', 'rating'):
            valid = type(v) in (int, float) and math.isfinite(float(v))  # type: ignore[arg-type]
            if valid and q.kind != 'number':
                valid = float(v).is_integer() and q.minimum <= float(v) <= q.maximum  # type: ignore[arg-type]
        elif q.kind == 'single_choice':
            valid = isinstance(v, str) and v in {o.id for o in q.options}
        elif q.kind == 'multiple_choice':
            valid = (isinstance(v, list) and all(isinstance(x, str) for x in v) and
                     len(v) == len(set(str(x) for x in v)) and
                     set(str(x) for x in v) <= {o.id for o in q.options})
        if not valid:
            raise ValueError('Invalid answer')
        clean[q.id] = v
    return clean


class FormEdit(Input):
    expected_version: int = Field(ge=1)
    schema_body: FormSchema


class InvitationCreate(Input):
    recipient_user_id: UUID | None = None
    reader_ids: list[UUID] = Field(max_length=100)
    ttl_days: int = Field(default=7, ge=1, le=7)
    retention_days: int = Field(default=30, ge=1, le=365)
    deliver: bool = False

    @model_validator(mode='after')
    def unique_readers(self) -> Self:
        if len(set(self.reader_ids)) != len(self.reader_ids):
            raise ValueError('Duplicate readers')
        return self


class Answers(Input):
    answers: dict[str, JsonValue]


class Submit(Answers):
    idempotency_key: UUID
    acknowledged: Literal[True]


class Exchange(Input):
    public_id: UUID
    token: str = Field(min_length=40, max_length=100)
