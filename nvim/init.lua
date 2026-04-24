-- =============================================
-- Custom Neovim Configuration
-- =============================================

-- Leader key (must be set before plugins load)
vim.g.mapleader = " "
vim.g.maplocalleader = " "
vim.g.have_nerd_font = true

require("config.options")
require("config.keymaps")
require("config.autocmds")
require("config.nav_mode").setup()
require("config.lazy")

-- Conditional loading
if vim.g.vscode then
  require("config.vscode")
end
