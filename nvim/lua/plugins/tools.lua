-- =============================================
-- 工具集成: yazi (文件管理器), toggleterm (浮动终端)
-- =============================================
return {
  { -- Yazi: 终端文件管理器
    "mikavilpas/yazi.nvim",
    cond = not vim.g.vscode,
    event = "VeryLazy",
    keys = {
      { "<S-r>", "<cmd>Yazi<cr>", desc = "Open yazi at the current file" },
      { "<c-up>", "<cmd>Yazi toggle<cr>", desc = "Resume the last yazi session" },
    },
    opts = {
      open_for_directories = false,
      keymaps = {
        show_help = "<f1>",
      },
    },
  },

  { -- ToggleTerm: 浮动终端 (Ctrl+` 切换)
    "akinsho/toggleterm.nvim",
    cond = not vim.g.vscode,
    keys = {
      { "<C-`>", desc = "Toggle terminal" },
      { "<C-`>", "<C-\\><C-n><cmd>ToggleTerm<cr>", mode = "t", desc = "Toggle terminal" },
    },
    opts = {
      open_mapping = "<C-`>",
      direction = "float",
      float_opts = {
        border = "rounded",
        width = function()
          return math.floor(vim.o.columns * 0.8)
        end,
        height = function()
          return math.floor(vim.o.lines * 0.8)
        end,
        winblend = 8,
      },
      highlights = {
        FloatBorder = { link = "FloatBorder" },
      },
      shade_terminals = false,
    },
  },
}
