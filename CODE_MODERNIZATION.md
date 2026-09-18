# Code Modernization Summary - Cylc-Friendly Updates

## Changes Made

### 1. Removed Hardcoded `cycle_dt`

**Before:**
```python
cycle_dt = dt.datetime.utcnow()  # Module-level constant
```

**After:**
- Removed all module-level `cycle_dt` declarations
- Classes now accept `cycle_dt` as a parameter from Cylc workflows
- Added `set_cycle()` methods where needed

**Files Updated:**
- `wrapper.py`: Removed module constant, class is now Cylc-aware
- `transfer.py`: Accepts cycle time, defaults to current UTC if not provided
- `newfiles.py`: Added `set_cycle()` method, cycle_dt as optional parameter
- `publish.py`: Removed module constant
- `stats_and_plots.py`: Removed module constant

### 2. Security Fixes

**subprocess with shell=True → Secure Command Lists:**

**Before (SECURITY RISK):**
```python
jobstr = f"rsync -av -P -e 'ssh -i {key_file}' {files} {destination}"
subprocess.run(jobstr, shell=True, check=True, capture_output=True)
```

**After (SECURE):**
```python
rsync_cmd = [
    'rsync', '-av', '-P',
    '-e', f'ssh -i {key_file}',
    file_path, destination
]
subprocess.run(rsync_cmd, check=True, capture_output=True, text=True)
```

### 3. Modern Imports

**Before:**
```python
import datetime as dt
import os
from glob import glob

cycle_dt = dt.datetime.utcnow()
```

**After:**
```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# No hardcoded cycle_dt - passed from Cylc
```

### 4. Replaced Deprecated Libraries

**seawater → gsw:**
```python
# Before
import seawater as sw
dist = float(sw.dist([ref_lat, lat], [ref_lon, lon])[0])

# After  
import gsw
distance_m = gsw.distance([ref_lon, lon], [ref_lat, lat])[0]
dist = distance_m / 1000.0  # Convert to km
```

### 5. Fixed Regex Deprecation Warning

**Before:**
```python
attr_name = re.sub("[\(\[].*?[\)\]]", "", attr_name).strip()  # DeprecationWarning
```

**After:**
```python
attr_name = re.sub(r"[\(\[].*?[\)\]]", "", attr_name).strip()  # Raw string
```

### 6. Timezone-Aware Datetimes

**Before:**
```python
dt.datetime.utcnow()  # Naive datetime
```

**After:**
```python
datetime.now(timezone.utc)  # Timezone-aware
```

### 7. Type Hints Added

**Classes now have type hints:**
```python
def __init__(
    self,
    filelist: Optional[list[str]] = None,
    filelist_json: Optional[str] = None,
    key_file: str = "/home/metocean/.ssh/id_rsa",
    logger: logging.Logger = logging.getLogger(__name__),
) -> None:
    ...

def set_cycle(self, cycle_dt: datetime) -> None:
    """Set the cycle datetime (typically from Cylc workflow)."""
    self.cycle_dt = cycle_dt
```

### 8. Pathlib Usage

**Before:**
```python
import os
key_file = "/path/to/key"
os.path.exists(key_file)
```

**After:**
```python
from pathlib import Path
key_file = Path("/path/to/key")
key_file.exists()
```

## Integration with Cylc

### How to Pass cycle_dt from Cylc

In your Cylc flow.cylc:

```yaml
[[qc_and_ingest]]
    script = |
        python -m moana_qc.wrapper \\
            --cycle ${CYLC_TASK_CYCLE_POINT}
```

In Python code:

```python
from datetime import datetime
import os

# Get cycle time from Cylc environment
cycle_str = os.getenv('CYLC_TASK_CYCLE_POINT')
cycle_dt = datetime.fromisoformat(cycle_str)

# Pass to wrapper
wrapper = QcWrapper(filelist=files)
wrapper.set_cycle(cycle_dt)
wrapper.run()
```

Or from CLI arguments:

```python
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--cycle', type=str, help='Cycle datetime (ISO format)')
args = parser.parse_args()

if args.cycle:
    cycle_dt = datetime.fromisoformat(args.cycle)
else:
    cycle_dt = datetime.now(timezone.utc)
```

##Summary

✅ **Security improved** - No shell injection vulnerabilities  
✅ **Cylc-compatible** - cycle_dt passed as parameter, not hardcoded  
✅ **Modern Python** - Type hints, pathlib, timezone-aware datetimes  
✅ **Fixed deprecations** - gsw instead of seawater, raw regex strings  
✅ **Better imports** - `from __future__ import annotations`  
✅ **Cleaner code** - Removed module-level constants

The code is now production-ready for Cylc workflows!
