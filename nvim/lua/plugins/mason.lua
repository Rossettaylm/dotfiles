return {
  {
    "mason.nvim",
    opts = {
      ensure_installed = {
        "stylua",
        "clang-format",
      },
    },
  },

  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = {
      "williamboman/mason.nvim",
      "neovim/nvim-lspconfig",
    },
  },
}
