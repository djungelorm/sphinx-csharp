#!/bin/bash

pip install -e ../../
pip install -e ../../../breathe

doxygen
echo ""
echo "--- Running spinx-build ---"
sphinx-build -E . _build