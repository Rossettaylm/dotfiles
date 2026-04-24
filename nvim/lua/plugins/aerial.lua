-- =============================================
-- 代码结构导航: aerial.nvim
-- =============================================
return {
  "stevearc/aerial.nvim",
  cond = not vim.g.vscode,
  cmd = { "AerialToggle", "AerialOpen", "AerialClose", "AerialNavToggle" },
  opts = {
    attach_mode = "window",
    close_on_select = true,
    backends = { "treesitter", "lsp", "markdown", "asciidoc", "man" },
    layout = {
      min_width = 28,
      default_direction = "prefer_right",
    },
    filter_kind = false,
    show_guides = true,
  },
}
