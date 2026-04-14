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
    config = function(_, opts)
      opts.open_file_function = function(chosen_file)
        require("config.smart_open").open(chosen_file)
      end
      require("yazi").setup(opts)
    end,
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

  { -- Mini.ai: 增强文本对象 (函数参数、括号等)
    "echasnovski/mini.ai",
    event = "VeryLazy",
    dependencies = { "nvim-treesitter/nvim-treesitter-textobjects" },
    opts = function()
      local ai = require("mini.ai")
      return {
        custom_textobjects = {
          f = ai.gen_spec.treesitter({ a = "@function.outer", i = "@function.inner" }),
          c = ai.gen_spec.treesitter({ a = "@class.outer", i = "@class.inner" }),
        },
      }
    end,
  },

  { -- Grug-far: 全局搜索替换
    "MagicDuck/grug-far.nvim",
    cond = not vim.g.vscode,
    cmd = "GrugFar",
    keys = {
      { "<leader>rr", function() require("grug-far").open() end, desc = "Open grug-far (search & replace)" },
      { "<leader>rw", function() require("grug-far").open({ prefills = { search = vim.fn.expand("<cword>") } }) end, desc = "Search & replace current word" },
      { "<leader>rf", function() require("grug-far").open({ prefills = { paths = vim.fn.expand("%") } }) end, desc = "Search & replace in current file" },
      { "<leader>rw", function() require("grug-far").with_visual_selection() end, mode = "v", desc = "Search & replace visual selection" },
    },
    opts = {},
  },

  { -- Nvim-autopairs: 自动补全括号/引号
    "windwp/nvim-autopairs",
    cond = not vim.g.vscode,
    event = "InsertEnter",
    opts = {},
  },
}
