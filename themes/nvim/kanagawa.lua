-- =============================================
-- 主题配色: kanagawa
-- =============================================
return {
  "rebelot/kanagawa.nvim",
  name = "kanagawa",
  lazy = false,
  priority = 1000,
  config = function()
    require("kanagawa").setup({
      transparent = true,
      theme = "wave",
      overrides = function(colors)
        return {
          LineNr = { bg = "NONE" },
          CursorLineNr = { bg = "NONE" },
          SignColumn = { bg = "NONE" },
          FoldColumn = { bg = "NONE" },
          GitSignsAdd = { fg = colors.palette.autumnGreen, bg = "NONE" },
          GitSignsChange = { fg = colors.palette.autumnYellow, bg = "NONE" },
          GitSignsDelete = { fg = colors.palette.autumnRed, bg = "NONE" },
          DiagnosticSignError = { bg = "NONE" },
          DiagnosticSignWarn = { bg = "NONE" },
          DiagnosticSignInfo = { bg = "NONE" },
          DiagnosticSignHint = { bg = "NONE" },
          TabLine = { bg = "NONE" },
          TabLineFill = { bg = "NONE" },
          TabLineSel = { bg = "NONE", bold = true },
        }
      end,
    })
    vim.cmd.colorscheme("kanagawa-wave")
  end,
}
