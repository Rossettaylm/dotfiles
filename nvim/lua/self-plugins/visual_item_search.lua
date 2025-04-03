-- 定义函数用于在 visual 模式下获取选中的文本并进行搜索
function SearchVisualSelection()
  -- 进入 normal 模式
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "nx", false)

  -- 获取 visual 模式的起始和结束位置
  local start_pos = vim.fn.getpos("'<")
  local end_pos = vim.fn.getpos("'>")

  -- 根据起始和结束位置获取选中的文本
  local text = vim.fn.join(vim.fn.getline(start_pos[2], end_pos[2]), "\n")

  if start_pos[2] == end_pos[2] then
    text = string.sub(text, start_pos[3], end_pos[3])
  else
    text = string.sub(text, start_pos[3]) .. "\n" .. string.sub(text, 1, end_pos[3])
  end

  -- 对特殊字符进行转义
  text = vim.pesc(text)

  -- 执行搜索
  vim.cmd("/" .. text)
end

-- 绑定 <leader>f 到上述函数
vim.keymap.set("v", "<leader>f", ":<C-u>call v:lua.SearchVisualSelection()<CR>")
