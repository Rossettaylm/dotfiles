-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here
--

local i_mode = { "i" }
local n_mode = { "n" }
local nv_mode = { "n", "x" }
local all_mode = { "n", "x", "i", "t" }

local keymap_table = {
  { from = "jj", to = "<esc>", mode = i_mode, desc = "Exit insert Mode" },
  { from = "jk", to = "<esc>A", mode = i_mode, desc = "Jump to line tail in insert mode" },
  { from = ";", to = ":", mode = nv_mode, desc = "Call vim command" },
  { from = "<C-q>", to = "<cmd>quitall!<cr>", mode = all_mode, desc = "Force to quit all" },
  { from = "q", to = "<cmd>quit<cr>", mode = n_mode, desc = "Quit" },
  { from = "Q", to = "q", mode = n_mode, desc = "Macro mode" },
  { from = "(", to = "^", mode = nv_mode, desc = "Go to line head" },
  { from = ")", to = "$", mode = nv_mode, desc = "Go to line tail" },
  { from = "<leader>sl", to = "<cmd>set splitright<cr><cmd>vsplit<cr>", mode = n_mode, desc = "Split right" },
  { from = "<leader>sj", to = "<cmd>set splitbelow<cr><cmd>split<cr>", mode = n_mode, desc = "Split below" },

  { from = "<S-j>", to = "7j", mode = nv_mode, desc = "Move down quickly" },
  { from = "<S-k>", to = "7k", mode = nv_mode, desc = "Move up quickly" },
  { from = "<S-h>", to = "7h", mode = nv_mode, desc = "Move left quickly" },
  { from = "<S-l>", to = "7l", mode = nv_mode, desc = "Move right quickly" },

  { from = "<leader><cr>", to = "<cmd>nohl<cr>", mode = n_mode, "Set no highlight" },
  { from = "[[", to = "<C-o>", mode = n_mode, "Go back" },
  { from = "]]", to = "<C-i>", mode = n_mode, "Go front" },
  { from = "<", to = "<<", mode = nv_mode, "Indent left" },
  { from = ">", to = ">>", mode = nv_mode, "Indent right" },

  -- fzflua
  { from = "<leader>pa", to = "<cmd>FzfLua commands<cr>", mode = n_mode, desc = "fzflua commands" },
  {
    from = "<leader>o",
    to = "<cmd>FzfLua lsp_document_symbols<cr>",
    mode = n_mode,
    desc = "fzflua documention symbols",
  },

  -- figlet
  { from = "<leader>fl", to = ":r! figlet ", mode = n_mode, desc = "import figlet title" },
}

for _, mapping in ipairs(keymap_table) do
  vim.keymap.set(mapping.mode, mapping.from, mapping.to, { noremap = true, desc = mapping.desc })
end
