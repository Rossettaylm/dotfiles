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
  { -- Preview markdown in browser
    "iamcco/markdown-preview.nvim",
    cond = not vim.g.vscode,
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = "markdown",
    build = "cd app && npm install",
    keys = {
      { "<leader>mp", "<cmd>MarkdownPreviewToggle<cr>", desc = "Markdown Preview" },
    },
  },
}
