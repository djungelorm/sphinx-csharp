#!/bin/bash

pip install -e ../../

doxygen
echo ""
echo "--- Running spinx-build ---"
sphinx-build -E . _build