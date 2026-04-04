-- =============================================
-- 自动补全与代码片段: blink.cmp + LuaSnip
-- Tab/S-Tab 选择, Enter 确认
-- =============================================
return {
  "saghen/blink.cmp",
  cond = not vim.g.vscode,
  event = "VimEnter",
  version = "1.*",
  dependencies = {
    {
      "L3MON4D3/LuaSnip",
      version = "2.*",
      build = (function()
        if vim.fn.has("win32") == 1 or vim.fn.executable("make") == 0 then
          return
        end
        return "make install_jsregexp"
      end)(),
      opts = {},
    },
  },
  ---@module 'blink.cmp'
  ---@type blink.cmp.Config
  opts = {
    keymap = {
      preset = "enter",
      ["<Tab>"] = { "select_next", "snippet_forward", "fallback" },
      ["<S-Tab>"] = { "select_prev", "snippet_backward", "fallback" },
    },
    appearance = {
      nerd_font_variant = "mono",
    },
    completion = {
      documentation = { auto_show = true, auto_show_delay_ms = 300 },
    },
    sources = {
      default = { "lsp", "path", "snippets" },
    },
    snippets = { preset = "luasnip" },
    fuzzy = { implementation = "lua" },
    signature = { enabled = true },
  },
}
