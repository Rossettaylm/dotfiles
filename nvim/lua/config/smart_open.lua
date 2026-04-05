-- 智能打开文件：已有 tab/window → 跳转，已有 buffer → 切换，否则 tabedit
local M = {}

---@param file string 文件路径
---@param line? number 行号
---@param col? number 列号
function M.open(file, line, col)
  local abs = vim.fn.fnamemodify(file, ":p")

  -- 1. 文件已在某个 tab/window 中 → 跳过去
  for _, tp in ipairs(vim.api.nvim_list_tabpages()) do
    for _, win in ipairs(vim.api.nvim_tabpage_list_wins(tp)) do
      if vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(win)) == abs then
        vim.api.nvim_set_current_tabpage(tp)
        vim.api.nvim_set_current_win(win)
        if line then
          vim.api.nvim_win_set_cursor(win, { line, (col or 1) - 1 })
        end
        return
      end
    end
  end

  -- 2. buffer 已加载但无 window → 切到该 buffer
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) and vim.api.nvim_buf_get_name(buf) == abs then
      vim.cmd("buffer " .. buf)
      if line then
        vim.api.nvim_win_set_cursor(0, { line, (col or 1) - 1 })
      end
      return
    end
  end

  -- 3. 全新文件 → 可替换的 buffer 直接覆盖，否则新 tab
  local ft = vim.bo.filetype
  local bufname = vim.api.nvim_buf_get_name(0)
  local disposable = ft == "dashboard" or ft == "alpha" or ft == "starter"
    or ft == "NvimTree" or ft == "neo-tree" or ft == "oil"
    or (bufname == "" and not vim.bo.modified)
  if disposable then
    vim.cmd("edit " .. vim.fn.fnameescape(file))
  else
    vim.cmd("tabedit " .. vim.fn.fnameescape(file))
  end
  if line then
    vim.api.nvim_win_set_cursor(0, { line, (col or 1) - 1 })
  end
end

return M
