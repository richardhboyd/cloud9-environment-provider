from functools import singledispatch
from enum import Enum, auto
from typing import Any, Callable, List, MutableMapping, Optional

from .models import ResourceHandlerRequest, ResourceModel

from cloudformation_cli_python_lib import (
    OperationStatus,
    ProgressEvent,
    SessionProxy,
)

import logging
LOG = logging.getLogger(__name__)

HandlerSignature = Callable[[Any], Any]

class _AutoName(Enum):
    @staticmethod
    def _generate_next_value_(
        name: str, _start: int, _count: int, _last_values: List[str]
    ) -> str:
        return name


class Step(str, _AutoName):
    VALIDATE_IAM = auto()
    RESIZE_EBS = auto()
    RUN_SSM = auto()
    CLEAN_UP = auto()

class StateMachine:
    def __init__(self) -> None:
        self._handlers: MutableMapping[Step, HandlerSignature] = {}

    def handler(self, action: Step) -> Callable[[HandlerSignature], HandlerSignature]:
        def _add_handler(f: HandlerSignature) -> HandlerSignature:
            self._handlers[action] = f
            return f

        return _add_handler
    @staticmethod
    def _parse_request(context) -> Step:
        if "STATUS" in context:
            return Step[context["STATUS"]]
        else:
            return Step.VALIDATE_IAM
        

state_machine = StateMachine()

@singledispatch
def handle(obj):
    pass
def os_to_ssm_path(operating_system: str) -> str:
    mapping = {
        "AmazonLinux": "amazonlinux-1-x86_64",
        "AmazonLinux2": "amazonlinux-2-x86_64",
        "Ubuntu": "ubuntu-18.04-x86_64"
    }
    return mapping[operating_system]
    
@state_machine.handler(Step.VALIDATE_IAM)
def handle_validate_iam(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
        callbackContext=callback_context
    )
    
    iam_client = session.client('iam')
    iam = session.resource('iam')
    role = iam.Role('AWSCloud9SSMAccessRole')
    try:
        role.role_id
    except iam.meta.client.exceptions.NoSuchEntityException as _:
        LOG.info("Creating Role")
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
    if model.InstancePolicyArn:
        iam_client.attach_role_policy(RoleName='AWSCloud9SSMAccessRole', PolicyArn=model.InstancePolicyArn)
    
    c9_client = session.client('cloud9')
    arguments = {
        'name': model.EnvironmentName,
        'instanceType': model.InstanceType,
        'imageId': os_to_ssm_path(model.OperatingSystem),
        'automaticStopTimeMinutes': 60,
        'ownerArn': model.OwnerArn,
        'connectionType': 'CONNECT_SSM',
    }
    if model.SubnetId:
        arguments['subnetId']=model.SubnetId
    LOG.info("Creating Cloud9 Environment")
    create_environment_response = c9_client.create_environment_ec2(**arguments)
    LOG.info(f"Created Cloud9 Environment: {create_environment_response['environmentId']}")
    callback_context["STATUS"] = Step.RESIZE_EBS
    progress.callbackContext = callback_context
    progress.resourceModel.EnvironmentId = create_environment_response['environmentId']
    progress.message = f"Created Environment {create_environment_response['environmentId']}"
    progress.callbackDelaySeconds = 180
    progress.status = OperationStatus.IN_PROGRESS

    return progress

@state_machine.handler(Step.RESIZE_EBS)
def handle_resize_ebs(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    LOG.info("Resizing EBS Volume, or not, who am I to judge?")
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
        callbackContext=callback_context
    )
    if model.EbsVolumeSize:
        LOG.info("Okay, for real, we're resizing the EBS Volume")
        ec2_client = session.client('ec2')
        response = ec2_client.describe_instances(Filters=[{'Name': 'tag:aws:cloud9:environment', 'Values': [model.EnvironmentId]}])
        instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
        instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
        progress.resourceModel.InstanceId = instance_id

        volume_id = response['Reservations'][0]['Instances'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        if instance_state == "running":
            response = ec2_client.modify_volume(VolumeId=volume_id, Size=int(progress.resourceModel.EbsVolumeSize))
            LOG.info(f"resized volume ({volume_id}) to {progress.resourceModel.EbsVolumeSize}")
            progress.callbackContext["STATUS"] = Step.RUN_SSM
            progress.message = f"resized volume ({volume_id}) to {progress.resourceModel.EbsVolumeSize}"
            return progress
        if instance_state in ['pending', 'stopping', 'shutting-down']:
            LOG.info("Instance isn't running or stopped, let's check back in a few minutes")
            progress.callbackDelaySeconds = 180
            return progress
        if instance_state == 'stopped':
            LOG.info("restarting instance")
            response = ec2_client.start_instances(InstanceIds=[instance_id])
            progress.callbackDelaySeconds = 180
            return progress
    else:
        print("Skipping EBS Volume resize because the field was not provided")
        progress.callbackContext["STATUS"] = Step.RUN_SSM
        return progress

@state_machine.handler(Step.RUN_SSM)
def handle_run_ssm(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
        callbackContext=callback_context
    )
    if model.BootstrapCommands:
        LOG.info("Sending Bootstrap Command")
        ssm_client = session.client('ssm')
        send_command_response = ssm_client.send_command(
            InstanceIds=[model.InstanceId],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': model.BootstrapCommands}
        )
        progress.callbackContext['CommandId'] = send_command_response['Command']['CommandId']
        LOG.info(f"Sent Command: {progress.callbackContext['CommandId']}")
        progress.message = f"Sent Command: {progress.callbackContext['CommandId']}"
        progress.callbackDelaySeconds = 180
        progress.callbackContext["STATUS"] = Step.CLEAN_UP
        return progress
    else:
        LOG.info("Skipping Bootstrap because the field was not provided")
        progress.callbackContext['CommandId'] = "000000000000"
        progress.callbackContext["STATUS"] = Step.CLEAN_UP
        return progress

@state_machine.handler(Step.CLEAN_UP)
def handle_clean_up(
    session: Optional[SessionProxy],
    request: ResourceHandlerRequest,
    callback_context: MutableMapping[str, Any],
) -> ProgressEvent:
    LOG.info("Waiting for command to finish")
    model = request.desiredResourceState
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS,
        resourceModel=model,
        callbackContext=callback_context
    )
    ssm_client = session.client('ssm')
    response = ssm_client.get_command_invocation(CommandId=callback_context['CommandId'], InstanceId=model.InstanceId)
    if response['Status'] in ['Pending', 'InProgress', 'Delayed']:
        LOG.info("Command is still running")
        progress.callbackDelaySeconds = 120
    elif response['Status'] in ['Cancelled', 'TimedOut', 'Failed', 'Cancelling']:
        LOG.info("Command failed to complete successfully")
        progress.message = "Command failed to complete successfully"
        progress.status = OperationStatus.FAILED
    else:
        progress.status = OperationStatus.SUCCESS
        progress.message = f"Yay! It's done!!"
    return progress