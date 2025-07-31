-- plugins
require("git"):setup()

require("yamb"):setup({
	cli = "fzf",
})

-- require("yaziline"):setup({
-- 	-- Optinal config
-- 	color = "#A1C178",
-- 	separator_style = "angly", -- preconfigured style
-- 	separator_open = "", -- instead of 
-- 	separator_close = "", -- instead of 
-- 	separator_open_thin = "", -- change to anything
-- 	separator_close_thin = "", -- change to anything
-- 	separator_head = "", -- to match the style
-- 	separator_tail = "", -- to match the style
-- })

-- require("restore"):setup({
-- 	-- Set the position for confirm and overwrite dialogs.
-- 	-- don't forget to set height: `h = xx`
-- 	-- https://yazi-rs.github.io/docs/plugins/utils/#ya.input
-- 	position = { "center", w = 70, h = 40 },
--
-- 	-- Show confirm dialog before restore.
-- 	-- NOTE: even if set this to false, overwrite dialog still pop up
-- 	show_confirm = true,
--
-- 	-- colors for confirm and overwrite dialogs
-- 	theme = {
-- 		title = "blue",
-- 		header = "green",
-- 		-- header color for overwrite dialog
-- 		header_warning = "yellow",
-- 		list_item = { odd = "blue", even = "blue" },
-- 	},
-- })
