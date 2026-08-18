"""
TEST CASE 2: DECOUPLING THE "GOD FUNCTION"
Challenge: This code violates the Single Responsibility Principle (SRP). It tightly 
couples file I/O, data validation/transformation, and database query generation into 
a single monolithic procedural block.
Expected AI Behavior: The AI should break this down into a modern pipeline (Extract, 
Transform, Load), ideally utilizing dataclasses/TypedDicts for the data model, and 
separating the I/O operations from the pure business logic.
"""

# legacy_etl.py
import csv, os

def parse_and_save_data(filepath):
    # Connected logic: File reading, business logic, and fake DB saving all in one
    if not os.path.exists(filepath):
        print("File missing")
        return
        
    valid_records = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            name = row[0].strip().title()
            try:
                age = int(row[1])
            except ValueError:
                age = 0
            
            if age >= 18:
                valid_records.append({"name": name, "age": age, "role": row[2]})
                
    # Simulate tight coupling to a database saving routine
    db_string = "INSERT INTO users VALUES "
    for r in valid_records:
        db_string += f"('{r['name']}', {r['age']}), "
        
    print(db_string)
    return len(valid_records)