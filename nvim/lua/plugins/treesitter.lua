return {
  "nvim-treesitter/nvim-treesitter",
  opts = {
    ensure_installed = {
      "bash",
      "c",
      "cpp",
      "json",
      "lua",
      "markdown",
      "cmake",
      "python",
      "regex",
      "vim",
      "yaml",
      "rust",
    },

    incremental_selection = {
      enable = true,
      keymaps = {
        init_selection = "<cr>",
        node_incremental = "<cr>",
        node_decremental = "<BS>",
      },
    },

    highlight = {
      enable = true,
      additional_vim_regex_highlighting = false,
    },

    indent = {
      enable = true,
    },
  },
}
