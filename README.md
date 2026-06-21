# ORCP — Open Robot Control Protocol

A simple, safe, transport-agnostic protocol for robot control.

## What is ORCP?

ORCP defines a standard interface between a high-level controller (laptop, SBC, PLC)
and a low-level device controller (microcontroller managing actuators, sensors, and
safety systems).

It is designed to be:

- **Human-readable** — type commands in a terminal, read responses with your eyes
- **Safe** — mandatory safety system with presets, timeouts, heartbeat, and e-stop
- **Transport-agnostic** — works over USB, WiFi/TCP, UART, or CAN bus
- **Extensible** — add fields and commands without breaking existing clients

## Quick Example
```
>>> PING
<<< OK PONG

>>> CMD_VEL v=0.200 w=0.000
<<< OK CMD_VEL v=0.200 w=0.000 tl=4.082 tr=4.082

>>> STATUS
<<< OK STATUS preset=SLOW mode=VELOCITY en=1 fault=OK ...

>>> STOP
<<< OK STOP mode=BRAKE
```

## Specification

**Current — ORCP v1.1**

- [ORCP v1.1 Specification (Markdown)](spec/ORCP-v1.1.md)
- [ORCP v1.1 Specification (Word)](spec/ORCP-v1.1.docx)

<details>
<summary>Previous versions</summary>

- [ORCP v1.0 Specification (Markdown)](spec/ORCP-v1.0.md)
- [ORCP v1.0 Specification (Word)](spec/ORCP_Specification_v1.0.docx)

</details>

## Client Libraries

- **Python** — [`orcp`](https://github.com/orcp-protocol/orcp-python) (`pip install orcp`): Pythonic client over USB serial or WiFi, plus the `orcp-drive` keyboard teleop demo.
- **ROS 2** — [`orcp-ros2`](https://github.com/orcp-protocol/orcp-ros2): an `rclpy` driver bridging `/cmd_vel` & `/wheel` to odometry/TF/battery/diagnostics.
- **MATLAB** — *coming soon*

## Conformance Levels

Choose a level by transport and topology requirements, not by whether the project is hobby, research, or commercial.

| Level | Name     | Adds                                                                  | Typical transport / topology              |
|-------|----------|-----------------------------------------------------------------------|-------------------------------------------|
| 1     | Basic    | Motion + mandatory safety (presets, enable gate, command timeout, stall detection); parameters fixed at compile time | Any single link                           |
| 2     | Standard | Runtime configuration with persistence, heartbeat & e-stop monitoring, telemetry streaming | USB, UART, or TCP — single controller     |
| 3     | Extended | CAN binary encoding, multi-controller bus addressing, per-motor diagnostics | CAN fieldbus / multiple devices on one bus |

## Implementations

- **[`orcp-sim`](https://github.com/orcp-protocol/orcp-sim)** (`pip install orcp-sim`) — reference simulator: emulates an ORCP-compliant controller (Levels 1–3) on a virtual serial port or WebSocket, no hardware. Ships device *profiles* (e.g. an MC1 profile) and accepts third-party profiles, so any host tool can be developed and tested against the protocol.
- *Your project here — submit a PR to be listed*

## Contributing

ORCP is an open standard. Contributions are welcome:

- **Found an issue?** Open an [Issue](../../issues)
- **Have a suggestion?** Start a [Discussion](../../discussions)
- **Built an implementation?** Submit a PR to add it to the list above

## License

MIT — see [LICENSE](LICENSE) for details. You are free to implement, modify,
and distribute implementations of this protocol without restriction.
