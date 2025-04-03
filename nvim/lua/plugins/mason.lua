return {
  {
    "mason.nvim",
    opts = {
      ensure_installed = {
        "cmakelang",
        "cmakelint",
        "stylua",
        "clang-format",
        "black",
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
