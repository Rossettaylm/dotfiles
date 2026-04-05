-- =============================================
-- 模糊搜索: fzf-lua (替代 Telescope)
-- =============================================
return {
  "ibhagwan/fzf-lua",
  cond = not vim.g.vscode,
  dependencies = {
    "nvim-tree/nvim-web-devicons",
  },
  cmd = "FzfLua",
  keys = {
    {
      "<leader>,",
      function()
        local root = vim.fs.root(0, ".git") or vim.uv.cwd()
        require("fzf-lua").files({ cwd = root })
      end,
      desc = "Find files (project root)",
    },
    { "<leader><leader>", "<cmd>FzfLua buffers<cr>", desc = "Find buffers" },
    { "<leader>v", "<cmd>FzfLua registers<cr>", desc = "Find registers" },
    { "<leader>sg", "<cmd>FzfLua live_grep<cr>", desc = "Search by grep" },
    { "<leader>sh", "<cmd>FzfLua help_tags<cr>", desc = "Search help" },
    { "<leader>sk", "<cmd>FzfLua keymaps<cr>", desc = "Search keymaps" },
    { "<leader>sd", "<cmd>FzfLua diagnostics_document<cr>", desc = "Search diagnostics" },
    { "<leader>sr", "<cmd>FzfLua resume<cr>", desc = "Search resume" },
    { "<leader>s.", "<cmd>FzfLua oldfiles<cr>", desc = "Search recent files" },
    { "<leader>sc", "<cmd>FzfLua commands<cr>", desc = "Search commands" },
    { "<leader>sw", "<cmd>FzfLua grep_cword<cr>", desc = "Search current word" },
    { "<leader>sb", "<cmd>FzfLua lgrep_curbuf<cr>", desc = "Search in current buffer" },
    { "<leader>ss", "<cmd>FzfLua builtin<cr>", desc = "Search fzf builtins" },
    { "<leader>st", "<cmd>TodoFzfLua<cr>", desc = "Search TODOs" },
    { "<leader>o", "<cmd>FzfLua lsp_document_symbols<cr>", desc = "Document symbols" },
    { "<leader>pa", "<cmd>FzfLua commands<cr>", desc = "Command palette" },
    { "/", "<cmd>FzfLua lgrep_curbuf<cr>", mode = "n", desc = "Search in current buffer" },
    { "?", "<cmd>FzfLua lgrep_curbuf<cr>", mode = "n", desc = "Search in current buffer" },
  },
  opts = function()
    local smart_action = function(selected, o)
      local smart = require("config.smart_open")
      local path = require("fzf-lua.path")
      for _, sel in ipairs(selected) do
        local entry = path.entry_to_file(sel, o)
        smart.open(entry.path, entry.line > 1 and entry.line or nil, entry.col > 1 and entry.col or nil)
      end
    end
    return {
      actions = {
        files = {
          ["default"] = smart_action,
        },
      },
      lsp = {
        jump1_action = smart_action,
      },
    }
  end,
}
