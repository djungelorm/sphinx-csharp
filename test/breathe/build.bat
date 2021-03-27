pip install ../../

doxygen
echo
echo --- Running spinx-build ---
python -m sphinx -E . _build