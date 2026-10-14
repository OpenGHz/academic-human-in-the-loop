"""Run the whole suite under a throwaway $HOME.

Several tests run the real installers, which write the global pointer
`$HOME/.aris/repo` by design. Without this, a test run repoints a developer's
existing ARIS install at the clone under test, or at a temp directory that is
gone a moment later (#449). Set at import time so subprocesses inherit it.
"""
import atexit
import os
import shutil
import tempfile

_home = tempfile.mkdtemp(prefix="aris-test-home-")
os.environ["HOME"] = _home
os.environ["USERPROFILE"] = _home
atexit.register(shutil.rmtree, _home, ignore_errors=True)

# Local mock servers listen on 127.0.0.1. With http(s)_proxy set in the shell,
# urllib routes those requests through the proxy, which answers 502. Exempt
# loopback so the suite passes behind a proxy; subprocesses inherit this too.
_loopback = ["127.0.0.1", "localhost", "::1"]
for _var in ("NO_PROXY", "no_proxy"):
    _hosts = [h for h in os.environ.get(_var, "").split(",") if h.strip()]
    os.environ[_var] = ",".join(_hosts + [h for h in _loopback if h not in _hosts])
