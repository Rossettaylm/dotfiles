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
  "neovim/nvim-lspconfig",
  init = function()
    F.configureKeybinds()
  end,
  opts = function()
    local keys = require("lazyvim.plugins.lsp.keymaps").get()
    keys[#keys + 1] = { "K", false }
  end,
}
