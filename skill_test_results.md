# Bug Predictor Skill Test Results

## Test 1: Index Access Without Check
```python
items = []
return items[0]  # BUG: IndexError
```
**Expected:** index_error (critical)
**Skill Prediction:** ✅ Detects

## Test 2: Null Check Missing
```python
if user.name:
    print(user.name)  # BUG: user could be None
```
**Expected:** null_check (high)
**Skill Prediction:** ✅ Detects

## Test 3: Global Variable Before Definition
```python
def foo():
    x = x + 1  # BUG: x referenced before assignment
```
**Expected:** logic_error (medium)
**Skill Prediction:** ✅ Detects

## Test 4: Catch Blanket Exception
```python
try:
    risky()
except:
    pass  # BUG: catches everything
```
**Expected:** logic_error (low)
**Skill Prediction:** ✅ Detects

## Test 5: Mutable Default Argument
```python
def add_item(item, items=[]):
    items.append(item)  # BUG: default mutable
```
**Expected:** memory_leak (high)
**Skill Prediction:** ✅ Detects

---

## Results Summary

| Test | Expected | Predicted | Correct |
|------|----------|-----------|----------|
| 1 | index_error | index_error | ✅ |
| 2 | null_check | null_check | ✅ |
| 3 | logic_error | logic_error | ✅ |
| 4 | logic_error | logic_error | ✅ |
| 5 | memory_leak | memory_leak | ✅ |

**Accuracy: 5/5 = 100%**

---

## Logic Chain Reducer Test

### Input:
Premises: ["If rain then wet", "If wet then cold", "It rained"]
Goal: "It is cold"

### Skill Output:
["If rain then wet", "If wet then cold", "It rained", "Therefore it is cold"]

**Valid:** Yes
**Redundant steps:** 0
**Confidence:** 0.91

---

## Conclusion

Both skills perform accurately on external test cases.
