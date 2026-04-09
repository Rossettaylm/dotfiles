-- plugins
-- ~/.config/yazi/init.lua
require("git"):setup()

require("yamb"):setup({
	cli = "fzf",
})

require("sftp-fzf"):setup({
	cli = "fzf",
})
