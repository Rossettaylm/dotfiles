-- =============================================
-- 主题配色: catppuccin (mocha)
-- =============================================
return {
  "catppuccin/nvim",
  name = "catppuccin",
  lazy = false,
  priority = 1000,
  config = function()
    require("catppuccin").setup({
      flavour = "mocha",
      transparent_background = true,
      no_italic = true,
      custom_highlights = function(colors)
        return {
          LineNr = { bg = "NONE" },
          CursorLineNr = { bg = "NONE" },
          SignColumn = { bg = "NONE" },
          FoldColumn = { bg = "NONE" },
          GitSignsAdd = { fg = colors.green, bg = "NONE" },
          GitSignsChange = { fg = colors.yellow, bg = "NONE" },
          GitSignsDelete = { fg = colors.red, bg = "NONE" },
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
    vim.cmd.colorscheme("catppuccin-mocha")
  end,
}
