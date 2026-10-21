Here's a simple Python function to reverse a string:

```python
def reverse_string(s):
    return s[::-1]
```

**Usage:**
```python
print(reverse_string("hello"))  # olleh
```

**How it works:** `s[::-1]` is slice notation with a step of -1, which walks the string from the last character to the first and builds a new, reversed string. Strings in Python are immutable, so the original is never changed.
