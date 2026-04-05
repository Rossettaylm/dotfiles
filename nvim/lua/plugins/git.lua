-- =============================================
-- Git 集成: gitsigns (侧边栏变更标记), diffview (diff 和冲突解决)
-- =============================================
return {
  { -- Gitsigns: 侧边栏变更标记
    "lewis6991/gitsigns.nvim",
    cond = not vim.g.vscode,
    opts = {
      signs = {
        add = { text = "+" },
        change = { text = "~" },
        delete = { text = "_" },
        topdelete = { text = "‾" },
        changedelete = { text = "~" },
      },
      current_line_blame = true,
      current_line_blame_opts = {
        delay = 300,
        virt_text_pos = "eol",
      },
    },
    keys = {
      { "<leader>gb", "<cmd>Gitsigns toggle_current_line_blame<cr>", desc = "Toggle git blame" },
    },
  },

  { -- Diffview: diff 查看和 merge 冲突解决
    "sindrets/diffview.nvim",
    cond = not vim.g.vscode,
    cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewFileHistory" },
    keys = {
      { "<leader>gd", "<cmd>DiffviewOpen<cr>", desc = "Git diff view" },
      { "<leader>gh", "<cmd>DiffviewFileHistory %<cr>", desc = "Git file history" },
      { "<leader>gH", "<cmd>DiffviewFileHistory<cr>", desc = "Git branch history" },
      { "<leader>gc", "<cmd>DiffviewClose<cr>", desc = "Close diff view" },
    },
    opts = {},
  },

  { -- Lazygit: 在 Neovim 中打开 lazygit
    "kdheepak/lazygit.nvim",
    cond = not vim.g.vscode,
    cmd = { "LazyGit", "LazyGitConfig", "LazyGitCurrentFile", "LazyGitFilter", "LazyGitFilterCurrentFile" },
    dependencies = { "nvim-lua/plenary.nvim" },
    keys = {
      { "<leader>gg", "<cmd>LazyGit<cr>", desc = "Open LazyGit" },
    },
  },
}
