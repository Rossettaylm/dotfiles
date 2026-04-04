-- =============================================
-- 工具集成: yazi, toggleterm, flash, nvim-surround, todo-comments
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

  { -- Flash: 快速跳转 (s 触发)
    "folke/flash.nvim",
    cond = not vim.g.vscode,
    event = "VeryLazy",
    opts = {},
    keys = {
      { "s", mode = { "n", "x", "o" }, function() require("flash").jump() end, desc = "Flash jump" },
      { "S", mode = { "n", "x", "o" }, function() require("flash").treesitter() end, desc = "Flash treesitter" },
      { "<c-s>", mode = "c", function() require("flash").toggle() end, desc = "Toggle Flash search" },
    },
  },

  { -- Nvim-surround: 快速操作包围符号 (ys/cs/ds)
    "kylechui/nvim-surround",
    event = "VeryLazy",
    opts = {},
  },

  { -- Todo-comments: 高亮 TODO/FIXME/HACK 注释
    "folke/todo-comments.nvim",
    cond = not vim.g.vscode,
    event = "VeryLazy",
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {},
  },
}
