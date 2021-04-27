from .context import resource_statemachine
from .context import models

def inc(x):
    handler = resource_statemachine.state_machine._handlers[resource_statemachine.Step.VALIDATE_IAM]
    response = handler(session=None, request=None, callback_context=None)
    action: resource_statemachine.Step = resource_statemachine.Step["VALIDATE_IAM"]
    print(action)
    print(type(action))
    return x + 1


def test_answer():
    assert inc(3) == 4