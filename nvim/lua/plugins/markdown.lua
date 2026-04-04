-- =============================================
-- Markdown 支持: 浏览器预览 + buffer 内渲染
-- =============================================
return {
  { -- Markdown preview in browser
    "iamcco/markdown-preview.nvim",
    cond = not vim.g.vscode,
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = "markdown",
    build = "cd app && npm install",
    config = function()
      vim.api.nvim_create_autocmd("FileType", {
        pattern = "markdown",
        callback = function(event)
          vim.keymap.set("n", "<leader>mp", "<cmd>MarkdownPreviewToggle<cr>", { buffer = event.buf, desc = "Markdown preview" })
        end,
      })
    end,
  },

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
