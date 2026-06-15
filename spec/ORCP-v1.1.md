# ORCP — Open Robot Control Protocol

## Specification v1.1

**Version:** 1.1  
**Date:** June 2026  
**License:** MIT  

*A simple, safe, transport-agnostic protocol for robot control.*

*This specification is released under the MIT License. You are free to implement, modify, and distribute implementations of this protocol without restriction.*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [ASCII Message Format](#2-ascii-message-format)
3. [Transport Layer](#3-transport-layer)
4. [Command Reference](#4-command-reference)
5. [Safety System](#5-safety-system)
6. [Push Messages](#6-push-messages)
7. [Standard Configuration Parameters](#7-standard-configuration-parameters)
8. [Kinematic Model](#8-kinematic-model)
9. [Conformance Levels](#9-conformance-levels)
10. [Units](#10-units)
- [Annex A: CAN Binary Encoding](#annex-a-can-binary-encoding-normative)
- [Annex B: Extending ORCP](#annex-b-extending-orcp-informative)
- [Revision History](#revision-history)
- [License](#license)

---

## 1. Introduction

### 1.1 Purpose

The Open Robot Control Protocol (ORCP) defines a standard interface for controlling and monitoring robots. It provides a common language between a high-level controller (a laptop, single-board computer, PLC, or fleet management system) and a low-level device controller (a microcontroller managing actuators, sensors, and safety systems). ORCP v1.1 focuses on mobile platform motion control, with future versions extending to sensor integration, manipulator control, and multi-robot coordination.

ORCP is designed to be simple enough to type in a terminal, structured enough for real-time control, safe enough for deployment in educational and commercial environments, and extensible enough for research and industrial applications.

### 1.2 Scope

ORCP v1.1 covers the following functional areas:

- **Motion control:** Velocity commands for differential-drive and skid-steer mobile platforms, using both unicycle (linear/angular) and direct wheel velocity models.
- **Safety management:** Operating mode presets, enable gates, heartbeat monitoring, emergency stop integration, and configurable fault handling.
- **Telemetry:** Real-time streaming of velocities, duty cycles, battery status, and sensor data.
- **Configuration:** Runtime parameter management with persistent storage for tuning, calibration, and deployment.
- **System information:** Device identification, capability reporting, and diagnostics.

ORCP does not define motor driver hardware, mechanical design, kinematics beyond differential drive, path planning, or SLAM algorithms. It is a device-level protocol, not a middleware or application framework.

Future versions of this specification may define standard commands for sensor integration, manipulator control, and multi-robot coordination. The message format, safety system, and configuration framework defined in this version are designed to support these extensions without modification.

### 1.3 Design Principles

- **Human-readable:** The primary encoding is ASCII text. Commands can be typed and responses read in any serial terminal. No special tools are required to operate an ORCP device.
- **Transport-agnostic:** ORCP defines message semantics independently of the physical transport. Normative encodings are provided for ASCII (over USB CDC, UART, or TCP) and binary (over CAN bus). Other transports may be used provided the message semantics are preserved.
- **Named parameters:** All parameters use `key=value` syntax. Parameters are order-independent and self-documenting. Clients MUST ignore unrecognised parameters in responses.
- **Forward-compatible:** Implementations MAY add new parameters to existing responses and new commands to the protocol without breaking conformant clients, provided existing semantics are preserved.
- **Fail-safe:** Unrecognised commands MUST return an error. The safety system MUST enforce timeouts. The device MUST stop if communication is lost.

### 1.4 Terminology

- **Controller:** The device implementing ORCP — typically a microcontroller board driving actuators and reading sensors. Also called the "device" or "server".
- **Host:** The system sending commands to the controller — a laptop, SBC, PLC, or any software client. Also called the "client".
- **Base:** The mobile robot platform containing the controller, motors, wheels, battery, and safety systems.
- **Transport:** The physical and data-link layer carrying ORCP messages (USB CDC, TCP socket, UART, CAN bus, etc.).

### 1.5 Normative Language

The key words MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. ASCII Message Format

### 2.1 Overview

ORCP uses a line-oriented ASCII message format. Each message is a single line of UTF-8 text terminated by a newline character. The protocol follows a request-response model with support for unsolicited push messages from the controller.

### 2.2 Commands (Host → Controller)

```
COMMAND [param=value ...] <newline>
```

- **COMMAND:** An uppercase ASCII keyword identifying the operation.
- **Parameters:** Zero or more space-separated `key=value` pairs. Keys are lowercase. Values may be integers, floats, or strings depending on the parameter.
- **Empty values:** A parameter with an empty value (e.g. `SET kp=`) MUST be rejected with `ERR code=BAD_ARG`. Silently coercing an empty value to zero is unsafe and has caused real failures in shipping implementations.
- **Terminator:** LF (`0x0A`) or CR+LF (`0x0D 0x0A`). Implementations MUST accept both.
- **Maximum line length:** 256 bytes including terminator.

### 2.3 Success Response (Controller → Host)

```
OK COMMAND [field=value ...] <newline>
```

The response echoes the command keyword and includes zero or more result fields. Clients MUST ignore unrecognised fields to ensure forward compatibility.

Success response lines MAY exceed the 256-byte command limit defined in §2.2 (notably for `GET ALL`-style enumeration responses, which can be ~1 KB on implementations with large configuration surfaces). Hosts SHOULD provide a receive buffer of at least 2 KB and use line-buffered reads to accommodate this case. The 256-byte limit applies only to commands sent host → controller.

### 2.4 Error Response (Controller → Host)

```
ERR code=<ERROR_CODE> msg="<description>" <newline>
```

Returned when a command cannot be executed. The error code is a machine-readable keyword. The message is a human-readable description.

### 2.5 Push Messages (Controller → Host, Unsolicited)

```
! TYPE [field=value ...] <newline>
```

Push messages are sent asynchronously by the controller without a preceding command. They are prefixed with `!` followed by a space and a type keyword. Hosts MUST be prepared to receive push messages at any time, including between sending a command and receiving its response.

### 2.6 Error Codes

| Code | Description |
|------|-------------|
| `BAD_CMD` | Unrecognised command keyword |
| `BAD_ARG` | Missing or malformed parameter |
| `BAD_VAL` | Parameter value out of valid range |
| `TOO_LONG` | Command line exceeded the maximum length (see §2.2) |
| `NOT_ENABLED` | Motion rejected: safety enable gate not set |
| `ESTOP` | Motion rejected: emergency stop active |
| `LOWBATT` | Motion rejected: battery critically low |
| `HEARTBEAT` | Motion rejected: heartbeat timeout |
| `TIMEOUT` | Motion rejected: command timeout |
| `NO_FEEDBACK` | Closed-loop motion rejected: required feedback sensor (e.g. encoder) is unavailable or absent |
| `BUSY` | Command cannot execute in current state |
| `CONFIG_CONFLICT` | Value is individually valid but conflicts with another parameter's current value |
| `FLASH_ERR` | Persistent storage read/write error |

Implementations MAY define additional error codes. Clients SHOULD handle unknown error codes gracefully by displaying the code and message to the user.

---

## 3. Transport Layer

### 3.1 General Requirements

ORCP is transport-agnostic. Any reliable byte-stream or message-based transport may be used. The ASCII encoding (Section 2) is normative for stream-based transports. The CAN binary encoding (Annex A) is normative for CAN bus. Implementations MUST specify which transports they support.

### 3.2 USB CDC (Recommended Default)

The controller presents as a USB CDC ACM device (virtual COM port). No special drivers are required on modern operating systems. The baud rate setting (typically 115200) is required by the USB CDC specification but has no effect on actual throughput, as USB CDC operates at full USB speed.

### 3.3 TCP Socket (WiFi / Ethernet)

The controller listens on a TCP port (default 3333). The host connects as a TCP client. Multiple simultaneous clients SHOULD be supported (RECOMMENDED minimum: 4). Each client maintains an independent session. Push messages (streaming telemetry) SHOULD be sent to all connected clients.

Service discovery via mDNS is RECOMMENDED. The default service type is `_orcp._tcp` and the default hostname is the device's configured name.

### 3.4 UART

For direct microcontroller-to-microcontroller communication. Settings: 115200 baud, 8 data bits, no parity, 1 stop bit (8N1). Hardware flow control is OPTIONAL.

### 3.5 CAN Bus

CAN 2.0B at up to 1 Mbit/s. Messages use the binary encoding defined in Annex A. Each device on the bus is identified by a configurable base ID. Multiple devices MAY share a single CAN bus using different base IDs.

---

## 4. Command Reference

This section defines all ORCP commands. Commands are listed alphabetically. An implementation that supports a given conformance level (Section 9) MUST implement all commands marked as required for that level.

**Syntax convention.** In the syntax examples below, parameters in square brackets are optional. Vendor-extension parameters (which opt into non-standard behaviour, e.g. `[mode=<vendor_mode>]`) appear in the same bracketed form. Standard hosts that do not supply optional or vendor parameters MUST receive the default conformant behaviour. Conformant implementations MUST reject unknown bracketed parameters they do not recognise, rather than silently ignoring them, so a host writing against the spec cannot accidentally invoke vendor-specific behaviour on a different controller. Response examples use the same descriptive placeholders (`<float>`, `<int>`, `<parameter_name>`, etc.) as the input syntax for consistency.

---

### CMD_VEL

**Category:** Motion

Set the robot's linear and angular velocity using the unicycle kinematic model. The controller converts these to individual wheel velocities using its calibrated kinematics (wheel radius, track width). This is the primary motion command for most applications.

**Syntax:**
```
CMD_VEL v=<float> w=<float>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `v` | float | Yes | Linear velocity in m/s. Positive = forward. |
| `w` | float | Yes | Angular velocity in rad/s. Positive = counter-clockwise. |

**Response:**
```
OK CMD_VEL v=<f> w=<f> tl=<f> tr=<f>
```

**Example:**
```
>>> CMD_VEL v=0.200 w=0.500
<<< OK CMD_VEL v=0.200 w=0.500 tl=2.271 tr=5.893
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `v` | float | Linear velocity (m/s) — echo of the accepted target after any clamping the controller applied |
| `w` | float | Angular velocity (rad/s) — echo of the accepted target after any clamping |
| `tl` | float | Target *left* wheel velocity (rad/s) computed from the unicycle kinematic conversion (§8). What the left-side PID will be asked to track. |
| `tr` | float | Target *right* wheel velocity (rad/s), same conversion |

The controller MAY implement acceleration limiting. If present, the actual PID setpoint ramps towards the commanded target. The STOP command MUST bypass any acceleration limiter for instant braking.

---

### DEFAULTS

**Category:** Configuration

Reset all configuration parameters to factory default values. Does not automatically persist — the host MUST send SAVE to make the reset permanent.

**Syntax:**
```
DEFAULTS
```

**Response:**
```
OK DEFAULTS
```

**Example:**
```
>>> DEFAULTS
<<< OK DEFAULTS
```

Implementations MUST define sensible defaults for all parameters.

---

### ENABLE

**Category:** Safety

Set or clear the motor safety enable gate. In restricted operating modes, motion commands are rejected until the enable gate is set. In permissive modes, the gate may be set automatically at power-on.

**Syntax:**
```
ENABLE <ON|OFF>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ON` | keyword | Yes | Enable the motor safety gate. Clears recoverable faults. |
| `OFF` | keyword | Yes | Disable the motor safety gate. Motors stop immediately. |

**Response:**
```
OK ENABLE state=<ON|OFF>
```

**Example:**
```
>>> ENABLE ON
<<< OK ENABLE state=ON
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `state` | `ON`\|`OFF` | Resulting state of the safety enable gate after the command completes |

ENABLE ON MUST be rejected with `ERR code=ESTOP` if the emergency stop is active.

---

### GET

**Category:** Configuration

Read the current value of a configuration parameter. See Section 7 for the standard parameter set.

**Syntax:**
```
GET <parameter_name>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parameter_name` | string | Yes | Name of the parameter to read. |

**Response:**
```
OK GET <parameter_name>=<value>
```

**Example:**
```
>>> GET pid.kp
<<< OK GET pid.kp=0.050
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `<parameter_name>` | varies | The requested parameter's current value. The field name in the response echoes the parameter name (e.g. `pid.kp=0.050`). For `GET ALL`, one such field is returned per parameter in a single line. |

Implementations SHOULD support `GET ALL` to return all parameters.

---

### HB

**Category:** Safety

Send a heartbeat to the safety system. In modes that require heartbeat monitoring, the host MUST send HB commands periodically. If the heartbeat timeout expires, the controller MUST stop the motors and raise a HEARTBEAT fault.

**Syntax:**
```
HB
```

**Response:**
```
OK HB
```

**Example:**
```
>>> HB
<<< OK HB
```

The heartbeat also resets the command timeout timer. A typical heartbeat interval is 100 ms.

---

### INFO

**Category:** System

Return device identification and protocol version.

**Syntax:**
```
INFO
```

**Response:**
```
OK INFO fw=<version> hw=<hardware> proto=ORCP/<version> [vendor=<string>] [model=<string>] [level=<int>]
```

**Example:**
```
>>> INFO
<<< OK INFO fw=1.0.0 hw=STM32F103CB proto=ORCP/1.1 vendor=Acme model=BaseBot level=2
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `fw` | string | Firmware version. Vendor-defined format; semver `major.minor.patch` is RECOMMENDED. |
| `hw` | string | Hardware identifier. Vendor-defined; typically the board model or MCU part number. |
| `proto` | string | Protocol version, prefixed `ORCP/` (e.g. `ORCP/1.1`). MUST be present. |
| `vendor` | string | Optional. Vendor or manufacturer name. |
| `model` | string | Optional. Product model name. |
| `level` | int | Optional. Declared conformance level (`1`, `2`, or `3` per §9). Hosts MAY use this to adapt their behaviour to the controller's capabilities — for example, skipping `GET`/`SET` calls when talking to a Level 1 controller. |

The `proto` field MUST include the ORCP version. All other fields are OPTIONAL.

---

### LOAD

**Category:** Configuration

Load configuration parameters from persistent storage, replacing current in-memory values.

**Syntax:**
```
LOAD
```

**Response:**
```
OK LOAD
```

**Example:**
```
>>> LOAD
<<< OK LOAD
```

If no saved configuration exists, LOAD SHOULD apply factory defaults.

---

### PING

**Category:** System

Test connectivity. The simplest possible command. If you get a response, the link is working.

**Syntax:**
```
PING
```

**Response:**
```
OK PONG
```

**Example:**
```
>>> PING
<<< OK PONG
```

Implementations MUST respond to PING regardless of safety state, faults, or operating mode.

---

### PRESET

**Category:** Safety

Switch the safety system between operating modes. Presets configure the duty limit, command timeout, heartbeat requirement, and enable gate behaviour as a single atomic operation. Motors MUST be stopped when switching presets.

**Syntax:**
```
PRESET <preset_name>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `preset_name` | string | Yes | Name of the safety preset to activate. |

**Response:**
```
OK PRESET name=<preset_name> timeout_ms=<int> enable_required=<0|1> hb_required=<0|1> duty_limit=<float>
```

**Example:**
```
>>> PRESET NORMAL
<<< OK PRESET name=NORMAL timeout_ms=250 enable_required=1 hb_required=1 duty_limit=1.000
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Name of the now-active preset |
| `timeout_ms` | int | Command timeout for this preset (ms). A value of `0` means no command timeout. |
| `enable_required` | `0`\|`1` | Whether `ENABLE ON` must be issued before motion commands are accepted in this preset |
| `hb_required` | `0`\|`1` | Whether heartbeat monitoring is active in this preset |
| `duty_limit` | float | Active duty-cycle limit (0.0–1.0) under this preset |

Implementations MUST define at least two presets: a restricted mode (low power, auto-enabled) and a full mode (full power, requires explicit enable). The standard preset names are `SLOW` and `NORMAL`. Heartbeat monitoring is an independent safety feature (Level 2 and above, §9): a preset MAY require it, and a controller declares this per preset via the `hb_required` field rather than it being implied by the preset being "full". A Level 1 full preset reports `hb_required=0`; a Level 2+ full preset typically reports `hb_required=1`.

---

### SAVE

**Category:** Configuration

Save current configuration parameters to persistent storage. Parameters persist across power cycles.

**Syntax:**
```
SAVE
```

**Response:**
```
OK SAVE
```

**Example:**
```
>>> SAVE
<<< OK SAVE
```

Implementations SHOULD use integrity checking (e.g. CRC32) on stored data. Flash write endurance is limited; hosts SHOULD NOT call SAVE in a loop.

---

### SET

**Category:** Configuration

Change a configuration parameter in memory. The change takes effect immediately but does not persist across power cycles unless followed by SAVE.

**Syntax:**
```
SET <parameter_name>=<value>
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parameter_name` | string | Yes | Name of the parameter to change. |
| `value` | varies | Yes | New value. Type depends on the parameter. |

**Response:**
```
OK SET <parameter_name>=<value>
```

**Example:**
```
>>> SET pid.kp=0.080
<<< OK SET pid.kp=0.080
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `<parameter_name>` | varies | The parameter that was changed, echoed with the value the controller actually stored. If the controller coerced the value (e.g. cast a float to int), this field reflects what is now in memory rather than the raw input. |

Implementations MUST validate the value and return `ERR code=BAD_VAL` if out of range.

---

### STATUS

**Category:** System

Return a complete snapshot of the device state: safety mode, control mode, velocities, duty cycles, battery status, and active faults.

**Syntax:**
```
STATUS
```

**Response:**
```
OK STATUS preset=<preset_name> mode=<mode> en=<0|1> fault=<fault_code> estop=<0|1> tl=<float> tr=<float> vl=<float> vr=<float> dl=<float> dr=<float> lim=<float> vbat=<float> battery=<battery_level>
```

**Example:**
```
>>> STATUS
<<< OK STATUS preset=SLOW mode=IDLE en=1 fault=OK estop=0 tl=0.000 tr=0.000 vl=0.000 vr=0.000 dl=0.000 dr=0.000 lim=0.300 vbat=12.45 battery=HIGH
```

**Standard STATUS response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `preset` | string | Active safety preset name |
| `mode` | string | Control mode: `IDLE`, `VELOCITY`, or `OPEN_LOOP` |
| `en` | 0\|1 | Safety enable gate state |
| `fault` | string | Active fault code or `OK` |
| `estop` | 0\|1 | Emergency stop state (1 = active) |
| `tl`, `tr` | float | Target velocity left/right (rad/s) |
| `vl`, `vr` | float | Measured velocity left/right (rad/s) |
| `dl`, `dr` | float | Duty cycle left/right (−1.0 to +1.0) |
| `lim` | float | Active duty limit (0.0 to 1.0) |
| `vbat` | float | Battery voltage (V) |
| `battery` | string | Battery level (percentage or band label) |

Implementations MAY include additional fields. Clients MUST ignore unrecognised fields.

---

### STOP

**Category:** Motion

Immediately stop all motors using active braking. MUST bypass any acceleration limiter for instant response. MUST be accepted regardless of safety state — STOP never fails.

**Syntax:**
```
STOP [mode=<vendor_mode>]
```

**Response:**
```
OK STOP mode=BRAKE
```

**Example:**
```
>>> STOP
<<< OK STOP mode=BRAKE
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Stop mode applied. `BRAKE` is the only standard value. Vendor extensions MAY return other identifiers (e.g. `COAST` for a free-wheeling stop) — see the vendor-extension paragraph below. |

STOP does not disable the safety enable gate. After STOP, the host can immediately send a new motion command.

STOP MAY accept additional mode parameters as vendor extensions (e.g. `COAST` for a free-wheeling stop), provided they do not redefine or weaken the default `BRAKE` behaviour. Hosts written against the spec MUST be prepared for `STOP` (no argument) to behave as `BRAKE` on any conformant implementation.

---

### STREAM

**Category:** Telemetry

Enable or disable continuous telemetry streaming. When enabled, the controller pushes telemetry at the specified rate.

**Syntax:**
```
STREAM <ON|OFF> [rate]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ON` | keyword | Yes | Enable streaming. |
| `OFF` | keyword | Yes | Disable streaming. |
| `rate` | int (1–50) | No | Stream rate in Hz. Default: 10. |

**Response:**
```
OK STREAM state=<ON|OFF> rate=<int>
```

**Example:**
```
>>> STREAM ON 20
<<< OK STREAM state=ON rate=20
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `state` | `ON`\|`OFF` | Streaming state after the command completes |
| `rate` | int | Configured stream rate in Hz. Reflects the value the controller actually applied, which may differ from the requested rate if it was clamped to the 1–50 Hz range. |

Stream data is sent as push messages with prefix `! STREAM`. The controller SHOULD maintain timing accuracy within ±10% of the requested rate.

**Standard streaming telemetry format:**
```
! STREAM tl=5.000 tr=5.000 vl=4.987 vr=5.012 dl=0.142 dr=0.143 vbat=12.44 battery=HIGH
```

Implementations MAY include additional fields (e.g. current monitoring, IMU data). Clients MUST ignore unrecognised fields.

---

### WHEEL

**Category:** Motion

Set individual wheel side velocities directly in rad/s of the output shaft. This bypasses the unicycle kinematic model and gives direct control over each wheel side's PID controller. For skid-steer and 4WD platforms, "left" and "right" refer to the entire side, not individual wheels.

**Syntax:**
```
WHEEL l=<float> r=<float> [mode=<vendor_mode>]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `l` | float | Yes | Left side velocity in rad/s. Positive = forward. |
| `r` | float | Yes | Right side velocity in rad/s. Positive = forward. |

**Response:**
```
OK WHEEL l=<f> r=<f>
```

**Example:**
```
>>> WHEEL l=5.0 r=-5.0
<<< OK WHEEL l=5.000 r=-5.000
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `l` | float | Left side target velocity (rad/s) — echo of the accepted value after any clamping the controller applied |
| `r` | float | Right side target velocity (rad/s) — echo of the accepted value after any clamping |

Acceleration limiting, if implemented, applies to WHEEL commands the same as CMD_VEL.

The `l` and `r` parameters MUST be interpreted as rad/s of output-shaft velocity. Implementations MAY offer additional control modes (e.g. direct duty cycle, current/torque) as vendor extensions, but these MUST be opt-in via an explicit parameter (for example, `mode=DUTY`). The default semantics — when no mode parameter is supplied — MUST be rad/s closed-loop velocity. This ensures hosts written against the spec without vendor knowledge cannot accidentally invoke an open-loop mode.

If the platform is configured as having no encoders (see Section 7.1, `kin.counts_per_rev=0`), WHEEL commands using rad/s semantics MUST be rejected with `ERR code=NO_FEEDBACK`. Vendor-extension modes (e.g. `mode=DUTY`) that do not rely on rotational feedback MAY still be accepted in that case.

---

## 5. Safety System

ORCP defines a mandatory safety system that MUST be implemented by all conformant controllers. The safety system prevents uncontrolled motion and ensures the robot can be stopped at any time.

### 5.1 Operating Presets

Presets group safety parameters into named configurations that can be switched atomically. Implementations MUST define at least two presets:

| Feature | Restricted (e.g. SLOW) | Full (e.g. NORMAL) |
|---------|------------------------|---------------------|
| Duty limit | Reduced (≤30%) | Full (100%) |
| Command timeout | Lenient (≥1000 ms) | Tight (≤250 ms) |
| Auto-enabled | Yes | No (requires ENABLE ON) |
| Heartbeat required | No | Yes at Level 2+ (see note) |
| Intended use | Manual testing, beginners | Autonomous operation, production |

The controller MUST power on in the restricted preset. This ensures safe default behaviour.

Heartbeat monitoring is a Level 2+ feature (§9), not part of the definition of "full" mode. The dead-man protection that a full preset always provides is the **command timeout** (§5.4), which Level 1 requires. A Level 1 full preset is therefore conformant with `hb_required=0`; the "Yes" above applies once heartbeat monitoring is implemented (Level 2 and above). See §5.5.

### 5.2 Fault Hierarchy

The safety system MUST check for faults on every control tick and report the highest-priority active fault. Faults MUST be checked in the following priority order:

| Priority | Fault | Cause | Recovery |
|----------|-------|-------|----------|
| 1 (highest) | `ESTOP` | Emergency stop hardware signal active | Release, then ENABLE ON |
| 2 | `LOWBATT` | Battery below critical threshold | Recharge, then ENABLE ON |
| 3 | `NOT_ENABLED` | Enable gate not set (full mode) | ENABLE ON |
| 4 | `HEARTBEAT` | Heartbeat timeout (presets with `hb_required=1`; Level 2+) | HB, then ENABLE ON |
| 5 | `ENCODER_STALL` | Motor output applied but no encoder feedback observed | Diagnose wiring / sensor, then ENABLE ON |
| 6 (lowest) | `TIMEOUT` | No motion command within timeout | Send any motion command |

### 5.3 Emergency Stop

ORCP controllers SHOULD support a hardware emergency stop input. When active, the controller MUST immediately stop all motors and reject all motion commands with `ERR code=ESTOP`. The ENABLE ON command MUST also be rejected while the emergency stop is active.

After the emergency stop is released, the fault MUST persist until the host explicitly sends ENABLE ON. Motors MUST NOT restart automatically after e-stop release.

### 5.4 Command Timeout

If no motion command (CMD_VEL, WHEEL) or heartbeat (HB) is received within the configured timeout period, the controller MUST stop the motors. This protects against host software crashes, network disconnections, or interrupted programs.

### 5.5 Heartbeat

Heartbeat monitoring is a Level 2 and above feature (§9); it is independent of the operating preset and is not what makes "full" mode safe — the command timeout (§5.4) provides the dead-man protection at every level. Where a preset declares `hb_required=1` (typically the full preset on a Level 2+ controller), the host MUST periodically send HB commands to prove it is alive and in control. The recommended interval is 100 ms with a default timeout of 500 ms. If the timeout expires, the controller MUST stop the motors and raise a HEARTBEAT fault. A controller that does not implement heartbeat monitoring (e.g. a Level 1 implementation) reports `hb_required=0` for all presets and MUST NOT raise the HEARTBEAT fault.

### 5.6 Acceleration Limiting

Implementations SHOULD include a configurable acceleration limiter that ramps the PID setpoint towards the commanded target at a maximum rate. This prevents wheel spin, reduces mechanical stress, and improves controllability. The STOP command MUST always bypass the acceleration limiter for instant braking.

### 5.7 Feedback Sensor Failures

Closed-loop motion commands (CMD_VEL and rad/s-mode WHEEL) require valid feedback from rotational sensors. An implementation that applies motor output with no corresponding feedback is in an undefined state: the control loop cannot detect runaway, integral terms wind up against the output limiter, and the motors will not stop in response to a zero-velocity command. This is a silent and dangerous failure mode.

Implementations SHOULD detect the case where motor output is being applied but the expected feedback is absent — for example, where duty cycle exceeds a small threshold but encoder counts have not advanced over a sustained window (a typical window is several hundred milliseconds). On detection, the controller MUST stop the motors and raise an `ENCODER_STALL` fault. The fault MUST persist until ENABLE ON is explicitly re-asserted by the host.

The specific thresholds (minimum duty, maximum permitted velocity, debounce window) are implementation-defined and should be tuned to the platform's mechanical envelope so that legitimate stall conditions (e.g. a wheel pressed against a wall) are also caught.

This detection MUST NOT run when the platform is configured as having no encoders (see Section 7.1, `kin.counts_per_rev=0`). In that configuration, closed-loop commands are rejected at the command boundary with `ERR code=NO_FEEDBACK` instead, and there is no closed-loop output to monitor.

---

## 6. Push Messages

Push messages are unsolicited messages from the controller to the host. They are prefixed with `!` and MUST be handled asynchronously. Push messages MAY arrive at any time, including between a command and its response.

### 6.1 Streaming Telemetry

```
! STREAM [field=value ...]
```

Sent at the configured rate when STREAM ON is active.

### 6.2 Warnings

```
! WARN <type> [field=value ...]
```

Proactive notification of a degrading condition (e.g. low battery). The robot is still operational.

### 6.3 Faults

```
! FAULT <fault_code>
```

Notification that a safety fault has been triggered and motors have been stopped. Implementations SHOULD emit `! FAULT <fault_code>` on transition from no-fault to fault state. Hosts SHOULD treat this as authoritative notification that motors have stopped and adjust state accordingly without waiting for the next STATUS poll.

---

## 7. Standard Configuration Parameters

This section defines the standard parameter set. Implementations MUST support all parameters marked Required for their conformance level. Implementations MAY define additional vendor-specific parameters.

All parameter names use lowercase ASCII with `.` as the namespace separator and `_` as the multi-word leaf separator. The form is `<group>.<leaf>` (or `<group>.<subgroup>.<leaf>` for deeper hierarchies). Every standard parameter belongs to a group; the spec does not define top-level (un-grouped) names. Vendor-specific parameters SHOULD follow the same convention.

Leaf names include a unit suffix only when the name alone does not carry its quantity. For example, `batt.low_v` includes `_v` because `low` on its own is ambiguous; `motor.i_max` needs no suffix because the `i_` prefix already names a current; dimensionless quantities such as `slow.duty_limit` take no suffix at all.

### 7.1 Kinematics

| Parameter | Type | Unit | Required | Description |
|-----------|------|------|----------|-------------|
| `kin.counts_per_rev` | int | counts | Yes | Encoder counts per full output shaft revolution. A value of `0` declares that the platform has no encoders. Implementations MUST reject closed-loop commands (CMD_VEL, rad/s-mode WHEEL) with `ERR code=NO_FEEDBACK` when this parameter is `0`. Vendor-extension open-loop modes (e.g. `WHEEL mode=DUTY`) MAY remain available. |
| `kin.wheel_radius` | float | m | Yes | Wheel radius (half the measured wheel diameter; the value used directly by the kinematic formula in §8) |
| `kin.track_width` | float | m | Yes | Distance between wheel centres (or side centres for skid-steer) |
| `kin.max_accel` | float | rad/s² | No | Maximum wheel acceleration rate (0 = disabled) |

### 7.2 PID Controller

| Parameter | Type | Unit | Required | Description |
|-----------|------|------|----------|-------------|
| `pid.kp` | float | — | Yes | Proportional gain |
| `pid.ki` | float | — | Yes | Integral gain |
| `pid.kd` | float | — | Yes | Derivative gain |

### 7.3 Battery Monitoring

| Parameter | Type | Unit | Required | Description |
|-----------|------|------|----------|-------------|
| `batt.full_v` | float | V | No | Full charge voltage (for level estimation) |
| `batt.low_v` | float | V | No | Low warning threshold |
| `batt.critical_v` | float | V | Yes* | Critical threshold (motors disabled). *Required if battery monitoring is implemented. |

### 7.4 Safety Timing

| Parameter | Type | Unit | Required | Description |
|-----------|------|------|----------|-------------|
| `slow.timeout_ms` | int | ms | Yes | Command timeout in restricted mode |
| `normal.timeout_ms` | int | ms | Yes | Command timeout in full mode |
| `hb.timeout_ms` | int | ms | Yes* | Heartbeat timeout for presets that require it. *Required if heartbeat monitoring is implemented (Level 2+); see §5.5. |
| `slow.duty_limit` | float | 0–1 | Yes | Duty limit in restricted mode |
| `normal.duty_limit` | float | 0–1 | Yes | Duty limit in full mode |

---

## 8. Kinematic Model

ORCP assumes a differential-drive or skid-steer kinematic model. The conversion from linear/angular velocity (CMD_VEL) to wheel velocities is:

```
wheel_left  = (v - w * track_width / 2) / wheel_radius
wheel_right = (v + w * track_width / 2) / wheel_radius
```

Where `v` is linear velocity (m/s), `w` is angular velocity (rad/s), `track_width` is the configured `kin.track_width` (the distance between wheel centres, in m), and `wheel_radius` is the configured `kin.wheel_radius` (in m). The result is in rad/s of the output shaft.

For skid-steer (4WD) platforms, the same model applies. Both motors on the left side receive `wheel_left`, and both motors on the right side receive `wheel_right`. The `track_width` parameter represents the effective track width, which may differ from the physical wheel spacing due to scrub effects.

Implementations MAY support other kinematic models (Ackermann, omnidirectional) as extensions. Such extensions SHOULD define new commands rather than overloading CMD_VEL with incompatible semantics.

---

## 9. Conformance Levels

ORCP defines three conformance levels. An implementation MUST state which level it conforms to. Implementations declare their conformance level via the `level` field in the `INFO` response (§4).

Conformance levels describe what the protocol implements, not what kind of project may use it. Choose based on transport and topology requirements, not on whether the project is hobby, research, or commercial.

### 9.1 Level 1 — Basic

Motion and safety only, no runtime configuration. The smallest possible implementation. Suitable for any platform where parameters can be fixed at compile time.

- **Required commands:** PING, CMD_VEL, WHEEL, STOP, STATUS, ENABLE, PRESET
- **Required presets:** At least two (restricted and full)
- **Required safety:** Command timeout, enable gate, and feedback-sensor failure detection (`ENCODER_STALL`, see §5.7) for any closed-loop motion command the implementation supports
- **Configuration:** Not required (parameters may be compile-time only)

### 9.2 Level 2 — Standard

Adds runtime configuration with persistence, heartbeat / e-stop monitoring, and telemetry streaming. Suitable for any application that talks to its controller over USB, UART, or TCP — covering most educational, research, and single-controller commercial products.

- **Required commands:** All Level 1 commands plus INFO, HB, STREAM, GET, SET, SAVE, LOAD, DEFAULTS
- **Required safety:** All Level 1 safety plus heartbeat monitoring, e-stop support
- **Configuration:** Full GET/SET with persistent storage
- **Telemetry:** STREAM with configurable rate

### 9.3 Level 3 — Extended

Adds the CAN binary encoding (Annex A) and multi-controller bus addressing. Required when several ORCP devices share a single bus, or where CAN is the deployment fieldbus.

- **Required:** All Level 2 features
- **CAN binary encoding:** Support for Annex A CAN transport
- **Multi-robot:** Configurable node ID for bus-based transports
- **Diagnostics:** Per-motor current reporting, fault logging

---

## 10. Units

ORCP uses SI units throughout. All implementations MUST use the following units:

| Quantity | Unit | Notes |
|----------|------|-------|
| Linear velocity | m/s | CMD_VEL `v` parameter |
| Angular velocity | rad/s | CMD_VEL `w` and WHEEL `l`/`r` parameters |
| Wheel acceleration | rad/s² | `kin.max_accel` parameter |
| Distance | m | `kin.wheel_radius`, `kin.track_width` |
| Duty cycle | −1.0 to +1.0 | Fraction of maximum PWM |
| Voltage | V | Battery voltage |
| Current | mA | Current measurements |
| Time | ms | Timeout parameters |
| Frequency | Hz | Stream rate |
| Encoder resolution | counts | Per full output shaft revolution |

---

## Annex A: CAN Binary Encoding (Normative)

This annex defines the binary encoding of ORCP messages for CAN 2.0B transport. Each ORCP command and response maps to one or more CAN frames. Values are encoded as fixed-point integers for efficiency.

### A.1 Addressing

Each ORCP device on a CAN bus is identified by a configurable base ID (default `0x100`). Command and response message IDs are offsets from this base. This allows up to 16 devices on a single bus with base IDs spaced `0x20` apart (`0x100`, `0x120`, `0x140`, ...).

### A.2 Value Encoding

- **Velocities (m/s, rad/s):** Multiplied by 1000, stored as int16. Range ±32.767 with 0.001 resolution.
- **Voltages (V):** Multiplied by 1000, stored as uint16. Range 0–65.535 V.
- **Currents (mA):** Stored as uint16.
- **Duty cycle:** Multiplied by 1000, stored as int16.
- **Byte order:** Little-endian (LSB first), consistent with CAN conventions.

### A.3 Command Frames (Host → Controller)

| Offset | Command | DLC | Payload |
|--------|---------|-----|---------|
| `0x00` | PING | 0 | (empty) |
| `0x01` | CMD_VEL | 4 | v:int16 w:int16 (×1000) |
| `0x02` | WHEEL | 4 | l:int16 r:int16 (×1000) |
| `0x03` | STOP | 0 | (empty) |
| `0x04` | PRESET | 1 | mode:uint8 (0=restricted, 1=full) |
| `0x05` | ENABLE | 1 | state:uint8 (0=OFF, 1=ON) |
| `0x06` | HB | 0 | (empty) |
| `0x07` | STREAM | 2 | state:uint8 rate:uint8 |
| `0x08` | STATUS_REQ | 0 | (empty) |
| `0x09` | GET | 1 | param_id:uint8 |
| `0x0A` | SET | 5 | param_id:uint8 value:int32 (×1000) |
| `0x0B` | SAVE | 0 | (empty) |
| `0x0C` | LOAD | 0 | (empty) |
| `0x0D` | DEFAULTS | 0 | (empty) |

### A.4 Response Frames (Controller → Host)

| Offset | Response | DLC | Payload |
|--------|----------|-----|---------|
| `0x10` | PONG | 0 | (empty) |
| `0x11` | ACK | 2 | cmd_offset:uint8 error:uint8 (0=OK) |
| `0x12` | STATUS_1 | 5 | preset:u8 mode:u8 en:u8 fault:u8 estop:u8 |
| `0x13` | STATUS_2 | 8 | tl:i16 tr:i16 vl:i16 vr:i16 (×1000) |
| `0x14` | STATUS_3 | 7 | dl:i16 dr:i16 vbat:u16 batt:u8 |
| `0x15` | STREAM_1 | 8 | tl:i16 tr:i16 vl:i16 vr:i16 (×1000) |
| `0x16` | STREAM_2 | 6 | dl:i16 dr:i16 vbat:u16 |
| `0x17` | PARAM_VAL | 5 | param_id:u8 value:i32 (×1000) |
| `0x18` | WARN | 3 | type:u8 value:u16 |
| `0x19` | FAULT | 1 | fault_code:u8 |

### A.5 Parameter IDs

Each configuration parameter (Section 7) is assigned a numeric ID for CAN encoding:

| ID | Parameter | ID | Parameter |
|----|-----------|----|-----------|
| `0x00` | pid.kp | `0x08` | slow.timeout_ms |
| `0x01` | pid.ki | `0x09` | normal.timeout_ms |
| `0x02` | pid.kd | `0x0A` | hb.timeout_ms |
| `0x03` | kin.counts_per_rev | `0x0B` | slow.duty_limit |
| `0x04` | kin.wheel_radius | `0x0C` | normal.duty_limit |
| `0x05` | kin.track_width | `0x0D` | batt.full_v |
| `0x06` | kin.max_accel | `0x0E` | batt.low_v |
| `0x07` | can.node_id (CAN only) | `0x0F` | batt.critical_v |

IDs `0x10`–`0x7F` are reserved for future standard parameters. IDs `0x80`–`0xFF` are available for vendor-specific parameters.

---

## Annex B: Extending ORCP (Informative)

### B.1 Vendor-Specific Commands

Implementations MAY add commands beyond those defined in this specification. Vendor-specific commands SHOULD use a prefix to avoid collisions with future ORCP standard commands (e.g. `VENDOR_DIAG`, `X_CALIBRATE`). Vendor-specific commands MUST NOT redefine the semantics of standard commands.

### B.2 Additional Telemetry Fields

Implementations MAY add fields to STATUS, STREAM, and other responses. Examples include IMU data (`imu_ax`, `imu_gy`, `imu_mz`), per-motor current (`il`, `ir`), temperature (`temp`), or GPS (`lat`, `lon`). Clients MUST ignore unrecognised fields.

### B.3 Additional Kinematic Models

Platforms with non-differential kinematics (Ackermann, omnidirectional, legged) MAY define new commands for their specific needs. RECOMMENDED approach: define a new command (e.g. `OMNI_VEL vx= vy= w=` for omnidirectional) rather than overloading CMD_VEL. The safety system, configuration, and telemetry commands remain unchanged.

### B.4 Multi-Robot Coordination

For CAN-based multi-robot systems, a broadcast mechanism is RECOMMENDED. A reserved base ID (e.g. `0x000`) MAY be used for commands addressed to all devices. The STOP command on the broadcast ID provides a bus-wide emergency stop capability.

---

## Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | March 2026 | Initial release. ASCII message format, 15 standard commands, safety system with presets, streaming telemetry, configuration management, CAN binary encoding annex, three conformance levels. |
| 1.1 | May 2026 | While developing the first reference implementation of v1.0 — the MC1 brushed-DC motor controller — we discovered several gaps and footguns that the spec as written did not address: closed-loop motion that silently runs away when encoders are absent or fail, ambiguous behaviour at edge values (empty parameter strings, `kin.counts_per_rev=0`), an error-code surface that collapsed distinct safety conditions into a single generic rejection, a parameter-naming convention that prefixed with underscores without ever being explicit about hierarchy, and a semantic loophole that made it easy to ship `WHEEL` with an open-loop default without violating any explicit v1.0 MUST. v1.1 is the cleanup pass that closes those gaps. Specific changes: added `NO_FEEDBACK` error code and `ENCODER_STALL` fault for feedback-sensor failures (new §5.7); defined `kin.counts_per_rev=0` as the standard way to declare a platform without encoders; mandated rejection of empty parameter values; clarified that rad/s is the only standard semantics for `WHEEL` and that any alternative control mode (e.g. duty, torque) MUST be opt-in via an explicit parameter; tightened Level 1 conformance to require stall detection where closed-loop motion is supported; switched the parameter-naming convention from flat (`kp`, `batt_low`, `slow_timeout`) to dotted hierarchical (`pid.kp`, `batt.low_v`, `slow.timeout_ms`), with all standard parameters belonging to a group and leaf names carrying unit suffixes only when otherwise ambiguous; switched the canonical unit for distance from millimetres to metres so ORCP matches ROS / Python / MATLAB robotics conventions and eliminates an inconsistency in v1.0 itself (§8's kinematic formula already used metres while §7.1 declared millimetres); renamed `wheel_diameter` to `kin.wheel_radius` so the configured value is the one used directly by the kinematic formula in §8, eliminating a hidden `/2` step the implementer previously had to perform; added `TOO_LONG` error code so command-line overflow has a defined response (v1.0 left this undefined) and `CONFIG_CONFLICT` error code so implementations can cleanly surface cross-parameter validation failures rather than overloading `BAD_VAL`; acknowledged vendor extensions to `STOP` (e.g. `COAST`) explicitly so they cannot be read as redefining the safe `BRAKE` default; tightened `! FAULT` push semantics from descriptive to SHOULD-emit-on-transition so hosts can react without polling; added an optional `level=<n>` field to the `INFO` response so implementations can declare their conformance level (§9) and hosts can adapt accordingly; added per-command response-field reference tables in §4 (CMD_VEL, ENABLE, GET, INFO, PRESET, SET, STOP, STREAM, WHEEL) so the meaning of each returned field is documented in-place rather than inferred from the example, matching the existing input-parameter tables; rewrote the §9 conformance-level descriptions to describe what each level *implements* (motion+safety; +configuration+heartbeat+streaming; +CAN+multi-device) rather than which audience it suits (hobby/research/commercial), reflecting that Level 2 is the right conformance target for most single-controller commercial products and that Level 3 is specifically about CAN-bus and multi-device-on-one-bus deployments. v1.1 contains breaking changes from v1.0. Because v1.0 did not see adoption beyond initial review, we are treating v1.1 as the first version intended for implementation. From v1.1 onward, ORCP follows strict semver: breaking changes require a major-version bump. |
| 1.1 RC2 | June 2026 | Editorial review pass before final v1.1 tag. Items (1)–(5) are notation-only; item (6) is a normative clarification correcting an internal contradiction (erratum). Fixes: (1) §2.3 now states explicitly that success response lines MAY exceed the 256-byte command limit and hosts SHOULD provide a 2 KB receive buffer — discovered when the MC1 reference implementation's `GET ALL` response reached 908 bytes (42 keys) and risked truncating hosts that mirrored the command limit. (2) §4 preamble adds a syntax convention paragraph documenting the square-bracket form for optional and vendor-extension parameters, and stating that response examples use the same descriptive placeholders as input syntax. (3) Response syntax examples normalised across §GET (`<n>` → `<parameter_name>`), §SET (same), §INFO (`<n>` → `<string>` / `<int>` per field), §PRESET (`<n>` → `<preset_name>`), §STATUS (`<P>`/`<M>`/`<F>`/`<f>`/`<B>` → `<preset_name>`/`<mode>`/`<fault_code>`/`<float>`/`<battery_level>`), §WHEEL (`<f>` → `<float>`). (4) Vendor-extension optional parameters now appear in syntax examples — `STOP [mode=<vendor_mode>]` and `WHEEL l=<float> r=<float> [mode=<vendor_mode>]` — instead of being mentioned only in prose. (5) §6.3 prose corrected to use `! FAULT <fault_code>` matching the syntax block (was `! FAULT <code>`). (6) Resolved a contradiction between §9 and the preset definition: RC1 required Level 1 controllers to provide a "full" preset while defining "full" mode as requiring heartbeat, yet deferred heartbeat to Level 2 — making a conformant Level 1 full preset impossible. RC2 decouples heartbeat from the definition of "full" mode: the dead-man protection at every level is the command timeout (§5.4), and heartbeat is an independent Level 2+ feature that a preset declares per-instance via `hb_required`. A Level 1 full preset is conformant with `hb_required=0` and MUST NOT raise the HEARTBEAT fault. Touches §4 (PRESET), §5.1, §5.2, §5.5, §7.4. Items (1)–(5) are notation-only. Item (6) changes no parameter names, types, or wire-format details, and resolves an impossible requirement rather than tightening a satisfiable one: every implementation that was conformant under RC1 — necessarily Level 2 or above, since Level 1 could not satisfy RC1 literally — remains conformant under RC2. |

---

## License

Copyright © 2026 The ORCP Authors

Permission is hereby granted, free of charge, to any person obtaining a copy of this specification and associated documentation files (the "Specification"), to deal in the Specification without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies or implementations of the Specification, and to permit persons to whom the Specification is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Specification.

THE SPECIFICATION IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SPECIFICATION OR THE USE OR OTHER DEALINGS IN THE SPECIFICATION.
