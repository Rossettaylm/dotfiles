-- =============================================
-- Options + Neovide + Diagnostic
-- =============================================

vim.o.number = true
vim.o.relativenumber = false
vim.o.mouse = "a"
vim.o.showmode = false
vim.o.clipboard = "unnamedplus"
if os.getenv("SSH_TTY") then
  local cached = {}
  local function make_copy(reg)
    -- 检测是否需要 tmux DCS 包裹（本地是 tmux 但 $TMUX 无法透过 SSH 传递，
    -- 用 NVIM_FORCE_TMUX_OSC52=1 在远程 shell 中手动标记）
    if os.getenv("TMUX") or os.getenv("NVIM_FORCE_TMUX_OSC52") == "1" then
      return function(lines)
        cached = lines
        local text = table.concat(lines, "\n")
        local b64 = vim.fn.system({ "base64" }, text):gsub("\n", "")
        -- DCS 包裹: ESC P tmux; ESC ESC ] 52 ; c ; <b64> BEL ESC \
        local seq = "\027Ptmux;\027\027]52;" .. reg .. ";" .. b64 .. "\007\027\\"
        io.write(seq)
        io.flush()
      end
    else
      local osc52 = require("vim.ui.clipboard.osc52")
      return osc52.copy(reg)
    end
  end
  vim.g.clipboard = {
    name = "OSC 52",
    copy = {
      ["+"] = make_copy("+"),
      ["*"] = make_copy("*"),
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
