#!/bin/bash

# RAG System Test Runner
# This script runs tests with warnings suppressed for cleaner output

echo "🧪 Running RAG System Tests..."
echo "================================"

# Set environment variable to suppress warnings
export PYTHONWARNINGS=ignore

# Run tests with clean output
if [ $# -eq 0 ]; then
    # Run all tests if no arguments provided
    echo "Running all tests..."
    python -m pytest tests/ -v --tb=short
else
    # Run specific tests if arguments provided
    echo "Running specific tests: $@"
    python -m pytest "$@" -v --tb=short
fi

echo "================================"
echo "✅ Test run completed!"