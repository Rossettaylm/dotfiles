from pyutils.git import get_branches_v2
from pyutils.shell import run_cmd_chain
from pyutils.git import git_log_cmd
import shlex


out = get_branches_v2("test", True)
if out:
    print(out)
else:
    print("err in get branches")
