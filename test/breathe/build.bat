pip install -e ../../
pip install -e ../../../breathe

doxygen
echo
echo --- Running spinx-build ---
python -m sphinx -E . _build