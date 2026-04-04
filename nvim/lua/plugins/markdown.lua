-- =============================================
-- Markdown 支持: 浏览器预览 + buffer 内渲染
-- =============================================
return {
  { -- Render markdown in buffer (headings, code blocks, links)
    "MeanderingProgrammer/render-markdown.nvim",
    cond = not vim.g.vscode,
    ft = "markdown",
    dependencies = {
      "nvim-treesitter/nvim-treesitter",
      "nvim-tree/nvim-web-devicons",
    },
    opts = {},
  },
}
