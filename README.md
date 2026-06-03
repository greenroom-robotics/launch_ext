# launch_ext - Launch Extensions

Extended functionality for ROS 2 launch system providing additional actions, substitutions, and conditions.

### Supported Distros
- Kilted

## Table of Contents

- [launch\_ext - Launch Extensions](#launch_ext---launch-extensions)
    - [Supported Distros](#supported-distros)
  - [Table of Contents](#table-of-contents)
  - [Actions](#actions)
    - [ExecuteProcessExt](#executeprocessext)
    - [IncludePackageLaunchFile](#includepackagelaunchfile)
    - [LogRotate](#logrotate)
    - [MakeDeviceNode](#makedevicenode)
    - [SetLaunchConfigurationIfNotNone](#setlaunchconfigurationifnotnone)
    - [WriteFile](#writefile)
    - [Git Repository Actions](#git-repository-actions)
      - [LogRepoInfo](#logrepoinfo)
      - [VerifyRepoCommit](#verifyrepocommit)
      - [VerifyRepoClean](#verifyrepoclean)
    - [Middleware Configuration](#middleware-configuration)
      - [ConfigureZenoh](#configurezenoh)
      - [ConfigureFastDDS](#configurefastdds)
  - [Conditions](#conditions)
    - [EnumEqual](#enumequal)
  - [Substitutions](#substitutions)
    - [Templated](#templated)
    - [Unary](#unary)
    - [WriteTempFile](#writetempfile)
    - [YAMLToFile / YamlToJson](#yamltofile--yamltojson)
    - [ResolveHost](#resolvehost)
    - [Xacro](#xacro)

## Actions

### ExecuteProcessExt

Enhanced process execution action with additional features beyond the standard ExecuteProcess.

```python
ExecuteProcessExt(
    cmd=['my_command', '--arg'],
    name='my_process',
    output='both'
)
```

**Features:**
- Extended process management capabilities
- Enhanced output handling
- Additional lifecycle management

### IncludePackageLaunchFile

Include launch files from packages with enhanced functionality.

```python
IncludePackageLaunchFile(
    package='my_package',
    launch_file='my_launch.py'
)
```

**Parameters:**
- `package`: Name of the package containing the launch file
- `launch_file`: Path to the launch file within the package

### LogRotate

Manage log file rotation to prevent disk space issues.

```python
LogRotate(
    log_file='/path/to/logfile.log',
    max_size='100MB',
    backup_count=5
)
```

**Parameters:**
- `log_file`: Path to the log file to rotate
- `max_size`: Maximum size before rotation
- `backup_count`: Number of backup files to keep

### MakeDeviceNode

Create Linux device nodes for USB devices that are not automatically created by the kernel or when udev is not permitted.

```python
MakeDeviceNode(
    "/dev/tty-magnetometer",
    "ttyUSB",
    "Prolific Technology Inc.",
    "USB-Serial Controller D"
)
```

**Parameters:**
- `target_node`: Path where the device node should be created
- `device_type`: Type of device (e.g., "ttyUSB")
- `manufacturer`: USB device manufacturer name
- `product`: USB device product name

Will create a device node at `/dev/tty-magnetometer` if it does not already exist. The device node will be created if the USB device with the vendor name `Prolific Technology Inc.` and product name `USB-Serial Controller D` is connected.

### SetLaunchConfigurationIfNotNone

Conditionally set launch configurations only if the value is not None.

```python
SetLaunchConfigurationIfNotNone(
    name='my_config',
    value=LaunchConfiguration('optional_param')
)
```

**Parameters:**
- `name`: Configuration parameter name
- `value`: Value to set (only if not None)

### WriteFile

Write content to a file during launch execution.

```python
WriteFile(
    file_path='/tmp/config.txt',
    content='configuration data'
)
```

**Parameters:**
- `file_path`: Path where the file should be written
- `content`: Content to write to the file

### Git Repository Actions

#### LogRepoInfo

Log git repository information including branch, commit, and status.

```python
LogRepoInfo("/path/to/repo")
```

**Parameters:**
- `path`: Path to the git repository

#### VerifyRepoCommit

Verify that a repository is at a specific commit hash.

```python
VerifyRepoCommit(
    "/path/to/repo",
    "abc123...",
    pass_on_failure=False
)
```

**Parameters:**
- `path`: Path to the git repository
- `commit`: Expected commit hash
- `pass_on_failure`: Whether to continue on verification failure

#### VerifyRepoClean

Verify that a repository has no uncommitted changes.

```python
VerifyRepoClean(
    "/path/to/repo",
    pass_on_failure=False
)
```

**Parameters:**
- `path`: Path to the git repository
- `pass_on_failure`: Whether to continue on verification failure

### Middleware Configuration

#### ConfigureZenoh

Configure Zenoh middleware for ROS 2 communication.

```python
ConfigureZenoh(
    with_router=True,
    router_config={'port': 7447},
    session_config={'mode': 'peer'}
)
```

**Parameters:**
- `with_router`: Whether to start a Zenoh router
- `router_config`: Router configuration overrides
- `session_config`: Session configuration overrides

#### ConfigureFastDDS

Configure FastDDS middleware settings.

```python
ConfigureFastDDS(
    config_file='/path/to/fastdds.xml'
)
```

## Conditions

### EnumEqual

Check if a substitution value equals a specific enum value.

```python
from enum import Enum

class Mode(Enum):
    DEBUG = "debug"
    RELEASE = "release"

EnumEqual(
    LaunchConfiguration('build_mode'),
    Mode.DEBUG
)
```

**Parameters:**
- `substitute`: Substitution to evaluate
- `check_enum_value`: Enum value to compare against

## Substitutions

### Templated

Template-based string substitution using Python's string.Template.

```python
Templated("Hello ${name}, mode is ${mode}")
```

Uses launch configurations as template variables.

### Unary

Unary operation substitution for mathematical expressions.

```python
Unary('-', LaunchConfiguration('value'))
```

### WriteTempFile

Create a temporary file with specified content and return its path.

```python
WriteTempFile("temporary content")
```

Returns the path to the created temporary file.

### YAMLToFile / YamlToJson

Convert YAML content to JSON format.

```python
YamlToJson(
    FileContent(file_path),
    quote_output=True
)
```

**Parameters:**
- `file_content_substitution`: Source of YAML content
- `quote_output`: Whether to wrap JSON in quotes

### ResolveHost

Resolve hostname to IP address.

```python
ResolveHost("example.com")
```

### Xacro

Process Xacro files for robot descriptions.

```python
Xacro("robot.urdf.xacro")
```