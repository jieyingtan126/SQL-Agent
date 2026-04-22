import sys
import os
import pytest

# Adds the parent directory (root) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import list_tables, get_schema, get_business_rule, execute_query


### Test list_tables

def test_list_tables_success():
    result = list_tables.invoke({})
    assert isinstance(result, list)
    assert len(result) > 0
    assert "Customers" in result


### Test get_schema

def test_get_schema_success():
    # Testing with a known valid table
    result = get_schema.invoke({"table_name": "Customers"})
    assert isinstance(result, str)
    assert "CREATE TABLE" in result

def test_get_schema_invalid_table():
    # Testing the error handling logic we added
    result = get_schema.invoke({"table_name": "NonExistentTable"})
    assert isinstance(result, dict)
    assert "error" in result
    assert "not found" in result["error"]


### Test get_business_rule

def test_get_business_rule_valid_keyword():
    result_vip = get_business_rule.invoke({"keyword": "VIP"})
    assert isinstance(result_vip, dict)
    assert all("vip" in k.lower() for k in result_vip.keys())
    assert len(result_vip) > 0

def test_get_business_rule_case_sensitivity():
    result_caps = get_business_rule.invoke({"keyword": "profit"})
    result_lower = get_business_rule.invoke({"keyword": "PROFIT"})
    assert result_caps == result_lower

def test_get_business_rule_invalid_keyword():
    result_empty = get_business_rule.invoke({"keyword": "non_existent_rule_xyz"})
    assert isinstance(result_empty, dict)
    assert len(result_empty) == 0


### Test execute_query

## Test 1: Successful query with data returned

def test_execute_query_returns_data():
    query = "SELECT product_id, name, price, category FROM Products LIMIT 1;"
    result = execute_query.invoke({"query": query})
    assert isinstance(result, str)
    assert "error" not in result
    assert "returned no results" not in result


## Test 2: Successful query with no data returned

def test_execute_query_returns_no_data():
    query = "SELECT customer_id FROM Orders WHERE order_id = -999;"
    result = execute_query.invoke({"query": query})
    assert "message" in result
    assert "returned no results" in result["message"]


## Test 3: Forbidden commands

@pytest.mark.parametrize("forbidden_query", [
    "DROP TABLE Orders;",
    "TRUNCATE TABLE Logs;",
    "DELETE FROM Products;"
    "UPDATE Customers SET name = 'Hacked';",
    "INSERT INTO Products (name) VALUES ('Ghost');",
    "ALTER TABLE Users ADD COLUMN password TEXT;",
])
def test_execute_query_forbidden_commands(forbidden_query):
    result = execute_query.invoke({"query": forbidden_query})
    assert isinstance(result, dict)
    assert "error" in result
    assert "Forbidden keyword detected" in result["error"]


## Test 4: Incorrect table or column name

def test_execute_query_incorrect_table():
    query = "SELECT customer_id FROM NonExistentTable"
    result = execute_query.invoke({"query": query})
    assert "error" in result
    assert "no such table" in result["error"]

def test_execute_query_incorrect_column():
    query = "SELECT NonExistentColumn FROM Customers"
    result = execute_query.invoke({"query": query})
    assert "error" in result
    assert "no such column" in result["error"]