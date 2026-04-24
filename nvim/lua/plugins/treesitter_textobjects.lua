-- =============================================
-- Treesitter 文本对象: nvim-treesitter-textobjects
-- =============================================
return {
  "nvim-treesitter/nvim-treesitter-textobjects",
  cond = not vim.g.vscode,
  lazy = true,
}
