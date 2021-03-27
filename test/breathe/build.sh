#!/bin/bash

pip install ../../

doxygen
echo ""
echo "--- Running spinx-build ---"
sphinx-build . _build