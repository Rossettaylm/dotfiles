return {
  {
    "stevearc/conform.nvim",
    dependencies = { "mason.nvim" },
    lazy = true,
    cmd = "ConformInfo",
    init = function()
      -- Install the conform formatter on VeryLazy
      LazyVim.on_very_lazy(function()
        LazyVim.format.register({
          name = "conform.nvim",
          priority = 100,
          primary = true,
          format = function(buf)
            require("conform").format({ bufnr = buf })
          end,
          sources = function(buf)
            local ret = require("conform").list_formatters(buf)
            ---@param v conform.FormatterInfo
            return vim.tbl_map(function(v)
              return v.name
            end, ret)
          end,
        })
      end)
    end,

    opts = function()
      local opts = {
        default_format_opts = {
          async = false,
          quiet = false,
          lsp_format = "fallback",
          format_after_save = true,
        },

        formatters_by_ft = {
          lua = { "stylua" },
          sh = { "shfmt" },
          python = { "black" },
          cpp = { "clang-format" },
          kotlin = { "ktfmt" },
        },

        formatter = {
          "ast_grep",
        },
      }

      return opts
    end,
  },
}
