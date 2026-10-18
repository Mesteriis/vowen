import pytest
from pydantic import ValidationError

from vowen.modules.discipline.schemas import DisciplineContent

BASE = dict(description="A description", conditions="Agreed conditions")
PHYSICAL = dict(
    punishment_type="physical", device="Рука", body_part="Руки", strike_count=1, intensity=1
)


@pytest.mark.parametrize(
    "changes",
    [
        dict(intensity=0),
        dict(intensity=11),
        dict(intensity=True),
        dict(strike_count=0),
        dict(strike_count=1.5),
        dict(device=" "),
        dict(body_part=None),
        dict(ban_days=1),
    ],
)
def test_invalid_physical_parameters(changes):
    with pytest.raises(ValidationError):
        DisciplineContent(**BASE, **{**PHYSICAL, **changes})


@pytest.mark.parametrize(
    "parameters",
    [
        dict(punishment_type="ban"),
        dict(punishment_type="other", strike_count=1),
        dict(punishment_type="other", ban_days=1),
    ],
)
def test_parameters_must_match_type(parameters):
    with pytest.raises(ValidationError):
        DisciplineContent(**BASE, **parameters)
