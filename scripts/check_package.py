""" Build the sdist and wheel into dist/, check them, and build the basic project with the wheel installed """

import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'


def main() -> int:
    # Note: hatch build takes the active environment as its builder, so it runs outside the package environment.
    env = {name: value for name, value in os.environ.items() if name != 'HATCH_ENV_ACTIVE'}
    subprocess.run(['hatch', 'build', '--clean'], cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, '-m', 'twine', 'check', '--strict', *map(str, DIST.iterdir())], check=True)

    # Every module, the py.typed marker and the stylesheet
    wheel = next(DIST.glob('*.whl'))
    expected = {f'sphinx_csharp/{path.name}' for path in (ROOT / 'sphinx_csharp').iterdir()
                if path.suffix == '.py' or path.name == 'py.typed'} | {'sphinx_csharp/static/sphinx_csharp.css'}
    missing = sorted(expected - set(zipfile.ZipFile(wheel).namelist()))
    if missing:
        print(f'{wheel.name} leaves out {", ".join(missing)}')
        return 1

    # Note: The build runs outside the repository, so it imports the package from the wheel.
    with tempfile.TemporaryDirectory() as temp:
        venv_dir = Path(temp) / 'venv'
        venv.create(venv_dir, with_pip=True)
        bin_dir = venv_dir / ('Scripts' if sys.platform == 'win32' else 'bin')
        subprocess.run([bin_dir / 'pip', 'install', '--quiet', '--disable-pip-version-check', wheel], check=True)
        source = ROOT / 'tests' / 'roots' / 'test-basic'
        subprocess.run([bin_dir / 'sphinx-build', '-W', '-n', '-q', '-b', 'html', source, 'html'], cwd=temp, check=True)
    print(f'{wheel.name} and its sdist pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
