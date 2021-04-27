# DO NOT modify this file by hand, changes will be overwritten
import sys
from dataclasses import dataclass
from inspect import getmembers, isclass
from typing import (
    AbstractSet,
    Any,
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from cloudformation_cli_python_lib.interface import (
    BaseModel,
    BaseResourceHandlerRequest,
)
from cloudformation_cli_python_lib.recast import recast_object
from cloudformation_cli_python_lib.utils import deserialize_list

T = TypeVar("T")


def set_or_none(value: Optional[Sequence[T]]) -> Optional[AbstractSet[T]]:
    if value:
        return set(value)
    return None


@dataclass
class ResourceHandlerRequest(BaseResourceHandlerRequest):
    # pylint: disable=invalid-name
    desiredResourceState: Optional["ResourceModel"]
    previousResourceState: Optional["ResourceModel"]


@dataclass
class ResourceModel(BaseModel):
    EnvironmentId: Optional[str]
    EnvironmentName: Optional[str]
    InstanceType: Optional[str]
    SubnetId: Optional[str]
    InstanceId: Optional[str]
    OwnerArn: Optional[str]
    OperatingSystem: Optional[str]
    EbsVolumeSize: Optional[int]
    BootstrapCommands: Optional[Sequence[str]]
    InstancePolicyArn: Optional[str]
    Tags: Optional[AbstractSet["_Tag"]]

    @classmethod
    def _deserialize(
        cls: Type["_ResourceModel"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_ResourceModel"]:
        if not json_data:
            return None
        dataclasses = {n: o for n, o in getmembers(sys.modules[__name__]) if isclass(o)}
        recast_object(cls, json_data, dataclasses)
        return cls(
            EnvironmentId=json_data.get("EnvironmentId"),
            EnvironmentName=json_data.get("EnvironmentName"),
            InstanceType=json_data.get("InstanceType"),
            SubnetId=json_data.get("SubnetId"),
            InstanceId=json_data.get("InstanceId"),
            OwnerArn=json_data.get("OwnerArn"),
            OperatingSystem=json_data.get("OperatingSystem"),
            EbsVolumeSize=json_data.get("EbsVolumeSize"),
            BootstrapCommands=json_data.get("BootstrapCommands"),
            InstancePolicyArn=json_data.get("InstancePolicyArn"),
            Tags=set_or_none(json_data.get("Tags")),
        )


# work around possible type aliasing issues when variable has same name as a model
_ResourceModel = ResourceModel


@dataclass
class Tag(BaseModel):
    Key: Optional[str]
    Value: Optional[str]

    @classmethod
    def _deserialize(
        cls: Type["_Tag"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_Tag"]:
        if not json_data:
            return None
        return cls(
            Key=json_data.get("Key"),
            Value=json_data.get("Value"),
        )


# work around possible type aliasing issues when variable has same name as a model
_Tag = Tag


