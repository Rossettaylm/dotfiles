local F = {}

-- 递归拷贝table
local function clone(ob)
  local lookup_table = {}
  local function _copy(object)
    if type(object) ~= "table" then
      return object
    elseif lookup_table[object] then
      return lookup_table[object]
    end
    local new_table = {}
    lookup_table[object] = new_table
    for key, value in pairs(object) do
      new_table[_copy(key)] = _copy(value)
    end
    return setmetatable(new_table, getmetatable(object))
  end
  return _copy(ob)
end

F.configureKeybinds = function()
  vim.api.nvim_create_autocmd("LspAttach", {
    desc = "LSP actions",
    callback = function(event)
      local default_opts = { buffer = event.buf, noremap = true, nowait = true, desc = "" }
      local function opts_with_desc(description)
        local opts = clone(default_opts)
        opts["desc"] = description
        return opts
      end

      vim.keymap.set("n", "gd", vim.lsp.buf.definition, default_opts)
      vim.keymap.set("n", "gD", ":tab sp<CR><cmd>lua vim.lsp.buf.definition()<cr>", default_opts)
      vim.keymap.set("n", "gi", vim.lsp.buf.implementation, default_opts)
      vim.keymap.set("n", "go", vim.lsp.buf.type_definition, default_opts)
      vim.keymap.set("n", "gu", vim.lsp.buf.references, default_opts)
      vim.keymap.set("n", "gh", vim.lsp.buf.hover, opts_with_desc("show hover documentation"))
      vim.keymap.set("i", "<c-f>", vim.lsp.buf.signature_help, default_opts)
      vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, default_opts)
      -- vim.keymap.set({ 'n', 'x' }, '<leader>f', function() vim.lsp.buf.format({ async = true }) end, opts)
      vim.keymap.set("n", "<C-.>", vim.lsp.buf.code_action, default_opts)
      -- vim.keymap.set('x', '<leader>aw', vim.lsp.buf.range_code_action, opts)
      -- vim.keymap.set('x', "<leader>,", vim.lsp.buf.range_code_action, opts)
      vim.keymap.set("n", "<leader>t", ":Trouble<cr>", default_opts)
      vim.keymap.set("n", "gp", vim.diagnostic.goto_prev, default_opts)
      vim.keymap.set("n", "ge", vim.diagnostic.goto_next, default_opts)
    end,
  })
end

return {
  {
    "neovim/nvim-lspconfig",
    init = function()
      local keys = require("lazyvim.plugins.lsp.keymaps").get()
      -- disable keymaps
      keys[#keys + 1] = { "K", false }
      F.configureKeybinds()
    end,

    diagnostics = {
      underline = true,
      update_in_insert = false,
      virtual_text = {
        spacing = 4,
        source = "if_many",
        prefix = "●",
        -- this will set set the prefix to a function that returns the diagnostics icon based on the severity
        -- this only works on a recent 0.10.0 build. Will be set to "●" when not supported
        -- prefix = "icons",
      },
      severity_sort = true,
      signs = {
        text = {
          [vim.diagnostic.severity.ERROR] = LazyVim.config.icons.diagnostics.Error,
          [vim.diagnostic.severity.WARN] = LazyVim.config.icons.diagnostics.Warn,
          [vim.diagnostic.severity.HINT] = LazyVim.config.icons.diagnostics.Hint,
          [vim.diagnostic.severity.INFO] = LazyVim.config.icons.diagnostics.Info,
        },
      },
    },
    -- Enable this to enable the builtin LSP inlay hints on Neovim >= 0.10.0
    -- Be aware that you also will need to properly configure your LSP server to
    -- provide the inlay hints.
    inlay_hints = {
      enabled = true,
      exclude = {}, -- filetypes for which you don't want to enable inlay hints
    },

    opts = {
      servers = {
        -- Ensure mason installs the server
        lua_ls = {},
        bashls = {},
        clangd = {
          keys = {
            { "<F4>", "<cmd>ClangdSwitchSourceHeader<cr>", desc = "Switch Source/Header (C/C++)" },
          },
          root_dir = function(fname)
            return require("lspconfig.util").root_pattern(
              "Makefile",
              "configure.ac",
              "configure.in",
              "config.h.in",
              "meson.build",
              "meson_options.txt",
              "build.ninja"
            )(fname) or require("lspconfig.util").root_pattern("compile_commands.json", "compile_flags.txt")(
              fname
            ) or require("lspconfig.util").find_git_ancestor(fname)
          end,
          capabilities = {
            offsetEncoding = { "utf-8" },
          },
          cmd = {
            "clangd",
            "--background-index",
            "--clang-tidy",
            "--header-insertion=iwyu",
            "--completion-style=detailed",
            "--function-arg-placeholders",
            "--fallback-style=llvm",
          },
          init_options = {
            usePlaceholders = true,
            completeUnimported = true,
            clangdFileStatus = true,
          },
        },

        pyright = {},

        neocmake = {
          cmd = {
            "neocmakelsp",
            "--stdio",
          },
          filetypes = { "cmake" },
          root_dir = function(fname)
            require("lspconfig.util").find_git_ancestor(fname)
          end,
          single_file_support = true,
          on_attach = function() end,
          init_options = {
            format = {
              enable = true,
            },
            lint = {
              enable = true,
            },
            scan_cmake_in_package = true,
          },
        },
      },
      setup = {
        clangd = function(_, opts)
          local clangd_ext_opts = LazyVim.opts("clangd_extensions.nvim")
          require("clangd_extensions").setup(vim.tbl_deep_extend("force", clangd_ext_opts or {}, { server = opts }))
          return false
        end,
      },
    },
  },
}
