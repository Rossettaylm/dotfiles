from pyutils.git import get_branches, get_branches_v2
from pyutils.shell import run_cmd_chain
from pyutils.git import git_log_cmd
from pyutils.git import git_branch_fzf_preview_opt

value = git_branch_fzf_preview_opt()
print(value)
branch = get_branches("", True)
for item in branch.branch_list:
    print(item)
