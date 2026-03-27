return {
  "ojroques/nvim-osc52",
  cond = not vim.g.vscode,
  config = function()
    require("osc52").setup({
      max_length = 0, -- 不限制长度
      silent = true,  -- 不显示提示
      trim = false,
    })

    -- 覆盖系统剪贴板，使 "+y / "*y 都走 OSC 52
    local function copy(lines, _)
      require("osc52").copy(table.concat(lines, "\n"))
    end

    local function paste()
      return { vim.fn.split(vim.fn.getreg(""), "\n"), vim.fn.getregtype("") }
    end

    vim.g.clipboard = {
      name = "osc52",
      copy = { ["+"] = copy, ["*"] = copy },
      paste = { ["+"] = paste, ["*"] = paste },
    }
  end,
}
