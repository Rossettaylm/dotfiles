-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

if vim.g.vscode then
  -- VSCode-specific keymaps and config
  require("config.vscode")
else
  -- 自定义插件（仅在原生 Neovim 中加载）
  require("self-plugins")
end
