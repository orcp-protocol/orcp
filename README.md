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

- [ORCP v1.0 Specification (Markdown)](spec/ORCP-v1.0.md)
- [ORCP v1.0 Specification (Word)](spec/ORCP_Specification_v1.0.docx)

## Client Libraries

- Python: *coming soon*
- MATLAB: *coming soon*
- ROS2: *coming soon*

## Conformance Levels

| Level | Name     | Use Case                    | Requirements                    |
|-------|----------|-----------------------------|---------------------------------|
| 1     | Basic    | Hobby, simple platforms     | Core motion + safety commands   |
| 2     | Standard | Education, research         | Full command set + config       |
| 3     | Extended | Commercial, multi-robot     | CAN encoding + diagnostics      |

## Implementations

- *Your project here — submit a PR to be listed*

## Contributing

ORCP is an open standard. Contributions are welcome:

- **Found an issue?** Open an [Issue](../../issues)
- **Have a suggestion?** Start a [Discussion](../../discussions)
- **Built an implementation?** Submit a PR to add it to the list above

## License

MIT — see [LICENSE](LICENSE) for details. You are free to implement, modify,
and distribute implementations of this protocol without restriction.
