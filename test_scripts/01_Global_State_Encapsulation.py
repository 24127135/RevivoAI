"""
TEST CASE 1: GLOBAL STATE ENCAPSULATION
Challenge: This legacy script relies on global state variables and in-place mutations, 
making it inherently thread-unsafe and difficult to unit test.
Expected AI Behavior: The AI should identify the side-effects and refactor the code 
to encapsulate `_DATA_STORE` and `_ERROR_COUNT` into a cohesive Class (e.g., `DataProcessor`), 
eliminating the `global` keyword while maintaining the exact data transformation logic.
"""

# legacy_state_processor.py
_DATA_STORE = {}
_ERROR_COUNT = 0

def process_item(item_id, val):
    global _DATA_STORE, _ERROR_COUNT
    if item_id == "":
        _ERROR_COUNT += 1
        return False
        
    if item_id in _DATA_STORE:
        if type(_DATA_STORE[item_id]) == list:
            _DATA_STORE[item_id].append(val)
        else:
            _DATA_STORE[item_id] = [_DATA_STORE[item_id], val]
    else:
        _DATA_STORE[item_id] = val
    return True

def get_report():
    return f"Processed {len(_DATA_STORE)} items with {_ERROR_COUNT} errors."