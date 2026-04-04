-- =============================================
-- Git 集成: gitsigns (侧边栏变更标记)
-- =============================================
return {
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
  },
}
