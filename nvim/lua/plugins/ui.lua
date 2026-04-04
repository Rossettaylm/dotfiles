-- =============================================
-- 界面增强: which-key, lualine, bufferline, nvim-notify, indent-blankline
-- =============================================
return {
  { -- Which-key: 快捷键提示面板
    "folke/which-key.nvim",
    event = "VimEnter",
    opts = {
      delay = 0,
      icons = { mappings = vim.g.have_nerd_font },
      spec = {
        { "<leader>s", group = "Search", icon = " " },
        { "<leader>c", group = "Code" },
        { "<leader>r", group = "Rename" },
        { "<leader>p", group = "Commands" },
        { "<leader>f", group = "Figlet/Find" },
        { "<leader>t", group = "Toggle/Trouble" },
        { "g", group = "Goto" },
        { "[", group = "Prev" },
        { "]", group = "Next" },
        { "<leader>m", group = "Messages" },
        { "<leader>g", group = "Git" },
      },
    },
    keys = {
      {
        "<leader>?",
        function()
          require("which-key").show({ global = true })
        end,
        desc = "Show all keymaps (which-key)",
      },
    },
  },

  { -- Lualine: 底部状态栏
    "nvim-lualine/lualine.nvim",
    cond = not vim.g.vscode,
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {},
  },

  { -- Bufferline: 顶部 tab 栏
    "akinsho/bufferline.nvim",
    cond = not vim.g.vscode,
    dependencies = { "nvim-tree/nvim-web-devicons" },
    event = "VeryLazy",
    opts = {
      options = {
        mode = "tabs",
        separator_style = "slant",
        show_buffer_close_icons = false,
        show_close_icon = false,
        diagnostics = "nvim_lsp",
        always_show_bufferline = false,
      },
    },
  },

  { -- Nvim-notify: 通知弹窗美化
    "rcarriga/nvim-notify",
    cond = not vim.g.vscode,
    config = function(_, opts)
      local notify = require("notify")
      notify.setup(opts)
      -- 设为默认通知后端
      vim.notify = notify

      -- <leader>mm  打开通知历史（可复制的 buffer）
      vim.keymap.set("n", "<leader>mm", function()
        local history = notify.history()
        if #history == 0 then
          vim.notify("No notification history")
          return
        end
        local lines = {}
        for i, item in ipairs(history) do
          if i > 1 then
            table.insert(lines, string.rep("─", 60))
          end
          table.insert(lines, string.format("[%s] %s", item.level, item.title and table.concat(item.title, " ") or ""))
          local msg = type(item.message) == "table" and table.concat(item.message, "\n") or tostring(item.message or "")
          for line in msg:gmatch("[^\n]+") do
            table.insert(lines, line)
          end
        end
        vim.cmd("botright new")
        local buf = vim.api.nvim_get_current_buf()
        vim.bo[buf].buftype = "nofile"
        vim.bo[buf].bufhidden = "wipe"
        vim.bo[buf].filetype = "notify_history"
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
        vim.bo[buf].modifiable = false
      end, { desc = "Notification history" })

      -- <leader>my  复制最后一条通知到剪贴板
      vim.keymap.set("n", "<leader>my", function()
        local history = notify.history()
        if #history > 0 then
          local msg = type(history[#history].message) == "table" and table.concat(history[#history].message, "\n") or tostring(history[#history].message or "")
          vim.fn.setreg("+", msg)
          print("Copied last notification to clipboard")
        else
          print("No notification to copy")
        end
      end, { desc = "Yank last notification" })

      -- <leader>md  关闭所有通知
      vim.keymap.set("n", "<leader>md", function()
        notify.dismiss({ silent = true, pending = true })
      end, { desc = "Dismiss notifications" })
    end,
    opts = {
      timeout = 5000,
      max_width = 80,
      render = "wrapped-compact",
      stages = "fade",
    },
  },

  { -- Indent-blankline: 缩进参考线
    "lukas-reineke/indent-blankline.nvim",
    cond = not vim.g.vscode,
    main = "ibl",
    event = "VeryLazy",
    opts = {
      indent = { char = "│" },
      scope = { enabled = true },
      exclude = { filetypes = { "dashboard" } },
    },
  },
}
