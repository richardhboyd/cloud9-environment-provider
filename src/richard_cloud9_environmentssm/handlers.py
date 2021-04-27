import logging
from typing import Any, MutableMapping, Optional

from cloudformation_cli_python_lib import (
    Action,
    HandlerErrorCode,
    OperationStatus,
    ProgressEvent,
    Resource,
    SessionProxy,
    exceptions,
    identifier_utils,
)

import boto3
import botocore

from .models import ResourceHandlerRequest, ResourceModel
from .resource_statemachine import StateMachine, state_machine

LOG = logging.getLogger(__name__)
TYPE_NAME = "Richard::Cloud9::EnvironmentSSM"

resource = Resource(TYPE_NAME, ResourceModel)
test_entrypoint = resource.test_entrypoint

def create_service_linked_role(session) -> str:
    iam_client = session.client('iam')
    create_role_response = iam_client.create_role(
        Path='/service-role/',
        RoleName='AWSCloud9SSMAccessRole',
        AssumeRolePolicyDocument='{"Version": "2012-10-17","Statement": ["Effect": "Allow", "Principal":{"Service": ["cloud9.amazonaws.com", "ec2.amazonaws.com"]},"Action": ["sts:AssumeRole"]]}'
    )
    create_instance_profile_response = iam_client.create_instance_profile(
        InstanceProfileName='AWSCloud9SSMInstanceProfile',
        Path='/cloud9/'
    )
    waiter = iam_client.get_waiter('role_exists')
    waiter.wait(RoleName=create_role_response['Role']['RoleName'],WaiterConfig={'Delay':1,'MaxAttempts':60})
    
    iam_client.attach_role_policy(
        RoleName=create_role_response['Role']['RoleName'],
        PolicyArn='arn:aws:iam::aws:policy/AWSCloud9SSMInstanceProfile'
    )
    iam_client.attach_role_policy(
        RoleName=create_role_response['Role']['RoleName'],
        PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
    )
    
    waiter = iam_client.get_waiter('instance_profile_exists')
    waiter.wait(InstanceProfileName=create_instance_profile_response['InstanceProfile']['InstanceProfileName'],WaiterConfig={'Delay': 1,'MaxAttempts': 60})
    
    iam_client.add_role_to_instance_profile(
        InstanceProfileName=create_instance_profile_response['InstanceProfile']['InstanceProfileName'],
        RoleName=create_role_response['Role']['RoleName']
    )
    return create_role_response['Role']['RoleName']

def attach_bootstrap_policy(session, policy_arn: str):
    iam_client = boto3.client('iam')
    iam_client.attach_role_policy(RoleName='AWSCloud9SSMAccessRole', PolicyArn=policy_arn)
    return

def cloud9_role_exists(session) -> bool:
    iam = session.resource('iam')
    role = iam.Role('AWSCloud9SSMAccessRole')
    try:
        role.role_id
    except iam.meta.client.exceptions.NoSuchEntityException as _:
        return False
    return True

@resource.handler(Action.CREATE)
def create_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    # Example:
    try:
        step = StateMachine._parse_request(callback_context)
        print(f"Step: {step}")
        handler = state_machine._handlers[step]
        response = handler(session=session, request=request, callback_context=callback_context)

    except TypeError as e:
        # exceptions module lets CloudFormation know the type of failure that occurred
        raise exceptions.InternalFailure(f"was not expecting type {e}")
        # this can also be done by returning a failed progress event
        # return ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"was not expecting type {e}")

    return response


@resource.handler(Action.UPDATE)
def update_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
    )
    # TODO: put code here
    progress.status = OperationStatus.SUCCESS
    return read_handler(session, request, callback_context)


@resource.handler(Action.DELETE)
def delete_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=None,
    )
    cloud9_client = session.client('cloud9')
    try:
        cloud9_client.delete_environment(environmentId=model.EnvironmentId)
        progress.status = OperationStatus.SUCCESS
        return progress
    except cloud9_client.exceptions.NotFoundException as _:
        progress.status = OperationStatus.SUCCESS
        return progress
    except Exception as error:
        progress.message = f"{error}"
        progress.status = OperationStatus.FAILED
        return progress
    


@resource.handler(Action.READ)
def read_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    model = request.desiredResourceState
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModel=model,
    )


@resource.handler(Action.LIST)
def list_handler(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS,
        resourceModels=[],
    )
