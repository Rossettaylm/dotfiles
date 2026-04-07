-- =============================================
-- 语言服务器: lspconfig + mason + fidget
-- 添加新语言: 在 servers 表中增加对应 LSP 配置即可
-- =============================================
return {
  "neovim/nvim-lspconfig",
  cond = not vim.g.vscode,
  dependencies = {
    { "mason-org/mason.nvim", opts = {} },
    "mason-org/mason-lspconfig.nvim",
    { "WhoIsSethDaniel/mason-tool-installer.nvim" },
    { "j-hui/fidget.nvim", opts = {} },
  },
  config = function()
    -- K → 7k (override default hover)
    vim.keymap.set("n", "K", "7k", { noremap = true, nowait = true, desc = "Move up quickly" })

    -- LSP keymaps on attach
    vim.api.nvim_create_autocmd("LspAttach", {
      group = vim.api.nvim_create_augroup("custom-lsp-attach", { clear = true }),
      callback = function(event)
        local map = function(keys, func, desc, mode)
          mode = mode or "n"
          vim.keymap.set(mode, keys, func, { buffer = event.buf, noremap = true, nowait = true, desc = "LSP: " .. desc })
        end

        map("gi", vim.lsp.buf.implementation, "Go to implementation")
        map("gd", "<cmd>FzfLua lsp_definitions<cr>", "Go to definition")
        map("gs", "<cmd>FzfLua lsp_typedefs<cr>", "Go to type definition / super class")
        map("ga", "<cmd>FzfLua lsp_references<cr>", "Find all references")
        map("gh", vim.lsp.buf.hover, "Show hover documentation")

        map("<leader>rn", vim.lsp.buf.rename, "Rename symbol")
        map("<leader>.", "<cmd>FzfLua lsp_code_actions<cr>", "Code actions")
        map("ge", function() vim.diagnostic.jump({ count = 1 }) end, "Next diagnostic")
        map("gE", function() vim.diagnostic.jump({ count = -1 }) end, "Previous diagnostic")

        -- Highlight references on cursor hold
        local client = vim.lsp.get_client_by_id(event.data.client_id)
        if client and client:supports_method("textDocument/documentHighlight", event.buf) then
          local highlight_augroup = vim.api.nvim_create_augroup("lsp-highlight", { clear = false })
          vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
            buffer = event.buf,
            group = highlight_augroup,
            callback = vim.lsp.buf.document_highlight,
          })
          vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
            buffer = event.buf,
            group = highlight_augroup,
            callback = vim.lsp.buf.clear_references,
          })
          vim.api.nvim_create_autocmd("LspDetach", {
            group = vim.api.nvim_create_augroup("lsp-detach", { clear = true }),
            callback = function(event2)
              vim.lsp.buf.clear_references()
              vim.api.nvim_clear_autocmds({ group = "lsp-highlight", buffer = event2.buf })
            end,
          })
        end

        -- Toggle inlay hints
        if client and client:supports_method("textDocument/inlayHint", event.buf) then
          map("<leader>th", function()
            vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled({ bufnr = event.buf }))
          end, "Toggle inlay hints")
        end
      end,
    })

    -- Language servers
    ---@type table<string, vim.lsp.Config>
    local servers = {
      lua_ls = {
        on_init = function(client)
          if client.workspace_folders then
            local path = client.workspace_folders[1].name
            if
              path ~= vim.fn.stdpath("config")
              and (vim.uv.fs_stat(path .. "/.luarc.json") or vim.uv.fs_stat(path .. "/.luarc.jsonc"))
            then
              return
            end
          end
          client.config.settings.Lua = vim.tbl_deep_extend("force", client.config.settings.Lua, {
            runtime = {
              version = "LuaJIT",
              path = { "lua/?.lua", "lua/?/init.lua" },
            },
            workspace = {
              checkThirdParty = false,
              library = vim.tbl_extend("force", vim.api.nvim_get_runtime_file("", true), {
                "${3rd}/luv/library",
                "${3rd}/busted/library",
              }),
            },
          })
        end,
        settings = {
          Lua = {},
        },
      },
      -- Python
      pyright = {},

      -- Rust
      rust_analyzer = {
        settings = {
          ["rust-analyzer"] = {
            check = { command = "clippy" },
          },
        },
      },

      -- TypeScript / JavaScript
      ts_ls = {},

      -- Shell (bash/zsh)
      bashls = {},

      -- JSON
      jsonls = {
        settings = {
          json = {
            validate = { enable = true },
          },
        },
      },

      -- HTML (+ wxml 微信小程序模板)
      html = {
        filetypes = { "html", "wxml" },
      },

      -- CSS (+ wxss 微信小程序样式)
      cssls = {
        filetypes = { "css", "wxss" },
      },
    }

    -- Tools to install via Mason
    local ensure_installed = vim.tbl_keys(servers or {})
    vim.list_extend(ensure_installed, {
      "stylua",
      "ruff", -- Python linter/formatter
      "shfmt", -- Shell formatter
    })
    require("mason-tool-installer").setup({ ensure_installed = ensure_installed })
    require("mason-lspconfig").setup()

    -- Enable servers
    for name, server in pairs(servers) do
      vim.lsp.config(name, server)
    end
    vim.lsp.enable(vim.tbl_keys(servers))
  end,
}
