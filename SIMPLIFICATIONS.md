# Code Simplification Summary

This document summarizes simplifications made to the moana-qc codebase for better maintainability.

## Major Simplifications

### 1. **Gear Classifications → Config File** ✅

**Before:**
```python
# 40+ line hardcoded dictionary in __init__
gear_class={
    "Bottom trawl": "mobile",
    "Potting": "stationary",
    # ... 20+ more entries
}
```

**After:**
```python
# Load from gear_classifications.yml
DEFAULT_GEAR_CLASS = load_yaml(_GEAR_CLASS_FILE).get("GEAR_CLASSIFICATIONS", {})

# In __init__
self.gear_class = gear_class or DEFAULT_GEAR_CLASS
```

**Benefits:**
- ✅ Easier to update gear classifications without code changes
- ✅ Cleaner __init__ method (40+ lines → 1 line)
- ✅ Can be version-controlled separately
- ✅ Reusable across modules

### 2. **Fixed Default Class Names** ✅

**Before:**
```python
self._default_datareader_class = "ops_qc.readers.MangopareStandardReader"
self._default_metareader_class = "ops_qc.readers.MangopareMetadataReader"
```

**After:**
```python
self._default_datareader_class = "moana_qc.readers.MangopareStandardReader"
self._default_metareader_class = "moana_qc.readers.MangopareMetadataReader"
```

**Prevents import errors** when using the renamed package!

### 3. **Simplified Default Parameters** ✅

**Before:**
```python
metafile_username=[],      # Empty list (weird default)
metafile_token=[],         # Empty list
datareader={},            # Empty dict
gear_class={...40 lines...}  # Huge dict
```

**After:**
```python
metafile_username: Optional[str] = None,  # Proper optional
metafile_token: Optional[str] = None,
datareader: Optional[dict] = None,
gear_class: Optional[dict] = None,  # Load from config if None
```

**Benefits:**
- ✅ Clearer intent (None vs empty list/dict)
- ✅ Better type hints
- ✅ Less confusing for users

### 4. **pathlib Throughout** ✅

**Before:**
```python
import os
head, tail = os.path.split(filename)
savefile = "{}{}{}{}".format(
    self.out_dir, os.path.splitext(tail)[0], self.outfile_ext, ".nc"
)
```

**After:**
```python
from pathlib import Path
file_path = Path(filename)
out_dir = Path(self.out_dir) if self.out_dir else file_path.parent
savefile = out_dir / f"{file_path.stem}{self.outfile_ext}.nc"
```

**Benefits:**
- ✅ More readable and Pythonic
- ✅ Cross-platform path handling
- ✅ Cleaner string formatting

### 5. **Removed Redundant _initialize_outdir** ✅

**Before:**
```python
def _initialize_outdir(self, out_dir):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

# Then call it
self._initialize_outdir(self.out_dir)
```

**After:**
```python
# Just use pathlib's built-in
out_dir.mkdir(parents=True, exist_ok=True)
```

**Benefits:**
- ✅ One line instead of function + call
- ✅ Built-in and well-tested
- ✅ Handles race conditions better

### 6. **Removed Duplicate Docstring** ✅

**Before:**
```python
"""Quality control tests for oceanographic observations.
... (30 lines of documentation)
"""

# Then 20 lines later, SAME documentation again in a string literal
"""
QC Tests for ocean observations. The test options are:
... (same 30 lines again)
"""
```

**After:**
```python
"""Quality control tests for oceanographic observations.
... (documentation at top only)
"""

class QcTests:
    # No duplicate
```

**Removed 50+ lines of duplicate text!**

### 7. **Type Hints Added Throughout** ✅

**Before:**
```python
def __init__(self, ds, test_list=None, save_flags=False, ...):
    ...

def set_cycle(self, cycle_dt):
    ...
```

**After:**
```python
def __init__(
    self,
    ds: xr.Dataset,
    test_list: Optional[list[str]] = None,
    save_flags: bool = False,
    ...
) -> None:
    ...

def set_cycle(self, cycle_dt: datetime) -> None:
    ...
```

**Benefits:**
- ✅ Better IDE autocomplete
- ✅ Catches type errors early
- ✅ Self-documenting code

### 8. **Simplified File Path Handling** ✅

**Before:**
```python
attr_file=os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "attribute_list.yml"
)
```

**After:**
```python
# With defaults in __init__
self.attr_file = Path(attr_file) if attr_file else Path(__file__).parent / "attribute_list.yml"
```

**Benefits:**
- ✅ More readable
- ✅ Works with both str and Path inputs
- ✅ Proper default handling

### 9. **Better Default Handling** ✅

**Before:**
```python
self.test_list_1 = test_list_1  # Could be None
self.test_list_2 = test_list_2  # Could be None

# Later, need to check everywhere:
if self.test_list_1:
    for test in self.test_list_1:
        ...
```

**After:**
```python
self.test_list_1 = test_list_1 or []  # Always a list
self.test_list_2 = test_list_2 or []

# Later, just iterate:
for test in self.test_list_1:  # Works even if empty
    ...
```

**Benefits:**
- ✅ No None checks needed
- ✅ Simpler iteration logic
- ✅ Fewer edge case bugs

### 10. **Modern Class Definitions** ✅

**Before:**
```python
class QcWrapper(object):
    ...

class QcApply(object):
    ...
```

**After:**
```python
class QcWrapper:  # Python 3.10+ doesn't need (object)
    ...

class QcApply:
    ...
```

**Minor but modern!**

## Summary Statistics

### Lines of Code Reduced
- `wrapper.py`: ~50 lines (gear dict moved to config)
- `qc_tests_df.py`: ~50 lines (removed duplicate docstring)  
- `apply_qc.py`: ~10 lines (simplified init)
- **Total: ~110 lines removed**

### Complexity Reduced
- ✅ 1 fewer method (_initialize_outdir)
- ✅ 40-line dict → external config file
- ✅ Duplicate documentation removed
- ✅ String concatenation → f-strings and pathlib

### Maintainability Improved
- ✅ Type hints throughout
- ✅ Config files for data (not code)
- ✅ Modern Python idioms
- ✅ Better defaults
- ✅ Less confusing parameters

## Still Could Be Simplified (Future Work)

### 1. **Dual Data Structures** 🔄
The code maintains both `self.ds` (xarray) and `self.df` (pandas) for the same data:

```python
# In QcApply.__init__
self.ds = ds  # xarray Dataset
self.df = self.ds.to_dataframe().reset_index()  # Convert to pandas
```

**Why:** Legacy from inheriting code. QC tests use pandas, but need xarray attributes.

**Could simplify:** Use xarray throughout, or use pandas throughout with attrs dict.

### 2. **status_dict_keys List** 🔄
Hardcoded list of 23 status dictionary keys:

```python
self.status_dict_keys = [
    "filename", "baseline", "cellular_signal_strength",
    # ... 20 more keys
]
```

**Could simplify:** Use a dataclass or Pydantic model for type safety and validation.

### 3. **Complex _set_class Pattern** 🔄
```python
def _set_class(self, in_class, default_class):
    klass = in_class.pop("class", default_class)
    out_class = import_pycallable(klass)
    return out_class
```

**Could simplify:** Just use the class directly instead of string imports (unless dynamic loading is truly needed).

### 4. **metadata_columns Dictionary** 🔄
Another hardcoded mapping in PreProcessMangopare:

```python
metadata_columns={
    "gear_class": "Gear Class",
    "vessel_email": "Contact email",
    # ... more mappings
}
```

**Could simplify:** Move to config file like gear_classifications.

## Recommendations

### High Priority ✅ DONE
- [x] Move gear_class to config file
- [x] Fix default class names (ops_qc → moana_qc)
- [x] Add type hints
- [x] Use pathlib consistently
- [x] Simplify default parameters
- [x] Remove duplicate documentation

### Medium Priority 🔄 Consider
- [ ] Consider dataclasses for status_dict
- [ ] Move metadata_columns to config
- [ ] Evaluate if dual ds/df is needed
- [ ] Add configuration validation

### Low Priority 💡 Nice to Have
- [ ] Add comprehensive docstrings to all methods
- [ ] Create configuration schema documentation
- [ ] Add examples in docstrings
- [ ] Consider dependency injection for classes

---

**Overall Result:** The code is now cleaner, more maintainable, and follows modern Python best practices while maintaining backward compatibility where needed!
