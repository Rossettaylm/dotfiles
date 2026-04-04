-- =============================================
-- Custom Neovim Configuration
-- Based on kickstart.nvim structure
-- =============================================

-- Leader key (must be set before plugins load)
vim.g.mapleader = " "
vim.g.maplocalleader = " "
vim.g.have_nerd_font = true

-- Neovide (GUI) 配置 — 必须在最早期设置字体
if vim.g.neovide then
  vim.o.guifont = "CommitMono Nerd Font:h15"
  vim.g.neovide_opacity = 0.8
  vim.g.neovide_window_blurred = true
  vim.g.neovide_cursor_animation_length = 0.08
  vim.g.neovide_cursor_trail_size = 0.3
  vim.g.neovide_cursor_vfx_mode = "railgun"
  vim.g.neovide_scroll_animation_length = 0.2
end

-- =============================================
-- Options
-- =============================================
vim.o.number = true
vim.o.relativenumber = false
vim.o.mouse = "a"
vim.o.showmode = false
vim.schedule(function()
  vim.o.clipboard = "unnamedplus"
end)
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

-- =============================================
-- Keymaps
-- =============================================
local i_mode = { "i" }
local n_mode = { "n" }
local nv_mode = { "n", "x" }
local all_mode = { "n", "x", "i", "t" }

-- Shared keymaps (Neovim + VSCode)
local shared_keymap_table = {
  { from = "jj", to = "<esc>", mode = i_mode, desc = "Exit insert mode" },
  { from = "jk", to = "<esc>A", mode = i_mode, desc = "Jump to line tail in insert mode" },
  { from = ";", to = ":", mode = nv_mode, desc = "Call vim command" },
  { from = "(", to = "^", mode = nv_mode, desc = "Go to line head" },
  { from = ")", to = "$", mode = nv_mode, desc = "Go to line tail" },
  { from = "<S-j>", to = "7j", mode = nv_mode, desc = "Move down quickly" },
  { from = "<S-k>", to = "7k", mode = nv_mode, desc = "Move up quickly" },
  { from = "<S-h>", to = "7h", mode = nv_mode, desc = "Move left quickly" },
  { from = "<S-l>", to = "7l", mode = nv_mode, desc = "Move right quickly" },
  { from = "<", to = "<<", mode = nv_mode, desc = "Indent left" },
  { from = ">", to = ">>", mode = nv_mode, desc = "Indent right" },
}

for _, mapping in ipairs(shared_keymap_table) do
  vim.keymap.set(mapping.mode, mapping.from, mapping.to, { noremap = true, desc = mapping.desc })
end

-- Neovim-only keymaps
if not vim.g.vscode then
  -- Clear search highlight
  vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")
  vim.keymap.set("n", "<leader><cr>", "<cmd>nohl<cr>", { noremap = true, desc = "Clear search highlight" })

  -- Window navigation
  vim.keymap.set("n", "<C-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
  vim.keymap.set("n", "<C-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
  vim.keymap.set("n", "<C-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
  vim.keymap.set("n", "<C-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })

  -- Exit terminal mode (exclude yazi/toggleterm 等浮动终端工具)
  vim.keymap.set("t", "<Esc><Esc>", function()
    local ft = vim.bo.filetype
    if ft == "yazi" or ft == "toggleterm" then
      return "<Esc><Esc>"
    end
    return "<C-\\><C-n>"
  end, { expr = true, desc = "Exit terminal mode" })

  local nvim_keymap_table = {
    { from = "<C-q>", to = "<cmd>quitall!<cr>", mode = all_mode, desc = "Force quit all" },
    { from = "q", to = "<cmd>quit<cr>", mode = n_mode, desc = "Quit" },
    { from = "Q", to = "q", mode = n_mode, desc = "Macro mode" },
    { from = "<leader>sl", to = "<cmd>set splitright<cr><cmd>vsplit<cr>", mode = n_mode, desc = "Split right" },
    { from = "<leader>sj", to = "<cmd>set splitbelow<cr><cmd>split<cr>", mode = n_mode, desc = "Split below" },
    { from = "[[", to = "<C-o>", mode = n_mode, desc = "Go back" },
    { from = "]]", to = "<C-i>", mode = n_mode, desc = "Go forward" },
    { from = "ti", to = "<cmd>tabnew<cr>", mode = n_mode, desc = "New tab" },
    { from = "[b", to = "<cmd>tabprevious<cr>", mode = n_mode, desc = "Previous tab" },
    { from = "]b", to = "<cmd>tabnext<cr>", mode = n_mode, desc = "Next tab" },
    { from = "<leader>fl", to = ":r! figlet ", mode = n_mode, desc = "Import figlet title" },
  }

  for _, mapping in ipairs(nvim_keymap_table) do
    vim.keymap.set(mapping.mode, mapping.from, mapping.to, { noremap = true, desc = mapping.desc })
  end

  -- Force [[ and ]] on every buffer to prevent ftplugin overrides
  vim.api.nvim_create_autocmd("BufEnter", {
    group = vim.api.nvim_create_augroup("force-jump-keymaps", { clear = true }),
    callback = function(event)
      vim.keymap.set("n", "[[", "<C-o>", { buffer = event.buf, noremap = true, desc = "Go back" })
      vim.keymap.set("n", "]]", "<C-i>", { buffer = event.buf, noremap = true, desc = "Go forward" })
    end,
  })
end

-- =============================================
-- Diagnostic config
-- =============================================
vim.diagnostic.config({
  update_in_insert = false,
  severity_sort = true,
  float = { border = "rounded", source = "if_many" },
  underline = { severity = { min = vim.diagnostic.severity.WARN } },
  virtual_text = true,
  virtual_lines = false,
  jump = { float = true },
})

-- =============================================
-- Autocommands
-- =============================================
vim.api.nvim_create_autocmd("TextYankPost", {
  desc = "Highlight when yanking text",
  group = vim.api.nvim_create_augroup("highlight-yank", { clear = true }),
  callback = function()
    vim.hl.on_yank()
  end,
})

-- =============================================
-- Install lazy.nvim
-- =============================================
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local out = vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
  if vim.v.shell_error ~= 0 then
    error("Error cloning lazy.nvim:\n" .. out)
  end
end
vim.opt.rtp:prepend(lazypath)

-- =============================================
-- Setup plugins
-- =============================================
require("lazy").setup({
  { import = "plugins" },
}, {
  defaults = {
    lazy = false,
    version = false,
  },
  install = { colorscheme = { "tokyonight", "habamax" } },
  checker = {
    enabled = false,
  },
  performance = {
    rtp = {
      disabled_plugins = {
        "gzip",
        "tarPlugin",
        "tohtml",
        "tutor",
        "zipPlugin",
      },
    },
  },
})

-- =============================================
-- Conditional loading
-- =============================================
if vim.g.vscode then
  require("config.vscode")
else
  require("self-plugins")
end
