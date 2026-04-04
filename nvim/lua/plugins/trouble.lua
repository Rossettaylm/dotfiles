-- =============================================
-- 诊断面板: trouble.nvim (<leader>t 切换)
-- =============================================
return {
  "folke/trouble.nvim",
  cond = not vim.g.vscode,
  cmd = "Trouble",
  keys = {
    { "<leader>t", "<cmd>Trouble diagnostics toggle<cr>", desc = "Diagnostics (Trouble)" },
  },
  opts = {},
}
