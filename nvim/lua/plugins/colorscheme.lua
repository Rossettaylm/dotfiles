-- =============================================
-- 主题配色: kanagawa (wave/dragon/lotus)
-- =============================================
return {
  "rebelot/kanagawa.nvim",
  priority = 1000,
  config = function()
    require("kanagawa").setup({
      commentStyle = { italic = false },
      keywordStyle = { italic = false },
    })
    vim.cmd.colorscheme("kanagawa-wave")
  end,
}
