import pytest
from pydantic import ValidationError
from vowen.modules.forms.schemas import FormSchema, validate_answers


def schema(questions):
    return FormSchema.model_validate({'title':'Test', 'questions':questions})


@pytest.mark.parametrize('kind,value', [
    ('short_text','hello'),('long_text','long'),('number',2.5),('date','2026-10-15'),
    ('boolean',False),('single_choice','a'),('multiple_choice',['a','b']),
    ('scale',3),('rating',4),('acknowledgement',True),
])
def test_typed_answers(kind,value):
    q={'id':'q','label':'Question','kind':kind,'required':True}
    if 'choice' in kind: q['options']=[{'id':'a','label':'A'},{'id':'b','label':'B'}]
    s=schema([q])
    assert validate_answers(s,{'q':value},final=True)=={'q':value}
    with pytest.raises(ValueError): validate_answers(s,{'q':{}},final=True)


def test_conditions_drop_hidden_values_and_required_applies_only_when_visible():
    s=schema([
        {'id':'first','label':'First','kind':'boolean'},
        {'id':'second','label':'Second','kind':'short_text','required':True,
         'visibility':{'all':[{'question_id':'first','op':'equals','value':True}]}},
    ])
    assert validate_answers(s,{'first':False,'second':'secret'},final=True)=={'first':False}
    with pytest.raises(ValueError): validate_answers(s,{'first':True},final=True)
    assert validate_answers(s,{'first':True},final=False)=={'first':True}


@pytest.mark.parametrize('questions',[
    [{'id':'q','label':'Q','kind':'code'}],
    [{'id':'q','label':'Q','kind':'short_text','unknown':1}],
    [{'id':'q','label':'Q','kind':'single_choice','options':[{'id':'a','label':'A','html':'x'}]}],
    [{'id':'q','label':'Q','kind':'boolean','visibility':{'all':[{'question_id':'q','op':'answered'}]}}],
    [{'id':'q','label':'Q','kind':'boolean'}]*101,
    [{'id':'q','label':'Q','kind':'single_choice','options':[{'id':'a','label':'A'}]*2}],
])
def test_reject_invalid_structures(questions):
    with pytest.raises(ValidationError): schema(questions)


def test_limits_unknown_answers_and_conditions():
    s=schema([{'id':'q','label':'Q','kind':'short_text','max_length':3}])
    for answers in [{'q':'long'},{'other':'x'},{'q':4}]:
        with pytest.raises(ValueError): validate_answers(s,answers,final=True)
