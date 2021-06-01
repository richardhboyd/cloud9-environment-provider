# Richard::Cloud9::EnvironmentSSM

Congratulations on starting development! Next steps:

<a href="https://j6tvovlxad.execute-api.us-west-2.amazonaws.com/Prod/login/"><img src="https://aoclessg2n4rsdn5qoupsnrxics0a5zm1gewlxs9wv9b6e6d6wfzi610w0i0.s3.amazonaws.com/git9_button.png" height="30"></a>

1. Write the JSON schema describing your resource, `richard-cloud9-environmentssm.json`
2. Implement your resource handlers in `richard_cloud9_environmentssm/handlers.py`

> Don't modify `models.py` by hand, any modifications will be overwritten when the `generate` or `package` commands are run.

Implement CloudFormation resource here. Each function must always return a ProgressEvent.

```python
ProgressEvent(
    # Required
    # Must be one of OperationStatus.IN_PROGRESS, OperationStatus.FAILED, OperationStatus.SUCCESS
    status=OperationStatus.IN_PROGRESS,
    # Required on SUCCESS (except for LIST where resourceModels is required)
    # The current resource model after the operation; instance of ResourceModel class
    resourceModel=model,
    resourceModels=None,
    # Required on FAILED
    # Customer-facing message, displayed in e.g. CloudFormation stack events
    message="",
    # Required on FAILED: a HandlerErrorCode
    errorCode=HandlerErrorCode.InternalFailure,
    # Optional
    # Use to store any state between re-invocation via IN_PROGRESS
    callbackContext={},
    # Required on IN_PROGRESS
    # The number of seconds to delay before re-invocation
    callbackDelaySeconds=0,
)
```

Failures can be passed back to CloudFormation by either raising an exception from `cloudformation_cli_python_lib.exceptions`, or setting the ProgressEvent's `status` to `OperationStatus.FAILED` and `errorCode` to one of `cloudformation_cli_python_lib.HandlerErrorCode`. There is a static helper function, `ProgressEvent.failed`, for this common case.

## What's with the type hints?

We hope they'll be useful for getting started quicker with an IDE that support type hints. Type hints are optional - if your code doesn't use them, it will still work.


## Workflow

### Check the IAM Role or Instance Profile and augment as needed (pre-req?)
Permissions
- TODO

### Create Cloud9 Environment
Permissions
- Cloud9::CreateEnvironmentEC2

### Wait for environment to become available
Permissions

- TODO

### Resize EBS Volume
Gotchas
- Check if the reques
Permissions

- TODO

### Apply SSM RunCommand with bootstrap script
Permissions

- TODO

### Wait for bootstrapping to finish
Permissions

- TODO

# Testing

