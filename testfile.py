#!/usr/bin/env python3
"""
This is a sample test file for file upload/download testing.
"""

class TestClass:
    def __init__(self, name):
        self.name = name
        
    def greet(self):
        return f"Hello from {self.name}!"
        
    def __str__(self):
        return f"TestClass instance: {self.name}"

if __name__ == "__main__":
    # Simple test output when the file is executed directly
    test_obj = TestClass("TestFile")
    print(test_obj.greet())
    print(f"This file can be used for testing file uploads and downloads.")
    print(f"File information: {__file__}")