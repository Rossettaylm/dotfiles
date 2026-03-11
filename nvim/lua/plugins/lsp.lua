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

      -- vim.keymap.set("n", "gd", vim.lsp.buf.definition, default_opts)
      -- vim.keymap.set("n", "gD", ":tab sp<CR><cmd>lua vim.lsp.buf.definition()<cr>", default_opts)
      vim.keymap.set("n", "gi", vim.lsp.buf.implementation, default_opts)
      vim.keymap.set("n", "gd", "<cmd>FzfLua lsp_definitions<cr>", default_opts)
      vim.keymap.set("n", "ga", "<cmd>FzfLua lsp_finder<cr>", default_opts)
      vim.keymap.set("n", "gh", vim.lsp.buf.hover, opts_with_desc("show hover documentation"))
      vim.keymap.set("i", "<c-f>", vim.lsp.buf.signature_help, default_opts)
      vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, default_opts)
      -- vim.keymap.set({ 'n', 'x' }, '<leader>f', function() vim.lsp.buf.format({ async = true }) end, opts)
      vim.keymap.set("n", "<leader>.", "<cmd>FzfLua lsp_code_actions<cr>", default_opts)
      -- vim.keymap.set('x', '<leader>aw', vim.lsp.buf.range_code_action, opts)
      -- vim.keymap.set('x', "<leader>,", vim.lsp.buf.range_code_action, opts)
      vim.keymap.set("n", "<leader>t", ":Trouble<cr>", default_opts)
      -- vim.keymap.set("n", "<leader>.", vim.lsp.buf.code_action, default_opts)
      vim.keymap.set("n", "ge", vim.diagnostic.goto_next, default_opts)
    end,
  })
end

local function removeKey(tlb, key)
  for i, v in ipairs(tlb) do
    if v[1] == key then
      table.remove(tlb, i)
    end
  end
end

return {
  "neovim/nvim-lspconfig",
  cond = not vim.g.vscode,
  init = function()
    F.configureKeybinds()
    local keys = require("lazyvim.plugins.lsp.keymaps").get()
    removeKey(keys, "K")
    local default_opts = { noremap = true, nowait = true, desc = "" }
    vim.keymap.set("n", "K", "7k", default_opts)
  end,
}
