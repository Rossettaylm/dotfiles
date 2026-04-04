-- =============================================
-- Autocommands
-- =============================================

vim.api.nvim_create_autocmd("TextYankPost", {
  desc = "Highlight when yanking text",
  group = vim.api.nvim_create_augroup("highlight-yank", { clear = true }),
  callback = function()
    vim.hl.on_yank()
  end,
})

-- Force [[ and ]] on every buffer to prevent ftplugin overrides
if not vim.g.vscode then
  vim.api.nvim_create_autocmd("BufEnter", {
    group = vim.api.nvim_create_augroup("force-jump-keymaps", { clear = true }),
    callback = function(event)
      vim.keymap.set("n", "[[", "<C-o>", { buffer = event.buf, noremap = true, desc = "Go back" })
      vim.keymap.set("n", "]]", "<C-i>", { buffer = event.buf, noremap = true, desc = "Go forward" })
    end,
  })
end
