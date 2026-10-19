""" Run the tests in every hatch test environment in parallel, and summarize the results """

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / 'test-output'


def environments(python: str | None) -> list[str]:
    """ The names of the test environments, such as test.py3.12-9.1-5.1, optionally for one Python """
    output = subprocess.run(['hatch', 'env', 'show', '--json'], cwd=ROOT, check=True, capture_output=True, text=True)
    names = [name for name in json.loads(output.stdout) if name.startswith('test.')]
    if python:
        names = [name for name in names if name.startswith(f'test.py{python}-')]
    return names


def run(name: str, args: list[str]) -> tuple[str, bool, str, float]:
    """ Run the tests in one environment, and return whether they passed and the last line of the output """
    start = time.monotonic()
    log = LOGS / f'{name}.log'
    # Each environment has its own pytest temporary directory, as pytest removes old ones from a shared directory
    temp = LOGS / 'tmp' / name
    temp.mkdir(parents=True, exist_ok=True)
    with log.open('w') as file:
        # Note: The cache provider writes to one directory, which parallel runs share.
        result = subprocess.run(['hatch', 'run', f'{name}:all', '-p', 'no:cacheprovider', *args], cwd=ROOT,
                                stdout=file, stderr=subprocess.STDOUT, check=False,
                                env={**os.environ, 'PYTEST_DEBUG_TEMPROOT': str(temp)})
    lines = [line for line in log.read_text().splitlines() if line.strip()]
    return name, result.returncode == 0, lines[-1].strip('= ') if lines else '', time.monotonic() - start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', help='only the environments for this Python, such as 3.12')
    parser.add_argument('--jobs', type=int, default=os.cpu_count(), help='the number of environments to run at once')
    parser.add_argument('args', nargs='*', help='arguments for pytest')
    options = parser.parse_args()

    names = environments(options.python)
    if not names:
        print(f'no test environments for Python {options.python}')
        return 1
    LOGS.mkdir(exist_ok=True)
    failed = []
    with ThreadPoolExecutor(options.jobs) as executor:
        for name, passed, summary, seconds in executor.map(lambda name: run(name, options.args), names):
            print(f'{"PASS" if passed else "FAIL"} {name} ({seconds:.0f}s): {summary}', flush=True)
            if not passed:
                failed.append(name)

    print(f'\n{len(names) - len(failed)} of {len(names)} environments passed. Logs are in {LOGS.relative_to(ROOT)}.')
    # The end of each failing log, which has the failures and the coverage report
    for name in failed:
        print(f'\n{name}:\n' + '\n'.join((LOGS / f'{name}.log').read_text().splitlines()[-40:]))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
