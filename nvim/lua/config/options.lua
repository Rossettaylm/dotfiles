-- =============================================
-- Options + Neovide + Diagnostic
-- =============================================

vim.o.number = true
vim.o.relativenumber = false
vim.o.mouse = "a"
vim.o.showmode = false
vim.o.clipboard = "unnamedplus"
if os.getenv("SSH_TTY") then
  local osc52 = require("vim.ui.clipboard.osc52")
  local cached = {}
  vim.g.clipboard = {
    name = "OSC 52",
    copy = {
      ["+"] = function(lines)
        cached = lines
        osc52.copy("+")(lines)
      end,
      ["*"] = function(lines)
        cached = lines
        osc52.copy("*")(lines)
      end,
    },
    paste = {
      ["+"] = function() return cached end,
      ["*"] = function() return cached end,
    },
  }
end
vim.o.breakindent = true
vim.o.undofile = true
vim.o.ignorecase = true
vim.o.smartcase = true
vim.o.signcolumn = "yes"
vim.o.updatetime = 250
vim.o.timeoutlen = 300
vim.o.splitright = true
vim.o.splitbelow = true
vim.o.list = true
vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
vim.o.inccommand = "split"
vim.o.cursorline = true
vim.o.scrolloff = 10
vim.o.confirm = true
vim.o.wrap = true
vim.o.autochdir = true
vim.o.termguicolors = true
vim.o.expandtab = true
vim.o.tabstop = 2
vim.o.shiftwidth = 2
vim.o.softtabstop = 2

vim.diagnostic.config({
  update_in_insert = false,
  severity_sort = true,
  float = { border = "rounded", source = "if_many" },
  underline = { severity = { min = vim.diagnostic.severity.WARN } },
  virtual_text = true,
  virtual_lines = false,
  jump = { float = true },
})
