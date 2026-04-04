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
    { from = "<C-q>", to = "<cmd>quitall<cr>", mode = all_mode, desc = "Quit all" },
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
end
