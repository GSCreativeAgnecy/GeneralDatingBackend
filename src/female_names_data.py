import csv
import os

DATA = []

def _load():
    global DATA
    if DATA:
        return DATA
    path = os.path.join(os.path.dirname(__file__), "indian_women_names_complete_1500.csv")
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                DATA.append({
                    "first": row.get("Name", "").strip(),
                    "last": row.get("Last", "").strip(),
                    "age": int(row.get("Age", 25)),
                    "height": int(float(row.get("Height", 155))),
                    "category": row.get("Category", "").strip(),
                })
    return DATA


FEMALE_USERS = _load()

MALE_FIRST = ["Rahul", "Arjun", "Vikram", "Karan", "Amit", "Siddharth", "Rohan", "Aditya", "Nikhil", "Deepak",
              "Harsh", "Varun", "Pranav", "Manav", "Kunal", "Rishi", "Tarun", "Vivek", "Raj", "Abhishek"]
MALE_LAST = ["Sharma", "Patel", "Singh", "Kumar", "Verma", "Gupta", "Reddy", "Nair", "Joshi", "Mehta",
             "Shah", "Yadav", "Rao", "Choudhary", "Pandey", "Iyer", "Menon", "Naik", "Pillai", "Deshmukh"]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
          "Surat", "Nagpur", "Indore", "Bhopal", "Chandigarh", "Coimbatore", "Kochi", "Visakhapatnam", "Goa", "Udaipur"]


def random_male_full():
    import random
    return f"{random.choice(MALE_FIRST)} {random.choice(MALE_LAST)}"
