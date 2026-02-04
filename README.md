# tcx2ics

Convert a `.tcx` activity file (from Garmin, Strava, etC.) into a single `.ics`
calendar event with basic workout Statistics.

The calendar event contains:
- start and end time of the activity
- sport type
- total duration
- total distance


## 📦 Installation

### pip

Install tcx2ics with pip:

```sh
pip install tcx2ics
```

## 🚀 Examples

### Basic example

```python
from tcx2ics import Tcx2Ics
Tcx2Ics().convert("15.tcx", "workout.ics")
```

## 🔑 License

This package is distributed under the MIT License. This license can be found online at <http://www.opensource.org/licenses/MIT>.

## Disclaimer

This framework is provided as-is, and there are no guarantees that it fits your purposes or that it is bug-free. Use it at your own risk!

## 🔗 Related frameworks

[1] [AST-Monitor: A wearable Raspberry Pi computer for cyclists](https://github.com/firefly-cpp/AST-Monitor)

[2] [TCXReader.jl: Julia package designed for parsing TCX files](https://github.com/firefly-cpp/TCXReader.jl)

[3] [TCXWriter: A Tiny Library for writing/creating TCX files on Arduino](https://github.com/firefly-cpp/tcxwriter)
