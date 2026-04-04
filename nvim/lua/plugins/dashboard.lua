-- =============================================
-- 启动页: dashboard-nvim
-- =============================================
return {
  "nvimdev/dashboard-nvim",
  cond = not vim.g.vscode,
  event = "VimEnter",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  opts = function()
    local version = vim.version()
    local nvim_version = string.format("Neovim v%d.%d.%d", version.major, version.minor, version.patch)
    return {
      theme = "hyper",
      shortcut_type = "number",
      config = {
        week_header = { enable = true },
        shortcut = {
          { icon = " ", desc = "Files", group = "@property", key = "f", action = "FzfLua files" },
          { icon = " ", desc = "Recent", group = "Number", key = "r", action = "FzfLua oldfiles" },
          { icon = " ", desc = "Grep", group = "DiagnosticHint", key = "g", action = "FzfLua live_grep" },
          { icon = " ", desc = "Config", group = "Constant", key = "c", action = "FzfLua files cwd=~/.config/nvim" },
          { icon = " ", desc = "Lazy", group = "@property", key = "p", action = "Lazy" },
          { icon = " ", desc = "Quit", group = "Error", key = "q", action = "qa" },
        },
        mru = { limit = 8, icon = " ", label = "Recent Files", cwd_only = false },
        project = { enable = true, limit = 5, icon = " ", label = "Recent Projects", action = "FzfLua files cwd=" },
        footer = { "", nvim_version },
	vertical_center = true,
      },
    }
  end,
}
